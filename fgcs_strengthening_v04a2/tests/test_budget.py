import json
import subprocess
import sys
import unittest

from fgcs_strengthening_v04a2.src.identity import ROOT


class BudgetTests(unittest.TestCase):
    def test_dry_planner_counts_and_no_training_imports(self):
        script = """
import sys
from fgcs_strengthening_v04a2.plan_execution import main
main([])
if {'torch', 'lightgbm', 'pandas', 'numpy'} & sys.modules.keys():
    raise RuntimeError('Dry planner imported a scientific runtime')
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        summary = json.loads(result.stdout)
        # Amendment A2 schedules the tier-2 core and modern 2x2 under the change parameterisation.
        self.assertEqual(summary["core"], [3000, 3000])
        self.assertEqual(summary["modern"], [7500, 7500])
        self.assertEqual(summary["modern_by_family"], {"DLinear": [3000, 3000], "PatchTST": [3000, 3000],
                                                       "iTransformer": [1500, 1500]})
        self.assertEqual(set(summary) & {"intervention", "pairwise", "leave_one_out", "diagnostic_slots"}, set())
        self.assertEqual(summary["fits"], [10500, 10500])
        self.assertEqual(summary["fit_total"], 21000)
        self.assertEqual(summary["evaluations"], 10500)
        self.assertEqual(summary["identity_total"], 21000)
