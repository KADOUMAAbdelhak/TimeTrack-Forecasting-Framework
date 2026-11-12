import unittest

import numpy as np

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.models.lightgbm import FeatureLayout


class LightGBMFeatureTests(unittest.TestCase):
    def test_exact_chronological_and_resource_major_order(self):
        for context in (4, 9, 18):
            history = np.array([[100 * resource + lag for resource in range(4)] for lag in range(context)])
            windows = np.stack((history, history + 1000))
            own = FeatureLayout(context, "MEMORY", "own")
            both = FeatureLayout(context, "MEMORY", "all")
            self.assertEqual(own.flatten(windows).shape, (2, context))
            self.assertEqual(both.flatten(windows).shape, (2, 4 * context))
            np.testing.assert_array_equal(own.flatten(windows), windows[:, :, 2])
            for i, resource in enumerate(RESOURCES):
                interval = slice(i * context, (i + 1) * context)
                np.testing.assert_array_equal(both.flatten(windows)[:, interval], windows[:, :, i])
                self.assertEqual(both.names[interval], tuple(f"{resource}_lag_{k}" for k in reversed(range(context))))

    def test_other_resource_perturbation_affects_only_all_input_features(self):
        windows = np.arange(32).reshape(2, 4, 4).astype(float)
        changed = windows.copy()
        changed[:, :, 3] += 100
        own = FeatureLayout(4, "CPU", "own")
        all_inputs = FeatureLayout(4, "CPU", "all")
        np.testing.assert_array_equal(own.flatten(windows), own.flatten(changed))
        self.assertFalse(np.array_equal(all_inputs.flatten(windows), all_inputs.flatten(changed)))
        np.testing.assert_array_equal(all_inputs.flatten(changed)[:, -4:], changed[:, :, 3])
