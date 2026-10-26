"""Create exact candidate/archival path ledgers, without touching Git's index."""
from pathlib import Path
from collections import Counter
import hashlib, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
AUDIT_REL=str(OUT.relative_to(ROOT))
tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))-{''}
changed=set(subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0'))-{''}
files={r['path']:r for r in map(json.loads,(OUT/'working_tree_before.jsonl').open())}

def classify(rel,item):
    p=Path(rel);parts=p.parts
    if rel in tracked:
        return ('MODIFY' if rel in changed else 'INHERITED_TRACKED','Existing tracked tree; no deletion or retroactive relicensing proposed')
    if item['kind']=='symlink' or any(s in parts for s in ['__pycache__','.pytest_cache','.venv_legacy','node_modules','.cache']):
        return 'LOCAL_ONLY','Local environment/cache/symlink; never vendor into checkpoint'
    if rel.startswith(('data/raw/','data/external/raw/','old_fgcs_rejected/root_dataset_duplicates/')):
        return 'UPSTREAM_DATA','Retain locally; acquire by upstream URL/hash; separate source rights'
    if p.name=='.gitkeep' or p.name=='runtime.lock' or p.suffix in ['.pyc','.pyo']:
        return 'LOCAL_ONLY','Placeholder, bytecode or advisory runtime lock'
    if rel.startswith('manuscript/jss/'):
        if 'submission' in parts:return 'OUT_OF_SCOPE','Existing submission material; not part of authorised checkpoint delta'
        if p.suffix in ['.aux','.bbl','.blg','.log','.out','.abs','.synctex']:
            return 'BUILD_ARCHIVE','Generated manuscript build intermediate; retain outside publication artifacts'
        if p.suffix=='.tex':return 'ADD','Current manuscript/supplement editable source'
        return 'OUT_OF_SCOPE','Non-authoritative manuscript-local asset not newly required'
    if rel.startswith('review_revision/experiments/'):
        name=parts[2]
        if '_predecessor_' in name:return 'HISTORICAL_ARCHIVE','Blocked predecessor; retain exact evidence, not current endpoint'
        if any(s in parts for s in ['models','predictions','attempts','completions','progress']):
            return 'SCIENTIFIC_ARCHIVE','Per-fit stored artifact; needed for full audit/regeneration, not normal Git'
        if p.suffix=='.jsonl':return 'PROVENANCE_ARCHIVE','Full protected-tree inventory; retain companion archive and hash anchor'
        if p.suffix in ['.pt','.pth','.npz','.pkl','.joblib','.parquet'] and 'metrics' not in parts and p.name!='posthoc_metric_rows.parquet':
            return 'SCIENTIFIC_ARCHIVE','Saved model/prediction or recovery binary'
        if p.suffix=='.log':return 'HISTORICAL_ARCHIVE','Execution history, not publication table'
        if p.name in ['STAGE18B1_S2_COMMON_CONTEXT_REPORT.md','STAGE18B3_AR_ARX_BASELINE_REPORT.md','STAGE18B1R_RECOVERY_PROGRESS.md']:
            return 'HISTORICAL_ARCHIVE','Superseded/blocked report; final successor report is authoritative'
        return 'ADD','Active control code/config/plans/selections/metrics/seals/audits and recovery evidence'
    if rel.startswith('review_revision/'):
        if rel=='review_revision/stage19h2b_housekeeping/build/supplement/final_evidence_supplement.pdf':
            return 'ADD','Current authoritative three-page supplement PDF, verified at Stage 19H2B; explicit build-path exception'
        if any(s in parts for s in ['build','render','archive','before']):
            return 'BUILD_ARCHIVE','Historical build/render/predecessor snapshot; keep but not current publication artifact'
        if p.suffix=='.jsonl':return 'PROVENANCE_ARCHIVE','Large full-tree hash ledger; preserve separately with its digest'
        if p.suffix in ['.png','.jpg','.pdf']:
            return 'BUILD_ARCHIVE','Superseded build/visual evidence; canonical manuscript PDF is already tracked'
        if p.suffix in ['.py','.mjs','.md','.json','.csv','.parquet','.tex','.diff','.patch','.toml']:
            return 'ADD','Evidence, exact tables, source snapshots, provenance or reproducibility script'
        return 'OUT_OF_SCOPE','Incidental evidence-directory item'
    if rel.startswith(('multiresource/04_lstm_factorial/','independent_validation/05_bitbrains_factorial/','independent_validation/06_materna_replication/')):
        if rel.startswith('independent_validation/05_bitbrains_factorial/outputs/scientific/'):
            return 'HISTORICAL_ARCHIVE','Superseded first external execution; scientific_v2 is authoritative'
        return 'SCIENTIFIC_ARCHIVE','Original per-fit runtime/model/prediction artifacts; retain as frozen archive'
    if p.suffix=='.parquet':return 'UPSTREAM_DERIVED_CACHE','Raw-derived/canonical/cache data; retain source terms, not a new code grant'
    return 'OUT_OF_SCOPE','Unrelated or legacy local file; no blanket git add'

# The audit report and compact ledgers are checkpoint documentation, not submission files.
audit_include=[
 'STAGE19I1_REPRODUCIBILITY_CHECKPOINT_AUDIT.md','audit_checkpoint.py','verify_coverage.py',
 'collect_public_licences.py','plan_checkpoint.py','build_licence_ledger.py','finalise.py',
 'coverage_checks.json','licence_findings.json','dataset_licence_metadata.json',
 'preservation_before.json','preservation_after.json','verification.json','candidate_plan.json',
 'candidate_commit_paths.txt','candidate_commit_delta.jsonl','candidate_tree_paths.txt',
 'output_sha256_inventory.json']
counts=Counter();sizes=Counter();delta=[];inherited=[];excluded=[]
for rel,item in sorted(files.items()):
    action,reason=classify(rel,item);counts[action]+=1;sizes[action]+=item['bytes']
    if action in ['ADD','MODIFY']:
        delta.append(dict(path=rel,action=action,bytes=item['bytes'],sha256=item['sha256'],reason=reason))
    elif action=='INHERITED_TRACKED':inherited.append(rel)
    else:excluded.append(dict(path=rel,disposition=action,reason=reason))
assert len(changed)==11 and {r['path'] for r in delta if r['action']=='MODIFY'}==changed
for name in audit_include:
    delta.append(dict(path=AUDIT_REL+'/'+name,action='ADD_AUDIT_DOCUMENTATION',
        reason='Authorised checkpoint audit and compact exact allowlist; output inventory supplies hashes'))
candidate_paths=sorted(r['path'] for r in delta)
assert len(candidate_paths)==len(set(candidate_paths))
assert not any(Path(r).suffix in ['.pt','.pth','.joblib','.pkl','.zip'] for r in candidate_paths)
assert not any(files.get(r,{}).get('bytes',0)>=100000000 for r in candidate_paths)
tree_paths=sorted(set(inherited)|set(candidate_paths))
(OUT/'candidate_commit_paths.txt').write_text('\n'.join(candidate_paths)+'\n')
(OUT/'candidate_tree_paths.txt').write_text('\n'.join(tree_paths)+'\n')
with (OUT/'candidate_commit_delta.jsonl').open('w') as stream:
    for row in sorted(delta,key=lambda r:r['path']):stream.write(json.dumps(row,separators=(',',':'))+'\n')
with (OUT/'files_excluded.jsonl').open('w') as stream:
    for row in excluded:stream.write(json.dumps(row,separators=(',',':'))+'\n')
with (OUT/'inherited_tracked.jsonl').open('w') as stream:
    for rel in inherited:stream.write(json.dumps(files[rel],separators=(',',':'))+'\n')

ignored=subprocess.run(['git','check-ignore','--no-index','--stdin'],cwd=ROOT,
    input='\n'.join(r['path'] for r in delta if r['action']=='ADD')+'\n',text=True,capture_output=True)
assert ignored.returncode in [0,1]
force_paths=ignored.stdout.splitlines()
(OUT/'candidate_requires_ignore_override.txt').write_text('\n'.join(force_paths)+'\n' if force_paths else '')
audit_include.append('candidate_requires_ignore_override.txt')
# Add the newly enumerated ignore-override ledger to the exact documentation set.
extra=AUDIT_REL+'/candidate_requires_ignore_override.txt'
if extra not in candidate_paths:
    candidate_paths.append(extra);candidate_paths.sort();tree_paths.append(extra);tree_paths.sort()
    delta.append(dict(path=extra,action='ADD_AUDIT_DOCUMENTATION',reason='Explicit ignored-Parquet allowlist; no force-add executed'))
    (OUT/'candidate_commit_paths.txt').write_text('\n'.join(candidate_paths)+'\n')
    (OUT/'candidate_tree_paths.txt').write_text('\n'.join(tree_paths)+'\n')
    with (OUT/'candidate_commit_delta.jsonl').open('w') as stream:
        for row in sorted(delta,key=lambda r:r['path']):stream.write(json.dumps(row,separators=(',',':'))+'\n')

plan=dict(status='PROPOSED_ONLY_NO_STAGING',base_commit='f6936cd111d911e40ec2725a18fdfc53768d9ccf',
    branch='paper/jss-review-revision',proposed_commit_subject='JSS reviewer robustness and manuscript evidence checkpoint',
    proposed_tag='jss-review-robustness-reproducibility-v1',
    repository='https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework',
    proposed_tag_url='https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework/tree/jss-review-robustness-reproducibility-v1',
    future_commit_sha='UNKNOWN_UNTIL_COMMIT_EXISTS',baseline_files=len(files),current_tracked_files=len(tracked),
    counts_by_disposition=dict(counts),bytes_by_disposition=dict(sizes),
    candidate_delta_files=len(candidate_paths),candidate_tree_files=len(tree_paths),
    audit_documentation_additions=len(audit_include),candidate_existing_file_bytes=sum(r.get('bytes',0) for r in delta),
    candidate_ignore_override_count=len(force_paths),deletions_proposed=0,
    companion_archive_required_for_full_saved_artifact_reaudit=True,
    companion_archive_created=False,archive_public_location='USER_ACTION_NOT_ASSIGNED',
    licence_and_portability_followups_not_added_to_candidate=True,commit='no',tag='no',push='no')
(OUT/'candidate_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(plan,indent=2))
