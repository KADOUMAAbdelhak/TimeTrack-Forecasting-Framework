"""Generated windows and a scratch journal for Stage 3B unit tests."""

from contextlib import contextmanager
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import tempfile
from types import MappingProxyType
from unittest.mock import patch

import numpy as np

from fgcs_strengthening_v04a2.src.data_adapters import PreparedPartition, Windows
from fgcs_strengthening_v04a2.src.identity import HOME, RESOURCES, ScientificIdentity, read_config
from fgcs_strengthening_v04a2.src.provenance import Journal
from fgcs_strengthening_v04a2.src.training import TrainingEngine, training_fingerprints


def identity(formulation="M1", *, phase="inner", seed=0):
    tasks = ("MEMORY",) if formulation.startswith("S") else RESOURCES
    return ScientificIdentity("fastStorage", "697", 1, seed, phase, "core", formulation, tasks,
                              "own" if formulation in {"S1", "M0"} else "all", 64, "baseline")


def digest(value):
    return sha256(value.encode()).hexdigest()


def partition(unit, *, n=7):
    config = read_config()
    block = config["blocks"][unit.block]
    context, horizons = block["contexts"][0], len(block["horizons"])
    gen = np.random.default_rng(982)
    train = Windows(gen.normal(size=(n, context, 4)).astype("float32"),
                    gen.normal(size=(n, 4, horizons)).astype("float32"), None, np.arange(n))
    val = Windows(gen.normal(size=(3, context, 4)).astype("float32"),
                  gen.normal(size=(3, 4, horizons)).astype("float32"), None, np.arange(n, n + 3))
    accesses = []
    train_origins = np.array([0])
    evaluation_origins = np.array([1 if unit.phase == "inner" else 2])

    class Adapter:
        def _windows(self, frame, entity, length, origins, scaler):
            accesses.append(int(origins[0]))
            if origins[0] == 2:
                raise AssertionError("Outer test materialisation in training")
            return train if origins[0] == 0 else val

    split_hashes = MappingProxyType({name: digest(name) for name in
                                    ("inner_train", "inner_validation", "outer_train", "outer_test")})
    return PreparedPartition(unit.block, unit.entity, unit.fold, unit.phase, context,
                             digest(unit.phase + "support"), split_hashes, digest(unit.phase + "scaler"),
                             Adapter(), None, train_origins, evaluation_origins, None), accesses


@lru_cache(maxsize=1)
def _seal():
    return training_fingerprints()


@contextmanager
def scratch_engine(seal=None, *, closed_fits=False):
    """closed_fits writes the C6 fit-closure record, standing in for a closed orchestrator schedule."""
    seal = _seal() if seal is None else seal
    with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
            "fgcs_strengthening_v04a2.src.provenance.HOME", Path(scratch)):
        engine = TrainingEngine(Journal(seal))
        if closed_fits:
            close_fits(engine.journal)
        yield engine


def _synthetic_closure(journal, name, phases, abandoned, evaluation):
    """Stand-in for Orchestrator.close: map every journalled outcome (and each abandonment) to its hash."""
    from fgcs_strengthening_v04a2.src.identity import canonical_json
    from fgcs_strengthening_v04a2.src.provenance import _atomic_publish, sha256_file

    directory = journal._path(*(("evaluations",) if evaluation else ()), "outcomes")
    outcomes = {path.stem: sha256_file(path) for path in directory.glob("*.json")} if directory.is_dir() else {}
    outcomes.update({digest: None for digest in abandoned})
    outcomes = dict(sorted(outcomes.items()))
    gates = journal._path("orchestrator", "gates")
    _atomic_publish(gates / f"{name}.outcomes.json", outcomes)
    _atomic_publish(gates / f"{name}.json",
                    {"gate": name, "phases": list(phases), "synthetic": True, "schedule_sha256": "synthetic",
                     "outcomes_sha256": sha256(canonical_json(outcomes)).hexdigest(),
                     "abandoned_identity_sha256": sorted(abandoned)})


def close_fits(journal, abandoned=()):
    from fgcs_strengthening_v04a2.src.evaluation import FIT_CLOSURE_PHASES

    _synthetic_closure(journal, "fits", FIT_CLOSURE_PHASES, abandoned, False)


def close_evaluation(journal, abandoned=()):
    _synthetic_closure(journal, "evaluation", ("evaluation",), abandoned, True)
