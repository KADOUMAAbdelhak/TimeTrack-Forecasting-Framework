"""Worker process for launcher tests: the real worker loop on a tiny generated canary in a scratch journal.

    python -m fgcs_strengthening_v04a1.tests.launcher_fixture <scratch_dir> <phase>
"""

from dataclasses import replace
import json
from pathlib import Path
import sys
from unittest.mock import patch

from fgcs_strengthening_v04a1.src.identity import RESOURCES


def tiny_canary():
    from fgcs_strengthening_v04a1.src.orchestrator import Schedule, Unit
    from fgcs_strengthening_v04a1.tests.training_fixtures import identity

    s1 = [replace(identity("S1"), tasks=(task,)) for task in RESOURCES]
    units = [*s1, identity("M1"), identity("M0")]
    return Schedule([Unit("fit", "canary", unit.digest, unit) for unit in units])


def provider(block, entity, fold, phase):
    from fgcs_strengthening_v04a1.src.identity import ScientificIdentity
    from fgcs_strengthening_v04a1.tests.test_evaluation import heldout

    unit = ScientificIdentity(block, entity, fold, 0, phase, "core", "M1", RESOURCES, "all", 64, "baseline")
    return heldout(unit)[0]


def open_orchestrator(scratch):
    """Call inside a patch of provenance.HOME to the scratch directory."""
    from fgcs_strengthening_v04a1.src.orchestrator import Orchestrator, ProductionExecutors, execution_fingerprints
    from fgcs_strengthening_v04a1.src.provenance import Journal

    journal = Journal(execution_fingerprints())
    return Orchestrator(journal, tiny_canary(), ProductionExecutors(journal, partitions=provider),
                        registration=Path(scratch) / "registration.txt", workers=6)


def main(scratch, phase):
    from fgcs_strengthening_v04a1.launch import run_worker
    from fgcs_strengthening_v04a1.src.orchestrator import configure_worker_process

    configure_worker_process()
    with patch("fgcs_strengthening_v04a1.src.provenance.HOME", Path(scratch)):
        code, summary = run_worker(open_orchestrator(scratch), phase)
    print(json.dumps(summary), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
