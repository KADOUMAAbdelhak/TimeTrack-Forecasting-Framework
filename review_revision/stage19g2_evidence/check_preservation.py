"""Hash-only preservation check; no scientific calculations or model execution."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MODE = sys.argv[1]
MAIN = 'manuscript/jss/manuscript.tex'
NEW = {'manuscript/jss/supplementary/final_evidence_supplement.tex'}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4194304), b''):
            h.update(chunk)
    return h.hexdigest()

def read(rel):
    return json.loads((ROOT / rel).read_text())

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

meta = read('review_revision/stage18c1_evidence/preservation_baseline.json')
baseline = ROOT / 'review_revision/stage18c1_evidence/preservation_before.jsonl'
assert sha(baseline) == meta['inventory_sha256']
with baseline.open() as stream:
    expected = {v['path']: v for v in map(json.loads, stream)}
overlays = dict(read('review_revision/stage19c_evidence/verification.json')['source_hashes'])
overlays.update(read('review_revision/stage19e_evidence/verification.json')['after_sha256'])
overlays.update(read('review_revision/stage19f1_evidence/verification.json')['after_sha256'])
for rel, digest in overlays.items():
    expected[rel] = dict(path=rel, sha256=digest)
assert len(expected) == 395786
if MODE == 'before':
    assert not (OUT / 'manuscript_before.tex').exists()
    assert not any((ROOT / rel).exists() for rel in NEW)
    assert sha(ROOT / MAIN) == expected[MAIN]['sha256']
    shutil.copyfile(ROOT / MAIN, OUT / 'manuscript_before.tex')
else:
    assert MODE == 'after'
    assert sha(OUT / 'manuscript_before.tex') == expected[MAIN]['sha256']

roots = ['multiresource/04_lstm_factorial', 'independent_validation/05_bitbrains_factorial',
         'independent_validation/06_materna_replication', 'manuscript/jss', 'benchmark/src',
         *['review_revision/experiments/' + name for name in
           ['s2_common_context', 's2_common_context_predecessor_stage18b1r',
            'm1_capacity_matched', 'ar_arx_baseline', 'ar_arx_baseline_predecessor_stage18b3']],
         'review_revision/stage18a1_diagnostic_audit.md']
seen = set()
unchanged = 0
for rel in roots:
    path = ROOT / rel
    files = [path] if path.is_file() else (Path(base) / name for base, dirs, names in os.walk(path) for name in names)
    for path in files:
        rel = str(path.relative_to(ROOT))
        seen.add(rel)
        if MODE == 'after' and rel in NEW | {MAIN}:
            continue
        record = expected.get(rel)
        assert record and sha(path) == record['sha256'], rel
        unchanged += 1
        if unchanged % 100000 == 0:
            print('UNCHANGED', unchanged, flush=True)
assert seen == set(expected) | (NEW if MODE == 'after' else set())
extra_inventories = {}
for stage in ['stage18c1_evidence', 'stage19g1_evidence']:
    inventory = read('review_revision/' + stage + '/output_sha256_inventory.json')
    for record in inventory['files']:
        assert sha(ROOT / record['path']) == record['sha256'], record['path']
    extra_inventories[stage] = len(inventory['files'])
refs = {key: git('rev-parse', ref) for key, ref in {
    'HEAD': 'HEAD', 'main': 'refs/heads/main', 'paper_jss': 'refs/heads/paper/jss',
    'scientific_tag_object': 'refs/tags/phase4d-materna-final-scientific-freeze-v1',
    'scientific_tag_target': 'phase4d-materna-final-scientific-freeze-v1^{}'}.items()}
assert refs == meta['refs']
assert git('branch', '--show-current') == 'paper/jss-review-revision'
assert not git('diff', '--cached', '--name-only')
subprocess.check_call(['git', 'diff', '--check'], cwd=ROOT)
result = dict(status='PASS', phase=MODE, protected_membership=len(seen),
              protected_files_unchanged=unchanged, existing_manuscript_only_allowed_change=MAIN,
              authorised_new_files=sorted(NEW) if MODE == 'after' else [],
              additional_output_inventories_verified=extra_inventories, refs=refs,
              manuscript_sha256=sha(ROOT / MAIN), scientific_modifications=0,
              training=0, model_inference=0, commit='no', push='no')
(OUT / ('preservation_' + MODE + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2), flush=True)
