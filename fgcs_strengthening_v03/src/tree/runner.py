"""One-identity LightGBM fit, locked validation selection and explicit evaluation."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import lightgbm
import numpy as np

from ..data_adapters import PARTITIONS, PreparedPartition
from ..diagnostics.engine import _SOURCES as _DIAGNOSTIC_SOURCES
from ..identity import CONFIG, RESOURCES, ROOT, canonical_json, read_config
from ..models.lightgbm import FeatureLayout, encode_booster, fit_horizon, score_native_horizon
from ..modern.runner import _SOURCES as _MODERN_SOURCES
from ..provenance import Fingerprints, Journal, ProvenanceError, measure_seconds, verify_file
from ..transfer.runner import _SOURCES as _TRANSFER_SOURCES
from .design import GRID, HORIZONS, dry_budget, inner_configuration, native_score, require_tree, select_configuration

_CONFIG = read_config()
_HOME = Path(__file__).resolve().parents[1]
_SOURCES = tuple((_HOME / name).relative_to(ROOT).as_posix() for name in ("tree/runner.py", "models/lightgbm.py"))


def lightgbm_fingerprints():
    return Fingerprints.capture_protocol(additional_sources=(
        *_DIAGNOSTIC_SOURCES, *_TRANSFER_SOURCES, *_MODERN_SOURCES, *_SOURCES))


def _metadata(identity, partition):
    if not isinstance(partition, PreparedPartition):
        raise TypeError("Expected a verified Stage 3A partition")
    if (partition.block, partition.entity, partition.fold, partition.phase) != (
            identity.block, identity.entity, identity.fold, identity.phase):
        raise ProvenanceError("LightGBM partition differs from the declared identity")
    if set(partition.split_hashes) != {name for pair in PARTITIONS.values() for name in pair}:
        raise ProvenanceError("Expected exact frozen split metadata")
    layout = FeatureLayout(partition.context, identity.tasks[0], identity.input_scope)
    source_sha = _CONFIG["blocks"][identity.block]["common_context_source"]["sha256"]
    context_sha = sha256(canonical_json([identity.block, identity.entity, identity.fold,
                                         partition.context, source_sha])).hexdigest()
    return layout, {"context": partition.context, "context_sha256": context_sha,
                    "context_source_sha256": source_sha, "support_sha256": partition.support_sha256,
                    "split_hashes": dict(partition.split_hashes), "scaler_sha256": partition.scaler_sha256,
                    "features": layout.payload(), "lightgbm_version": lightgbm.__version__}


def _arrays(windows, layout, *, native=False):
    features = layout.flatten(windows.inputs)
    targets = np.asarray(windows.native_targets if native else windows.targets)
    if targets.shape != (len(features), len(RESOURCES), len(HORIZONS)):
        raise ValueError("Expected a four-resource, five-horizon target tensor")
    y = targets[:, RESOURCES.index(layout.target), :]
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite LightGBM target")
    if np.ndim(windows.origin_ids) != 1 or len(windows.origin_ids) != len(features):
        raise ValueError("Origin support does not match the LightGBM windows")
    ids = np.asarray(windows.origin_ids).tolist()
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate LightGBM origin identity")
    return features, y, {"origins": len(ids), "ordered_origin_ids_sha256": sha256(canonical_json(ids)).hexdigest()}


class LightGBMRunner:
    """Fit exactly one declared wrapper or evaluate one completed final wrapper."""

    dry_budget = staticmethod(dry_budget)

    def __init__(self, journal):
        if not isinstance(journal, Journal):
            raise TypeError("Expected a Stage 3A journal")
        journal.seal.require_protocol(additional_sources=_SOURCES)
        verify_file(CONFIG, journal.seal.configuration[1])
        if read_config() != _CONFIG:
            raise ProvenanceError("LightGBM configuration changed after module import")
        self.journal = journal

    def fit_inner(self, identity, partition):
        config = inner_configuration(identity)
        return self._fit(identity, partition, config)

    def fit_final(self, identity, partition):
        require_tree(identity, "final")
        _, metadata = _metadata(identity, partition)
        config, selection = self._selection(identity, metadata)
        return self._fit(identity, partition, config, selection=selection)

    def _selection(self, identity, expected):
        scores, candidates = {}, []
        inner_partition = None
        for config in GRID:
            inner = replace(identity, phase="inner", variant=config.variant)
            observed, outcome_hash = self.journal.completed_evidence(inner)
            matching = ("context", "context_sha256", "context_source_sha256",
                        "split_hashes", "features", "lightgbm_version")
            if (any(observed.get(key) != expected[key] for key in matching)
                    or observed.get("configuration") != config.payload()
                    or observed.get("configuration_sha256") != self.journal.seal.configuration[1]
                    or observed.get("scalar_estimator_count") != len(HORIZONS)
                    or tuple(row["horizon"] for row in observed["models"]) != HORIZONS):
                raise ProvenanceError("Inner candidate differs from the exact frozen wrapper")
            partition = (observed["support_sha256"], observed["scaler_sha256"], observed["validation"]["support"])
            if inner_partition is None:
                inner_partition = partition
            if partition != inner_partition:
                raise ProvenanceError("Inner candidates do not share validation support and scaler")
            rows = observed["validation"]["horizons"]
            if tuple(row["horizon"] for row in rows) != HORIZONS:
                raise ProvenanceError("Incomplete or misordered inner horizon evidence")
            score = {row["horizon"]: row["native_mae"] for row in rows}
            if native_score(score) != observed["validation"]["selection_score"]:
                raise ProvenanceError("Inner selection score differs from native horizon MAEs")
            scores[config] = score
            candidates.append({"configuration": config.payload(), "inner_identity_sha256": inner.digest,
                               "inner_outcome_sha256": outcome_hash,
                               "selection_score": observed["validation"]["selection_score"],
                               "horizons": rows})
        selected = select_configuration(scores)
        return selected, {"selected": candidates[GRID.index(selected)], "candidates": candidates}

    def _fit(self, identity, partition, config, *, selection=None):
        layout, evidence = _metadata(identity, partition)
        evidence.update(configuration=config.payload(), configuration_sha256=self.journal.seal.configuration[1],
                        scalar_estimator_count=0, models=[])
        if selection is not None:
            evidence["selection"] = selection
        attempt = self.journal.start(identity)
        timings = evidence["timing_seconds"] = {}
        started = perf_counter()
        try:
            X, y, support = _arrays(partition.training(), layout)
            evidence["training_support"] = support
            if identity.phase == "inner":
                vX, vy, vsupport = _arrays(partition.validation(), layout, native=True)
                evidence["validation"] = {"support": vsupport, "horizons": []}
            for index, lead in enumerate(HORIZONS):
                evidence["active_horizon"] = lead
                with measure_seconds(timings, "primary_optimisation"):
                    estimator = fit_horizon(config, X, y[:, index], layout.names)
                booster = estimator.booster_
                if tuple(booster.feature_name()) != layout.names:
                    raise ProvenanceError("Fitted LightGBM feature order differs")
                with measure_seconds(timings, "checkpoint_serialization"):
                    encoded = encode_booster(booster)
                model = {"horizon": lead, "model_sha256": sha256(encoded).hexdigest(),
                         "realised_trees": booster.num_trees()}
                evidence["scalar_estimator_count"] += 1
                evidence["models"].append(model)
                parameters = {"estimator": estimator.get_params(deep=False), "native": booster.params}
                if evidence.setdefault("estimator_parameters", parameters) != parameters:
                    raise ProvenanceError("LightGBM parameter set changed across horizons")
                if identity.phase == "inner":
                    with measure_seconds(timings, "validation"):
                        metrics = score_native_horizon(partition, booster, vX, vy[:, index], layout.target)
                    evidence["validation"]["horizons"].append({"horizon": lead, **metrics})
                else:
                    with measure_seconds(timings, "checkpoint_io"):
                        model["artifact"] = self.journal.save_lightgbm_model(attempt, lead, encoded)
            if identity.phase == "inner":
                metrics = evidence["validation"]["horizons"]
                evidence["validation"]["selection_score"] = native_score({r["horizon"]: r["native_mae"] for r in metrics})
            evidence.pop("active_horizon")
        except Exception as error:
            timings["elapsed"] = perf_counter() - started
            evidence["error"] = {"type": type(error).__name__, "message": str(error)}
            self.journal.finish(attempt, status="failed", evidence=evidence)
            raise
        timings["elapsed"] = perf_counter() - started
        self.journal.finish(attempt, status="complete", evidence=evidence)
        return evidence

    def evaluate(self, identity, partition):
        """Read a verified completed final model, then materialise its test partition once."""
        require_tree(identity, "final")
        from ..evaluation import require_fits_closed
        require_fits_closed(self.journal)
        layout, evidence = _metadata(identity, partition)
        fitted, digest = self.journal.completed_evidence(identity)
        if (any(fitted.get(key) != value for key, value in evidence.items())
                or fitted.get("configuration_sha256") != self.journal.seal.configuration[1]):
            raise ProvenanceError("LightGBM evaluation partition or runtime differs from the final fit")
        evidence.update(final_outcome_sha256=digest, configuration=fitted["configuration"])
        attempt = self.journal.start(identity, evaluation=True)
        try:
            if (fitted["scalar_estimator_count"] != len(HORIZONS)
                    or tuple(row["horizon"] for row in fitted["models"]) != HORIZONS):
                raise ProvenanceError("Incomplete final scalar-model set")
            boosters = []
            for row in fitted["models"]:
                encoded = self.journal.lightgbm_model_bytes(identity, row["horizon"], row["artifact"])
                if sha256(encoded).hexdigest() != row["model_sha256"]:
                    raise ProvenanceError("Scalar model differs from the final model hash")
                booster = lightgbm.Booster(model_str=encoded.decode("utf-8"))
                if tuple(booster.feature_name()) != layout.names or booster.num_trees() != row["realised_trees"]:
                    raise ProvenanceError("Restored LightGBM model metadata differs")
                boosters.append(booster)
            X, y, support = _arrays(partition.outer_test(), layout, native=True)
            evidence["test_support"] = support
            common = {"environment": identity.block, "entity": identity.entity, "fold": identity.fold,
                      "target": layout.target, "input_scope": identity.input_scope, "model_identity": identity.digest,
                      "context": partition.context, "context_sha256": evidence["context_sha256"],
                      "context_source_sha256": evidence["context_source_sha256"],
                      "support_sha256": partition.support_sha256, "outer_test_sha256": partition.split_hashes["outer_test"],
                      "scaler_sha256": partition.scaler_sha256,
                      "ordered_test_ids_sha256": support["ordered_origin_ids_sha256"]}
            evidence["cells"] = [
                {**common, "horizon": lead, "scalar_model_sha256": row["model_sha256"],
                 **score_native_horizon(partition, booster, X, y[:, index], layout.target)}
                for index, (lead, row, booster) in enumerate(zip(HORIZONS, fitted["models"], boosters, strict=True))
            ]
        except Exception as error:
            evidence["error"] = {"type": type(error).__name__, "message": str(error)}
            self.journal.finish(attempt, status="failed", evidence=evidence)
            raise
        self.journal.finish(attempt, status="complete", evidence=evidence)
        return evidence["cells"]
