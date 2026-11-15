from collections import Counter
from dataclasses import replace
import unittest

from fgcs_strengthening_v04.plan_execution import fit_identities
from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.modern.design import COHORTS, FAMILIES, dry_budget, modern_identities, pilot_context, pilot_identities


class PilotPlanTests(unittest.TestCase):
    def test_exact_reduced_cohorts_and_fit_counts(self):
        self.assertEqual(COHORTS["fastStorage"], tuple("697 860 366 679 360 505 481 109 680 50".split()))
        self.assertEqual(COHORTS["Rnd"], tuple("99 409 269 493 474 97 118 233 142 151".split()))
        units = tuple(modern_identities())
        self.assertEqual(set(units), {i for i in fit_identities() if i.arm == "modern"})
        self.assertEqual(len({unit.digest for unit in units}), 3000)
        for block, cohort in COHORTS.items():
            self.assertEqual(tuple(dict.fromkeys(i.entity for i in units if i.block == block)), cohort)
        budget = dry_budget()
        self.assertEqual((budget["inner"], budget["final"]), (1500, 1500))
        self.assertEqual(budget["families"], {f: {"inner": 500, "final": 500} for f in FAMILIES})

    def test_exact_nonadditive_pilot_identities(self):
        pilot = pilot_identities()
        self.assertEqual(len(pilot), 30)
        self.assertEqual(len(set(pilot)), 30)
        self.assertTrue(set(pilot) <= set(modern_identities()))
        counts = Counter()
        complements = tuple((task,) for task in RESOURCES) + (RESOURCES,)
        for unit in pilot:
            self.assertEqual((unit.fold, unit.seed, unit.phase), (1, 0, "inner"))
            self.assertEqual((unit.entity, pilot_context(unit)), ("697", 18) if unit.block == "fastStorage" else ("99", 4))
            self.assertIn(unit.tasks, complements)
            self.assertIsNone(pilot_context(replace(unit, phase="final")))
            counts[unit.block, unit.formulation, unit.variant] += 1
        for block in COHORTS:
            for family in FAMILIES:
                self.assertEqual(counts[block, family, "independent"], 4)
                self.assertEqual(counts[block, family, "shared"], 1)
