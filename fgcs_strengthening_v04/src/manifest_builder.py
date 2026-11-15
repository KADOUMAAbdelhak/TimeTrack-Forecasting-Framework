"""Build the scientific cells/diagnostics bundle from a closed journal. Nothing runs on import.

This is the only code that reads outer-test MAEs in bulk. It requires the orchestrator's fit and
evaluation closure records, and refuses to run while any registered identity lacks a terminal record,
unless the matching closure record lists that identity as abandoned (C6).
"""

from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

from .evaluation import FIT_CLOSURE_PHASES, evaluation_source
from .historical import HistoricalReader
from .identity import ROOT, canonical_json, read_config
from .provenance import Journal, ProvenanceError
from .statistics.design import CORE, FOLDS, TRACES, analysis_slots, cohort_for, expected_identity, model_slices
from .statistics.endpoints import Cell
from .statistics.schema import Provenance
from .statistics.synthesis import DiagnosticCell

_CONFIG = read_config()
_SOURCES = (Path(__file__).resolve().relative_to(ROOT).as_posix(),)
HISTORICAL_MODELS = frozenset({"persistence", "S2-v1", "M1-H64-v1", "S2-common-v1", "M1-H129-v1",
                               "Ridge-AR", "Ridge-ARX"})
DIAGNOSTIC_BLOCKS = ("fastStorage", "Rnd", *TRACES)


def _seed_key(seed):
    return -1 if seed is None else seed


def required_coordinates():
    """Every (model, block, entity, resource, fold, horizon, seed) cell the registered catalogue reads."""
    expected = defaultdict(set)
    for slot in analysis_slots():
        for (model, seeds), block, entity in product(model_slices(slot), slot.blocks, slot.cohort):
            expected[model, block, entity, slot.resource].update(seeds)
    for (model, block, entity, resource), seeds in sorted(expected.items()):
        horizons = _CONFIG["blocks"][block]["horizons"]
        for fold, horizon, seed in product(FOLDS, horizons, sorted(seeds, key=_seed_key)):
            yield model, block, entity, resource, fold, horizon, seed


def _blank(coordinate, status="missing", evidence=None, identity=None):
    return Cell(*coordinate, None, None, None, None, None, status, evidence, identity)


class ScheduleNotClosed(ProvenanceError):
    """A registered identity has neither a terminal record nor an explicit abandonment."""


def _closure(journal, name, phases):
    path = journal._path("orchestrator", "gates", f"{name}.json")
    try:
        record = json.loads(path.read_text())
    except FileNotFoundError:
        raise ScheduleNotClosed(f"The bundle requires the {name} closure record (C6)") from None
    if record.get("gate") != name or not set(phases) <= set(record.get("phases", ())):
        raise ScheduleNotClosed(f"The {name} closure record does not cover {', '.join(phases)}")
    try:
        outcomes = json.loads(path.with_name(f"{name}.outcomes.json").read_text())
    except FileNotFoundError:
        raise ScheduleNotClosed(f"The {name} closure lacks its outcome map") from None
    if sha256(canonical_json(outcomes)).hexdigest() != record.get("outcomes_sha256"):
        raise ProvenanceError(f"The {name} outcome map differs from its closure record")
    abandoned = set(record.get("abandoned_identity_sha256", ()))
    if any(outcomes.get(digest, "") is not None for digest in abandoned):
        raise ProvenanceError(f"The {name} closure lists an abandoned identity that has an outcome")
    return record, outcomes


class BundleBuilder:
    def __init__(self, journal, historical):
        if not isinstance(journal, Journal) or not isinstance(historical, HistoricalReader):
            raise TypeError("Expected a sealed journal and the registered historical reader")
        from ..analyse_study import _sources

        journal.seal.require_protocol(additional_sources=(*_sources(), *_SOURCES))
        self.journal, self.historical = journal, historical
        self.inputs = {}
        self._evaluations = {}

    def _abandoned(self):
        """Abandoned fit and evaluation identities, read only from the closure records."""
        if not hasattr(self, "_closed"):
            fits, fit_outcomes = _closure(self.journal, "fits", FIT_CLOSURE_PHASES)
            evaluations, evaluation_outcomes = _closure(self.journal, "evaluation", ("systems", "evaluation"))
            if fits.get("schedule_sha256") != evaluations.get("schedule_sha256"):
                raise ScheduleNotClosed("Fit and evaluation closures belong to different schedules")
            self._closed = {False: (frozenset(fits.get("abandoned_identity_sha256", ())), fit_outcomes),
                            True: (frozenset(evaluations.get("abandoned_identity_sha256", ())), evaluation_outcomes)}
        return self._closed

    def _record(self, identity, *, evaluation=False):
        """(status, evidence, file hash) or None when no terminal record exists.

        Every record must be exactly the one its closure recorded: an identity outside the closure, an
        outcome created, removed or changed after closure, all stop the bundle (C6).
        """
        abandoned, closed = self._abandoned()[evaluation]
        if identity.digest not in closed:
            raise ScheduleNotClosed(f"Registered identity is not in its closure record: {identity.digest}")
        path = self.journal._record_path("outcomes", identity, evaluation)
        if not path.exists():
            if closed[identity.digest] is None and identity.digest in abandoned:
                return None
            if closed[identity.digest] is not None:
                raise ProvenanceError(f"A closed outcome was removed after closure: {identity.digest}")
            raise ScheduleNotClosed(f"Registered identity has no terminal record: {identity.digest}")
        status, evidence, digest = self.journal.terminal_evidence(identity, evaluation=evaluation)
        if digest != closed[identity.digest]:
            raise ProvenanceError(f"Outcome differs from its closure record: {identity.digest}")
        self.inputs[path.relative_to(ROOT).as_posix()] = digest
        return status, evidence, digest

    def _evaluation(self, identity):
        if identity.digest in self._evaluations:
            return self._evaluations[identity.digest]
        source = evaluation_source(identity)
        fit = self._record(source)
        if fit is None:
            result = ("missing", None, {})
        elif fit[0] != "complete":
            result = ("failed", fit[2], {})
        else:
            evaluation = self._record(identity, evaluation=True)
            if evaluation is None:
                result = ("missing", None, {})
            elif evaluation[0] != "complete":
                message = evaluation[1].get("error", {}).get("message", "")
                nonfinite = "onfinite" in message or "Invalid native outer-test predictions" in message
                result = ("nonfinite_prediction" if nonfinite else "failed", evaluation[2], {})
            else:
                _, evidence, digest = evaluation
                if evidence["final_outcome_sha256"] != fit[2]:
                    raise ProvenanceError("Evaluation no longer matches its final-fit outcome")
                rows = {}
                for row in evidence["cells"]:
                    target = row.get("target", identity.tasks[0])
                    mae = row["mae"] if "mae" in row else row["native_mae"]
                    key = target, row["horizon"]
                    if key in rows:
                        raise ProvenanceError("Duplicate evaluated cell")
                    rows[key] = mae
                ordered = evidence.get("ordered_test_ids_sha256") or evidence["test_support"]["ordered_origin_ids_sha256"]
                meta = (evidence["context"], evidence["support_sha256"], evidence["scaler_sha256"], ordered)
                result = ("ok", digest, {"rows": rows, "meta": meta})
        self._evaluations[identity.digest] = result
        return result

    def _new_cell(self, coordinate):
        identity = expected_identity(_blank(coordinate))
        if identity is None:
            raise ProvenanceError(f"No registered identity for model {coordinate[0]}")
        status, evidence, payload = self._evaluation(identity)
        if status != "ok":
            return _blank(coordinate, status, evidence, identity.digest)
        _, _, _, resource, _, horizon, _ = coordinate
        try:
            mae = payload["rows"][resource, horizon]
        except KeyError:
            raise ProvenanceError("Evaluation lacks a registered target/horizon cell") from None
        context, support, scaler, ordered = payload["meta"]
        return Cell(*coordinate, mae, context, support, scaler, ordered, "ok", evidence, identity.digest)

    def cells(self, coordinates=None):
        historical = {(c.model, c.block, c.entity, c.resource, c.fold, c.horizon, c.seed): c
                      for c in self.historical.cells()}
        self.inputs.update(self.historical.input_hashes())
        for coordinate in (required_coordinates() if coordinates is None else coordinates):
            if coordinate[0] in HISTORICAL_MODELS:
                yield historical.get(tuple(coordinate)) or _blank(coordinate)
            else:
                yield self._new_cell(tuple(coordinate))

    def diagnostics(self, keys=None):
        if keys is None:
            keys = ((block, entity, fold, seed) for block in DIAGNOSTIC_BLOCKS for entity in cohort_for(block)
                    for fold, seed in product(FOLDS, CORE))
        for block, entity, fold, seed in keys:
            row = DiagnosticCell(block, entity, fold, seed, None)
            identity = row.identity()
            record = self._record(identity)
            if record is None:
                yield row
                continue
            status, evidence, digest = record
            value = evidence.get("primary_K") if status == "complete" else None
            yield DiagnosticCell(block, entity, fold, seed, value, evidence_sha256=digest,
                                 identity_sha256=identity.digest)

    def build(self, directory, *, coordinates=None, diagnostic_keys=None):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        artifacts = {}
        for name, rows in (("cells", self.cells(coordinates)), ("diagnostics", self.diagnostics(diagnostic_keys))):
            path = directory / f"{name}.jsonl"
            digest = sha256()
            with path.open("xb") as stream:
                for row in rows:
                    line = json.dumps(asdict(row), sort_keys=True, allow_nan=False).encode() + b"\n"
                    stream.write(line)
                    digest.update(line)
            artifacts[name] = {"path": path.name, "sha256": digest.hexdigest()}
        seal = self.journal.seal
        inputs = dict(seal.inputs)
        protocol = inputs[_CONFIG["protocol"]["path"]]
        provenance = Provenance(protocol, seal.configuration[1], dict(seal.sources), {**inputs, **self.inputs})
        manifest = {"mode": "scientific", "artifacts": artifacts,
                    "provenance": {"protocol_sha256": provenance.protocol_sha256,
                                   "config_sha256": provenance.config_sha256,
                                   "source_hashes": dict(provenance.source_hashes),
                                   "input_hashes": dict(provenance.input_hashes)}}
        path = directory / "manifest.json"
        with path.open("xb") as stream:
            stream.write(canonical_json(manifest) + b"\n")
        return path
