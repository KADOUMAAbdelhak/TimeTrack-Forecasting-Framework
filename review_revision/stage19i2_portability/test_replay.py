"""Public unittest suite. Uses copied compact inputs and disposable scratch only."""
import ast
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('derived_only_replay',HERE/'replay_derived.py')
replay=importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)

class CSVContract(unittest.TestCase):
    def test_plain_column_and_row_order(self):
        self.assertEqual(replay.serialize_csv([['b','a'],['02','01'],['04','03']]),b'b,a\n02,01\n04,03\n')
    def test_quote_comma(self):
        self.assertEqual(replay.serialize_csv([['x'],['a,b']]),b'x\n"a,b"\n')
    def test_quote_double_quote(self):
        self.assertEqual(replay.serialize_csv([['x'],['a"b']]),b'x\n"a""b"\n')
    def test_quote_bare_cr(self):
        self.assertEqual(replay.serialize_csv([['x'],['a\rb']]),b'x\n"a\rb"\n')
    def test_quote_lf_and_crlf(self):
        self.assertEqual(replay.serialize_csv([['x'],['a\nb'],['c\r\nd']]),b'x\n"a\nb"\n"c\r\nd"\n')
    def test_empty_fields(self):
        self.assertEqual(replay.serialize_csv([['a','b'],['','']]),b'a,b\n,\n')
    def test_utf8_no_bom(self):
        self.assertEqual(replay.serialize_csv([['x'],['mémoire']]),'x\nmémoire\n'.encode('utf-8'))
    def test_numeric_lexemes_not_normalised(self):
        self.assertEqual(replay.serialize_csv([['v'],['-0.000'],['1e-09'],['35.35714285714285900']]),
            b'v\n-0.000\n1e-09\n35.35714285714285900\n')
    def test_nonstring_rejected(self):
        with self.assertRaises(replay.ReplayError):replay.serialize_csv([['x'],[1.25]])
    def test_ragged_rejected(self):
        with self.assertRaises(replay.ReplayError):replay.serialize_csv([['a','b'],['c']])
    def test_stdlib_imports_only(self):
        tree=ast.parse((HERE/'replay_derived.py').read_text())
        imports={n.names[0].name.split('.')[0] if isinstance(n,ast.Import) else n.module.split('.')[0]
                 for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))}
        self.assertEqual(imports,{'argparse','csv','decimal','hashlib','io','json','pathlib','sys'})
        text=(HERE/'replay_derived.py').read_text()
        self.assertNotIn('subprocess',text)
        self.assertNotIn('assert ',text,'Safety guards must remain active under -O')

class ScratchReplay(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='timetrack-i2-test-')
        self.base=Path(self.temp.name)
        self.root=self.base/'compact-checkout';self.root.mkdir()
        self.manifest=json.loads((HERE/'replay_sources.json').read_text())
        for row in self.manifest['files']:
            dst=self.root/row['path'];dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/row['path'],dst)
        self.code=self.root/'review_revision/stage19i2_portability/replay_derived.py'
        self.code.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(HERE/'replay_derived.py',self.code)
        shutil.copyfile(HERE/'replay_sources.json',self.code.with_name('replay_sources.json'))
        self.out=self.base/'scratch'
    def tearDown(self):self.temp.cleanup()
    def call(self,out=None,optimised=False):
        return subprocess.run([sys.executable,'-I','-S','-B',*(['-O'] if optimised else []),str(self.code),
            '--output-dir',str(out or self.out)],cwd=self.base,text=True,capture_output=True)
    def check_success(self):
        result=self.call();self.assertEqual(result.returncode,0,result.stderr)
        checks=json.loads(result.stdout);self.assertEqual(checks['status'],'PASS')
        for name in replay.NAMES:
            self.assertEqual((self.out/name).read_bytes(),(ROOT/replay.G1/name).read_bytes())
        return checks
    def test_no_git_environment_or_models_needed(self):
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        checks=self.check_success()
        self.assertEqual(checks['source_hashes_verified'],11)
        self.assertFalse((self.root/'.git').exists())
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_unrelated_historical_head_does_not_matter(self):
        (self.root/'.git').mkdir();(self.root/'.git/HEAD').write_text('1111111111111111111111111111111111111111\n')
        self.check_success()
    def test_nonempty_output_refused(self):
        self.out.mkdir();marker=self.out/'keep.txt';marker.write_bytes(b'keep')
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertIn('OUTPUT_NOT_EMPTY',result.stderr);self.assertEqual(marker.read_bytes(),b'keep')
        self.assertEqual([p.name for p in self.out.iterdir()],['keep.txt'])
    def test_existing_empty_output_supported(self):
        self.out.mkdir();self.check_success()
    def test_inside_input_root_refused(self):
        target=self.root/'empty-scratch';target.mkdir()
        result=self.call(target);self.assertNotEqual(result.returncode,0)
        self.assertIn('OUTPUT_INSIDE_SOURCE_ROOT',result.stderr);self.assertEqual(list(target.iterdir()),[])
    def test_output_symlink_refused(self):
        destination=self.base/'elsewhere';destination.mkdir();self.out.symlink_to(destination,target_is_directory=True)
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertIn('OUTPUT_SYMLINK_REFUSED',result.stderr);self.assertEqual(list(destination.iterdir()),[])
    def test_source_tampering_fails_before_writes(self):
        path=self.root/self.manifest['files'][0]['path'];path.write_bytes(path.read_bytes()+b' ')
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertIn('SOURCE_HASH_MISMATCH',result.stderr);self.assertFalse(self.out.exists())
    def test_tampering_still_fails_under_optimisation(self):
        path=self.root/self.manifest['files'][0]['path'];path.write_bytes(path.read_bytes()+b' ')
        result=self.call(optimised=True);self.assertNotEqual(result.returncode,0)
        self.assertIn('SOURCE_HASH_MISMATCH',result.stderr);self.assertFalse(self.out.exists())
    def test_missing_source_fails_before_writes(self):
        (self.root/self.manifest['files'][0]['path']).unlink()
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertIn('SOURCE_MISSING',result.stderr);self.assertFalse(self.out.exists())
    def test_manifest_tampering_refused(self):
        path=self.code.with_name('replay_sources.json');path.write_bytes(path.read_bytes()+b' ')
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertIn('MANIFEST_HASH_MISMATCH',result.stderr);self.assertFalse(self.out.exists())
    def test_source_symlink_escape_refused(self):
        path=self.root/self.manifest['files'][0]['path'];outside=self.base/'payload.json'
        shutil.move(str(path),str(outside));path.symlink_to(outside)
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertIn('SOURCE_ESCAPES_ROOT',result.stderr);self.assertFalse(self.out.exists())
    def test_second_run_never_overwrites(self):
        self.check_success();before={p.name:p.read_bytes() for p in self.out.iterdir()}
        result=self.call();self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.out.iterdir()})
    def test_supplement_fragments_exact(self):
        self.check_success()
        for name,digest in self.manifest['authoritative_supplement_fragment_sha256'].items():
            self.assertEqual(hashlib.sha256((self.out/name).read_bytes()).hexdigest(),digest)
    def test_all_scientific_outputs_deterministic(self):
        self.check_success();second=self.base/'second';result=self.call(second)
        self.assertEqual(result.returncode,0,result.stderr)
        for p in self.out.iterdir():self.assertEqual(p.read_bytes(),(second/p.name).read_bytes())

if __name__=='__main__':
    unittest.main(verbosity=2)
