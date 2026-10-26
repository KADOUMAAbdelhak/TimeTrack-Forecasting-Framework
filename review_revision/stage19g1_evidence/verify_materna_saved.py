"""Fresh static checks of saved T1/T3 S2/M1 disk artifacts. Never run models."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd,torch
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
BASE=ROOT/'independent_validation/06_materna_replication'
inputs=json.loads((OUT/'input_sha256_inventory.json').read_text())
index={r['path']:r for r in inputs['files']}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as s:
        for b in iter(lambda:s.read(4194304),b''):h.update(b)
    return h.hexdigest()
def used(p):
    index[str(p.relative_to(ROOT))]=dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)
    return p
def record(p):return json.loads(used(p).read_text())
scalers=pd.read_csv(used(BASE/'manifests/MATERNA_SCALER_PARTITIONS.csv'),dtype={'VM_ID':str},float_precision='round_trip')
assert len(scalers)==3150
analysis=json.loads((OUT/'analysis.json').read_text());checks={}
for block,dominant in [('Materna-T1','266'),('Materna-T3','272')]:
    root=BASE/'outputs/scientific_v1'/block
    validation=record(root/'validation/technical_validation.json')
    assert validation['status']=='PASS' and not validation['failures'] and all(v==0 for v in validation['violations'].values())
    registry=pd.read_csv(used(root/'run_registry.csv'),dtype={'vm_id':str},float_precision='round_trip')
    registry=registry[(registry.formulation.eq('S2')&registry.resource.eq('DISK_WRITE'))|registry.formulation.eq('M1')]
    assert len(registry)==1050 and not registry.duplicated(['formulation','vm_id','fold','seed']).any()
    metrics=pd.read_parquet(used(root/'metrics.parquet'));metrics=metrics[metrics.resource.eq('DISK_WRITE')]
    pairs={};dominant_epochs=[];maximum=0.;scaler_count=set()
    for i,r in enumerate(registry.itertuples(),1):
        comp=record(root/f'runtime/completions/final/{r.run_id}.json')
        assert comp['status']=='complete' and comp['test_evaluations']==1
        assert comp['scaler_fit_split']=='complete_legal_outer_train_only'
        sc=comp['scaler'];assert np.isfinite(list(sc.values())).all() and min(sc['transformed_iqr'])>0
        row=scalers[scalers.trace.eq(block)&scalers.VM_ID.eq(r.vm_id)&scalers.fold.eq(r.fold)&scalers.L.eq(r.L)&scalers.phase.eq('final')]
        assert len(row)==1
        row=row.iloc[0];expected={k:json.loads(row[v]) for k,v in [('native_iqr','native_iqrs'),('transformed_iqr','transformed_iqrs'),('transformed_median','transformed_medians')]}
        assert sc==expected
        scaler_count.add((r.vm_id,int(r.fold),int(r.L)))
        for kind in ['model','prediction']:
            path=used(BASE/getattr(r,kind+'_path'))
            assert index[str(path.relative_to(ROOT))]['sha256']==getattr(r,kind+'_sha256')==comp[kind+'_sha256']
        weights=torch.load(BASE/r.model_path,map_location='cpu',weights_only=True)
        assert all(torch.isfinite(v).all().item() for v in weights.values())
        assert sum(v.numel() for v in weights.values())==(52500 if r.formulation=='M1' else 51525)
        p=pd.read_parquet(BASE/r.prediction_path,filters=[('resource','=','DISK_WRITE')]).sort_values(['origin_index','lead']).reset_index(drop=True)
        assert not p.duplicated(['origin_index','lead']).any() and len(p)==comp['outer_test_n']*5
        assert np.isfinite(p[['y_true','y_pred_scaled','y_pred','y_pred_unclipped']].to_numpy()).all()
        inv=np.expm1(p.y_pred_scaled.to_numpy(dtype=float)*sc['transformed_iqr'][3]+sc['transformed_median'][3])
        assert np.array_equal(inv,p.y_pred_unclipped) and np.array_equal(np.maximum(0.,inv),p.y_pred)
        calculated=p.assign(error=np.abs(p.y_true-p.y_pred)).groupby('lead').error.mean()
        old=metrics[metrics.run_id.eq(r.run_id)].sort_values('lead')
        assert len(old)==5 and np.allclose(calculated,old.mae,rtol=1e-12,atol=0)
        key=(r.vm_id,int(r.fold),int(r.seed))
        cols=['origin_index','lead','target_index','origin_timestamp_seconds','target_timestamp_seconds','support_hash','y_true']
        signature=hashlib.sha256(pd.util.hash_pandas_object(p[cols],index=False).to_numpy().tobytes()).hexdigest()
        if key in pairs:assert pairs.pop(key)==signature
        else:pairs[key]=signature
        if r.formulation=='M1':
            assert comp['epoch_logs'] and all(np.isfinite(e['joint_loss']) for e in comp['epoch_logs'])
            maximum=max(maximum,float(p.y_pred.max()))
            if r.vm_id==dominant:dominant_epochs.append(int(r.selected_epoch))
        if i%350==0:print(block,'SAVED_DISK_ARTIFACTS_VERIFIED',i,flush=True)
    assert not pairs and len(dominant_epochs)==15
    checks[block]=dict(status='NO_TRAINING_FAILURE_VISIBLE',fresh_final_checkpoints=1050,fresh_prediction_files=1050,
        finite_weights_targets_predictions=True,inverse_mapping_exact=True,
        final_scalers_exact_against_frozen_partitions=True,unique_final_scaler_partitions=len(scaler_count),
        matched_S2_M1_target_support=True,one_recorded_final_test_evaluation=True,
        dominant_VM=dominant,dominant_M1_epoch_min=min(dominant_epochs),dominant_M1_epoch_max=max(dominant_epochs),
        largest_saved_M1_disk_prediction=maximum,
        raw_scaler_reconstruction='Stage18A1 verified all 3150 partitions from raw archive; reused with full protected-tree preservation, not rerun here')
    # Historical failures are evidence, never erased or silently treated as valid.
    fail=[]
    for p in sorted((root/'runtime/failures').glob('*.json')):
        c=record(p);fail.append({'path':str(p.relative_to(ROOT)),'identity':c.get('identity',{})})
    checks[block]['preserved_failure_records']=fail
    assert not any(v['identity'].get('formulation')=='M1' for v in fail)
assert np.isclose(checks['Materna-T3']['largest_saved_M1_disk_prediction'],109920.414001,atol=.0000005,rtol=0)
analysis['materna_fitting_checks']=checks
analysis['classification']='BROAD_DEGRADATION'
analysis['classification_basis']='Descriptive, no numerical cutoff: all seven machine means and 31/35 machine-folds worsen; 239/280 lead cells worsen. Magnitude is nonuniform, with 50.63% of per-machine excess on machine01. Not uniform degradation and not a causal sharing diagnosis.'
temporal=pd.read_csv(used(BASE/'outputs/scientific_v1/analysis/temporal_classification_changes.csv'))
assert len(temporal)==12 and temporal.temporally_classification_variable.sum()==7 and temporal.raw_sign_reversal.sum()==5
analysis['frozen_RQ4_check']={'resource_comparison_pairs':12,'classification_variable':7,'raw_sign_reversal':5,'frozen_rule_unchanged':True}
(OUT/'analysis.json').write_text(json.dumps(analysis,indent=2,allow_nan=False)+'\n')
(OUT/'input_sha256_inventory.json').write_text(json.dumps({'files':[index[k] for k in sorted(index)]},indent=2)+'\n')
print(json.dumps(checks,indent=2),flush=True)
