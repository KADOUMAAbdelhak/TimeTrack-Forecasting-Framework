from dataclasses import replace
from functools import lru_cache
import json
import unittest
from unittest.mock import patch

import numpy as np

from fgcs_strengthening_v04.src.data_adapters import Windows
from fgcs_strengthening_v04.src.identity import ScientificIdentity
from fgcs_strengthening_v04.src.models.lightgbm import fit_horizon
from fgcs_strengthening_v04.src.provenance import DuplicateIdentity, ProvenanceError, sha256_file
from fgcs_strengthening_v04.src.tree.design import GRID, HORIZONS
from fgcs_strengthening_v04.src.tree.runner import LightGBMRunner, lightgbm_fingerprints
from fgcs_strengthening_v04.tests.training_fixtures import partition, scratch_engine


@lru_cache(maxsize=1)
def seal():
    return lightgbm_fingerprints()


def final_identity(scope):
    return ScientificIdentity("fastStorage", "697", 1, 0, "final", "lightgbm", "LightGBM",
                              ("DISK_WRITE",), scope, None, "selected")


def generated(unit, *, invalid=False):
    prepared, _ = partition(unit)
    reads = []

    class Adapter:
        def _windows(self, frame, entity, context, origins, scaler):
            role = int(origins[0])
            reads.append(role)
            rng = np.random.default_rng(200 + role + (10 if unit.phase == "final" else 0))
            n = (65 if unit.phase == "final" else 58) if role == 0 else 11
            X = rng.normal(size=(n, context, 4)).astype(np.float32)
            base = .3 * X[:, -1, :] + .4 * X[:, 0, :]
            y = (base[:, :, None] + np.arange(5)[None, None, :] / 10).astype(np.float32)
            native = np.maximum(np.expm1(y.astype(np.float64)), 0)
            if invalid and role == 1:
                native[0, 3, 0] = np.nan
            return Windows(X, y, native, np.arange(n) + role * 1000)

        def _inverse(self, scaler, scaled, target):
            raw = np.expm1(scaled)
            return np.maximum(raw, 0.), float(np.mean(raw < 0)), raw

    return replace(prepared, _adapter=Adapter()), reads


class LightGBMRunnerTests(unittest.TestCase):
    def run_wrapper(self, scope):
        final = final_identity(scope)
        reference, final_reads = generated(final)
        fit_objects = []

        def capture(config, X, y, names):
            model = fit_horizon(config, X, y, names)
            fit_objects.append((config, X.shape, model))
            return model

        with scratch_engine(seal(), closed_fits=True) as engine, patch(
                "fgcs_strengthening_v04.src.tree.runner.fit_horizon", side_effect=capture):
            runner = LightGBMRunner(engine.journal)
            with self.assertRaises(ProvenanceError):
                runner.fit_final(final, reference)
            with self.assertRaises(ProvenanceError):
                runner.evaluate(final, reference)
            self.assertEqual(final_reads, [])
            candidates = []
            for config in GRID:
                unit = replace(final, phase="inner", variant=config.variant)
                inner, reads = generated(unit)
                outcome = runner.fit_inner(unit, inner)
                self.assertEqual(reads, [0, 1])
                self.assertEqual(outcome["scalar_estimator_count"], 5)
                self.assertEqual([row["horizon"] for row in outcome["validation"]["horizons"]], list(HORIZONS))
                self.assertEqual([row["horizon"] for row in outcome["models"]], list(HORIZONS))
                candidates.append(outcome)
            winning_score, winning_config = min((e["validation"]["selection_score"], config)
                                                for config, e in zip(GRID, candidates, strict=True))
            final_record = runner.fit_final(final, reference)
            self.assertEqual(final_record["configuration"], winning_config.payload())
            self.assertEqual(final_record["selection"]["selected"]["selection_score"], winning_score)
            self.assertEqual(final_record["scalar_estimator_count"], 5)
            self.assertEqual(final_reads, [0])
            self.assertEqual(len(fit_objects), 45)
            self.assertEqual(len({id(row[2]) for row in fit_objects}), 45)
            width = 4 if scope == "own" else 16
            self.assertEqual([(row[0], row[1]) for row in fit_objects[-5:]], [(winning_config, (65, width))] * 5)
            self.assertTrue(all(row[1] == (58, width) for row in fit_objects[:40]))
            params = final_record["estimator_parameters"]
            self.assertEqual(params["estimator"]["n_estimators"], winning_config.n_estimators)
            self.assertEqual(params["estimator"]["objective"], "regression_l1")
            self.assertEqual(params["estimator"]["random_state"], 0)
            self.assertEqual(params["estimator"]["n_jobs"], 1)
            self.assertEqual(params["estimator"]["subsample"], 1.)
            self.assertEqual(params["estimator"]["colsample_bytree"], 1.)
            self.assertEqual(params["native"]["num_threads"], 1)
            self.assertTrue(params["native"]["deterministic"])
            self.assertTrue(params["native"]["force_col_wise"])
            self.assertTrue(final_record["lightgbm_version"])
            for model in final_record["models"]:
                path = engine.journal.runtime / model["artifact"]["path"]
                self.assertEqual(sha256_file(path), model["model_sha256"])
            fit_record = engine.journal.runtime / "outcomes" / f"{final.digest}.json"
            fit_sha = sha256_file(fit_record)
            with self.assertRaises(DuplicateIdentity):
                runner.fit_final(final, reference)
            self.assertEqual(final_reads, [0])
            cells = runner.evaluate(final, reference)
            self.assertEqual(final_reads, [0, 2])
            self.assertEqual([cell["horizon"] for cell in cells], list(HORIZONS))
            for cell in cells:
                self.assertEqual((cell["environment"], cell["entity"], cell["fold"], cell["target"],
                                  cell["input_scope"], cell["model_identity"]),
                                 (final.block, final.entity, final.fold, final.tasks[0], scope, final.digest))
                self.assertEqual(cell["context_sha256"], final_record["context_sha256"])
                self.assertEqual(cell["context_source_sha256"], final_record["context_source_sha256"])
                self.assertEqual(cell["support_sha256"], reference.support_sha256)
                self.assertEqual(cell["scaler_sha256"], reference.scaler_sha256)
                self.assertEqual(cell["outer_test_sha256"], reference.split_hashes["outer_test"])
                self.assertTrue(np.isfinite(cell["native_mae"]))
            with self.assertRaises(DuplicateIdentity):
                runner.evaluate(final, reference)
            self.assertEqual(final_reads, [0, 2])
            self.assertEqual(sha256_file(fit_record), fit_sha)
            logged = engine.journal.runtime / "evaluations" / "outcomes" / f"{final.digest}.json"
            outcome = json.loads(logged.read_text())
            self.assertEqual(outcome["fingerprint_sha256"], seal().digest)
            self.assertEqual(outcome["evidence"]["final_outcome_sha256"], fit_sha)
        return ([e["validation"] for e in candidates], [e["models"] for e in candidates],
                final_record["configuration"], final_record["models"], cells)

    def test_deterministic_selection_models_and_predictions_in_both_scopes(self):
        for scope in ("own", "all"):
            with self.subTest(scope=scope):
                self.assertEqual(self.run_wrapper(scope), self.run_wrapper(scope))

    def test_invalid_inner_evidence_is_terminal_without_final_or_outer_test(self):
        final = final_identity("own")
        inner = replace(final, phase="inner", variant=GRID[0].variant)
        prepared, reads = generated(inner, invalid=True)
        with scratch_engine(seal(), closed_fits=True) as engine:
            runner = LightGBMRunner(engine.journal)
            with self.assertRaisesRegex(ValueError, "Nonfinite LightGBM target"):
                runner.fit_inner(inner, prepared)
            outcome = engine.journal.runtime / "outcomes" / f"{inner.digest}.json"
            digest = sha256_file(outcome)
            self.assertEqual(json.loads(outcome.read_text())["status"], "failed")
            with self.assertRaises(DuplicateIdentity):
                runner.fit_inner(inner, prepared)
            self.assertEqual(reads, [0, 1])
            outer, outer_reads = generated(final)
            with self.assertRaises(ProvenanceError):
                runner.fit_final(final, outer)
            self.assertEqual(outer_reads, [])
            self.assertEqual(sha256_file(outcome), digest)


    def test_tampered_model_fails_evaluation_before_outer_access(self):
        final = final_identity("own")
        outer, reads = generated(final)
        with scratch_engine(seal(), closed_fits=True) as engine:
            runner = LightGBMRunner(engine.journal)
            for config in GRID:
                inner = replace(final, phase="inner", variant=config.variant)
                runner.fit_inner(inner, generated(inner)[0])
            fitted = runner.fit_final(final, outer)
            path = engine.journal.runtime / fitted["models"][0]["artifact"]["path"]
            path.write_bytes(b"tampered synthetic LightGBM model")
            with self.assertRaisesRegex(ProvenanceError, "Artifact bytes differ"):
                runner.evaluate(final, outer)
            self.assertEqual(reads, [0])
            logged = engine.journal.runtime / "evaluations" / "outcomes" / f"{final.digest}.json"
            outcome = json.loads(logged.read_text())
            self.assertEqual(outcome["status"], "failed")
            self.assertNotIn("cells", outcome["evidence"])
            with self.assertRaises(DuplicateIdentity):
                runner.evaluate(final, outer)
