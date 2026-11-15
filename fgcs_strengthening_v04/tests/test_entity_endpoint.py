from dataclasses import replace
import math
import unittest

from fgcs_strengthening_v04.src.statistics.design import CORE
from fgcs_strengthening_v04.src.statistics.endpoints import contrast, entity_aggregate
from fgcs_strengthening_v04.tests.statistics_fixtures import aggregate, cells


class EntityEndpointTests(unittest.TestCase):
    def test_horizons_folds_seeds_equally_weighted_before_log(self):
        data = cells("M1", lambda f, h, s: f + h + s)
        result = self.measure(data)
        # Five horizon values average 6.8, folds average 3 and seeds average 2.
        self.assertAlmostEqual(result.mae, 11.8)
        reference = aggregate("S2", 2.)
        effect = contrast("fastStorage", "M1", "S2", result, reference)
        self.assertAlmostEqual(effect.value, math.log(5.9))
        cell_log_mean = sum(math.log(row.mae / 2) for row in data) / len(data)
        self.assertNotAlmostEqual(effect.value, cell_log_mean)

    def measure(self, data):
        return entity_aggregate(data, model="M1", block="fastStorage", entity="697", resource="CPU", seeds=CORE)

    def test_zero_cells_and_all_zero_categories(self):
        data = cells("M1", 1.)
        data[0] = replace(data[0], mae=0.)
        self.assertAlmostEqual(self.measure(data).mae, 124 / 125)
        for a, b, ratio, log, key in ((0., 2., 0., -math.inf, "candidate_only_zero"),
                                      (2., 0., math.inf, math.inf, "reference_only_zero"),
                                      (0., 0., None, None, "both_zero")):
            effect = contrast("fastStorage", "M1", "S2", aggregate("M1", a), aggregate("S2", b))
            self.assertEqual((effect.ratio, effect.value), (ratio, log))
            self.assertFalse(effect.available)
            self.assertEqual(effect.zeros[key], 1)
            self.assertEqual(effect.native[("fastStorage", "M1")], a)

    def test_missing_duplicate_nonfinite_and_mismatch_fail_closed(self):
        data = cells("M1")
        self.assertIsNone(self.measure(data[:-1]).mae)
        self.assertEqual(self.measure(data[:-1]).status, "incomplete_grid")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.measure([*data, data[0]])
        for status in ("missing", "failed", "nonfinite_prediction"):
            self.assertIn(status, self.measure([replace(data[0], status=status), *data[1:]]).status)
        self.assertEqual(self.measure([replace(data[0], mae=float("nan")), *data[1:]]).status, "invalid_mae")
        self.assertEqual(self.measure([replace(data[0], ordered_test_ids_sha256=None), *data[1:]]).status, "support_mismatch")
        effect = contrast("fastStorage", "M1", "S2", self.measure(data), aggregate("S2", support="different"))
        self.assertFalse(effect.available)
        self.assertEqual(effect.issues, {"support_mismatch": 1})

    def test_incompatible_seed_slice_entity_or_comparator_rejected(self):
        left = aggregate("M1")
        for right in (aggregate("S2", seeds=(0, 1, 2)), aggregate("S2", entity="860"), aggregate("S1")):
            with self.subTest(identity=right.identity), self.assertRaises(ValueError):
                contrast("fastStorage", "M1", "S2", left, right)


    def test_historical_context_exception_requires_same_test_support(self):
        candidate = aggregate("M1-H129-v1", 3., seeds=(0, 1, 2), context=18, scaler="h129")
        reference = aggregate("S2-common-v1", 2., seeds=(0, 1, 2))
        self.assertFalse(contrast("fastStorage", "M1-H129-v1", "S2-common-v1", candidate, reference).available)
        compatible = contrast("fastStorage", "M1-H129-v1", "S2-common-v1",
                              candidate, reference, match_context=False)
        self.assertAlmostEqual(compatible.value, math.log(1.5))
        other = aggregate("S2-common-v1", 2., seeds=(0, 1, 2), support="other")
        self.assertFalse(contrast("fastStorage", "M1-H129-v1", "S2-common-v1",
                                  candidate, other, match_context=False).available)


    def test_tiny_positive_cells_remain_positive_and_near_ties_keep_direction(self):
        smallest = math.ulp(0.)
        self.assertEqual(aggregate("M1", smallest).mae, smallest)
        lower = 1e250
        higher = math.nextafter(lower, math.inf)
        effect = contrast("fastStorage", "M1", "S2", aggregate("M1", higher), aggregate("S2", lower))
        self.assertGreater(effect.value, 0.)
