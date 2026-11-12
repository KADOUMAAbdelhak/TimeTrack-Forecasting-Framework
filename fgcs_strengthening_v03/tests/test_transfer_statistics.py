import math
import unittest

from fgcs_strengthening_v03.src.statistics.design import SECONDARY, analysis_slots
from fgcs_strengthening_v03.src.statistics.synthesis import ResultTable, analyse, entity_for_slot
from fgcs_strengthening_v03.tests.statistics_fixtures import GENERATED_PROVENANCE, cells


class TransferStatisticsTests(unittest.TestCase):
    def test_f_q_signs_bootstrap_and_q_exclusion(self):
        planned = [slot for slot in analysis_slots() if slot.transfer and slot.environment == "fastStorage"
                   and slot.resource == "CPU" and slot.transfer.source_task == "THROUGHPUT"
                   and slot.transfer.scope == "all" and slot.transfer.arm == "leave_one_out"]
        F, Q = planned
        self.assertEqual((F.estimand, Q.estimand), ("F", "Q"))
        rows = []
        for entity in F.cohort:
            for model, error in ((F.reference, 8.), (F.candidate, 4.), (Q.candidate, 2.)):
                rows.extend(cells(model, error, entity=entity, seeds=SECONDARY))
        table = ResultTable(rows)
        for slot in planned:
            self.assertAlmostEqual(entity_for_slot(table, slot, "697").value, math.log(2))
        reports = {row.slot.analysis_id: row for row in analyse(table, GENERATED_PROVENANCE)}
        f, q = (reports[slot.analysis_id] for slot in planned)
        self.assertAlmostEqual(f.inference.point, math.log(2))
        self.assertEqual(f.inference.raw_p, 1 / 10001)
        self.assertAlmostEqual(f.adjusted_p, 12 / 10001)
        self.assertTrue(f.rejected)
        self.assertAlmostEqual(q.inference.point, math.log(2))
        self.assertIsNotNone(q.inference.ci)
        self.assertIsNone(q.inference.raw_p)
        self.assertIsNone(q.adjusted_p)
        self.assertIsNone(q.slot.family)

    def test_missing_transfer_cell_does_not_create_available_effect(self):
        F = next(slot for slot in analysis_slots() if slot.estimand == "F")
        data = cells(F.candidate, 2., seeds=SECONDARY)[:-1] + cells(F.reference, 3., seeds=SECONDARY)
        result = entity_for_slot(ResultTable(data), F, "697")
        self.assertFalse(result.available)
        self.assertEqual(result.issues["incomplete_grid"], 1)
