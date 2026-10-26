"""Write an I1-successor checkpoint plan under I2, without altering I1 or Git."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PRIOR=ROOT/'review_revision/stage19i1_reproducibility'
OUT=HERE/'checkpoint_candidate'
PREFIX=str(HERE.relative_to(ROOT))+'/'
RETIRED={'review_revision/stage19g1_evidence/export_tables.mjs',
         'review_revision/stage19g1_evidence/inspect_artifact_api.mjs'}
NEW=[
 'README.md','ENVIRONMENT.md','requirements-derived.txt','environment.json',
 'replay_derived.py','replay_sources.json','test_replay.py','check_preservation.py',
 'build_source_manifest.py','verify_portability.py','refresh_checkpoint.py','finalise.py',
 'STAGE19I2_REPRODUCIBILITY_PORTABILITY_REPORT.md','validation_results.json',
 'preservation_before.json','preservation_after.json','verification.json','output_sha256_inventory.json',
 'validation/python39_checks.json','validation/python312_checks.json',
 'validation/python39_tests.txt','validation/python312_tests.txt',
 'checkpoint_candidate/candidate_commit_paths.txt','checkpoint_candidate/candidate_commit_delta.jsonl',
 'checkpoint_candidate/candidate_tree_paths.txt','checkpoint_candidate/candidate_requires_ignore_override.txt',
 'checkpoint_candidate/candidate_plan.json','checkpoint_candidate/exclusion_summary.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(exist_ok=True)
    prior=json.loads((PRIOR/'candidate_plan.json').read_text())
    old_paths=set((PRIOR/'candidate_commit_paths.txt').read_text().splitlines())
    old_tree=set((PRIOR/'candidate_tree_paths.txt').read_text().splitlines())
    assert RETIRED<=old_paths and len(NEW)==28
    added={PREFIX+p for p in NEW}
    paths=sorted((old_paths-RETIRED)|added)
    tree=sorted((old_tree-RETIRED)|added)
    assert len(paths)==8598 and len(tree)==10578
    manifest=json.loads((HERE/'replay_sources.json').read_text())
    assert {r['path'] for r in manifest['files']}<=set(tree)
    (OUT/'candidate_commit_paths.txt').write_text('\n'.join(paths)+'\n')
    (OUT/'candidate_tree_paths.txt').write_text('\n'.join(tree)+'\n')
    rows=[r for r in map(json.loads,(PRIOR/'candidate_commit_delta.jsonl').open()) if r['path'] not in RETIRED]
    rows.extend(dict(path=p,action='ADD_PORTABILITY',reason='Public derived-only replay, tests/documentation or compact successor audit',
        hashes='I2 output_sha256_inventory.json; no self-hash for its self-referential inventory') for p in added)
    with (OUT/'candidate_commit_delta.jsonl').open('w') as stream:
        for row in sorted(rows,key=lambda r:r['path']):stream.write(json.dumps(row,separators=(',',':'))+'\n')
    shutil_data=(PRIOR/'candidate_requires_ignore_override.txt').read_bytes()
    (OUT/'candidate_requires_ignore_override.txt').write_bytes(shutil_data)
    counts=Counter();ledger=OUT/'files_excluded.jsonl'
    extra=[dict(path=p,disposition='HISTORICAL_ARCHIVE',reason='Retired private G1 tool; exact historical source preserved') for p in sorted(RETIRED)]
    for name in ['files_excluded.jsonl','working_tree_before.jsonl','git_before.json','inherited_tracked.jsonl']:
        extra.append(dict(path=str((PRIOR/name).relative_to(ROOT)),disposition='PROVENANCE_ARCHIVE',
            reason='I1 full audit ledger/metadata retained outside normal Git; compact audit anchors are included'))
    extra.append(dict(path=str(ledger.relative_to(ROOT)),disposition='PROVENANCE_ARCHIVE',
        reason='Full exact successor exclusion ledger is too large for normal Git; digest/summary are included'))
    with ledger.open('w') as stream:
        for row in map(json.loads,(PRIOR/'files_excluded.jsonl').open()):
            counts[row['disposition']]+=1;stream.write(json.dumps(row,separators=(',',':'))+'\n')
        for row in extra:
            counts[row['disposition']]+=1;stream.write(json.dumps(row,separators=(',',':'))+'\n')
    assert sum(counts.values())==432935
    summary=dict(status='PROPOSED_ONLY',full_exclusion_ledger=str(ledger.relative_to(ROOT)),
        ledger_sha256=sha(ledger),excluded_paths=sum(counts.values()),by_disposition=dict(counts),
        retired_private_tools=sorted(RETIRED),historical_files_deleted=0,old_plan_preserved=True)
    (OUT/'exclusion_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    plan=dict(status='PROPOSED_SUCCESSOR_NO_STAGING',supersedes='review_revision/stage19i1_reproducibility/candidate_plan.json',
        predecessor_plan_sha256=sha(PRIOR/'candidate_plan.json'),predecessor_delta_files=8572,
        added_portability_files=28,retired_private_tools_from_candidate=sorted(RETIRED),
        candidate_delta_files=len(paths),candidate_tree_files=len(tree),
        modifications_to_existing_tracked_files=11,new_additions=8587,proposed_deletions=0,
        required_compact_replay_inputs=11,all_replay_inputs_in_candidate=True,
        ignored_Parquet_override_paths=21,full_exclusion_ledger_paths=sum(counts.values()),
        proposed_tag=prior['proposed_tag'],proposed_tag_url=prior['proposed_tag_url'],
        full_saved_artifact_archive_still_required_for_Level_C=True,
        level_B_private_dependencies=0,authoritative_artifacts_modified=0,
        commit='no',tag='no',push='no')
    (OUT/'candidate_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(plan,indent=2))
if __name__=='__main__':main()
