"""Inspect existing inventories/seals only; never import scientific runners."""
from pathlib import Path
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def load(p):return json.loads((ROOT/p).read_text())
meta=load('review_revision/stage19i1_reproducibility/preservation_before.json')
inventory=OUT/'working_tree_before.jsonl'
assert hashlib.sha256(inventory.read_bytes()).hexdigest()==meta['inventory_sha256']
FILES={r['path']:r for r in map(json.loads,inventory.open())}
def check(rel,digest):
    assert rel in FILES,('MISSING',rel)
    assert FILES[rel].get('sha256')==digest,('HASH_MISMATCH',rel)

def verify_inventory(rel,relative=False):
    value=load(rel);parent=str(Path(rel).parent)+'/' if relative else ''
    for r in value['files']:
        check(parent+r['path'],r['sha256'])
    return len(value['files'])

blocks=['TimeTrack','fastStorage','Rnd','Materna-T1','Materna-T2','Materna-T3']
posthoc=[]
specs=[
 ('s2_common_context','provenance/recovery_stage18b1r_successor.json','validation/stage18b1r_handoff.json','STAGE_18B1R_PASS'),
 ('m1_capacity_matched','provenance/experiment.json','validation/final_handoff.json','STAGE_18B2_PASS'),
 ('ar_arx_baseline','recovery/successor_audit_reduction_fix.json','recovery/final_handoff.json','STAGE_18B3R_PASS')]
for name,sealpath,handoffpath,status in specs:
    base='review_revision/experiments/'+name+'/'
    count=verify_inventory(base+'output_sha256_inventory.json',True)
    seal=load(base+sealpath);handoff=load(base+handoffpath)
    assert handoff['status']==status
    for rel,digest in seal['source_hashes'].items():check(rel,digest)
    original=load(base+'provenance/experiment.json')
    check(base+'control_config.json',original['configuration_sha256'])
    for block,digest in original.get('plan_hashes',{}).items():check(base+'plans/'+block+'.json',digest)
    for block in blocks:assert load(base+'validation/full_audit_'+block+'.json')['status']=='PASS'
    report=Path(handoff.get('report_path',handoff.get('summary',{}).get('report_path','')))
    assert report.is_absolute()
    check(str(report.relative_to(ROOT)),handoff['report_sha256'])
    summary=load(base+'completion_summary.json')
    assert summary['counts']['failed']==0
    with (ROOT/base/'posthoc_results.csv').open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==24 and len({(r['block'],r['resource']) for r in rows})==24
    posthoc.append(dict(experiment=name,status=status,inventory_files_verified=count,
        active_seal=base+sealpath,result=base+'posthoc_results.csv',
        metric_file=base+'posthoc_metric_rows.parquet',counts=summary['counts'],rows=24,
        historical_failures_preserved=True,missing_files=0))

originals=[]
for rel in [
 'multiresource/04_lstm_factorial/PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv',
 'independent_validation/05_bitbrains_factorial/PHASE4C_V2_SCIENTIFIC_CHECKPOINT_SHA256.csv',
 'independent_validation/06_materna_replication/PHASE4D_MATERNA_FINAL_SCIENTIFIC_CHECKPOINT_SHA256.csv',
 'independent_validation/05_bitbrains_factorial/PHASE4C_V2_EXECUTION_CHECKPOINT_SHA256.csv',
 'independent_validation/06_materna_replication/PHASE4D_MATERNA_EXECUTION_CHECKPOINT_SHA256.csv',
 'independent_validation/05_bitbrains_factorial/outputs/scientific_v2/runtime/PHASE4C_V2_EXECUTION_ARTIFACT_SHA256.csv',
 'independent_validation/06_materna_replication/outputs/scientific_v1/runtime/PHASE4D_EXECUTION_ARTIFACT_SHA256.csv']:
    with (ROOT/rel).open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    for r in rows:check(r['relative_path'],r['sha256'])
    originals.append(dict(inventory=rel,files_verified=len(rows)))

evidence={}
for stage in ['stage18c1_evidence','stage19g1_evidence','stage19g2_evidence','stage19h1_scale_context','stage19h2a_evidence','stage19h2b_housekeeping']:
    evidence[stage]=verify_inventory('review_revision/'+stage+'/output_sha256_inventory.json')
assert load('review_revision/stage18c1_evidence/final_handoff.json')['status']=='STAGE_18C1_PASS'
for stage,status in [('stage19g1_evidence','STAGE_19G1_PASS'),('stage19g2_evidence','STAGE_19G2_PASS'),
                     ('stage19h1_scale_context','STAGE_19H1_PASS'),('stage19h2a_evidence','STAGE_19H2A_PASS'),
                     ('stage19h2b_housekeeping','STAGE_19H2B_PASS')]:
    assert load('review_revision/'+stage+'/verification.json')['status']==status

direct_inputs={}
historical_manuscript_inputs=[]
for stage in ['stage19g1_evidence','stage19h1_scale_context']:
    v=load('review_revision/'+stage+'/input_sha256_inventory.json')
    rows=v['files']
    for row in rows:
        rel=row['path']
        if rel.startswith('manuscript/jss/') and FILES[rel].get('sha256')!=row['sha256']:
            archived=[r['path'] for r in FILES.values() if r['path'].startswith('review_revision/') and r.get('sha256')==row['sha256']]
            assert archived,('HISTORICAL_MANUSCRIPT_PREDECESSOR_MISSING',rel)
            historical_manuscript_inputs.append(dict(stage=stage,path=rel,
                historical_sha256=row['sha256'],exact_preserved_predecessors=archived,
                current_sha256=FILES[rel]['sha256'],reason='Authorised later manuscript revisions; scientific inputs unchanged'))
        else:
            check(rel,row['sha256'])
    direct_inputs[stage]=len(rows)

required=['review_revision/stage18a1_diagnostic_audit.md','review_revision/stage18c1_final_robustness_synthesis.md',
    'review_revision/stage19g1_evidence/m1_s2_robustness_24.csv',
    'review_revision/stage19g1_evidence/seed_sensitivity_48.csv',
    'review_revision/stage19g1_evidence/timetrack_memory_attribution.csv',
    'manuscript/jss/supplementary/final_evidence_supplement.tex',
    'data/external/raw/gwa_t_13_materna.zip']
assert all(r in FILES for r in required)
result=dict(status='PASS_LOCAL_COVERAGE_AND_HASH_AUDIT',posthoc=posthoc,originals=originals,
    evidence_output_hashes_verified=evidence,direct_input_hashes_verified=direct_inputs,
    historical_manuscript_inputs_resolved=historical_manuscript_inputs,
    named_required_inputs_present=True,missing_named_inputs=[],local_files_complete=True,
    public_clean_checkout_self_contained=False,
    portability_gaps=['Full checkpoints/predictions are local, not all tracked',
        'G1 CSV exporter uses private @oai/artifact-tool and an absolute local node_modules symlink',
        'Some verification scripts require historical HEAD/clean tree and historical output locations',
        'No unified portable dependency lock or checkpoint entry README'],
    training=0,inference=0,scientific_recomputation=0)
(OUT/'coverage_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
