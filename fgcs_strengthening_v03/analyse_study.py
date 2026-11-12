"""Dry planning and explicit manifest-driven synthesis for v0.3.

A manifest declares mode (synthetic or scientific), provenance (protocol and
config SHA-256, source_hashes and input_hashes mappings), and artifacts (cells
and diagnostics, each with a relative path and SHA-256). Tables are JSON Lines
using the Cell and DiagnosticCell schemas. Scientific manifests require the
full sealed source/input inventory and complete coordinates, including explicit
failure/missing records. No result directory is discovered automatically.
"""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from .src.identity import CONFIG, ROOT
from .src.provenance import Fingerprints
from .src.statistics.design import BLOCKS, analysis_slots, expected_identity
from .src.statistics.endpoints import Cell
from .src.statistics.multiplicity import registered_families
from .src.statistics.schema import Provenance, is_sha256
from .src.statistics.synthesis import DiagnosticCell, ResultTable, analyse

_HOME = Path(__file__).resolve().parent
_SOURCES = tuple((_HOME / name).relative_to(ROOT).as_posix() for name in (
    "analyse_study.py", "src/statistics/design.py", "src/statistics/endpoints.py", "src/statistics/bootstrap.py",
    "src/statistics/mechanism.py", "src/statistics/multiplicity.py", "src/statistics/schema.py",
    "src/statistics/synthesis.py",
))


def _sources():
    from .src.diagnostics.engine import _SOURCES as diagnostics
    from .src.evaluation import _SOURCES as evaluation
    from .src.historical import _SOURCES as historical
    from .src.manifest_builder import _SOURCES as builder
    from .src.modern.runner import _SOURCES as modern
    from .src.transfer.runner import _SOURCES as transfer
    from .src.tree.runner import _SOURCES as tree

    return (*diagnostics, *evaluation, *historical, *builder, *modern, *transfer, *tree, *_SOURCES)


def analysis_fingerprints():
    return Fingerprints.capture_protocol(additional_sources=_sources())


def dry_plan(*, enumerate_slots=False):
    slots = tuple(analysis_slots())
    if len({slot.analysis_id for slot in slots}) != len(slots):
        raise RuntimeError("Duplicate planned analysis ID")
    families = registered_families()
    result = {
        "inference_slots": sum(map(len, families.values())),
        "holm_families": {name: len(items) for name, items in families.items() if items[0].correction == "Holm"},
        "bh_families": {name: len(items) for name, items in families.items() if items[0].correction == "BH"},
        "descriptive": dict(Counter(slot.estimand for slot in slots if not slot.inferential)),
        "total_rows": len(slots),
    }
    if enumerate_slots:
        result["slots"] = [asdict(slot) for slot in slots]
    return result


def _reject_constant(token):
    raise ValueError(f"Nonstandard JSON number {token}; use null with explicit status")


def _parse(value):
    return json.loads(value, parse_constant=_reject_constant)


def _records(base, reference, constructor, scientific, verified_inputs, frozen):
    relative = Path(reference["path"])
    path = (base / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(base) or not is_sha256(reference["sha256"]):
        raise ValueError("Expected an in-bundle artifact path and SHA-256")
    digest = sha256()
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            row = constructor(**_parse(line))
            if scientific:
                required = row.status != "missing" if isinstance(row, Cell) else row.K is not None
                if required and row.evidence_sha256 not in verified_inputs:
                    raise ValueError("Scientific result lacks a verified evidence artifact hash")
                if isinstance(row, Cell) and row.status == "ok":
                    identity = expected_identity(row)
                    if identity is not None and identity.digest != row.identity_sha256:
                        raise ValueError("Scientific cell differs from its exact registered model identity")
                    if (row.model not in {"M1-H129-v1", "S2-v1", "persistence"}
                            and row.context != frozen[row.block].get((row.entity, row.fold))):
                        raise ValueError("Scientific cell differs from its frozen common context")
                    hashes = (row.support_sha256, row.ordered_test_ids_sha256)
                    if row.model != "persistence":
                        hashes += (row.scaler_sha256,)
                    if not all(is_sha256(value) for value in hashes):
                        raise ValueError("Scientific row lacks exact support or scaler fingerprints")
                if isinstance(row, DiagnosticCell) and row.K is not None and row.identity_sha256 != row.identity().digest:
                    raise ValueError("Diagnostic value differs from its exact registered identity")
            yield row
    if digest.hexdigest() != reference["sha256"]:
        raise ValueError(f"Artifact SHA-256 mismatch: {relative}")


def load_bundle(manifest_path, *, mode=None):
    path = Path(manifest_path).resolve()
    manifest = _parse(path.read_bytes())
    actual_mode = manifest["mode"]
    if actual_mode not in {"scientific", "synthetic"} or (mode is not None and mode != actual_mode):
        raise ValueError("Explicit input mode and manifest mode differ")
    provenance = Provenance(**manifest["provenance"])
    scientific = actual_mode == "scientific"
    frozen = {}
    if scientific:
        seal = Fingerprints((CONFIG.relative_to(ROOT).as_posix(), provenance.config_sha256),
                            tuple(provenance.input_hashes.items()), tuple(provenance.source_hashes.items()))
        seal.require_protocol(additional_sources=_sources())
        if dict(seal.inputs).get("review_revision/fgcs_strengthening/analysis_plan_v0.3.md") != provenance.protocol_sha256:
            raise ValueError("Scientific manifest has the wrong protocol fingerprint")
        seal.verify()
        from .src.data_adapters import frozen_contexts
        frozen = {block: frozen_contexts(block) for block in BLOCKS}
    artifacts = manifest["artifacts"]
    if set(artifacts) != {"cells", "diagnostics"}:
        raise ValueError("A bundle must declare both normalised tables")
    verified_inputs = set(provenance.input_hashes.values())
    table = ResultTable(*(
        _records(path.parent, artifacts[key], constructor, scientific, verified_inputs, frozen)
        for key, constructor in (("cells", Cell), ("diagnostics", DiagnosticCell))
    ))
    table.validate_domains(complete=scientific)
    provenance = Provenance(provenance.protocol_sha256, provenance.config_sha256, dict(provenance.source_hashes),
                            {**provenance.input_hashes, **{f"bundle:{key}": ref["sha256"] for key, ref in artifacts.items()}})
    return table, provenance, actual_mode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="summarise the frozen analysis plan")
    modes.add_argument("--enumerate", action="store_true", help="emit each planned slot without reading results")
    modes.add_argument("--validate", type=Path, help="validate an explicit manifest without computing statistics")
    modes.add_argument("--synthetic-input", type=Path, help="analyse a generated manifest")
    modes.add_argument("--scientific-input", type=Path, help="analyse an explicitly supplied complete scientific manifest")
    args = parser.parse_args(argv)
    if args.validate is not None:
        _, provenance, mode = load_bundle(args.validate)
        output = {"status": "validated", "mode": mode, "provenance": provenance.payload()}
    elif args.synthetic_input is not None or args.scientific_input is not None:
        mode = "synthetic" if args.synthetic_input else "scientific"
        table, provenance, _ = load_bundle(args.synthetic_input or args.scientific_input, mode=mode)
        output = {"mode": mode, "provenance": provenance.payload(),
                  "rows": [row.payload() for row in analyse(table, provenance)]}
    else:
        output = dry_plan(enumerate_slots=args.enumerate)
    json.dump(output, sys.stdout, allow_nan=False)
    print()


if __name__ == "__main__":
    main()
