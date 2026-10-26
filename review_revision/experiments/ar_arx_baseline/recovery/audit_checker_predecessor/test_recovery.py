"""Recovery regression checks. Reads frozen arrays; no scientific fits/inference."""
import ast
import difflib
import json
import multiprocessing as mp
from pathlib import Path
import pickle
import subprocess
import sys
import unittest
import numpy as np
import run_linear_control as r
from test_linear_control import SafetyTests

def fail_for_transport():
    raise r.transport_error("PERSISTENCE_REFERENCE_CONFLICT","synthetic mismatch")

class RecoveryTests(unittest.TestCase):
    def test_config_and_scientific_helpers_unchanged(self):
        snapshot = Path(r.read(r.HERE/"recovery/predecessor_snapshot.json")["snapshot_path"])
        self.assertEqual((snapshot/"control_config.json").read_bytes(),r.CONFIG.read_bytes())
        self.assertEqual(r.sha(r.CONFIG),"ae97a89cb1e8034890256fa8f21ea242fa729fcb725be43088be7552e1309626")
        old = ast.parse((snapshot/"run_linear_control.py").read_text())
        new = ast.parse((r.HERE/"run_linear_control.py").read_text())
        functions = ("ident","inputs","choose","arrays","inverse","checked_data","ridge_class","selector","model_state","reference_frame","plan_block")
        for name in functions:
            a = next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
            b = next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(a),ast.dump(b),name)
        def scientific_calls(tree):
            group = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_group")
            return [ast.dump(n) for n in ast.walk(group) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ("fit","predict")]
        self.assertEqual(scientific_calls(old),scientific_calls(new))
    def test_worker_error_transport(self):
        error = r.transport_error("PERSISTENCE_REFERENCE_CONFLICT","synthetic mismatch")
        self.assertEqual(str(pickle.loads(pickle.dumps(error))),str(error))
        with mp.get_context("spawn").Pool(1) as pool:
            with self.assertRaisesRegex(RuntimeError,"PERSISTENCE_REFERENCE_CONFLICT"):
                pool.apply_async(fail_for_transport).get(timeout=20)
    def test_all_timetrack_references_and_old_blocker(self):
        e = r.frozen.Engine("TimeTrack"); nref = 0; old_conflicts = 0
        for spec in r.read(r.HERE/"plans/TimeTrack.json")["groups"]:
            frame,fold,scaler = r.checked_data(e,spec,"final")
            X,y,_ = e.windows(frame,spec["entity"],spec["L"],fold.outer_test)
            record = r.read(spec["reference_record"])
            for i,resource in enumerate(e.resources):
                persistence = np.repeat(X[:,-1,i,None],len(e.leads),axis=1)
                old = np.mean(np.abs(y[:,i,:]-persistence),axis=0)
                corrected = r.persistence_reference_mae(np,y[:,i,:],persistence,True)
                expected = np.array([next(m["mae"] for m in record["persistence_metrics"] if m["resource"]==resource and m["lead"]==lead) for lead in e.leads])
                self.assertTrue(np.array_equal(corrected,expected),(spec["entity"],spec["fold"],resource))
                r.verify_persistence_reference(np,record,resource,e.leads,corrected)
                if resource=="CPU":
                    with self.assertRaises(r.frozen.Conflict): r.verify_persistence_reference(np,record,resource,e.leads,old)
                    old_conflicts += 1
                # Frozen skill's float32 denominator is unchanged by the fix.
                self.assertTrue(np.array_equal(old,np.mean(np.abs(y[:,i,:]-persistence),axis=0)))
                nref += len(e.leads)
        self.assertEqual(old_conflicts,35); self.assertEqual(nref,1120)
    def test_real_mismatch_fails(self):
        record = {"persistence_metrics":[{"resource":"CPU","lead":1,"mae":2.0}]}
        r.verify_persistence_reference(np,record,"CPU",[1],np.array([2.0]))
        with self.assertRaisesRegex(r.frozen.Conflict,"PERSISTENCE_REFERENCE_CONFLICT"):
            r.verify_persistence_reference(np,record,"CPU",[1],np.array([2.001]))
    def test_external_unchanged(self):
        for block in r.read(r.CONFIG)["blocks"][1:]:
            subprocess.run([sys.executable,"-B",str(Path(__file__)),"--external",block],cwd=r.ROOT,check=True)

def external(block):
    e = r.frozen.Engine(block); spec = r.read(r.HERE/f"plans/{block}.json")["groups"][0]
    frame,fold,scaler = r.checked_data(e,spec,"final")
    X,y,_ = e.windows(frame,spec["entity"],spec["L"],fold.outer_test)
    record = r.read(spec["reference_record"])
    for i,resource in enumerate(e.resources):
        persistence = np.repeat(X[:,-1,i,None],len(e.leads),axis=1)
        previous = np.mean(np.abs(y[:,i,:]-persistence),axis=0)
        current = r.persistence_reference_mae(np,y[:,i,:],persistence,False)
        r.require(np.array_equal(previous,current),"External arithmetic changed")
        r.verify_persistence_reference(np,record,resource,e.leads,current)
    print("EXTERNAL_UNCHANGED",block,flush=True)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--external": external(sys.argv[2]); raise SystemExit(0)
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests),unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryTests)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    r.write(r.HERE/"recovery/tests.json", {"status":"PASS" if result.wasSuccessful() else "FAIL","tests":result.testsRun,"original_safety_tests":8,"recovery_regression_tests":5,"timetrack_reference_values":1120,"old_float32_blockers_reproduced":35,"external_blocks_unchanged":5,"scientific_config_changes":0,"scientific_fits_or_inference_by_regressions":0,"failures":len(result.failures),"errors":len(result.errors),"timestamp":r.now()})
    raise SystemExit(not result.wasSuccessful())
