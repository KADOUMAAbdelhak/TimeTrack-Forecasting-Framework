import unittest

from fgcs_strengthening_v04.plan_execution import fit_identities
from fgcs_strengthening_v04.src.tree.design import HORIZONS, dry_budget, tree_identities


class LightGBMBudgetTests(unittest.TestCase):
    def test_exact_registered_wrapper_and_scalar_counts(self):
        self.assertEqual(HORIZONS, (1, 2, 4, 9, 18))
        self.assertEqual(dry_budget(), {
            "wrappers": {"inner": 22400, "final": 2800, "total": 25200},
            "scalar_estimators": {"inner": 112000, "final": 14000, "total": 126000},
        })
        units = set(tree_identities())
        self.assertEqual(len(units), 25200)
        self.assertEqual(units, {unit for unit in fit_identities() if unit.arm == "lightgbm"})
        self.assertEqual({unit.seed for unit in units}, {0})
        self.assertEqual({unit.input_scope for unit in units}, {"own", "all"})
        self.assertEqual({unit.block for unit in units}, {"fastStorage", "Rnd"})
        self.assertTrue(all(len(unit.tasks) == 1 for unit in units))
        self.assertTrue(all(len({unit.entity for unit in units if unit.block == block}) == 35
                            for block in ("fastStorage", "Rnd")))
