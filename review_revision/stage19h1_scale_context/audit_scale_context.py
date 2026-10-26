"""Read-only frozen-partition statistics and saved inverse-map checks. No model code."""
from pathlib import Path
import hashlib, importlib.util, json, sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'independent_validation/06_materna_replication'
sys.path.insert(0,str(ROOT/'independent_validation/05_bitbrains_factorial'))
from src.cleaning import clean_and_segment
from src.panel import scaler_rows
from src.support import sample_set_hash

inputs={}
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4194304),b''):h.update(chunk)
    return h.hexdigest()
def used(path):
    path=Path(path)
    rel=str(path.relative_to(ROOT))
    inputs[rel]=dict(path=rel,sha256=sha(path),bytes=path.stat().st_size)
    return path
def read(path):return json.loads(used(path).read_text())
def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
spec=importlib.util.spec_from_file_location('frozen_preflight_readonly',used(BASE/'run_phase4d_audit.py'))
preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
for rel in ['src/cleaning.py','src/panel.py','src/support.py','src/transforms.py','src/ingestion.py']:
    used(ROOT/'independent_validation/05_bitbrains_factorial'/rel)
archive=used(preflight.RAW_ARCHIVE)
assert inputs[str(archive.relative_to(ROOT))]['sha256']=='1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4'
cohort=pd.read_csv(used(BASE/'manifests/CANDIDATE_35_VM_COHORT.csv'),dtype={'entity_id':str})
ids=set(cohort.entity_id)
assert len(ids)==len(cohort)==35
scalers=pd.read_csv(used(BASE/'manifests/MATERNA_SCALER_PARTITIONS.csv'),dtype={'VM_ID':str},float_precision='round_trip')
support=pd.read_parquet(used(BASE/'manifests/MATERNA_SUPPORT_MANIFEST.parquet'))
assert len(scalers)==3150 and not scalers.duplicated(['trace','VM_ID','fold','phase','L']).any()
support_index={(r.environment,r.vm_id,int(r.fold),int(r.L)):r for r in support.itertuples(index=False)}
manifest={(r.trace,r.VM_ID,int(r.fold),int(r.L)):r for r in scalers[scalers.phase.eq('final')].itertuples(index=False)}
partitions=[];partition_index={};run_checks=[];inverse_checks=[];registries={}

for trace,dominant in [('Materna-T1','266'),('Materna-T3','272')]:
    root=BASE/'outputs/scientific_v1'/trace
    validation=read(root/'validation/technical_validation.json')
    assert validation['status']=='PASS' and not validation['failures'] and all(v==0 for v in validation['violations'].values())
    registry=pd.read_csv(used(root/'run_registry.csv'),dtype={'vm_id':str},float_precision='round_trip')
    registry=registry[registry.formulation.eq('M1')|registry.resource.eq('DISK_WRITE')].copy()
    assert len(registry)==1575 and set(registry.vm_id)==ids
    assert not registry.duplicated(['formulation','vm_id','fold','seed']).any()
    registries[trace]=registry
    for vm in sorted(ids,key=int):
        # The frozen reader/cleaner accesses only the existing raw archive.
        raw=preflight.read_vm(trace,vm)
        assert raw.archive_sha256==inputs[str(archive.relative_to(ROOT))]['sha256']
        clean=clean_and_segment(raw)
        frame=clean.frame
        timestamps=frame.timestamp_seconds.to_numpy(np.int64)
        native=frame.DISK_WRITE.to_numpy(np.float64)
        for fold in range(1,6):
            for L in [4,9,18]:
                key=(trace,vm,fold,L);s=support_index[key];m=manifest[key]
                train_ids=np.asarray(s.outer_train_origin_ids,dtype=np.int64)
                test_ids=np.asarray(s.outer_test_origin_ids,dtype=np.int64)
                assert sample_set_hash(train_ids)==s.outer_train_hash
                assert sample_set_hash(test_ids)==s.outer_test_hash
                origins=np.searchsorted(timestamps,train_ids)
                assert np.array_equal(timestamps[origins],train_ids)
                assert len(origins)==s.outer_train_count and len(test_ids)==s.outer_test_count
                assert np.all(timestamps[origins+max(preflight.LEADS)]<test_ids.min())
                fit_rows=scaler_rows(origins,L)
                fit_ids=timestamps[fit_rows]
                assert len(fit_rows)==m.fit_row_count
                assert sample_set_hash(fit_ids)==m.fit_timestamp_sha256
                assert fit_ids.max()<test_ids.min() and not np.intersect1d(fit_ids,test_ids).size
                values=native[fit_rows];transformed=np.log1p(values)
                tq=np.quantile(transformed,[.25,.5,.75]);nq=np.quantile(values,[.25,.5,.75])
                stored_median=json.loads(m.transformed_medians)[3]
                stored_iqr=json.loads(m.transformed_iqrs)[3]
                stored_native_iqr=json.loads(m.native_iqrs)[3]
                assert float(tq[1])==stored_median
                assert float(tq[2]-tq[0])==stored_iqr
                assert float(nq[2]-nq[0])==stored_native_iqr
                assert np.isfinite([*tq,*nq]).all() and stored_iqr>0 and stored_native_iqr>0
                identity=dict(trace=trace,VM_ID=vm,fold=fold,phase='final',L=L,
                    fit_row_count=int(m.fit_row_count),fit_timestamp_sha256=m.fit_timestamp_sha256,
                    transformed_medians=json.loads(m.transformed_medians),transformed_iqrs=json.loads(m.transformed_iqrs),native_iqrs=json.loads(m.native_iqrs))
                assert preflight.canonical_hash(identity)==m.scaler_partition_sha256
                record=dict(trace=trace,vm_id=vm,fold=fold,L=L,fit_row_count=len(fit_rows),
                    fit_timestamp_sha256=m.fit_timestamp_sha256,scaler_partition_sha256=m.scaler_partition_sha256,
                    transformed_median=stored_median,transformed_iqr=stored_iqr,
                    native_median=float(nq[1]),native_iqr=stored_native_iqr,
                    native_q25=float(nq[0]),native_q75=float(nq[2]),
                    fit_first_timestamp=int(fit_ids.min()),fit_last_timestamp=int(fit_ids.max()),
                    outer_test_first_timestamp=int(test_ids.min()),
                    all_fit_rows_precede_outer_test=True,raw_member_sha256=raw.members[0]['member_sha256'])
                partitions.append(record);partition_index[key]=record
        print(trace,'RAW_TRAINING_PARTITIONS_VERIFIED',vm,flush=True)
    for row in registry.itertuples(index=False):
        comp=read(root/f'runtime/completions/final/{row.run_id}.json')
        assert comp['status']=='complete' and comp['test_evaluations']==1
        assert comp['scaler_fit_split']=='complete_legal_outer_train_only'
        key=(trace,row.vm_id,int(row.fold),int(row.L));m=manifest[key];s=support_index[key]
        expected={name:json.loads(getattr(m,column)) for name,column in
            [('native_iqr','native_iqrs'),('transformed_iqr','transformed_iqrs'),('transformed_median','transformed_medians')]}
        assert comp['scaler']==expected
        assert np.isfinite(list(comp['scaler'].values())).all()
        assert min(comp['scaler']['transformed_iqr'])>0
        assert comp['outer_train_hash']==s.outer_train_hash and comp['outer_test_hash']==s.outer_test_hash
        assert comp['outer_train_n']==s.outer_train_count and comp['outer_test_n']==s.outer_test_count
        run_checks.append(dict(trace=trace,vm_id=row.vm_id,fold=int(row.fold),seed=int(row.seed),
            formulation=row.formulation,L=int(row.L),run_id=row.run_id,scaler_partition_sha256=m.scaler_partition_sha256))
        if row.vm_id!=dominant:continue
        model=used(BASE/row.model_path);pred=used(BASE/row.prediction_path)
        assert inputs[str(model.relative_to(ROOT))]['sha256']==row.model_sha256==comp['model_sha256']
        assert inputs[str(pred.relative_to(ROOT))]['sha256']==row.prediction_sha256==comp['prediction_sha256']
        p=pd.read_parquet(pred,filters=[('resource','=','DISK_WRITE')])
        assert len(p)==s.outer_test_count*len(preflight.LEADS)
        assert not p.duplicated(['origin_index','lead']).any()
        assert np.isfinite(p[['y_true','y_pred_scaled','y_pred','y_pred_unclipped']].to_numpy()).all()
        inv=np.expm1(p.y_pred_scaled.to_numpy(dtype=np.float64)*expected['transformed_iqr'][3]+expected['transformed_median'][3])
        assert np.array_equal(inv,p.y_pred_unclipped.to_numpy())
        assert np.array_equal(np.maximum(inv,0.),p.y_pred.to_numpy())
        assert set(p.origin_timestamp_seconds)==set(s.outer_test_origin_ids)
        inverse_checks.append(dict(trace=trace,vm_id=dominant,fold=int(row.fold),seed=int(row.seed),
            formulation=row.formulation,L=int(row.L),run_id=row.run_id,
            saved_rows=len(p),inverse_and_nonnegative_projection_exact=True,
            checkpoint_prediction_hashes_match=True,finite_predictions=True))
    print(trace,'COMPLETIONS_AND_DOMINANT_INVERSES_VERIFIED',len(registry),flush=True)

def relative(record,cohort_records):
    assert len(cohort_records)==35 and {v['vm_id'] for v in cohort_records}==ids
    result={}
    for key in ['transformed_iqr','transformed_median','native_iqr','native_median']:
        values=np.array([v[key] for v in cohort_records]);value=record[key]
        less=int(np.count_nonzero(values<value));le=int(np.count_nonzero(values<=value))
        result[key]=dict(value=value,ascending_rank_min=less+1,ascending_rank_max=le,
            ecdf_percent=100.*le/35,cohort_min=float(values.min()),cohort_median=float(np.median(values)),
            cohort_max=float(values.max()),cohort_ties=le-less,
            ratio_to_cohort_median=float(value/np.median(values)) if np.median(values)!=0 else None)
    return result

fixed=[];selected=[]
for trace,dominant in [('Materna-T1','266'),('Materna-T3','272')]:
    for fold in range(1,6):
        for L in [4,9,18]:
            record=partition_index[(trace,dominant,fold,L)]
            cr=[partition_index[(trace,vm,fold,L)] for vm in sorted(ids,key=int)]
            uses=registries[trace]
            uses=uses[uses.vm_id.eq(dominant)&uses.fold.eq(fold)&uses.L.eq(L)]
            users=[dict(formulation=form,seeds=sorted(int(x) for x in group.seed)) for form,group in uses.groupby('formulation')]
            fixed.append(dict(trace=trace,vm_id=dominant,fold=fold,L=L,selected_by=users,
                native_median_exactly_recovered_from_training_rows=True,metrics=relative(record,cr)))
        for form in ['S1','S2','M1']:
            group=registries[trace]
            group=group[group.fold.eq(fold)&group.formulation.eq(form)]
            # Context selection is shared across the three existing seeds, not repeated observations.
            assert group.groupby('vm_id').L.nunique().eq(1).all()
            chosen=group.groupby('vm_id').L.first().to_dict()
            cr=[partition_index[(trace,vm,fold,int(chosen[vm]))] for vm in sorted(ids,key=int)]
            record=partition_index[(trace,dominant,fold,int(chosen[dominant]))]
            selected.append(dict(trace=trace,vm_id=dominant,fold=fold,formulation=form,
                L=int(chosen[dominant]),seeds=[0,1,2],metrics=relative(record,cr)))
assert len(partitions)==1050 and len(fixed)==30 and len(selected)==30
assert len(run_checks)==3150 and len(inverse_checks)==90
for record in fixed+selected:
    # Report exact distances/ranks; no new "near-minimum" threshold or fit-health rule.
    assert record['metrics']['transformed_iqr']['value']>record['metrics']['transformed_iqr']['cohort_median']
    assert record['metrics']['native_iqr']['value']>record['metrics']['native_iqr']['cohort_median']
summary={}
for trace,vm in [('Materna-T1','266'),('Materna-T3','272')]:
    records=[v for v in fixed if v['trace']==trace]
    m1=[v for v in selected if v['trace']==trace and v['formulation']=='M1']
    summary[trace]=dict(vm_id=vm,classification='SCALE_INSTABILITY_NOT_SUPPORTED',
        transformed_iqr_range=[min(v['metrics']['transformed_iqr']['value'] for v in records),max(v['metrics']['transformed_iqr']['value'] for v in records)],
        native_iqr_range=[min(v['metrics']['native_iqr']['value'] for v in records),max(v['metrics']['native_iqr']['value'] for v in records)],
        M1_selected_contexts=[v['L'] for v in m1],
        M1_selected_log_iqr_ranks=[v['metrics']['transformed_iqr']['ascending_rank_min'] for v in m1],
        M1_selected_log_iqr_relative_median_range=[min(v['metrics']['transformed_iqr']['ratio_to_cohort_median'] for v in m1),max(v['metrics']['transformed_iqr']['ratio_to_cohort_median'] for v in m1)],
        M1_selected_native_iqr_ranks=[v['metrics']['native_iqr']['ascending_rank_min'] for v in m1],
        implementation_defect_demonstrated=False,further_experiment_required=False)
used(ROOT/'review_revision/stage18a1_diagnostic_audit.md')
used(ROOT/'review_revision/stage19g1_evidence/analysis.json')
used(ROOT/'review_revision/stage19g1_evidence/verification.json')
result=dict(status='AUDIT_CHECKS_PASS_AWAITING_PRESERVATION',summaries=summary,
    fixed_context_dominant_partitions=fixed,selected_context_cohort_comparisons=selected,
    cohort_partition_distribution=partitions,completion_scaler_checks=run_checks,dominant_inverse_checks=inverse_checks,
    raw_final_partitions_reconstructed=1050,cohort_completion_scalers_verified=3150,
    dominant_predictions_and_checkpoint_hashes_verified=90,training=0,inference=0,
    manuscript_modifications=0,scientific_modifications=0,commit='no',push='no')
write('analysis.json',result)
write('input_sha256_inventory.json',dict(files=[inputs[k] for k in sorted(inputs)]))
print(json.dumps(summary,indent=2),flush=True)
