import json
import subprocess
import sys
import unittest

from fgcs_strengthening_v04a1.src.identity import ROOT


class BudgetTests(unittest.TestCase):
    def test_dry_planner_counts_and_no_training_imports(self):
        script = """
import sys
from fgcs_strengthening_v04a1.plan_execution import main
main([])
if {'torch', 'lightgbm', 'pandas', 'numpy'} & sys.modules.keys():
    raise RuntimeError('Dry planner imported a scientific runtime')
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        summary = json.loads(result.stdout)
        # Amendment A1 schedules only the loss-balancing M1 fits and their D-4 slots.
        self.assertEqual(summary["intervention"], [600, 600])
        self.assertEqual(summary["intervention_by_mode"], {"gradnorm": [300, 300], "uncertainty": [300, 300]})
        self.assertEqual(set(summary) & {"core", "pairwise", "leave_one_out", "modern"}, set())
        self.assertEqual(summary["fits"], [600, 600])
        self.assertEqual(summary["fit_total"], 1200)
        self.assertEqual(summary["diagnostic_slots"], 600)
        self.assertEqual(summary["gradient_extractions"], 38400)
        self.assertEqual(summary["identity_total"], 1800)
