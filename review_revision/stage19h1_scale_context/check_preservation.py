"""Content/membership preservation only; all writes remain in this audit directory."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4194304),b''):h.update(chunk)
    return h.hexdigest()
def read(rel):return json.loads((ROOT/rel).read_text())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
meta=read('review_revision/stage18c1_evidence/preservation_baseline.json')
baseline=ROOT/'review_revision/stage18c1_evidence/preservation_before.jsonl'
assert sha(baseline)==meta['inventory_sha256']
with baseline.open() as stream:expected={v['path']:v['sha256'] for v in map(json.loads,stream)}
expected.update(read('review_revision/stage19c_evidence/verification.json')['source_hashes'])
expected.update(read('review_revision/stage19e_evidence/verification.json')['after_sha256'])
expected.update(read('review_revision/stage19f1_evidence/verification.json')['after_sha256'])
expected.update(read('review_revision/stage19g2_evidence/verification.json')['source_sha256'])
assert len(expected)==395787
roots=['multiresource/04_lstm_factorial','independent_validation/05_bitbrains_factorial',
'independent_validation/06_materna_replication','manuscript/jss','benchmark/src',
*['review_revision/experiments/'+n for n in ['s2_common_context','s2_common_context_predecessor_stage18b1r',
'm1_capacity_matched','ar_arx_baseline','ar_arx_baseline_predecessor_stage18b3']],
'review_revision/stage18a1_diagnostic_audit.md']
seen=set()
for rel in roots:
    p=ROOT/rel
    for path in ([p] if p.is_file() else (Path(b)/n for b,ds,fs in os.walk(p) for n in fs)):
        rel=str(path.relative_to(ROOT));seen.add(rel)
        assert rel in expected and sha(path)==expected[rel],rel
        if len(seen)%100000==0:print('PROTECTED_VERIFIED',len(seen),flush=True)
assert seen==set(expected)
extra={}
for stage in ['stage18c1_evidence','stage19g1_evidence','stage19g2_evidence']:
    inv=read('review_revision/'+stage+'/output_sha256_inventory.json')
    for v in inv['files']:assert sha(ROOT/v['path'])==v['sha256'],v['path']
    extra[stage]=len(inv['files'])
refs={k:git('rev-parse',r) for k,r in {'HEAD':'HEAD','main':'refs/heads/main','paper_jss':'refs/heads/paper/jss',
'scientific_tag_object':'refs/tags/phase4d-materna-final-scientific-freeze-v1',
'scientific_tag_target':'phase4d-materna-final-scientific-freeze-v1^{}'}.items()}
assert refs==meta['refs'] and git('branch','--show-current')=='paper/jss-review-revision'
assert not git('diff','--cached','--name-only')
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
result=dict(status='PASS',phase=sys.argv[1],protected_files_unchanged=len(seen),
additional_output_inventories_verified=extra,refs=refs,manuscript_modifications=0,
scientific_modifications=0,training=0,inference=0,commit='no',push='no')
(OUT/('preservation_'+sys.argv[1]+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
