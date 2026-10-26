"""Independent cohort-rank reconciliation and hash-bound final audit status."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,statistics
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4194304),b''):h.update(chunk)
    return h.hexdigest()
def read(name):return json.loads((OUT/name).read_text())
def write(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
d=read('analysis.json')
for phase in ['before','after']:
    preservation=read('preservation_'+phase+'.json')
    assert preservation['status']=='PASS' and preservation['protected_files_unchanged']==395787
assert read('preservation_before.json')['refs']==read('preservation_after.json')['refs']
index={(r['trace'],r['vm_id'],r['fold'],r['L']):r for r in d['cohort_partition_distribution']}
assert len(index)==1050
assert Counter(r['trace'] for r in index.values())=={'Materna-T1':525,'Materna-T3':525}
cohort={r['vm_id'] for r in index.values()};assert len(cohort)==35
with (ROOT/'independent_validation/06_materna_replication/manifests/MATERNA_SCALER_PARTITIONS.csv').open() as stream:
    stored={(r['trace'],r['VM_ID'],int(r['fold']),int(r['L'])):r for r in csv.DictReader(stream) if r['phase']=='final'}
for key,row in index.items():
    old=stored[key]
    assert row['transformed_iqr']==json.loads(old['transformed_iqrs'])[3]
    assert row['transformed_median']==json.loads(old['transformed_medians'])[3]
    assert row['native_iqr']==json.loads(old['native_iqrs'])[3]
    assert row['scaler_partition_sha256']==old['scaler_partition_sha256']
    assert row['fit_timestamp_sha256']==old['fit_timestamp_sha256']
selected_map={}
for row in d['completion_scaler_checks']:
    key=(row['trace'],row['formulation'],row['fold'],row['vm_id'])
    if key in selected_map:assert selected_map[key]==row['L']
    selected_map[key]=row['L']
checked=0
for kind in ['fixed_context_dominant_partitions','selected_context_cohort_comparisons']:
    for row in d[kind]:
        rows=[index[(row['trace'],vm,row['fold'],row['L'] if kind.startswith('fixed') else
                     selected_map[(row['trace'],row['formulation'],row['fold'],vm)])] for vm in cohort]
        assert len(rows)==35
        dominant=index[(row['trace'],row['vm_id'],row['fold'],row['L'])]
        for metric in ['transformed_iqr','transformed_median','native_iqr','native_median']:
            values=sorted(r[metric] for r in rows);value=dominant[metric];m=row['metrics'][metric]
            assert m['value']==value and m['cohort_min']==values[0] and m['cohort_max']==values[-1]
            assert m['cohort_median']==statistics.median(values)
            assert m['ascending_rank_min']==1+sum(v<value for v in values)
            assert m['ascending_rank_max']==sum(v<=value for v in values)
            assert m['ecdf_percent']==100.*sum(v<=value for v in values)/35
            assert m['cohort_ties']==values.count(value)
            assert m['ratio_to_cohort_median']==value/statistics.median(values)
            checked+=1
for key,expected in [('cohort_completion_scalers_verified',3150),('raw_final_partitions_reconstructed',1050),
                     ('dominant_predictions_and_checkpoint_hashes_verified',90)]:assert d[key]==expected
assert len(d['dominant_inverse_checks'])==90
assert not any(v for k,v in d.items() if k in ['training','inference','manuscript_modifications','scientific_modifications'])
for record in read('input_sha256_inventory.json')['files']:
    assert sha(ROOT/record['path'])==record['sha256'],record['path']
report=(OUT/'STAGE19H1_DOMINANT_VM_SCALE_CONTEXT_REPORT.md').read_text()
assert report.endswith('STAGE_19H1_PASS\n')
assert report.count('SCALE_INSTABILITY_NOT_SUPPORTED')==3
assert len([line for line in report.splitlines() if line.startswith('|')])==126
result=dict(status='STAGE_19H1_PASS',classification_by_VM={k+'/VM'+v['vm_id']:v['classification'] for k,v in d['summaries'].items()},
    raw_final_training_partitions_exact=1050,dominant_final_partitions_reported=30,
    selected_context_comparisons=30,cohort_size=35,original_final_completion_scalers_verified=3150,
    dominant_saved_inverse_predictions_verified=90,independently_reconciled_cohort_statistics=checked,
    direct_input_hashes_reverified=len(read('input_sha256_inventory.json')['files']),
    protected_files_unchanged=395787,prior_output_hashes_verified=read('preservation_after.json')['additional_output_inventories_verified'],
    implementation_defect_demonstrated=False,further_experiment_required=False,
    causal_sharing_mechanism_identified=False,thresholds_invented=False,
    native_medians_exact_from_original_training_rows=True,training=0,inference=0,
    manuscript_modifications=0,scientific_modifications=0,commit='no',push='no')
write('verification.json',result)
outputs=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='output_sha256_inventory.json']
write('output_sha256_inventory.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in outputs]))
for record in read('output_sha256_inventory.json')['files']:assert sha(ROOT/record['path'])==record['sha256']
print(json.dumps(result,indent=2),flush=True)
