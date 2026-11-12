import json
import math
import unittest

from fgcs_strengthening_v03.src.statistics.bootstrap import Inference
from fgcs_strengthening_v03.src.statistics.schema import AnalysisRow, Provenance, extended_json
from fgcs_strengthening_v03.tests.statistics_fixtures import GENERATED_PROVENANCE, slot


class AnalysisSchemaTests(unittest.TestCase):
    def test_required_hashes_and_result_fields(self):
        for bad in (("", "2" * 64, {"x": "3" * 64}, {"y": "4" * 64}),
                    ("1" * 64, "2" * 64, {}, {"y": "4" * 64}),
                    ("1" * 64, "2" * 64, {"x": "3" * 64}, {"y": "invalid"})):
            with self.assertRaises(ValueError):
                Provenance(*bad)
        primary = slot("D", "M1", "S2")
        with self.assertRaises(ValueError):
            AnalysisRow(primary, Inference(None, raw_p=1), None, "incomplete", {}, {}, {}, 1.)
        row = AnalysisRow(primary, Inference(.2, (.1, .3), .001, 1.2), GENERATED_PROVENANCE,
                          "complete", {}, {}, {}, .024, True)
        data = row.payload()
        self.assertTrue({"analysis_id", "estimand", "candidate", "reference", "environment", "resource",
                         "cohort_definition", "n_entities", "seeds", "context_rule", "point_estimate",
                         "ratio", "ci", "raw_p", "adjusted_p", "correction_family", "predicted_direction",
                         "support_status", "zero_counts", "missing_counts", "analysis_type",
                         "protocol_sha256", "config_sha256", "source_sha256", "input_sha256"} <= data.keys())
        self.assertEqual(data["n_entities"], 35)
        json.dumps(data, allow_nan=False)
        self.assertEqual(extended_json([math.inf, -math.inf, None]), ["+inf", "-inf", None])

    def test_time_track_has_no_inferential_values(self):
        descriptive = slot("D", "M1", "S2", "TimeTrack")
        row = AnalysisRow(descriptive, Inference(.1, ratio=1.1), GENERATED_PROVENANCE, "complete", {}, {}, {})
        self.assertEqual(row.payload()["analysis_type"], "descriptive")
        self.assertEqual(row.payload()["n_entities"], 7)
        for result in (Inference(.1, raw_p=.1), Inference(.1, ci=(.01, .2))):
            with self.assertRaises(ValueError):
                AnalysisRow(descriptive, result, GENERATED_PROVENANCE, "complete", {}, {}, {})
