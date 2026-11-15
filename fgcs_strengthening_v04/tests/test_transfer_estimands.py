from dataclasses import replace
import math
import unittest

from fgcs_strengthening_v04.src.identity import BLOCK_ENTITIES
from fgcs_strengthening_v04.src.transfer.design import transfer_matrices
from fgcs_strengthening_v04.src.transfer.estimands import NativeMAECell, entity_effect, group_effect


def select(arm="pairwise", scope="own", estimand="F"):
    return next(m.entries[0] for m in transfer_matrices()
                if (m.block, m.arm, m.scope, m.estimand) == ("fastStorage", arm, scope, estimand))


def grids(entry, first, second):
    groups = ([], [])
    for fold in range(1, 6):
        for seed in (0, 1, 2):
            models = entry.model_identities("697", fold, seed)
            for lead in (1, 2, 4, 9, 18):
                for index, value in enumerate((first, second)):
                    mae = value(fold, seed, lead) if callable(value) else value
                    groups[index].append(NativeMAECell(models[index], entry.target_task, lead, mae,
                                                       4, f"support-{fold}", f"scaler-{fold}", f"origins-{fold}"))
    return groups


class TransferEstimandTests(unittest.TestCase):
    def test_exact_references_and_signs(self):
        for scope, independent, full in (("own", "S1", "M0"), ("all", "S2", "M1")):
            F = select(scope=scope)
            Q = select("leave_one_out", scope, "Q")
            f_ref, f_subset = F.model_identities("697", 1, 2)
            q_subset, q_ref = Q.model_identities("697", 1, 2)
            self.assertEqual((f_ref.arm, f_ref.formulation, f_ref.tasks), ("core", independent, (F.target_task,)))
            self.assertEqual((f_subset.formulation, q_subset.formulation, q_ref.formulation), (full, full, full))
            self.assertEqual(q_ref.arm, "core")
            self.assertEqual(len(q_ref.tasks), 4)
            for entry in (F, Q):
                self.assertAlmostEqual(entity_effect(entry, "697", *grids(entry, 4., 2.)).log_effect, math.log(2.))
                self.assertAlmostEqual(entity_effect(entry, "697", *grids(entry, 2., 4.)).log_effect, -math.log(2.))

    def test_aggregates_rectangular_cells_before_logging(self):
        F = select()
        left, right = grids(F, lambda fold, seed, lead: fold + seed + lead, 2.)
        result = entity_effect(F, "697", reversed(left), right)
        self.assertAlmostEqual(result.numerator_mae, 10.8)
        self.assertEqual(result.denominator_mae, 2.)
        self.assertAlmostEqual(result.log_effect, math.log(5.4))
        self.assertAlmostEqual(result.native_difference, 8.8)

    def test_extra_seed_duplicate_and_wrong_comparator_are_rejected(self):
        F = select()
        left, right = grids(F, 1., 2.)
        with self.assertRaises(ValueError):
            entity_effect(F, "697", left + [replace(cell, identity=replace(cell.identity, seed=seed))
                                           for seed in (3, 4) for cell in left if cell.identity.seed == 0], right)
        with self.assertRaises(ValueError):
            entity_effect(F, "697", left + left[:1], right)
        with self.assertRaises(ValueError):
            entity_effect(F, "697", [replace(left[0], identity=replace(
                left[0].identity, formulation="S2", input_scope="all")), *left[1:]], right)

    def test_missing_mismatched_zero_and_nonfinite_are_unavailable(self):
        F = select()
        left, right = grids(F, 1., 2.)
        self.assertEqual(entity_effect(F, "697", left[:-1], right).status, "incomplete_grid")
        for field in ("support_sha256", "scaler_sha256", "ordered_test_ids_sha256", "context"):
            changed = replace(right[0], **{field: 9 if field == "context" else "other"})
            self.assertEqual(entity_effect(F, "697", left, [changed, *right[1:]]).status,
                             "mismatched_support_context_or_scaler")
        self.assertEqual(entity_effect(F, "697", [replace(left[0], mae=float("nan")), *left[1:]], right).status,
                         "invalid_native_mae")
        for a, b, ratio, effect in ((0., 2., 0., -math.inf), (2., 0., math.inf, math.inf), (0., 0., None, None)):
            result = entity_effect(F, "697", *grids(F, a, b))
            self.assertFalse(result.available)
            self.assertEqual((result.ratio, result.log_effect), (ratio, effect))
        left[0] = replace(left[0], mae=0.)
        self.assertTrue(entity_effect(F, "697", left, right).available)

    def test_group_needs_complete_frozen_cohort_and_finite_entity_effects(self):
        F = select()
        result = entity_effect(F, "697", *grids(F, 4., 2.))
        scores = {entity: result for entity in BLOCK_ENTITIES["fastStorage"]}
        self.assertAlmostEqual(group_effect(F, scores), math.log(2))
        self.assertIsNone(group_effect(F, scores | {"697": replace(result, status="incomplete_grid")}))
        scores.pop("697")
        self.assertIsNone(group_effect(F, scores))
