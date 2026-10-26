"""No training: fail-closed namespace, provenance and interpretation tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("run_control",Path(__file__).with_name("run_control.py"))
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)


class ControlTests(unittest.TestCase):
    def test_repository_root(self):
        self.assertEqual(str(control.ROOT),"/Users/fgtek002/TimeTrack")

    def test_no_frozen_write(self):
        with self.assertRaises(control.Conflict):
            control.output(control.ROOT/"manuscript/jss/forbidden-test-output")

    def test_child_path_allowed(self):
        self.assertEqual(control.output(control.HERE/"unit_test_allowed.json"),control.HERE/"unit_test_allowed.json")

    def test_canonical_order(self):
        self.assertEqual(control.canonical({"a":1,"b":2}),control.canonical({"b":2,"a":1}))

    def test_nonfinite_identity_rejected(self):
        with self.assertRaises(ValueError):control.canonical({"x":float("nan")})

    def test_failure_status(self):
        with self.assertRaises(control.Conflict) as caught:
            control.require(False,"missing unit","S2_COMMON_CONTEXT_INNER_RECORD_MISSING")
        self.assertEqual(caught.exception.code,"S2_COMMON_CONTEXT_INNER_RECORD_MISSING")

    def test_exact_identity_required(self):
        from types import SimpleNamespace
        engine=SimpleNamespace()
        with self.assertRaises(control.Conflict):
            control.validate_completion(engine,{"L":18},{"spec":{"L":9},"status":"complete"})

    def test_six_blocks(self):
        self.assertEqual(len(control.FROZEN),6)

    def test_refs_read_only(self):
        control.verify_refs()

    def test_category_and_gain(self):
        import sys
        sys.path.insert(0,str(control.HERE))
        from analyse_control import category,gain
        self.assertEqual(category(-20,-10),"GAP_REDUCED")
        self.assertEqual(category(-20,1),"GAP_REVERSED")
        self.assertEqual(category(-20,0),"GAP_REMOVED")
        self.assertEqual(category(-20,-21),"GAP_LARGELY_UNCHANGED")
        self.assertEqual(gain(120,100),-20)


if __name__=="__main__":unittest.main()
