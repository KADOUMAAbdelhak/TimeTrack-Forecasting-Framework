"""Close the audit with scope, candidate existence and preservation gates."""
from pathlib import Path
from collections import Counter
import hashlib, json, subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as s:
        for block in iter(lambda:s.read(4194304),b''):h.update(block)
    return h.hexdigest()
def read(name):return json.loads((OUT/name).read_text())
def write(name,v):(OUT/name).write_text(json.dumps(v,indent=2)+'\n')
before=read('preservation_before.json');after=read('preservation_after.json')
assert before['status']==after['status']=='PASS'
assert before['files']==after['files_unchanged']==443461
assert after['changes_outside_audit']==0 and after['git_refs_index_and_status_unchanged']
assert sha(OUT/'working_tree_before.jsonl')==before['inventory_sha256']
coverage=read('coverage_checks.json');licences=read('licence_findings.json');plan=read('candidate_plan.json')
assert coverage['status']=='PASS_LOCAL_COVERAGE_AND_HASH_AUDIT'
assert coverage['missing_named_inputs']==[] and len(coverage['posthoc'])==3
assert sum(r['inventory_files_verified'] for r in coverage['posthoc'])==179138
assert licences['repository_wide_licence_present'] is False and licences['licence_files_created']==0
assert len(read('dataset_licence_metadata.json')['local_raw_matches_Zenodo'])==6
assert all(r['exact_match'] for r in read('dataset_licence_metadata.json')['local_raw_matches_Zenodo'])
paths=(OUT/'candidate_commit_paths.txt').read_text().splitlines()
tree=(OUT/'candidate_tree_paths.txt').read_text().splitlines()
assert len(paths)==len(set(paths))==plan['candidate_delta_files']==8572
assert len(tree)==len(set(tree))==plan['candidate_tree_files']==10552
generated_here={str((OUT/name).relative_to(ROOT)) for name in ['verification.json','output_sha256_inventory.json']}
assert all((ROOT/p).is_file() or p in generated_here for p in paths)
assert plan['deletions_proposed']==0 and not plan['companion_archive_created']
delta=list(map(json.loads,(OUT/'candidate_commit_delta.jsonl').open()))
assert len(delta)==len(paths) and {r['path'] for r in delta}==set(paths)
for row in delta:
    if 'sha256' in row:
        assert sha(ROOT/row['path'])==row['sha256'],row['path']
assert sum(r['action']=='MODIFY' for r in delta)==11
assert sum(r['action']=='ADD_AUDIT_DOCUMENTATION' for r in delta)==19
assert sum(1 for line in (OUT/'files_excluded.jsonl').open())==432928
assert len((OUT/'candidate_requires_ignore_override.txt').read_text().splitlines())==21
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
assert not subprocess.check_output(['git','tag','--list',plan['proposed_tag']],cwd=ROOT,text=True).strip()
report=OUT/'STAGE19I1_REPRODUCIBILITY_CHECKPOINT_AUDIT.md'
assert 'STAGE_19I1_PASS' in report.read_text()
result=dict(status='STAGE_19I1_PASS',audit_scope='Read-only reproducibility/licence audit and unstaged checkpoint plan',
    release_clearance=False,USER_ACTION=licences['user_actions'],
    local_scientific_coverage='COMPLETE',missing_named_scientific_inputs=[],
    clean_public_checkout_self_contained=False,portability_gaps=coverage['portability_gaps'],
    protected_files_unchanged=443461,protected_bytes_unchanged=after['bytes_unchanged'],
    candidate_delta_files=8572,candidate_tree_files=10552,tracked_modifications_preserved=11,
    candidate_new_additions=8561,posthoc_output_entries_verified=179138,
    original_frozen_inventories=coverage['originals'],
    evidence_output_inventories=coverage['evidence_output_hashes_verified'],
    historical_manuscript_input_predecessors_resolved=len(coverage['historical_manuscript_inputs_resolved']),
    report_sha256=sha(report),manuscript_modifications=0,scientific_modifications=0,
    declaration_modifications=0,licence_files_created=0,training=0,inference=0,
    scientific_recomputation=0,package_generation=0,commit='no',tag='no',push='no')
write('verification.json',result)
outputs=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='output_sha256_inventory.json']
write('output_sha256_inventory.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in outputs],
    exclusions=['self-referential output inventory'],scope='Audit evidence, not a submission package or experiment archive'))
for row in read('output_sha256_inventory.json')['files']:assert sha(ROOT/row['path'])==row['sha256']
assert all((ROOT/p).is_file() for p in paths)
print(json.dumps(dict(status=result['status'],release_clearance=False,protected_files_unchanged=443461,
    candidate_delta_files=8572,candidate_tree_files=10552,output_files_verified=len(outputs),
    manuscript_modifications=0,scientific_modifications=0,commit='no',tag='no',push='no'),indent=2))
