"""One outer-test evaluation path for every neural final identity. Nothing runs on import."""

from dataclasses import replace
from hashlib import sha256
import io
import json
from pathlib import Path

import numpy as np
import torch

from .data_adapters import PreparedPartition
from .identity import RESOURCES, ROOT, ScientificIdentity, canonical_json, read_config
from .models.lstm import LSTM
from .models.registry import REGISTRY
from .provenance import Journal, ProvenanceError
from .training import _state_hash, _windows, cpu_seed_scope
from .transfer.estimands import NativeMAECell

_CONFIG = read_config()
_SOURCES = (Path(__file__).resolve().relative_to(ROOT).as_posix(),)
FIT_CLOSURE_PHASES = ("certify", "canary", "inner", "final", "diagnostics")
NEURAL_ARMS = frozenset({"core", "capacity", "pcgrad", "gradnorm", "pairwise", "leave_one_out", "modern",
                         "checkpoint_request"})


def _digest(value):
    return sha256(canonical_json(value)).hexdigest()


def prediction_sha256(values):
    return sha256(np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")).hexdigest()


def require_fits_closed(journal):
    """C6: outer-test data are readable only after the orchestrator has closed every fit phase."""
    path = journal._path("orchestrator", "gates", "fits.json")
    try:
        record = json.loads(path.read_text())
    except FileNotFoundError:
        raise ProvenanceError("Outer-test evaluation requires the closed fit phases (C6)") from None
    if record.get("gate") != "fits" or not set(FIT_CLOSURE_PHASES) <= set(record.get("phases", ())):
        raise ProvenanceError("The fit-closure record does not cover every fit phase (C6)")


def evaluation_source(identity):
    """The final fit whose checkpoint a deployment evaluates."""
    if identity.arm == "checkpoint_request":
        return replace(identity, arm="core", tasks=RESOURCES, variant="baseline")
    return identity


def _require(identity, partition):
    if (not isinstance(identity, ScientificIdentity) or identity.phase != "final"
            or identity.arm not in NEURAL_ARMS):
        raise ValueError("Expected a final neural deployment identity")
    if not isinstance(partition, PreparedPartition) or (
            partition.block, partition.entity, partition.fold, partition.phase
    ) != (identity.block, identity.entity, identity.fold, "final"):
        raise ProvenanceError("Expected the final partition for this exact identity")


def _model(source, context):
    if source.arm == "modern":
        return REGISTRY[source.formulation].build(context, source.tasks)
    return LSTM(formulation=source.formulation, block=source.block, tasks=source.tasks,
                hidden_size=source.hidden_size)


class OuterEvaluator:
    """Materialise one final partition's outer test once per deployment, after the full trajectory."""

    def __init__(self, journal):
        if not isinstance(journal, Journal):
            raise TypeError("Expected a Stage 3A journal")
        journal.seal.require_protocol(additional_sources=_SOURCES)
        self.journal = journal

    def evaluate(self, identity, partition):
        _require(identity, partition)
        require_fits_closed(self.journal)
        source = evaluation_source(identity)
        final, final_hash = self.journal.completed_evidence(source)
        metadata = {"context": partition.context, "support_sha256": partition.support_sha256,
                    "split_hashes": dict(partition.split_hashes), "scaler_sha256": partition.scaler_sha256,
                    "configuration_sha256": self.journal.seal.configuration[1]}
        if any(final.get(name) != value for name, value in metadata.items()):
            raise ProvenanceError("Evaluation partition differs from the final fit")
        evidence = {**metadata, "final_outcome_sha256": final_hash, "source_identity_sha256": source.digest}
        attempt = self.journal.start(identity, evaluation=True, source=None if source == identity else source)
        try:
            selection = final["selection"]
            if (final.get("primary_checkpoint_epoch") != selection["joint_epoch"]
                    or len(final["epochs"]) != selection["final_epoch"]):
                raise ProvenanceError("Final trajectory or primary checkpoint is incomplete")
            if identity.arm == "checkpoint_request":
                epoch = selection["task_epochs"][identity.tasks[0]]
            else:
                epoch = selection["joint_epoch"]
            reference = final["checkpoints"][str(epoch)]
            evidence.update(evaluated_epoch=epoch, checkpoint=reference)
            encoded = self.journal.checkpoint_bytes(source, epoch, reference)
            state = torch.load(io.BytesIO(encoded), map_location="cpu", weights_only=True)
            if _state_hash(state) != reference["model_sha256"]:
                raise ProvenanceError("Evaluation checkpoint tensor hash differs from the fit record")
            with cpu_seed_scope(identity.seed), torch.inference_mode():
                model = _model(source, partition.context)
                model.load_state_dict(state, strict=True)
                model.eval()
                self._score(model, identity, source, partition, evidence)
        except Exception as error:
            evidence.pop("cells", None)
            evidence["error"] = {"type": type(error).__name__, "message": str(error)}
            self.journal.finish(attempt, status="failed", evidence=evidence)
            raise
        self.journal.finish(attempt, status="complete", evidence=evidence)
        return evidence

    @staticmethod
    def _score(model, identity, source, partition, evidence):
        windows = partition.outer_test()
        inputs, _ = _windows(windows, source, partition.context)
        if source.arm == "modern" and source.input_scope == "own" and source.variant == "independent":
            index = RESOURCES.index(source.tasks[0])
            inputs = inputs[:, :, index:index + 1]
        ids = np.asarray(windows.origin_ids).tolist()
        if len(ids) != len(set(ids)):
            raise ProvenanceError("Duplicate outer-test origin ID")
        evidence["ordered_test_ids_sha256"] = _digest(ids)
        evidence["test_origins"] = len(ids)
        native = None if windows.native_targets is None else np.asarray(windows.native_targets, dtype=np.float64)
        if native is None or native.shape != windows.targets.shape or not np.isfinite(native).all():
            raise ValueError("Invalid native outer-test targets")
        batch_size = _CONFIG["lstm"]["batch_size"]
        scaled = torch.cat([model(batch) for batch in inputs.split(batch_size)]).numpy()
        horizons = _CONFIG["blocks"][identity.block]["horizons"]
        if scaled.shape != (len(ids), len(source.tasks), len(horizons)) or not np.isfinite(scaled).all():
            raise ValueError("Invalid scaled outer-test predictions")
        rows, predictions = [], {}
        for task in identity.tasks:
            column = scaled[:, source.tasks.index(task)]
            predicted, fraction, _ = partition.inverse_target(column, task)
            predicted = np.asarray(predicted, dtype=np.float64)
            actual = native[:, RESOURCES.index(task)]
            if predicted.shape != actual.shape or not np.isfinite(predicted).all() or not np.isfinite(fraction):
                raise ValueError("Invalid native outer-test predictions")
            mae = np.mean(np.abs(predicted - actual), axis=0)
            if not np.isfinite(mae).all():
                raise ValueError("Nonfinite native MAE")
            predictions[task] = {"scaled_prediction_sha256": prediction_sha256(column),
                                 "native_prediction_sha256": prediction_sha256(predicted),
                                 "projected_fraction": float(fraction)}
            rows.extend({"target": task, "horizon": lead, "mae": float(value)}
                        for lead, value in zip(horizons, mae, strict=True))
        evidence["predictions"] = predictions
        evidence["cells"] = rows

    def completed_cells(self, identity):
        """Typed estimand inputs from an authenticated evaluation still bound to its final fit."""
        if not isinstance(identity, ScientificIdentity) or identity.arm not in NEURAL_ARMS:
            raise ValueError("Expected a neural deployment identity")
        observed, _ = self.journal.completed_evidence(identity, evaluation=True)
        _, final_hash = self.journal.completed_evidence(evaluation_source(identity))
        if observed["final_outcome_sha256"] != final_hash:
            raise ProvenanceError("Evaluation no longer matches its final-fit outcome")
        return tuple(NativeMAECell(
            identity, row["target"], row["horizon"], row["mae"], observed["context"],
            observed["support_sha256"], observed["scaler_sha256"], observed["ordered_test_ids_sha256"])
            for row in observed["cells"])
