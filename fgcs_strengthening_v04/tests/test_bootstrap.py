import unittest

import numpy as np

from fgcs_strengthening_v04.src.statistics.bootstrap import Bootstrap, centred_p, mean_log
from fgcs_strengthening_v04.src.statistics.design import GROUPS, cohort_for


class BootstrapTests(unittest.TestCase):
    def test_exact_fixed_pcg64_draws_reused_by_identity(self):
        bootstrap, repeat = Bootstrap(), Bootstrap()
        reference = np.random.Generator(np.random.PCG64(20261110))
        for group in GROUPS:
            observed = bootstrap.indices(group)
            self.assertIs(observed, bootstrap.indices(group))
            self.assertFalse(observed.flags.writeable)
            np.testing.assert_array_equal(observed, reference.integers(0, 35, size=(10000, 35)))
            np.testing.assert_array_equal(observed, repeat.indices(group))

    def test_manual_mean_interval_ratio_and_centred_p(self):
        bootstrap = Bootstrap()
        group = "fastStorage"
        values = dict(zip(cohort_for(group), np.arange(35) / 100, strict=True))
        result = mean_log(bootstrap, group, values)
        raw = np.asarray(list(values.values()))
        replicates = raw[bootstrap.indices(group)].mean(axis=1)
        self.assertAlmostEqual(result.point, .17)
        np.testing.assert_allclose(result.ci, np.percentile(replicates, [2.5, 97.5], method="linear"))
        self.assertEqual(result.raw_p, (1 + sum(abs(replicates - result.point) >= abs(result.point))) / 10001)
        self.assertAlmostEqual(result.ratio, np.exp(.17))
        self.assertEqual(centred_p(2., [0., 1., 4., 6.]), 4 / 5)
        self.assertEqual(centred_p(2., [0., 1., 4., 6.], undefined=1), 5 / 6)
        with self.assertRaises(ValueError):
            mean_log(bootstrap, "TimeTrack", values)
        with self.assertRaises(ValueError):
            mean_log(bootstrap, group, {**values, "foreign": 0.})
