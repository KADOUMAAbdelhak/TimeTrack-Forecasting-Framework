"""Build or verify the v0.3 registration package. Reads no data values and no results.

    python -m fgcs_strengthening_v03.build_registration --build
    python -m fgcs_strengthening_v03.build_registration --verify

The package lives in fgcs_strengthening_v03/registration/. Every generated file and every referenced
repository file is listed with its SHA-256 in PACKAGE.json, whose own digest is the package digest.
"""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import sys

from .src.identity import HOME, ROOT, canonical_json

PACKAGE = HOME / "registration"
REFERENCES = (
    "review_revision/fgcs_strengthening/analysis_plan_v0.3.md",
    "fgcs_strengthening_v03/configs/protocol_v03.json",
    "fgcs_strengthening_v03/configs/historical_results_v03.json",
    "fgcs_strengthening_v03/STAGE03J_CLARIFICATIONS_DRAFT.md",
    "fgcs_strengthening_v03/STAGE03J_SCOPE.md",
    "fgcs_strengthening_v03/feasibility/estimate.json",
)
DECISIONS = {
    "date": "2026-11-12",
    "clarifications": "C1-C9 approved by the author; revision 2 after the independent audit (D1-D5, C6 note)",
    "training_workers": 4,
    "training_cost_concurrency": "C4 declared departure from the §9 one-worker condition for training-cost seconds",
    "origins": "C1 per partition",
    "systems_population": "C2 seed 0, fold 1, every entity",
    "retry_policy": "C3 two infrastructure retries; code repairs by chained seal amendment",
}


def _sha(data):
    return sha256(data).hexdigest()


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def generated():
    """Deterministic package contents, recomputed from the repository."""
    from .analyse_study import dry_plan
    from .plan_execution import fit_identities, overhead_identities, validate_schedule
    from .src.historical import load_manifest
    from .src.manifest_builder import HISTORICAL_MODELS, _blank, required_coordinates
    from .src.modern.design import pilot_identities
    from .src.orchestrator import (PHASES, Schedule, canary_identities, execution_fingerprints,
                                   registered_schedule, systems_population)
    from .src.statistics.design import expected_identity

    seal = execution_fingerprints()
    schedule = Schedule(registered_schedule())
    identities = sorted({unit.digest for unit in (*fit_identities(), *overhead_identities())})
    evaluations = sorted({expected_identity(_blank(c)).digest for c in required_coordinates()
                          if c[0] not in HISTORICAL_MODELS})
    cells = sum(1 for _ in required_coordinates())
    population = [{"partition": list(partition), "deployments": [[unit.digest for unit in deployment]
                                                                 for deployment in deployments]}
                  for partition, deployments in systems_population()]
    return {
        "execution_seal.json": {"digest": seal.digest, **seal.payload(),
                                "note": "single runtime seal: execution_fingerprints() (C9)"},
        "schedule.json": {
            "schedule_sha256": schedule.digest, "units": len(schedule.units),
            "phases": {phase: len(schedule.phase(phase)) for phase in PHASES},
            "budget": validate_schedule(), "identity_count": len(identities),
            "identity_list_sha256": _sha(canonical_json(identities)),
            "canary": [unit.payload() for unit in canary_identities()],
            "modern_pilots": [unit.payload() for unit in pilot_identities()],
        },
        "analysis_catalogue.json": {
            **dry_plan(enumerate_slots=True), "required_cells": cells,
            "evaluation_identity_count": len(evaluations),
            "evaluation_identity_list_sha256": _sha(canonical_json(evaluations)),
            "historical_tables": load_manifest()["tables"],
        },
        "systems_population.json": {"partitions": len(population),
                                    "deployments": sum(len(p["deployments"]) for p in population),
                                    "population": population},
    }


def package_record(files):
    from .src.systems_environment import MachineManifest

    host = MachineManifest.from_file(PACKAGE / "host_manifest.json")
    hardware = asdict(host.hardware)
    hardware.pop("hostname")
    listed = {**{name: _sha(content) for name, content in files.items()},
              "host_manifest.json": _sha((PACKAGE / "host_manifest.json").read_bytes())}
    return {
        "package": "fgcs-v03 registration package",
        "protocol": "review_revision/fgcs_strengthening/analysis_plan_v0.3.md",
        "generated_files": dict(sorted(listed.items())),
        "referenced_files": {path: _sha((ROOT / path).read_bytes()) for path in REFERENCES},
        "host": {"hardware_sha256": host.hardware_sha256, "software_sha256": host.software_sha256,
                 "hardware_without_hostname": hardware, "software_versions": {
                     key: value for key, value in asdict(host.software).items() if key != "blas_backend"},
                 "conditions": asdict(host.conditions)},
        "author_decisions": DECISIONS,
        "status": {"v0.3_author_approval": "to be confirmed by the author before external registration",
                   "external_registration": "not performed (author action)",
                   "scientific_execution": "none; the runtime journal is created at the start of Stage 4A"},
    }


def build():
    files = {name: _json(value) for name, value in generated().items()}
    for name, content in files.items():
        with (PACKAGE / name).open("xb") as stream:
            stream.write(content)
    record = package_record(files)
    digest = _sha(canonical_json(record))
    with (PACKAGE / "PACKAGE.json").open("xb") as stream:
        stream.write(_json({**record, "package_sha256": digest}))
    return digest


def verify():
    stored = json.loads((PACKAGE / "PACKAGE.json").read_text())
    digest = stored.pop("package_sha256")
    files = {name: _json(value) for name, value in generated().items()}
    problems = [name for name, content in files.items() if (PACKAGE / name).read_bytes() != content]
    record = package_record(files)
    if record != stored:
        problems.append("PACKAGE.json content")
    if _sha(canonical_json(stored)) != digest:
        problems.append("package digest")
    return digest, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if args.build:
        print(json.dumps({"package_sha256": build()}))
        return
    digest, problems = verify()
    print(json.dumps({"package_sha256": digest, "verified": not problems, "problems": problems}))
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
