"""No training: architecture, selection, identity and fail-closed safety tests."""
import argparse
import copy
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import run_capacity_control as c


class SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=c.configure_engine(BLOCK)

    def test_01_exact_parameters(self):
        e=self.e; m=e.core.build_model("M1",4)
        self.assertEqual(c.verify_model(e,m),207980 if e.tt else 206420)
        S=importlib_module("src.models").SingleTargetLSTM
        aggregate=4*sum(p.numel() for p in S(4).parameters())
        self.assertEqual(aggregate,206880 if e.tt else 206100)

    def test_02_wrong_factory_fails(self):
        for f,n in [("S2",4),("M1",1)]:
            with self.assertRaises(c.frozen.Conflict):self.e.core.build_model(f,n)

    def test_03_forward_shapes_no_training(self):
        e=self.e; e.core.set_seed(0); model=e.core.build_model("M1",4).eval()
        with e.torch.no_grad(): p=model(e.torch.zeros(2,4,4))
        self.assertEqual(tuple(p.shape),(2,4,len(e.leads)))

    def test_04_fresh_selection_and_epochs(self):
        e=self.e; rows=[]
        for L in c.lengths(e):
            for seed in (0,1,2): rows.append(e.core.SelectionRow("M1",L,seed,e.np.full((4,len(e.leads)),0 if L==c.lengths(e)[-1] else 1),seed+3))
        result=e.core.select_context(rows,"M1")
        self.assertEqual(result.context_length,c.lengths(e)[-1]); self.assertEqual(result.best_epoch_by_seed,{0:3,1:4,2:5})

    def test_05_short_context_tie(self):
        e=self.e; rows=[e.core.SelectionRow("M1",L,s,e.np.ones((4,len(e.leads))),2) for L in c.lengths(e) for s in (0,1,2)]
        self.assertEqual(e.core.select_context(rows,"M1").context_length,min(c.lengths(e)))

    def test_06_missing_seed_fails(self):
        with self.assertRaises(ValueError):self.e.core.select_context([],"M1")

    def test_07_nonfinite_primary_fails(self):
        for value in [float("nan"),float("inf"),None]:
            with self.assertRaises(c.frozen.Conflict):c.frozen.finite_primary({"mae":value})

    def test_08_no_outside_writes(self):
        with self.assertRaises(c.frozen.Conflict):c.output(c.PRIOR/"forbidden.json")

    def test_09_unchanged_training_primitives(self):
        e=self.e; t=importlib_module("src.training")
        self.assertIs(e.core.fit_inner,t.fit_inner)
        self.assertEqual(Path(inspect.getfile(e.core.fit_final_model)).resolve(),Path(e.core.__file__).resolve())
        self.assertNotIn("outer",str(inspect.signature(t.fit_inner)))

    def test_10_config(self):
        cfg=c.read(c.CONFIG)
        self.assertEqual(cfg["hidden_size"],129);self.assertEqual(cfg["seeds"],[0,1,2])
        self.assertEqual((cfg["learning_rate"],cfg["batch_size"],cfg["max_epochs"],cfg["patience"],cfg["gradient_clip"]),(.001,256,50,7,1.0))

    def test_11_formula(self):
        self.assertEqual(c.parameter_formula(4,129,20),206420)
        self.assertEqual(c.parameter_formula(4,129,32),207980)

    def test_12_strict_json(self):
        payload={"label":c.LABEL,"score":[[0.,1.]],"hidden_size":129}
        self.assertEqual(json.loads(json.dumps(payload,allow_nan=False)),payload)

    def test_13_attempt_no_retry(self):
        with tempfile.TemporaryDirectory(dir=c.HERE) as directory:
            with patch.object(c,"HERE",Path(directory)):
                ident={"phase":"inner","block":"test","run_id":"unit"}
                c.attempt(ident)
                with self.assertRaises(c.frozen.Conflict):c.attempt(ident)

    def test_14_identity_changes_only_on_scientific_fields(self):
        spec={"namespace":"test","configuration_sha256":"cfg","group_id":"g","block":BLOCK,"entity":"e","fold":1,"contexts":{"4":{"inner_support":"s","outer_support":"t","inner_scaler":{"scale":1},"outer_scaler":{"scale":2}}}}
        a=c.identity(spec,"inner",4,0);b=c.identity(spec,"inner",4,1)
        self.assertNotEqual(a["run_id"],b["run_id"])
        self.assertEqual(a,c.identity(spec,"inner",4,0))
        with self.assertRaises(c.frozen.Conflict):c.identity(spec,"final",4,0)

    def test_15_nan_prediction_fails(self):
        e=self.e
        row={k:1. for k in ["y_true","y_pred","y_pred_scaled","origin_index","target_index","lead","selected_L","selected_epoch","seed","fold"]};row["support_hash"]="h";row["y_pred"]=float("nan")
        with self.assertRaises(c.frozen.Conflict):c.frozen.validate_prediction_primary(e.pd.DataFrame([row]))

    def test_16_completed_identity_no_training(self):
        e=self.e
        with tempfile.TemporaryDirectory(dir=c.HERE) as directory:
            with patch.object(c,"HERE",Path(directory)):
                path=Path(directory)/"model.pt";path.write_bytes(b"test fixture, not a trained model")
                ident={"phase":"inner","run_id":"x"}
                val={"identity":ident,"status":"complete","parameter_count":207980 if e.tt else 206420,"test_evaluations":0,"model_path":str(path),"model_sha256":c.sha(path),"validation_score":[[1.]]}
                with patch.object(e.core,"fit_inner",side_effect=AssertionError("No training allowed")):
                    c.validate_completion(e,ident,val)
                val["identity"]={"phase":"inner","run_id":"changed"}
                with self.assertRaises(c.frozen.Conflict):c.validate_completion(e,ident,val)


def importlib_module(name):
    import importlib
    return importlib.import_module(name)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--block");args=parser.parse_args()
    if args.block:
        BLOCK=args.block
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests))
        sys.exit(0 if result.wasSuccessful() else 1)
    results=[]
    for block in ("TimeTrack","fastStorage","Materna-T1"):
        p=subprocess.run([sys.executable,"-B",__file__,"--block",block],capture_output=True,text=True)
        print(p.stdout+p.stderr,flush=True);results.append({"block":block,"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr})
    passed=all(p["exit_code"]==0 for p in results)
    c.write(c.HERE/"validation/tests.json",{"status":"PASS" if passed else "FAIL","test_cases":48,"training_runs_launched":0,"results":results,"timestamp":c.now()})
    sys.exit(0 if passed else 1)
