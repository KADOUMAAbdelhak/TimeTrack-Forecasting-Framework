"""Build or verify the frozen package of v0.4 amendment A2. Reads no data values and no results.

    python -m fgcs_strengthening_v04a2.host capture --out fgcs_strengthening_v04a2/registration/host_manifest.json
    python -m fgcs_strengthening_v04a2.build_registration --build
    python -m fgcs_strengthening_v04a2.build_registration --verify

The package lives in fgcs_strengthening_v04a2/registration/. Every generated file and every referenced
repository file is listed with its SHA-256 in PACKAGE.json, whose own digest is the package digest.
The host manifest is captured first, in a single-threaded worker environment (host.py).

--build refuses while the v0.4 protocol or the A2 amendment is still a draft, and never overwrites an
existing package. It also
writes REGISTRATION_EVIDENCE_TEMPLATE.md with EXECUTION_UNLOCKED = NO; that file is outside the package
digest because the author changes it to authorise execution.

Freezing is Git-based (protocol P9, deviation D1): after a build, the package is committed and the commit
gets the annotated tag launch.TAG (fgcs-v04-a2-residual). The launcher reads the commit, package digest
and seal from that tag. No external registration is made for A2, as for v0.4 (D1).
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from .src.identity import HOME, ROOT, canonical_json, read_config

PACKAGE = HOME / "registration"
GENERATED = ("execution_seal.json", "schedule.json", "analysis_catalogue.json")
DECISIONS = {
    "protocol": "v0.4 amendment A2: forecasts parameterised as the last observed value plus a learned change, for "
                "the tier-2 2x2 of all four backbones; post hoc, tier 2, descriptive, no confirmatory tests",
    "approval": "A2 approved by the authors as written on 2026-11-19, all four section 9 decisions as recommended",
    "architecture": "derived package fgcs_strengthening_v04a2 (from tag fgcs-v04-a1-intervention) with its own "
                    "namespace, runtime, seal and tag: the closed v0.4 and A1 journals accept no new fits (C6); "
                    "tier-2 references and v1 persistence are read read-only",
    "freezing": "Git-based, as v0.4 (P9, D1): annotated tag fgcs-v04-a2-residual on the package commit, with this "
                "package digest and execution seal; no external registration",
    "predecessor": {"tag": "fgcs-v04-a1-intervention", "commit": "7660bde98cb4f47d51226877b8f8c8235d1b9201",
                    "package_sha256": "416c4bb6bd9fd824da39822340b057073dfa9a900bf240ecaae3d71a66919f04",
                    "execution_seal": "ab38ce94677b49e96faae758afd9ddbacd3c33dd5e5ca18d1300fc5d7f88ed7a"},
    "training_workers": 6,
    "canary": "3 modern structural certificates, then 70 inner fits: first cohort VM per block, fold 1, seed 0, "
              "every A2 cell of every backbone",
    "retry_policy": "v0.3 C3: two infrastructure retries; code repairs only by chained seal amendment",
    "blinding": "v0.3 C6: no outer-test data before fit closure",
    "inputs": "byte-identical to the sealed v0.3/v0.4 inputs (Zenodo 10.5281/zenodo.24189108 plus tracked inputs)",
}
EVIDENCE_TEMPLATE = """# v0.4 amendment A2 execution authorisation

A2 is frozen by Git, as v0.4 (protocol P9, deviation D1): the annotated tag fgcs-v04-a2-residual, its
package digest and its execution seal. No external registration is made.

Before changing the line below to YES, run `python -m fgcs_strengthening_v04a2.launch preflight` and record
here its output (tag object, commit, package, seal, host check), the date and your decision. This file is
the only tracked A2 file the launcher allows to differ from the tag.

EXECUTION_UNLOCKED = NO
"""


class RegistrationRefused(RuntimeError):
    """A precondition failed; nothing was written."""


def _sha(data):
    return sha256(data).hexdigest()


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def protocol_path():
    return read_config()["protocol"]["path"]


def require_frozen_protocol(path=None):
    """A package may only be built from frozen protocols: no DRAFT name or 'Not frozen' status.

    Without a path, both the v0.4 protocol and the A2 amendment are checked.
    """
    for path in (path,) if path else (protocol_path(), read_config()["amendment"]["path"]):
        text = (ROOT / path).read_text()
        head = "\n".join(text.splitlines()[:5])
        if "DRAFT" in Path(path).name or "DRAFT" in head or "Not frozen" in head:
            raise RegistrationRefused(f"The protocol is still a draft: {path}")


def references():
    """Repository files the package pins (beyond everything the execution seal already covers)."""
    from .src.analysis.historical import MANIFEST

    config = read_config()
    for name in ("protocol", "amendment"):
        if _sha((ROOT / config[name]["path"]).read_bytes()) != config[name]["sha256"]:
            raise RegistrationRefused(f"The configuration's {name} hash differs from the {name} file")
    return (config["protocol"]["path"], config["amendment"]["path"],
            "fgcs_strengthening_v04a2/configs/protocol_v04a2.json", MANIFEST.relative_to(ROOT).as_posix())


def generated():
    """Deterministic package contents, recomputed from the repository."""
    from .analyse_residual import FORMAT, dry_plan
    from .plan_execution import fit_identities, overhead_identities, validate_schedule
    from .src.analysis.collect import final_identities
    from .src.orchestrator import PHASES, Schedule, canary_identities, execution_fingerprints, registered_schedule

    seal = execution_fingerprints()
    schedule = Schedule(registered_schedule())
    identities = sorted({unit.digest for unit in (*fit_identities(), *overhead_identities())})
    evaluations = sorted(unit.digest for unit in final_identities())
    config = read_config()
    return {
        "execution_seal.json": {"digest": seal.digest, **seal.payload(),
                                "note": "single runtime seal: orchestrator.execution_fingerprints(), "
                                        "covering the engine and the A2, A1 and v0.4 analysis sources"},
        "schedule.json": {
            "schedule_sha256": schedule.digest, "units": len(schedule.units),
            "phases": {phase: len(schedule.phase(phase)) for phase in PHASES},
            "budget": validate_schedule(), "identity_count": len(identities),
            "identity_list_sha256": _sha(canonical_json(identities)),
            "canary": [unit.payload() for unit in canary_identities()],
            "execution": config["execution"], "cohort": config["cohort"],
            "residual": config["residual"], "lineage": config["lineage"],
        },
        "analysis_catalogue.json": {
            "format": FORMAT, "plan": dry_plan(),
            "evaluation_identity_count": len(evaluations),
            "evaluation_identity_list_sha256": _sha(canonical_json(evaluations)),
            "references": {"package": "fgcs_strengthening_v04", "journal": "read only, closed",
                           "cells": "tier-2 core and modern 2x2 (level parameterisation)",
                           "persistence": "v1 persistence on the frozen outer-test support",
                           "v04_execution_seal": config["lineage"]["v04_execution_seal"]},
        },
    }


def package_record(files, package=None):
    host_path = Path(package or PACKAGE) / "host_manifest.json"
    try:
        host = json.loads(host_path.read_text())
    except FileNotFoundError:
        raise RegistrationRefused(f"Capture the host manifest first: {host_path}") from None
    hardware = dict(host["hardware"])
    hardware.pop("hostname", None)
    listed = {**{name: _sha(content) for name, content in files.items()},
              "host_manifest.json": _sha(host_path.read_bytes())}
    return {
        "package": "fgcs-v04-a2 frozen package",
        "protocol": protocol_path(),
        "amendment": read_config()["amendment"]["path"],
        "generated_files": dict(sorted(listed.items())),
        "referenced_files": {path: _sha((ROOT / path).read_bytes()) for path in references()},
        "host": {"hardware_without_hostname": hardware, "software_versions": host["software"],
                 "conditions": host["conditions"]},
        "author_decisions": DECISIONS,
        "status": {"a2_author_approval": "A2 approved as written by the authors (2026-11-19); freezing by Git tag",
                   "external_registration": "none for A2, A1 or v0.4 (D1)",
                   "scientific_execution": "none; the runtime journal is created by `launch start`"},
    }


def build(package=None):
    from .host import EXPECTED_CONDITIONS

    package = Path(package or PACKAGE)
    require_frozen_protocol()
    host = package / "host_manifest.json"
    if not host.is_file():
        raise RegistrationRefused(f"Capture the host manifest first: {host}")
    if json.loads(host.read_text()).get("conditions") != EXPECTED_CONDITIONS:
        raise RegistrationRefused("The host manifest was not captured under single-thread CPU conditions")
    existing = [name for name in (*GENERATED, "PACKAGE.json") if (package / name).exists()]
    if existing:
        raise RegistrationRefused(f"A package already exists ({', '.join(existing)}); it is never overwritten")
    files = {name: _json(value) for name, value in generated().items()}
    record = package_record(files, package)
    digest = _sha(canonical_json(record))
    for name, content in files.items():
        with (package / name).open("xb") as stream:
            stream.write(content)
    with (package / "PACKAGE.json").open("xb") as stream:
        stream.write(_json({**record, "package_sha256": digest}))
    evidence = package / "REGISTRATION_EVIDENCE_TEMPLATE.md"
    if not evidence.exists():
        evidence.write_text(EVIDENCE_TEMPLATE)
    return digest


def verify(package=None):
    """Recompute everything and compare. Returns (stored digest, problems)."""
    package = Path(package or PACKAGE)
    try:
        stored = json.loads((package / "PACKAGE.json").read_text())
    except FileNotFoundError:
        return None, ["no PACKAGE.json"]
    digest = stored.pop("package_sha256", None)
    files = {name: _json(value) for name, value in generated().items()}
    problems = [name for name, content in files.items()
                if not (package / name).is_file() or (package / name).read_bytes() != content]
    try:
        if package_record(files, package) != stored:
            problems.append("PACKAGE.json content")
    except RegistrationRefused as error:
        problems.append(str(error))
    if _sha(canonical_json(stored)) != digest:
        problems.append("package digest")
    return digest, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.build:
            print(json.dumps({"package_sha256": build()}))
            return 0
    except RegistrationRefused as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    digest, problems = verify()
    print(json.dumps({"package_sha256": digest, "verified": not problems, "problems": problems}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
