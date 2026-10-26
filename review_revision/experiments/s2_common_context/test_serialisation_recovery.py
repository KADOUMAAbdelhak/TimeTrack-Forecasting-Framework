"""Stage18B1R regressions: no training, inference or scientific outcome changes."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_control as c


class SerialisationTests(unittest.TestCase):
    def prediction(self):
        return pd.DataFrame({"y_true":[0.,0.], "y_pred":[.1,.2], "y_pred_scaled":[.1,.2], "y_pred_unclipped":[.1,.2], "origin_index":[0,1], "target_index":[1,2], "lead":[1,1], "selected_L":[18,18], "selected_epoch":[48,48], "seed":[0,0], "fold":[2,2], "support_hash":["support","support"], "origin_timestamp_seconds":[100,200], "target_timestamp_seconds":[200,300]})

    def original(self):
        return {"metrics":[{"lead":1,"mae":.15,"r2":float("nan"),"persistence_skill":float("nan")}], "persistence_metrics":[{"lead":1,"mae":0.}]}

    def assert_primary_conflict(self, fn):
        with self.assertRaises(c.Conflict) as caught: fn()
        self.assertEqual(caught.exception.code,"PRIMARY_NONFINITE_RESULT_CONFLICT")

    def test_A_constant_target_r2(self):
        rows,_=c.strict_reuse_metrics(self.original(),self.prediction())
        self.assertIsNone(rows[0]["r2"])
        self.assertEqual(rows[0]["r2_status"],"undefined_zero_target_variance")

    def test_B_zero_persistence_mae(self):
        rows,_=c.strict_reuse_metrics(self.original(),self.prediction())
        self.assertIsNone(rows[0]["persistence_skill"])
        self.assertEqual(rows[0]["persistence_skill_status"],"undefined_zero_persistence_mae")

    def test_C_finite_ancillary_unchanged(self):
        original=self.original();original["metrics"][0].update(r2=.123456789,persistence_skill=-2.5)
        rows,semantics=c.strict_reuse_metrics(original,self.prediction())
        self.assertEqual(rows,original["metrics"]);self.assertEqual(semantics,[])

    def test_D_nan_primary_mae(self):
        original=self.original();original["metrics"][0]["mae"]=float("nan")
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(original,self.prediction()))

    def test_E_nan_prediction(self):
        pred=self.prediction();pred.loc[0,"y_pred"]=float("nan")
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(self.original(),pred))

    def test_F_strict_json_and_raw_semantics(self):
        rows,semantics=c.strict_reuse_metrics(self.original(),self.prediction())
        value=json.loads(json.dumps({"metrics":rows,"original_raw_ancillary_semantics":semantics},allow_nan=False))
        self.assertEqual(value["metrics"][0]["mae"],.15)
        self.assertEqual([s["original_raw_value"] for s in semantics],["NaN","NaN"])

    def test_H_source_payload_unchanged(self):
        original=self.original();before=json.dumps(original,sort_keys=True)
        c.strict_reuse_metrics(original,self.prediction())
        self.assertEqual(json.dumps(original,sort_keys=True),before)

    def test_I_finite_payload_semantically_unchanged(self):
        original=self.original();original["metrics"][0].update(r2=0.,persistence_skill=.5)
        rows,semantics=c.strict_reuse_metrics(original,self.prediction())
        self.assertEqual(json.loads(json.dumps(rows,allow_nan=False)),original["metrics"])
        self.assertFalse(semantics)

    def test_unknown_nonfinite_metric_rejected(self):
        original=self.original();original["metrics"][0]["rmse"]=float("nan")
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(original,self.prediction()))

    def test_infinite_r2_not_zero_variance_marker(self):
        original=self.original();original["metrics"][0]["r2"]=float("inf")
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(original,self.prediction()))

    def test_nan_r2_nonconstant_target_rejected(self):
        pred=self.prediction();pred.loc[1,"y_true"]=1.
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(self.original(),pred))

    def test_nan_skill_positive_reference_rejected(self):
        original=self.original();original["persistence_metrics"][0]["mae"]=1.
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(original,self.prediction()))

    def test_nan_target_rejected(self):
        pred=self.prediction();pred.loc[0,"y_true"]=np.nan
        self.assert_primary_conflict(lambda:c.strict_reuse_metrics(self.original(),pred))

    def test_nonfinite_epoch_context_scaler_identity(self):
        for key in ("epoch","L","scaler","support_identity"):
            with self.subTest(key=key):self.assert_primary_conflict(lambda:c.finite_primary({key:float("inf")}))

    def test_missing_timestamp_rejected(self):
        pred=self.prediction();pred.loc[0,"target_timestamp_seconds"]=np.nan
        self.assert_primary_conflict(lambda:c.validate_prediction_primary(pred))

    def test_nan_scaled_or_unclipped_prediction_rejected(self):
        for key in ("y_pred_scaled","y_pred_unclipped"):
            pred=self.prediction();pred.loc[0,key]=np.nan
            with self.subTest(key=key):self.assert_primary_conflict(lambda:c.validate_prediction_primary(pred))

    def test_duplicate_scientific_identity_guard(self):
        with self.assertRaises(c.Conflict) as caught:c.require(False,"duplicate","CONTROL_COMPLETION_DUPLICATION_CONFLICT")
        self.assertEqual(caught.exception.code,"CONTROL_COMPLETION_DUPLICATION_CONFLICT")


class ExactFrozenReuseIntegration(unittest.TestCase):
    def test_G_H_failing_frozen_reuse_has_no_training_or_inference(self):
        real_here=c.HERE
        plan=c.read(real_here/"plans/Rnd.json")
        spec=next(s for s in plan["tasks"] if s["control_run_id"]=="518ea20860f5e00b03261916d14c5051f5a5a71fea5bd44336a813db7f326481")
        source=c.ROOT/spec["original_completion"];before=c.sha(source);original=c.read(source)
        engine=c.Engine("Rnd")
        parent=real_here/"recovery/test_tmp";parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp, mock.patch.object(c,"HERE",Path(temp)), mock.patch.object(c,"_ENGINE",engine), mock.patch.object(c,"_RECOVERING",False), mock.patch.object(engine.core,"fit_final_model",side_effect=AssertionError("Reuse trained")) as fit, mock.patch.object(engine.core,"build_model",side_effect=AssertionError("Reuse instantiated network")) as build:
            c.run_group([spec])
            result=c.read(Path(temp)/f"completions/Rnd/{spec['control_run_id']}.json")
            fit.assert_not_called();build.assert_not_called()
            self.assertTrue(result["reuse"] and result["no_training"] and result["no_new_test_evaluation"])
            self.assertEqual(result["test_evaluations"],0)
            self.assertEqual([r["mae"] for r in result["metrics"]],[r["mae"] for r in original["metrics"]])
            self.assertEqual(result["prediction_sha256"],original["prediction_sha256"])
            self.assertEqual(result["model_sha256"],original["model_sha256"])
            self.assertEqual(result["original_completion_sha256"],before)
            self.assertEqual(len(result["original_raw_ancillary_semantics"]),10)
            json.dumps(result,allow_nan=False)
        self.assertEqual(c.sha(source),before)


if __name__=="__main__":unittest.main()
