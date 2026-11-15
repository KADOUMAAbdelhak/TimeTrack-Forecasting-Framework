import unittest

from fgcs_strengthening_v04.src.statistics.design import DETERMINISTIC
from fgcs_strengthening_v04.src.statistics.synthesis import ResultTable, analyse, entity_for_slot
from fgcs_strengthening_v04.tests.statistics_fixtures import GENERATED_PROVENANCE, cells, slot


class PersistenceTests(unittest.TestCase):
    def test_geometric_entity_ratio_and_separate_native_macro_mae(self):
        planned = slot("R_persist", "M1", "persistence")
        rows = []
        for index, entity in enumerate(planned.cohort):
            rows += cells("M1", 4. if index == 0 else 1., entity=entity)
            rows += cells("persistence", 1., entity=entity, seeds=DETERMINISTIC)
        result = next(row for row in analyse(ResultTable(rows), GENERATED_PROVENANCE)
                      if row.slot.analysis_id == planned.analysis_id)
        self.assertAlmostEqual(result.inference.point, 4 ** (1 / 35))
        self.assertAlmostEqual(result.inference.ratio, 4 ** (1 / 35))
        self.assertNotAlmostEqual(result.inference.point, 38 / 35)
        self.assertAlmostEqual(result.details["native"]["fastStorage"]["M1"]["macro_mae"], 38 / 35)
        self.assertIsNone(result.inference.raw_p)

    def test_zero_persistence_is_undefined_with_explicit_counts(self):
        planned = slot("R_persist", "M1", "persistence")
        rows = cells("M1", 2.) + cells("persistence", 0., seeds=DETERMINISTIC)
        result = entity_for_slot(ResultTable(rows), planned, "697")
        self.assertIsNone(result.ratio)
        self.assertFalse(result.available)
        self.assertEqual(result.zeros["persistence_aggregate_zero"], 1)
        self.assertEqual(result.zeros["reference_only_zero"], 1)
