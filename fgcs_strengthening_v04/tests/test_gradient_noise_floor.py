import unittest

from fgcs_strengthening_v04.src.diagnostics.metrics import pair_metrics, slot_metrics
from fgcs_strengthening_v04.src.identity import RESOURCES


def tasks(*vectors):
    return dict(zip(RESOURCES, vectors, strict=True))


class NoiseFloorTests(unittest.TestCase):
    def test_aligned_and_conflicting_gradients(self):
        aligned = tasks(*([[1, 0]] * 4))
        row = pair_metrics(aligned, aligned)
        self.assertEqual((row["C"], row["N"], row["K_pair"]), (0, 0, 0))
        split = tasks([1, 0], [-1, 0], [1, 0], [-1, 0])
        row = pair_metrics(split, split)
        self.assertEqual((row["C"], row["N"], row["K_pair"]), (4 / 6, 0, 4 / 6))
        self.assertEqual(row["cross_task"][0]["dot"], -1)
        self.assertEqual(row["cross_task"][0]["cosine"], -1)
        self.assertEqual(row["cross_task"][0]["norm_ratio_left_over_right"], 1)
        summary = slot_metrics([row] * 8)
        self.assertEqual(summary["K"], 4 / 6)
        self.assertEqual(summary["task_pair_negative_cosine_matrix"]["CPU"]["THROUGHPUT"], 1)

    def test_same_task_conflict_contributes_only_to_N_and_zero_dot_is_not_negative(self):
        A = tasks([1, 0], [0, 1], [1, 0], [0, 1])
        B = tasks([-1, 0], [1, 0], [-1, 0], [0, 1])
        row = pair_metrics(A, B)
        self.assertEqual((row["C"], row["N"], row["K_pair"]), (0, 0.5, -0.5))
        self.assertEqual(row["cross_task"][0]["dot"], 0)
        self.assertEqual(row["same_task"][1]["dot"], 0)
        self.assertEqual(row["same_task"][1]["cosine"], 0)

    def test_zero_gradient_never_fills_in_an_eighth_pair(self):
        valid = tasks(*([[1, 0]] * 4))
        B = valid | {"CPU": [0, 0]}
        good, unavailable = pair_metrics(valid, valid), pair_metrics(valid, B)
        self.assertEqual(unavailable["zero_gradients"], [{"side": "B", "task": "CPU"}])
        self.assertIsNone(unavailable["same_task"][0]["cosine"])
        self.assertIsNone(unavailable["K_pair"])
        result = slot_metrics([good] * 7 + [unavailable])
        self.assertIsNone(result["K"])
        self.assertEqual(result["complete_pairs"], 7)
        self.assertEqual(result["zero_gradient_count"], 1)
        self.assertEqual(result["same_negative_cosine_frequency"][0]["defined"], 7)
