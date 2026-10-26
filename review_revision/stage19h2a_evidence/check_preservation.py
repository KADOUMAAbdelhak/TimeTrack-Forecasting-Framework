"""Hash-only before/after gate for the three authorised manuscript sources."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
MODE=sys.argv[1]
ALLOWED=['manuscript/jss/manuscript.tex','manuscript/jss/supplementary/final_evidence_supplement.tex',
         'manuscript/jss/tables/posthoc_controls.tex']
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
with p.open() as s:expected={r['path']:r['sha256'] for r in map(json.loads,s)}
expected.update(read('review_revision/stage19c_evidence/verification.json')['source_hashes'])
expected.update(read('review_revision/stage19e_evidence/verification.json')['after_sha256'])
expected.update(read('review_revision/stage19f1_evidence/verification.json')['after_sha256'])
expected.update(read('review_revision/stage19g2_evidence/verification.json')['source_sha256'])
assert len(expected)==395787
if MODE=='before':
    for n,rel in enumerate(ALLOWED):
        assert sha(ROOT/rel)==expected[rel]
        dst=OUT/f'before_{n}.tex';assert not dst.exists();shutil.copyfile(ROOT/rel,dst)
else:
    assert MODE=='after'
    for n,rel in enumerate(ALLOWED):assert sha(OUT/f'before_{n}.tex')==expected[rel]
roots=['multiresource/04_lstm_factorial','independent_validation/05_bitbrains_factorial',
'independent_validation/06_materna_replication','manuscript/jss','benchmark/src',
*['review_revision/experiments/'+n for n in ['s2_common_context','s2_common_context_predecessor_stage18b1r',
'm1_capacity_matched','ar_arx_baseline','ar_arx_baseline_predecessor_stage18b3']],
'review_revision/stage18a1_diagnostic_audit.md']
seen=set();unchanged=0
for rel in roots:
    p=ROOT/rel
    for f in ([p] if p.is_file() else (Path(b)/n for b,ds,fs in os.walk(p) for n in fs)):
        rel=str(f.relative_to(ROOT));seen.add(rel)
        if MODE=='after' and rel in ALLOWED:continue
        assert rel in expected and sha(f)==expected[rel],rel
        unchanged+=1
        if unchanged%100000==0:print('PROTECTED_UNCHANGED',unchanged,flush=True)
assert seen==set(expected)
extras={}
for stage in ['stage18c1_evidence','stage19g1_evidence','stage19g2_evidence','stage19h1_scale_context']:
    inv=read('review_revision/'+stage+'/output_sha256_inventory.json')
    for r in inv['files']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
    extras[stage]=len(inv['files'])
refs={k:git('rev-parse',r) for k,r in {'HEAD':'HEAD','main':'refs/heads/main','paper_jss':'refs/heads/paper/jss',
'scientific_tag_object':'refs/tags/phase4d-materna-final-scientific-freeze-v1',
'scientific_tag_target':'phase4d-materna-final-scientific-freeze-v1^{}'}.items()}
assert refs==meta['refs'] and git('branch','--show-current')=='paper/jss-review-revision'
assert not git('diff','--cached','--name-only')
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
result=dict(status='PASS',phase=MODE,protected_membership=len(seen),protected_files_unchanged=unchanged,
allowed_manuscript_sources=ALLOWED,source_sha256={rel:sha(ROOT/rel) for rel in ALLOWED},
prior_output_hashes_verified=extras,refs=refs,scientific_modifications=0,training=0,inference=0,commit='no',push='no')
(OUT/('preservation_'+MODE+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
