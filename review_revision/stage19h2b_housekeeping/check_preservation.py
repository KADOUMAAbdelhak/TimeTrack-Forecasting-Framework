"""Protect all frozen files and byte-archive every authorised housekeeping target."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
MODE=sys.argv[1]
GENERATED=['manuscript/jss/manuscript.'+ext for ext in ['abs','aux','bbl','blg','log','out','pdf']]
ALLOWED=['manuscript/jss/manuscript.tex','manuscript/jss/figures/framework_s1_s2_m1.tex',
'manuscript/jss/figures/framework_s1_s2_m1.pdf','manuscript/jss/tables/related_work_comparison.tex',
'manuscript/jss/supplementary/decision_criteria.tex','manuscript/jss/supplementary/overall_bootstrap_intervals.tex',
'manuscript/jss/supplementary/final_evidence_supplement.tex',*GENERATED]
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
with p.open() as s:expected={v['path']:v['sha256'] for v in map(json.loads,s)}
expected.update(read('review_revision/stage19c_evidence/verification.json')['source_hashes'])
expected.update(read('review_revision/stage19e_evidence/verification.json')['after_sha256'])
expected.update(read('review_revision/stage19f1_evidence/verification.json')['after_sha256'])
expected.update(read('review_revision/stage19g2_evidence/verification.json')['source_sha256'])
expected.update(read('review_revision/stage19h2a_evidence/verification.json')['source_sha256'])
assert len(expected)==395787
archived=[]
for rel in ALLOWED:
    dst=OUT/'archive'/rel
    if MODE=='before':
        assert sha(ROOT/rel)==expected[rel] and not dst.exists(),rel
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dst)
    else:assert MODE=='after'
    assert sha(dst)==expected[rel],rel
    archived.append(dict(original_path=rel,archive_path=str(dst.relative_to(ROOT)),sha256=sha(dst)))
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
extra={}
for stage in ['stage18c1_evidence','stage19g1_evidence','stage19g2_evidence','stage19h1_scale_context','stage19h2a_evidence']:
    inv=read('review_revision/'+stage+'/output_sha256_inventory.json')
    for r in inv['files']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
    extra[stage]=len(inv['files'])
refs={k:git('rev-parse',r) for k,r in {'HEAD':'HEAD','main':'refs/heads/main','paper_jss':'refs/heads/paper/jss',
'scientific_tag_object':'refs/tags/phase4d-materna-final-scientific-freeze-v1',
'scientific_tag_target':'phase4d-materna-final-scientific-freeze-v1^{}'}.items()}
assert refs==meta['refs'] and git('branch','--show-current')=='paper/jss-review-revision'
assert not git('diff','--cached','--name-only')
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
result=dict(status='PASS',phase=MODE,protected_membership=len(seen),protected_files_unchanged=unchanged,
allowed_manuscript_housekeeping=ALLOWED,archived_predecessors=archived,
source_sha256={r:sha(ROOT/r) for r in ALLOWED},prior_output_hashes_verified=extra,refs=refs,
scientific_modifications=0,training=0,inference=0,analysis=0,commit='no',push='no')
(OUT/('preservation_'+MODE+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
