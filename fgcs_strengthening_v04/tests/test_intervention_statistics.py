import math
import unittest

from fgcs_strengthening_v04.src.statistics.design import SECONDARY
from fgcs_strengthening_v04.src.statistics.synthesis import ResultTable, entity_for_slot
from fgcs_strengthening_v04.tests.statistics_fixtures import cells, slot


class InterventionStatisticsTests(unittest.TestCase):
    def test_signs_and_exact_registered_core_seed_slice(self):
        baseline = cells("M1", lambda f, h, s: 4. if s < 3 else 100.)
        for candidate, loss, expected, family in (
            ("PCGrad-M1", 2., -math.log(2), "PCGrad"),
            ("GradNorm-M1", 8., math.log(2), "GradNorm"),
            ("M1-task-selected", 1., -math.log(4), "checkpoint"),
        ):
            with self.subTest(candidate=candidate):
                planned = slot("D", candidate, "M1")
                table = ResultTable(baseline + cells(candidate, loss, seeds=SECONDARY))
                table.validate_domains()
                result = entity_for_slot(table, planned, "697")
                self.assertAlmostEqual(result.value, expected)
                self.assertEqual(result.native["fastStorage", "M1"], 4.)
                self.assertEqual((planned.seeds, planned.family, planned.predicted_direction),
                                 (SECONDARY, family, "negative"))

    def test_intervention_cannot_borrow_unregistered_seeds_or_environment(self):
        for data in (cells("PCGrad-M1"), cells("GradNorm-M1", block="Materna-T1", entity="74", seeds=SECONDARY)):
            with self.assertRaisesRegex(ValueError, "Unregistered"):
                ResultTable(data).validate_domains()
