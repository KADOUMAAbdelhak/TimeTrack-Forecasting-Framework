"""Explicit one-identity transfer fitting and post-fit outer evaluation."""

from pathlib import Path

from ..diagnostics.engine import _SOURCES as _DIAGNOSTIC_SOURCES
from ..evaluation import OuterEvaluator, _SOURCES as _EVALUATION_SOURCES
from ..identity import ROOT, ScientificIdentity
from ..provenance import Fingerprints
from ..training import TrainingEngine
from .design import ARMS, BLOCKS, SEEDS, dry_budget

_SOURCES = tuple(Path(__file__).with_name(name).resolve().relative_to(ROOT).as_posix()
                 for name in ("runner.py", "estimands.py"))


def transfer_fingerprints():
    return Fingerprints.capture_protocol(additional_sources=(*_DIAGNOSTIC_SOURCES, *_EVALUATION_SOURCES, *_SOURCES))


def _require_identity(identity, *, evaluation=False):
    if not isinstance(identity, ScientificIdentity):
        raise ValueError("Expected a declared scientific identity")
    if not evaluation and identity.arm in ARMS:
        return
    if (evaluation and identity.phase == "final" and identity.block in BLOCKS and identity.seed in SEEDS
            and identity.arm in {*ARMS, "core"}):
        return
    raise ValueError("Expected a transfer fit or a final transfer/comparator evaluation identity")


class TransferRunner:
    def __init__(self, engine):
        if not isinstance(engine, TrainingEngine):
            raise TypeError("Expected the sealed baseline training engine")
        engine.journal.seal.require_protocol(additional_sources=(*_EVALUATION_SOURCES, *_SOURCES))
        self.engine = engine
        self.journal = engine.journal

    dry_budget = staticmethod(dry_budget)

    def fit(self, identity, partition):
        """Run exactly one declared fit. The caller supplies a verified partition."""
        _require_identity(identity)
        method = self.engine.fit_inner if identity.phase == "inner" else self.engine.fit_final
        return method(identity, partition, mode="equal_loss")

    def evaluate(self, identity, partition):
        """Evaluate a completed final checkpoint once, through the shared evaluator."""
        _require_identity(identity, evaluation=True)
        return OuterEvaluator(self.journal).evaluate(identity, partition)

    def completed_cells(self, identity):
        """Read typed estimand inputs from an authenticated evaluation outcome."""
        _require_identity(identity, evaluation=True)
        return OuterEvaluator(self.journal).completed_cells(identity)
