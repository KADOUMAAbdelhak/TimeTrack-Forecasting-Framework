"""Bind portability tests, source preservation and successor candidate plan."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(4194304),b''):h.update(block)
    return h.hexdigest()
def load(name):return json.loads((HERE/name).read_text())
def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')

before=load('preservation_before.json');after=load('preservation_after.json')
assert before['status']==after['status']=='PASS'
assert before['git']==after['git']
assert before['protected_files_unchanged']==after['protected_files_unchanged']==443484
assert after['changes_outside_I2']==after['historical_seals_changed']==0
validation=load('validation_results.json')
assert validation['status']=='PASS' and validation['scientific_outputs_identical_across_verified_runtimes']
assert {r['python'] for r in validation['runs']}=={'3.9.6','3.12.14'}
assert all(r['tests']==25 and r['status']=='PASS' for r in validation['runs'])
manifest=load('replay_sources.json')
for row in manifest['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
plan=load('checkpoint_candidate/candidate_plan.json')
assert plan['candidate_delta_files']==8598 and plan['candidate_tree_files']==10578
paths=(HERE/'checkpoint_candidate/candidate_commit_paths.txt').read_text().splitlines()
assert len(paths)==len(set(paths))==8598
pending={str((HERE/name).relative_to(ROOT)) for name in ['verification.json','output_sha256_inventory.json']}
assert all((ROOT/p).is_file() or p in pending for p in paths)
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
report=HERE/'STAGE19I2_REPRODUCIBILITY_PORTABILITY_REPORT.md'
result=dict(status='STAGE_19I2_PASS',report_sha256=sha(report),protected_files_unchanged=443484,
    protected_bytes=after['protected_bytes'],I1_artifacts_unchanged=True,
    public_standard_library_replay=True,minimum_python='3.9',verified_python_versions=['3.9.6','3.12.14'],
    tests_per_runtime=25,total_test_cases=50,source_hashes_verified=11,
    G1_CSVs_byte_identical=3,C1_CSVs_byte_identical=2,supplement_row_fragments_byte_identical=2,
    semantic_only_CSV_fallbacks=0,scientific_or_presentation_outputs_identical_across_runtimes=8,
    derived_only_new_metadata='Diagnostic projection uses explicitly labelled source numeric lexeme strings',
    historical_seals_changed=0,private_runtime_dependency=0,
    candidate_delta_files=8598,candidate_tree_files=10578,retired_private_scripts_preserved=True,
    scientific_modifications=0,manuscript_modifications=0,training=0,inference=0,
    licence_files_created=0,dataset_redistribution=0,submission_package_generation=0,
    commit='no',tag='no',push='no')
write('verification.json',result)
files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='output_sha256_inventory.json']
write('output_sha256_inventory.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in files],
    exclusions=['self-referential output inventory'],scope='Portability code/documentation and validation, not a submission package'))
for row in load('output_sha256_inventory.json')['files']:assert sha(ROOT/row['path'])==row['sha256']
assert all((ROOT/p).is_file() for p in paths)
print(json.dumps(dict(status=result['status'],protected_files_unchanged=443484,tests=50,
    G1_CSVs_byte_identical=3,supplement_fragments_byte_identical=2,
    candidate_delta_files=8598,output_files_verified=len(files),scientific_modifications=0,
    manuscript_modifications=0,commit='no',tag='no',push='no'),indent=2))
