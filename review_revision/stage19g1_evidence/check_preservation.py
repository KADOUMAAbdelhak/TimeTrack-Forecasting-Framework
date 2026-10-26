"""Verify protected source/results against the previously audited frozen inventory."""
from pathlib import Path
import hashlib, json, os, subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as s:
        for b in iter(lambda:s.read(4194304),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
meta=read('review_revision/stage18c1_evidence/preservation_baseline.json')
p=ROOT/'review_revision/stage18c1_evidence/preservation_before.jsonl'
assert sha(p)==meta['inventory_sha256']
expected={v['path']:v for v in map(json.loads,p.open())}
overlays=dict(read('review_revision/stage19c_evidence/verification.json')['source_hashes'])
overlays.update(read('review_revision/stage19e_evidence/verification.json')['after_sha256'])
overlays.update(read('review_revision/stage19f1_evidence/verification.json')['after_sha256'])
for rel,h in overlays.items():
    assert sha(ROOT/rel)==h,rel
    expected[rel]=dict(path=rel,bytes=(ROOT/rel).stat().st_size,sha256=h)
roots=['multiresource/04_lstm_factorial','independent_validation/05_bitbrains_factorial',
'independent_validation/06_materna_replication','manuscript/jss','benchmark/src',
*['review_revision/experiments/'+n for n in ['s2_common_context','s2_common_context_predecessor_stage18b1r',
'm1_capacity_matched','ar_arx_baseline','ar_arx_baseline_predecessor_stage18b3']],
'review_revision/stage18a1_diagnostic_audit.md']
seen=set()
for rel in roots:
    p=ROOT/rel
    for f in ([p] if p.is_file() else (Path(b)/n for b,ds,fs in os.walk(p) for n in fs)):
        rel=str(f.relative_to(ROOT));seen.add(rel);v=expected.get(rel)
        assert v and f.stat().st_size==v['bytes'] and sha(f)==v['sha256'],rel
        if len(seen)%100000==0:print('PROTECTED_VERIFIED',len(seen),flush=True)
assert seen==set(expected) and len(seen)==395786
inv=read('review_revision/stage18c1_evidence/output_sha256_inventory.json')
for v in inv['files']:assert sha(ROOT/v['path'])==v['sha256'],v['path']
refs={k:git('rev-parse',r) for k,r in {'HEAD':'HEAD','main':'refs/heads/main','paper_jss':'refs/heads/paper/jss',
'scientific_tag_object':'refs/tags/phase4d-materna-final-scientific-freeze-v1',
'scientific_tag_target':'phase4d-materna-final-scientific-freeze-v1^{}'}.items()}
assert refs==meta['refs']
assert git('branch','--show-current')=='paper/jss-review-revision'
assert not git('diff','--cached','--name-only')
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
result=dict(status='PASS',protected_files_unchanged=len(seen),stage18c1_hashes_verified=len(inv['files']),
refs=refs,manuscript_sha256=sha(ROOT/'manuscript/jss/manuscript.tex'),
tracked_dirty_files=git('diff','--name-only').splitlines(),scientific_modifications=0,manuscript_modifications=0,
training=0,model_inference=0,commit='no',push='no')
(OUT/'preservation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
