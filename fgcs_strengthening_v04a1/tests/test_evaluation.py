"""Shared outer-test evaluation on generated windows and tiny generated fits."""

from dataclasses import replace
from functools import lru_cache
import io
import json
import unittest
from unittest.mock import patch

import numpy as np
import torch

from fgcs_strengthening_v04a1.src.data_adapters import Windows
from fgcs_strengthening_v04a1.src.evaluation import OuterEvaluator, evaluation_source, prediction_sha256
from fgcs_strengthening_v04a1.src.identity import RESOURCES, ScientificIdentity, canonical_json, read_config
from fgcs_strengthening_v04a1.src.models.lstm import LSTM
from fgcs_strengthening_v04a1.src.models.registry import REGISTRY
from fgcs_strengthening_v04a1.src.modern.design import family_identities
from fgcs_strengthening_v04a1.src.modern.runner import ModernRunner
from fgcs_strengthening_v04a1.src.provenance import DuplicateIdentity, ProvenanceError
from fgcs_strengthening_v04a1.src.orchestrator import execution_fingerprints
from fgcs_strengthening_v04a1.src.training import TrainingEngine
from fgcs_strengthening_v04a1.tests.training_fixtures import digest, identity, partition, scratch_engine

CONFIG = read_config()
IDS = list(range(100, 104))


@lru_cache(maxsize=1)
def seal():
    return execution_fingerprints()


def heldout(unit, *, broken=False):
    """Generated partition whose outer test (origin 2) is readable only by an explicit evaluation."""
    prepared, accesses = partition(unit)
    base = prepared._adapter
    horizons = len(CONFIG["blocks"][unit.block]["horizons"])
    generator = np.random.default_rng(11)
    inputs = generator.normal(size=(len(IDS), prepared.context, 4)).astype(np.float32)
    targets = generator.normal(size=(len(IDS), 4, horizons)).astype(np.float32)
    native = targets.astype(np.float64) * 2 + 1
    if broken:
        native[0, 0, 0] = np.nan

    class Adapter:
        def _windows(self, frame, entity, length, origins, scaler):
            if origins[0] != 2:
                window = base._windows(frame, entity, length, origins, scaler)
                return Windows(window.inputs, window.targets, window.targets.astype(np.float64), window.origin_ids)
            accesses.append(2)
            return Windows(inputs, targets, native, np.asarray(IDS))

        def _inverse(self, scaler, values, resource):
            values = np.asarray(values, dtype=np.float64) * 2 + 1
            return values, 0., values

    return replace(prepared, _adapter=Adapter()), accesses, (inputs, native)


def expected_cells(journal, unit, outer):
    """Independent recomputation from the journalled checkpoint and generated outer test."""
    source = evaluation_source(unit)
    final, _ = journal.completed_evidence(source)
    epoch = final["selection"]["joint_epoch"]
    reference = final["checkpoints"][str(epoch)]
    state = torch.load(io.BytesIO(journal.checkpoint_bytes(source, epoch, reference)), weights_only=True)
    inputs, native = outer
    with torch.inference_mode():
        if source.arm == "modern":
            model = REGISTRY[source.formulation].build(inputs.shape[1], source.tasks, source.input_scope)
        else:
            model = LSTM(formulation=source.formulation, block=source.block, tasks=source.tasks,
                         hidden_size=source.hidden_size)
        model.load_state_dict(state)
        model.eval()
        values = torch.from_numpy(inputs)
        if source.arm == "modern" and source.input_scope == "own" and source.variant == "independent":
            index = RESOURCES.index(source.tasks[0])
            values = values[:, :, index:index + 1]
        scaled = model(values).numpy()
    rows = []
    for task in unit.tasks:
        predicted = scaled[:, source.tasks.index(task)].astype(np.float64) * 2 + 1
        mae = np.mean(np.abs(predicted - native[:, RESOURCES.index(task)]), axis=0)
        rows.extend({"target": task, "horizon": lead, "mae": float(value)}
                    for lead, value in zip(CONFIG["blocks"][unit.block]["horizons"], mae))
    return epoch, rows


def fit_pair(engine, unit, *, mode="equal_loss", losses=None):
    final_unit = replace(unit, phase="final")
    inner_partition = heldout(unit)[0]
    if losses is None:
        engine.fit_inner(unit, inner_partition, mode=mode)
    else:
        with patch("fgcs_strengthening_v04a1.src.training._evaluate", side_effect=losses):
            engine.fit_inner(unit, inner_partition, mode=mode)
    prepared, accesses, outer = heldout(final_unit)
    engine.fit_final(final_unit, prepared, mode=mode)
    return final_unit, prepared, accesses, outer


class OuterEvaluationTests(unittest.TestCase):
    def check(self, evaluator, unit, prepared, accesses, outer):
        self.assertEqual(accesses, [0])
        evidence = evaluator.evaluate(unit, prepared)
        self.assertEqual(accesses, [0, 2])
        epoch, rows = expected_cells(evaluator.journal, unit, outer)
        self.assertEqual(evidence["evaluated_epoch"], epoch)
        self.assertEqual([(r["target"], r["horizon"]) for r in evidence["cells"]],
                         [(r["target"], r["horizon"]) for r in rows])
        np.testing.assert_allclose([r["mae"] for r in evidence["cells"]], [r["mae"] for r in rows],
                                   rtol=1e-6, atol=1e-7)
        self.assertEqual(evidence["ordered_test_ids_sha256"],
                         __import__("hashlib").sha256(canonical_json(IDS)).hexdigest())
        self.assertEqual(set(evidence["predictions"]), set(unit.tasks))
        with self.assertRaises(DuplicateIdentity):
            evaluator.evaluate(unit, prepared)
        cells = evaluator.completed_cells(unit)
        self.assertEqual(len(cells), len(unit.tasks) * len(CONFIG["blocks"][unit.block]["horizons"]))
        self.assertTrue(all(cell.identity == unit and cell.context == prepared.context for cell in cells))
        return evidence

    def test_core_cells_across_the_cohort_and_seeds(self):
        units = (
            ScientificIdentity("Rnd", "151", 5, 2, "inner", "core", "S1", ("MEMORY",), "own", 64, "baseline"),
            ScientificIdentity("Rnd", "99", 3, 1, "inner", "core", "M1", RESOURCES, "all", 64, "baseline"),
            replace(identity("S2"), seed=2),
            replace(identity("M0"), seed=1),
        )
        with scratch_engine(seal(), closed_fits=True) as engine:
            evaluator = OuterEvaluator(engine.journal)
            for unit in units:
                with self.subTest(unit=(unit.block, unit.formulation, unit.seed)):
                    self.check(evaluator, *fit_pair(engine, unit))

    def test_transfer_subsets_use_their_own_final_fit(self):
        base = identity("M1")
        units = (replace(base, arm="pairwise", tasks=("CPU", "MEMORY")),
                 replace(base, arm="leave_one_out", tasks=("CPU", "THROUGHPUT", "DISK_WRITE")))
        with scratch_engine(seal(), closed_fits=True) as engine:
            evaluator = OuterEvaluator(engine.journal)
            for unit in units:
                with self.subTest(arm=unit.arm):
                    self.check(evaluator, *fit_pair(engine, unit))

    def test_an_evaluation_may_not_name_another_fit_as_its_source(self):
        with scratch_engine(seal(), closed_fits=True) as engine:
            final, prepared, accesses, outer = fit_pair(engine, identity("M1"))
            with self.assertRaisesRegex(ProvenanceError, "no parent"):
                engine.journal.start(final, evaluation=True, source=final)
            self.assertEqual(self.check(OuterEvaluator(engine.journal), final, prepared, accesses, outer)
                             ["source_identity_sha256"], final.digest)

    def test_every_defined_modern_cell_routes_its_inputs_and_outputs(self):
        with scratch_engine(seal(), closed_fits=True) as engine:
            runner = ModernRunner(engine.journal)
            evaluator = OuterEvaluator(engine.journal)
            for family in REGISTRY:
                runner.validate_family(family)
                for unit in family_identities("Rnd", "99", 1, 0, "inner", family):
                    if unit.variant == "independent" and unit.tasks != ("MEMORY",):
                        continue
                    with self.subTest(family=family, cell=unit.cell):
                        self.check(evaluator, *fit_pair(runner, unit))

    def test_failures_are_terminal_and_partitions_are_exact(self):
        with scratch_engine(seal(), closed_fits=True) as engine:
            evaluator = OuterEvaluator(engine.journal)
            final, _, _, _ = fit_pair(engine, identity("S1"))
            broken, accesses, _ = heldout(final, broken=True)
            with self.assertRaisesRegex(ValueError, "native outer-test targets"):
                evaluator.evaluate(final, broken)
            record = json.loads((engine.journal.runtime / "evaluations" / "outcomes" /
                                 f"{final.digest}.json").read_text())
            self.assertEqual(record["status"], "failed")
            self.assertNotIn("cells", record["evidence"])
            with self.assertRaises(DuplicateIdentity):
                evaluator.evaluate(final, broken)
            with self.assertRaises(ProvenanceError):
                evaluator.completed_cells(final)

            other = replace(identity("M0"), phase="final")
            wrong_fold, reads, _ = heldout(replace(other, fold=2))
            with self.assertRaises(ProvenanceError):
                evaluator.evaluate(other, wrong_fold)
            unfitted, reads, _ = heldout(other)
            with self.assertRaises(ProvenanceError):
                evaluator.evaluate(other, unfitted)
            self.assertEqual(reads, [])
            with self.assertRaises(ValueError):
                evaluator.evaluate(replace(other, phase="inner"), unfitted)

    def test_outer_test_is_unreachable_before_fit_closure(self):
        from fgcs_strengthening_v04a1.src.evaluation import FIT_CLOSURE_PHASES
        from fgcs_strengthening_v04a1.src.orchestrator import FIT_PHASES
        from fgcs_strengthening_v04a1.src.provenance import _atomic_publish
        from fgcs_strengthening_v04a1.src.transfer.runner import TransferRunner

        self.assertEqual(FIT_CLOSURE_PHASES, ("certify", *FIT_PHASES))
        with scratch_engine(seal()) as engine:
            final, prepared, accesses, _ = fit_pair(engine, identity("S1"))
            for call in (lambda: OuterEvaluator(engine.journal).evaluate(final, prepared),
                         lambda: TransferRunner(engine).evaluate(final, prepared)):
                with self.assertRaisesRegex(ProvenanceError, "C6"):
                    call()
            _atomic_publish(engine.journal._path("orchestrator", "gates", "fits.json"),
                            {"gate": "fits", "phases": ["canary", "inner", "final"]})
            with self.assertRaisesRegex(ProvenanceError, "every fit phase"):
                OuterEvaluator(engine.journal).evaluate(final, prepared)
            self.assertEqual(accesses, [0])
            self.assertFalse(engine.journal._path("evaluations").exists())

    def test_evaluator_requires_its_source_in_the_seal(self):
        with scratch_engine() as engine, self.assertRaises(ProvenanceError):
            OuterEvaluator(engine.journal)
        self.assertIsInstance(TrainingEngine, type)
        self.assertEqual(prediction_sha256(np.zeros(2, dtype=np.float32)), prediction_sha256(np.zeros(2)))
        self.assertNotEqual(digest("a"), prediction_sha256(np.zeros(1)))


if __name__ == "__main__":
    unittest.main()
