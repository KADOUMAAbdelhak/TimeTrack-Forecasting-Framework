"""Small synthetic checks only: no frozen scientific fits or test evaluations."""
import unittest
import numpy as np
import pandas as pd
import run_linear_control as r

class SafetyTests(unittest.TestCase):
    def test_configuration(self):
        c = r.read(r.CONFIG)
        self.assertEqual(c["alphas"],[.01,.1,1.,10.,100.])
        self.assertEqual(c["seeds"],[])
        self.assertEqual(c["expected_inner"],910*4*2*5)
        self.assertEqual(c["expected_final"],910*4*2)
        self.assertEqual(c["expected_metric_rows"],35*8*8+875*8*5)
    def test_scope_guard(self):
        with self.assertRaises(r.frozen.Conflict): r.output(r.ROOT/"manuscript/jss/forbidden")
    def test_input_scope(self):
        X = np.arange(12*4*4).reshape(12,4,4)
        for i in range(4):
            self.assertTrue(np.array_equal(r.inputs(X,"AR",i),X[:,:,i:i+1]))
            self.assertTrue(np.array_equal(r.inputs(X,"ARX",i),X))
    def test_deterministic_multioutput_and_training_scaler(self):
        rng = np.random.default_rng(418)
        X = rng.normal(size=(32,4,4)); y = rng.normal(size=(32,5))
        m = r.ridge_class()(1).fit(X,y)
        mean = m.scaler.mean_.copy()
        p = m.predict(X[:7]+1000)
        self.assertEqual(p.shape,(7,5))
        self.assertTrue(np.array_equal(mean,m.scaler.mean_))
        self.assertTrue(np.allclose(mean,X.reshape(32,-1).mean(axis=0)))
        m2 = r.ridge_class()(1).fit(X,y)
        self.assertTrue(np.array_equal(p,m2.predict(X[:7]+1000)))
        self.assertEqual(m.model.random_state,None)
    def test_fixed_context_alpha_tie(self):
        frame = pd.DataFrame({"context_length":[9]*5,"alpha":[100,10,1,.1,.01],"inner_validation_mae":[1.]*5})
        s = r.selector()(frame,"Ridge")
        self.assertEqual(s.context_length,9); self.assertEqual(s.alpha,.01)
    def test_selector_refuses_test_column(self):
        frame = pd.DataFrame({"context_length":[9],"alpha":[1],"inner_validation_mae":[1.],"test_mae":[0.]})
        with self.assertRaises(ValueError): r.selector()(frame,"Ridge")
    def test_identity_has_no_artificial_seed(self):
        spec = {"namespace":"test","configuration_sha256":"c","group_id":"g","block":"TimeTrack","entity":"machine01","fold":1,"L":32,"inner_support":"i","final_support":"f","scalers":{"inner":{},"final":{}}}
        ids = [r.ident(spec,"inner",f,res,a) for f in ("AR","ARX") for res in r.read(r.CONFIG)["resources"] for a in r.read(r.CONFIG)["alphas"]]
        self.assertEqual(len({i["run_id"] for i in ids}),40)
        self.assertTrue(all("seed" not in i for i in ids))
        with self.assertRaises(r.frozen.Conflict): r.ident(spec,"final","AR","CPU",1)
    def test_nonfinite_primary_stops(self):
        for v in (float("nan"),float("inf"),-float("inf")):
            with self.assertRaises(r.frozen.Conflict): r.frozen.finite_primary([v])

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    r.write(r.HERE/"validation/tests.json", {"status":"PASS" if result.wasSuccessful() else "FAIL","tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"scope":"synthetic and non-training safety checks; not scientific replications","timestamp":r.now()})
    raise SystemExit(not result.wasSuccessful())
