from contextlib import redirect_stdout
from dataclasses import asdict
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fgcs_strengthening_v04.analyse_study import dry_plan, load_bundle, main
from fgcs_strengthening_v04.src.statistics.design import analysis_slots, expected_identity
from fgcs_strengthening_v04.src.statistics.synthesis import ResultTable
from fgcs_strengthening_v04.tests.statistics_fixtures import GENERATED_PROVENANCE, cells


class AnalysisPlanTests(unittest.TestCase):
    def test_dry_plan_is_data_free_and_complete(self):
        with patch("fgcs_strengthening_v04.analyse_study.load_bundle", side_effect=AssertionError("dry result read")):
            result = dry_plan(enumerate_slots=True)
            out = io.StringIO()
            with redirect_stdout(out):
                main(["--dry-run"])
        self.assertEqual(json.loads(out.getvalue())["inference_slots"], 156)
        self.assertEqual(len(result["slots"]), result["total_rows"])
        self.assertEqual(len({row["analysis_id"] for row in result["slots"]}), result["total_rows"])
        self.assertEqual(result["descriptive"]["Q"], 48)
        self.assertEqual(sum(result["holm_families"].values()), 60)
        self.assertEqual(sum(result["bh_families"].values()), 96)
        time_track = [item for item in analysis_slots() if item.environment == "TimeTrack"]
        self.assertTrue(all(not item.inferential and not item.interval for item in time_track))

    def test_manifest_validation_hash_check_and_synthetic_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            tables = {"cells": cells("M1", 2.) + cells("S2", 0.), "diagnostics": []}
            artifacts = {}
            for key, rows in tables.items():
                data = "".join(json.dumps(asdict(row)) + "\n" for row in rows).encode()
                name = f"{key}.jsonl"
                (base / name).write_bytes(data)
                artifacts[key] = {"path": name, "sha256": sha256(data).hexdigest()}
            provenance = GENERATED_PROVENANCE.payload()
            provenance.pop("source_sha256")
            provenance.pop("input_sha256")
            path = base / "manifest.json"
            path.write_text(json.dumps({"mode": "synthetic", "provenance": provenance, "artifacts": artifacts}))
            table, checked, mode = load_bundle(path, mode="synthetic")
            self.assertEqual(mode, "synthetic")
            self.assertEqual(checked.input_hashes["bundle:cells"], artifacts["cells"]["sha256"])
            with self.assertRaisesRegex(ValueError, "mode"):
                load_bundle(path, mode="scientific")
            with self.assertRaisesRegex(ValueError, "Missing normalised"):
                table.validate_domains(complete=True)
            validation = io.StringIO()
            with redirect_stdout(validation), patch("fgcs_strengthening_v04.analyse_study.analyse",
                                                     side_effect=AssertionError("validation computed statistics")):
                main(["--validate", str(path)])
            self.assertEqual(json.loads(validation.getvalue())["status"], "validated")
            out = io.StringIO()
            with redirect_stdout(out):
                main(["--synthetic-input", str(path)])
            result = json.loads(out.getvalue())
            row = next(row for row in result["rows"] if row["analysis_id"] == "D/M1/S2/fastStorage/CPU")
            self.assertEqual(row["raw_p"], 1.)
            self.assertEqual(row["adjusted_p"], 1.)
            self.assertEqual(row["zero_counts"]["reference_only_zero"], 1)
            self.assertEqual(row["details"]["entity_effects"]["697"]["log_effect"], "+inf")
            (base / "cells.jsonl").write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "Artifact SHA-256 mismatch"):
                load_bundle(path)

    def test_descriptive_scopes_reject_incompatible_seed_and_cohort_inputs(self):
        for data in (cells("Ridge-AR", seeds=(0,)),
                     cells("LightGBM-all", seeds=(1,)),
                     cells("DLinear-shared", entity="289", seeds=(0,))):
            with self.assertRaises(ValueError):
                ResultTable(data).validate_domains()


    def test_exact_normalised_identity_mapping(self):
        cases = (
            ("S1", 4, "core", "S1", "baseline"),
            ("PCGrad-M1", 2, "pcgrad", "M1", "pcgrad"),
            ("M1-task-selected", 1, "checkpoint_request", "M1", "task_selected"),
            ("M0/CPU+MEMORY", 0, "pairwise", "M0", "baseline"),
            ("LightGBM-own", 0, "lightgbm", "LightGBM", "selected"),
            ("iTransformer-shared", 0, "modern", "iTransformer", "shared"),
        )
        for model, seed, arm, family, variant in cases:
            with self.subTest(model=model):
                row = cells(model, seeds=(seed,))[0]
                unit = expected_identity(row)
                self.assertEqual((unit.arm, unit.formulation, unit.variant), (arm, family, variant))
                self.assertEqual((unit.block, unit.entity, unit.fold, unit.seed, unit.phase),
                                 (row.block, row.entity, row.fold, row.seed, "final"))
