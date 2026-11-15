from dataclasses import replace
import unittest

from fgcs_strengthening_v04.src.diagnostics.aggregation import entity_k, materna_k
from fgcs_strengthening_v04.src.identity import ScientificIdentity, RESOURCES


def grid(block, entity, value):
    return {
        ScientificIdentity(block, entity, fold, seed, "final", "diagnostic", "M1", RESOURCES, "all", 64, "final"):
        value(fold, seed)
        for fold in range(1, 6) for seed in range(5)
    }


class AggregationTests(unittest.TestCase):
    def test_entity_requires_all_25_m1_final_slots(self):
        scores = grid("fastStorage", "697", lambda f, s: (f * 5 + s) / 50)
        self.assertAlmostEqual(entity_k("fastStorage", "697", scores), 0.34)
        key = next(iter(scores))
        self.assertIsNone(entity_k("fastStorage", "697", scores | {key: None}))
        scores.pop(key)
        self.assertIsNone(entity_k("fastStorage", "697", scores))
        with self.assertRaises(ValueError):
            entity_k("fastStorage", "697", scores | {replace(key, variant="mid"): 0.5})
        with self.assertRaises(ValueError):
            entity_k("fastStorage", "697", scores | {replace(key, formulation="M0", input_scope="own"): 0.5})

    def test_materna_averages_three_complete_trace_scores_for_same_vm(self):
        t1 = grid("Materna-T1", "74", lambda *_: 0.5)
        t2 = grid("Materna-T2", "74", lambda *_: -0.4)
        t3 = grid("Materna-T3", "74", lambda *_: 0.2)
        self.assertAlmostEqual(materna_k("74", t1 | t2 | t3), 0.1)
        self.assertIsNone(materna_k("74", t1 | t2))
        t3.pop(next(iter(t3)))
        self.assertIsNone(materna_k("74", t1 | t2 | t3))
        with self.assertRaises(ValueError):
            materna_k("74", t1 | grid("Materna-T2", "134", lambda *_: 0.3))
