from itertools import product
import unittest

import numpy as np

from fgcs_strengthening_v04.src.models.lightgbm import score_native_horizon
from fgcs_strengthening_v04.src.tree.design import GRID, HORIZONS, TreeConfig, native_score, select_configuration


class LightGBMSelectionTests(unittest.TestCase):
    def test_exact_eight_grid_points_and_equal_horizon_scoring(self):
        self.assertEqual(GRID, tuple(TreeConfig(*v) for v in product((15, 31), (.03, .05), (200, 400))))
        errors = dict(zip(HORIZONS, (1., 2., 4., 8., 15.), strict=True))
        self.assertEqual(native_score(errors), 6.)
        scores = {config: {lead: 7. for lead in HORIZONS} for config in GRID}
        scores[GRID[-1]] = errors
        self.assertEqual(select_configuration(scores), GRID[-1])
        with self.assertRaises(ValueError):
            native_score({1: 1., 2: 2.})
        with self.assertRaises(ValueError):
            select_configuration({GRID[0]: errors})
        with self.assertRaises(ValueError):
            select_configuration(scores | {GRID[0]: errors | {18: float("nan")}})

    def test_selection_ties_follow_leaves_then_learning_rate_then_estimator_count(self):
        for first, other in ((TreeConfig(15, .05, 400), TreeConfig(31, .03, 200)),
                             (TreeConfig(15, .03, 400), TreeConfig(15, .05, 200)),
                             (TreeConfig(15, .03, 200), TreeConfig(15, .03, 400))):
            scores = {config: {lead: 9. for lead in HORIZONS} for config in GRID}
            scores[first] = scores[other] = {lead: 2. for lead in HORIZONS}
            self.assertEqual(select_configuration(scores), first)

    def test_score_uses_native_predictions_after_inverse(self):
        class Booster:
            def predict(self, features, *, num_iteration, num_threads):
                prediction_args.append((num_iteration, num_threads))
                return np.array([0., np.log(3.)])

        class Partition:
            def inverse_target(self, scaled, resource):
                resources.append(resource)
                native = np.expm1(scaled)
                return native, 0., native

        prediction_args, resources = [], []
        scores = score_native_horizon(Partition(), Booster(), np.ones((2, 4)), np.array([1., 5.]), "DISK_WRITE")
        self.assertEqual(prediction_args, [(-1, 1)])
        self.assertEqual(resources, ["DISK_WRITE"])
        self.assertAlmostEqual(scores["native_mae"], 2.)
        self.assertNotEqual(scores["scaled_prediction_sha256"], scores["native_prediction_sha256"])


    def test_nonfinite_scaled_prediction_fails_before_inverse(self):
        class Booster:
            def predict(self, features, **kwargs):
                return np.array([0., np.nan])

        with self.assertRaisesRegex(ValueError, "Invalid scaled scalar prediction"):
            score_native_horizon(None, Booster(), np.ones((2, 4)), np.ones(2), "CPU")
