import math
import unittest

import numpy as np

from fgcs_strengthening_v04.src.statistics.bootstrap import Bootstrap
from fgcs_strengthening_v04.src.statistics.design import cohort_for
from fgcs_strengthening_v04.src.statistics.mechanism import average_ranks, correlate, spearman
from fgcs_strengthening_v04.src.statistics.synthesis import DiagnosticCell, ResultTable


class MechanismTests(unittest.TestCase):
    def test_manual_average_ranks_and_spearman(self):
        np.testing.assert_array_equal(average_ranks([1, 2, 2, 4]), [1, 2.5, 2.5, 4])
        self.assertAlmostEqual(float(spearman([1, 2, 2, 4], [1, 2, 3, 4])), math.sqrt(.9))
        self.assertAlmostEqual(float(spearman([3, 1, 2], [1, 3, 2])), -1.)
        group = "fastStorage"
        values = dict(zip(cohort_for(group), np.arange(35) / 34, strict=True))
        result = correlate(Bootstrap(), group, values, values)
        self.assertEqual(result.point, 1.)
        self.assertEqual(result.ci, (1., 1.))
        self.assertEqual(result.undefined_replicates, 0)

    def test_original_constant_or_undefined_bootstrap_replicates(self):
        group = "Rnd"
        draws = Bootstrap()
        cohort = cohort_for(group)
        constant = dict.fromkeys(cohort, 0.)
        varying = {**constant, cohort[-1]: 1.}
        unavailable = correlate(draws, group, constant, varying)
        self.assertEqual((unavailable.point, unavailable.raw_p, unavailable.reason), (None, 1., "constant_original"))
        result = correlate(draws, group, varying, varying)
        undefined = int(np.count_nonzero(np.all(draws.indices(group) != 34, axis=1)))
        self.assertGreater(undefined, 0)
        self.assertEqual(result.undefined_replicates, undefined)
        self.assertEqual(result.raw_p, (1 + undefined) / 10001)
        self.assertIsNone(result.ci)

    def test_only_complete_m1_final_slots_are_consumed(self):
        with self.assertRaises(ValueError):
            ResultTable([], [DiagnosticCell("fastStorage", "697", 1, 0, .1, slot="mid")])
        cells = [DiagnosticCell("fastStorage", "697", fold, seed, .25)
                 for fold in range(1, 6) for seed in range(5)]
        self.assertEqual(ResultTable([], cells).K("fastStorage", "697"), .25)
        self.assertIsNone(ResultTable([], cells[:-1]).K("fastStorage", "697"))
