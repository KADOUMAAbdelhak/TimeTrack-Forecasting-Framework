import unittest

from fgcs_strengthening_v03.src.statistics.multiplicity import adjust_registered, bh, decision, holm, ranked_ids, registered_families


class MultiplicityTests(unittest.TestCase):
    def test_manual_holm_bh_and_lexicographic_ties(self):
        p = {"d": .20, "c": .04, "b": .01, "a": .01}
        self.assertEqual(ranked_ids(p), ["a", "b", "c", "d"])
        self.assertEqual(holm(p), {"a": .04, "b": .04, "c": .08, "d": .20})
        observed = bh(p)
        for key, expected in {"a": .02, "b": .02, "c": .16 / 3, "d": .20}.items():
            self.assertAlmostEqual(observed[key], expected)
        self.assertEqual(decision(-.2, .01, "positive"), (True, False))
        self.assertEqual(decision(.2, .01, "positive"), (True, True))
        self.assertEqual(decision(.2, .05, None), (False, None))

    def test_fixed_family_counts_and_unavailable_slots(self):
        families = registered_families()
        self.assertEqual({name: len(families[name]) for name in ("primary", "gradient_association", "PCGrad", "GradNorm", "checkpoint")},
                         {"primary": 24, "gradient_association": 12, "PCGrad": 8, "GradNorm": 8, "checkpoint": 8})
        self.assertEqual([len(v) for v in families.values() if v[0].correction == "BH"], [12] * 8)
        primary = families["primary"]
        self.assertEqual(sum(slot.predicted_direction == "positive" for slot in primary), 9)
        self.assertEqual(sum(slot.estimand == "I" for slot in primary), 12)
        a = primary[0].analysis_id
        results = adjust_registered({a: .001, primary[1].analysis_id: None})
        self.assertEqual(len(results), 156)
        self.assertEqual(results[a], (.001, .024))
        self.assertTrue(all(value == (1., 1.) for key, value in results.items() if key != a))
        with self.assertRaises(ValueError):
            adjust_registered({"Q/not-a-test": .1})
