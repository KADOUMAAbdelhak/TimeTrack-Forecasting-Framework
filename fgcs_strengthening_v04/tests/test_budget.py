import json
import subprocess
import sys
import unittest

from fgcs_strengthening_v04.src.identity import ROOT


class BudgetTests(unittest.TestCase):
    def test_dry_planner_counts_and_no_training_imports(self):
        script = """
import sys
from fgcs_strengthening_v04.plan_execution import main
main([])
if {'torch', 'lightgbm', 'pandas', 'numpy'} & sys.modules.keys():
    raise RuntimeError('Dry planner imported a scientific runtime')
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["core"], [3000, 3000])
        self.assertEqual(summary["pairwise"], [1800, 1800])
        self.assertEqual(summary["leave_one_out"], [1200, 1200])
        self.assertEqual(summary["modern"], [7500, 7500])
        self.assertEqual(summary["modern_by_family"], {"DLinear": [3000, 3000], "PatchTST": [3000, 3000],
                                                       "iTransformer": [1500, 1500]})
        self.assertEqual(summary["fits"], [13500, 13500])
        self.assertEqual(summary["fit_total"], 27000)
        self.assertEqual(summary["diagnostic_slots"], 600)
        self.assertEqual(summary["gradient_extractions"], 38400)
        self.assertEqual(summary["identity_total"], 27600)
