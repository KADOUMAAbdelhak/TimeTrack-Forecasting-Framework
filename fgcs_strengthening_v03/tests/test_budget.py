import json
import subprocess
import sys
import unittest

from fgcs_strengthening_v03.src.identity import ROOT


class BudgetTests(unittest.TestCase):
    def test_dry_planner_counts_and_no_training_imports(self):
        script = """
import sys
from fgcs_strengthening_v03.plan_execution import main
main([])
if {'torch', 'lightgbm', 'pandas', 'numpy'} & sys.modules.keys():
    raise RuntimeError('Dry planner imported a scientific runtime')
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["core"], [45500, 45500])
        self.assertEqual(summary["capacity"], [4550, 4550])
        self.assertEqual(summary["pairwise"], [12600, 12600])
        self.assertEqual(summary["leave_one_out"], [8400, 8400])
        self.assertEqual(summary["pcgrad"], [1050, 1050])
        self.assertEqual(summary["gradnorm"], [1050, 1050])
        self.assertEqual(summary["modern"], [1500, 1500])
        self.assertEqual(summary["lightgbm"], [22400, 2800])
        self.assertEqual(summary["tree_scalar"], [112000, 14000])
        self.assertEqual(summary["fit_total"], 174500)
        self.assertEqual(summary["scalar_adjusted_total"], 275300)
        self.assertEqual(summary["identity_total"], 206000)
        self.assertEqual(summary["modern_pilot_subset"], 30)
        self.assertEqual(summary["checkpoint_requests"], 4200)
        self.assertEqual(summary["gradient_extractions"], 1747200)
