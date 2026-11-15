from dataclasses import replace
import unittest

from fgcs_strengthening_v04.src.diagnostics.aggregation import entity_k
from fgcs_strengthening_v04.src.identity import ScientificIdentity, RESOURCES


def grid(block, entity, value):
    return {
        ScientificIdentity(block, entity, fold, seed, "final", "diagnostic", "M1", RESOURCES, "all", 64, "final"):
        value(fold, seed)
        for fold in range(1, 6) for seed in range(3)
    }


class AggregationTests(unittest.TestCase):
    def test_entity_requires_all_15_m1_final_slots(self):
        scores = grid("fastStorage", "697", lambda f, s: (f * 5 + s) / 50)
        self.assertEqual(len(scores), 15)
        self.assertAlmostEqual(entity_k("fastStorage", "697", scores), 0.32)
        key = next(iter(scores))
        self.assertIsNone(entity_k("fastStorage", "697", scores | {key: None}))
        scores.pop(key)
        self.assertIsNone(entity_k("fastStorage", "697", scores))
        with self.assertRaises(ValueError):
            entity_k("fastStorage", "697", scores | {replace(key, variant="mid"): 0.5})
        with self.assertRaises(ValueError):
            entity_k("fastStorage", "697", scores | {replace(key, formulation="M0", input_scope="own"): 0.5})


if __name__ == "__main__":
    unittest.main()
