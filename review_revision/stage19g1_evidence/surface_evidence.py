"""Post-hoc descriptive audit of SAVED errors and artifacts; no fit/forward/predict.

JSON is an analysis intermediate. Requested CSVs are authored separately by JS.
"""
from pathlib import Path
from decimal import Decimal
import csv, hashlib, importlib, json, re, sys
import numpy as np
import pandas as pd
import torch

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
# Pure support construction only. No runner, model definition or training import.
build_factorial_folds=importlib.import_module('multiresource.04_lstm_factorial.src.splits').build_factorial_folds

INPUTS={}
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as s:
        for b in iter(lambda:s.read(4194304),b''):h.update(b)
    return h.hexdigest()
def used(rel):
    p=Path(rel) if Path(rel).is_absolute() else ROOT/rel
    INPUTS[str(p.relative_to(ROOT))]={'sha256':sha(p),'bytes':p.stat().st_size}
    return p
def frame(rel,**kw):return pd.read_csv(used(rel),float_precision='round_trip',**kw)
def rows(rel):
    with used(rel).open(newline='') as s:return list(csv.DictReader(s))
def record(rel):return json.loads(used(rel).read_text())
def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def csv_payload(records):
    keys=list(records[0]);return {'columns':keys,'rows':[[str(r[k]) for k in keys] for r in records]}
def summary(f,keys):
    f=f.copy();d=f.candidate_mae-f.reference_mae
    pos=float(d.clip(lower=0).sum());net=float(d.sum())
    ranked=f.assign(excess=d,ratio=f.candidate_mae/f.reference_mae).sort_values('excess',ascending=False)
    def peak(n):
        q=ranked[ranked.excess>0].head(n)
        return {'units':q[keys].to_dict('records'),'excess_sum':float(q.excess.sum()),
            'share_positive_percent':100*float(q.excess.sum())/pos,
            'share_net_percent':100*float(q.excess.sum())/net}
    return dict(units=len(f),worse=int((d>0).sum()),better=int((d<0).sum()),ties=int((d==0).sum()),
        median_ratio=float(np.median(f.candidate_mae/f.reference_mae)),
        reference_MAE=float(f.reference_mae.mean()),candidate_MAE=float(f.candidate_mae.mean()),
        positive_excess_sum=pos,net_excess_sum=net,negative_excess_sum=float(d.clip(upper=0).sum()),
        largest=peak(1),top3=peak(3))

reportA=used('review_revision/stage18a1_diagnostic_audit.md').read_text()
used('review_revision/stage18c1_final_robustness_synthesis.md')
robust=rows('review_revision/stage18c1_evidence/robust_seed_mean_cells.csv')
robust=[r for r in robust if r['comparison']=='M1_vs_S2']
assert len(robust)==24 and len({(r['block'],r['resource']) for r in robust})==24
robust_out=[dict(block=r['block'],resource=r['resource'],
    frozen_MacroMAE_gain_percent=r['frozen_MacroMAE_gain_percent'],
    median_candidate_reference_MAE_ratio=r['median_MAE_ratio'],
    candidate_win_percent=str(Decimal(r['candidate_win_rate'])*100),ties=r['ties']) for r in robust]
assert all(Decimal(r['median_candidate_reference_MAE_ratio'])>1 and Decimal(r['candidate_win_percent'])<50 and r['ties']=='0' for r in robust_out)
seed=rows('review_revision/stage18c1_evidence/seed_sensitivity.csv')
assert len(seed)==48 and len({(r['block'],r['resource'],r['comparison']) for r in seed})==48
seed_out=[dict(block=r['block'],resource=r['resource'],comparison=r['comparison'],
    seed0_gain_percent=r['seed0_gain'],seed1_gain_percent=r['seed1_gain'],seed2_gain_percent=r['seed2_gain'],
    range_percentage_points=r['seed_gain_range_pp'],population_SD_percentage_points=r['seed_gain_population_SD_pp'],
    status='FLIP' if r['aggregate_seed_sign_variable']=='True' else 'stable') for r in seed]
assert sum(r['status']=='FLIP' for r in seed_out if r['comparison']=='S2_vs_S1')==9
assert sum(r['status']=='FLIP' for r in seed_out if r['comparison']=='M1_vs_S2')==4
for r in seed_out:
    values=[float(r[f'seed{i}_gain_percent']) for i in range(3)]
    assert r['status']==('FLIP' if min(values)<0<max(values) else 'stable')

# Materna: same Stage18A1 per-VM estimand, equal seed/fold/lead errors.
external=frame('independent_validation/06_materna_replication/outputs/scientific_v1/analysis/matched_vm_fold_cells.csv',dtype={'vm_id':str})
materna={};materna_rows=[]
appendix=reportA.split('## Appendix E.')[1].split('## Appendix F.')[0]
old={}
for line in appendix.splitlines():
    if line.startswith('| Materna-'):
        q=[v.strip() for v in line.strip('|').split('|')]
        old[(q[0],q[1])]=q[2:]
for block,largest,worse,better,shares in [('Materna-T1','266',28,7,('82.10','91.72')),('Materna-T3','272',32,3,('86.97','92.93'))]:
    f=external[external.environment_key.eq(block)&external.resource.eq('DISK_WRITE')&external.formulation.isin(['S2','M1'])]
    assert len(f)==1750 and not f.duplicated(['formulation','vm_id','fold','lead']).any()
    p=f.pivot(index=['vm_id','fold','lead'],columns='formulation',values='seed_mean_mae').reset_index()
    g=p.groupby('vm_id',as_index=False)[['S2','M1']].mean().rename(columns={'S2':'reference_mae','M1':'candidate_mae'})
    s=summary(g,['vm_id'])
    assert s['worse']==worse and s['better']==better and s['largest']['units']==[{'vm_id':largest}]
    assert f"{s['largest']['share_positive_percent']:.2f}"==shares[0]
    assert f"{s['top3']['share_positive_percent']:.2f}"==shares[1]
    for r in g.to_dict('records'):
        values=[r['reference_mae'],r['candidate_mae'],r['candidate_mae']/r['reference_mae'],r['candidate_mae']-r['reference_mae']]
        assert [f'{v:.6f}' for v in values]==old[(block,r['vm_id'])],(block,r)
        materna_rows.append(dict(block=block,vm=r['vm_id'],S2_MAE=r['reference_mae'],M1_MAE=r['candidate_mae'],ratio=values[2],excess=values[3]))
    materna[block]=s
assert reportA.count('**C. NO_TRAINING_FAILURE_VISIBLE**')==2

# TimeTrack: seed-mean entity/fold/lead errors, eight equally weighted leads.
ttroot='multiresource/04_lstm_factorial/outputs/scientific'
paired=frame('review_revision/stage18c1_evidence/matched_seed_mean_errors.csv')
cells=paired[paired.block.eq('TimeTrack')&paired.resource.eq('MEMORY')&paired.comparison.eq('M1_vs_S2')]
assert len(cells)==280 and not cells.duplicated(['entity','fold','lead']).any()
raw=frame(ttroot+'/comparisons/m1_vs_s2_cells.csv')
raw=raw[raw.resource.eq('MEMORY')]
assert len(raw)==840 and (raw.baseline_n==raw.candidate_n).all()
g=raw.groupby(['machine','fold','lead'],as_index=False)[['candidate_mae','baseline_mae']].mean().rename(columns={'machine':'entity','baseline_mae':'reference_mae'})
check=g.merge(cells,on=['entity','fold','lead'],validate='one_to_one',suffixes=('_raw','_saved'))
for col in ['candidate_mae','reference_mae']:
    assert np.allclose(check[col+'_raw'],check[col+'_saved'],rtol=1e-12,atol=0)
mf=cells.groupby(['entity','fold'],as_index=False)[['candidate_mae','reference_mae']].mean().rename(columns={'entity':'machine'})
machine=mf.groupby('machine',as_index=False)[['candidate_mae','reference_mae']].mean()
fold=mf.groupby('fold',as_index=False)[['candidate_mae','reference_mae']].mean()
diagnosis={'machine_fold':summary(mf,['machine','fold']),'machine':summary(machine,['machine']),'fold':summary(fold,['fold']),
    'entity_fold_lead':summary(cells,['entity','fold','lead'])}
contexts=frame(ttroot+'/selected_contexts.csv')
s2=contexts[contexts.formulation.eq('S2')&contexts.resource.eq('MEMORY')].rename(columns={'selected_L':'S2_L'})
m1=contexts[contexts.formulation.eq('M1')].rename(columns={'selected_L':'M1_L'})
ctx=mf.merge(s2[['machine','fold','S2_L']],on=['machine','fold'],validate='one_to_one').merge(m1[['machine','fold','M1_L']],on=['machine','fold'],validate='one_to_one')
ctx['excess']=ctx.candidate_mae-ctx.reference_mae
assert int((ctx.S2_L!=ctx.M1_L).sum())==17
top=ctx.sort_values('excess',ascending=False).head(5)
assert list(zip(top.machine.head(2),top.fold.head(2)))==[('machine01',2),('machine01',3)]
assert (top.head(2).S2_L!=top.head(2).M1_L).all()
diagnosis['dominant_contexts']=top.to_dict('records')
diagnosis['mismatched_machine_folds']=int((ctx.S2_L!=ctx.M1_L).sum())
attribution=[]
for scope,f in [('machine_fold',ctx),('machine',machine),('fold',fold)]:
    for r in f.to_dict('records'):
        attribution.append(dict(scope=scope,machine=r.get('machine','ALL'),fold=r.get('fold','ALL'),
            S2_MAE=r['reference_mae'],M1_MAE=r['candidate_mae'],M1_S2_ratio=r['candidate_mae']/r['reference_mae'],
            excess_MAE=r['candidate_mae']-r['reference_mae'],S2_context=r.get('S2_L','varies'),M1_context=r.get('M1_L','varies'),
            context_match=('YES' if r['S2_L']==r['M1_L'] else 'NO') if 'S2_L' in r else 'mixed across component cells'))

print('DESCRIPTIVE_ATTRIBUTION',json.dumps(diagnosis,indent=2),flush=True)

# Re-read all saved TimeTrack MEMORY predictions/checkpoints. No neural forward pass.
registry=frame(ttroot+'/run_registry.csv')
registry=registry[(registry.formulation.eq('S2')&registry.resource.eq('MEMORY'))|registry.formulation.eq('M1')]
assert len(registry)==210 and not registry.duplicated(['formulation','machine','fold','seed']).any()
metrics=pd.read_parquet(used(ttroot+'/metrics.parquet'))
metrics=metrics[metrics.resource.eq('MEMORY')&metrics.formulation.isin(['S2','M1'])]
panelpath=used('discovery/02_dependency_analysis/outputs/canonical_panel.parquet')
assert INPUTS[str(panelpath.relative_to(ROOT))]['sha256']=='c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a'
panel=pd.read_parquet(panelpath);times=panel.timestamp.to_numpy();segments=panel.segment_id.to_numpy()
foldcache={};scalecache={};pair_targets={};fitchecks=[]
for i,r in enumerate(registry.itertuples(),1):
    comp=record(ttroot+f'/runtime/completions/final/{r.run_id}.json')
    assert comp['status']=='complete'
    assert comp['identity']['run_id']==r.run_id and comp['identity']['L']==r.L
    for kind in ['model','prediction']:
        path=used(getattr(r,kind+'_path'))
        assert INPUTS[str(path.relative_to(ROOT))]['sha256']==getattr(r,kind+'_sha256')==comp[kind+'_sha256']
    checkpoint=torch.load(ROOT/r.model_path,map_location='cpu',weights_only=True)
    assert all(torch.isfinite(v).all().item() for v in checkpoint.values())
    parameters=sum(v.numel() for v in checkpoint.values())
    assert parameters==(53280 if r.formulation=='M1' else 51720)
    if r.machine not in foldcache:
        foldcache[r.machine]=build_factorial_folds(panel,r.machine,128)
    f=foldcache[r.machine][r.fold-1]
    assert len(f.outer_train)==comp['outer_train_n'] and len(f.outer_test)==comp['outer_test_n']
    assert f.hashes['outer_train']==comp['outer_train_hash'] and f.hashes['outer_test']==comp['outer_test_hash']
    assert times[f.outer_train+128].max()<times[f.outer_test[0]]
    sc_key=(r.machine,r.fold,r.L)
    if sc_key not in scalecache:
        indices=np.unique(np.concatenate([(f.outer_train[:,None]-np.arange(r.L-1,-1,-1)).ravel(),
            (f.outer_train[:,None]+np.array([1,2,4,8,16,32,64,128])).ravel()]))
        values=panel.loc[indices,r.machine+'__memory_used'].to_numpy(dtype=np.float64)
        q25,med,q75=np.quantile(values,[.25,.5,.75]);iqr=q75-q25
        scalecache[sc_key]=dict(transformed_median=float(med),transformed_iqr=float(iqr),native_iqr=float(iqr))
    sc=comp['scaler_metadata']['MEMORY'];assert sc==scalecache[sc_key] and sc['native_iqr']>0
    p=pd.read_parquet(ROOT/r.prediction_path,filters=[('resource','=','MEMORY')]).sort_values(['origin_index','lead']).reset_index(drop=True)
    assert not p.duplicated(['origin_index','lead']).any() and len(p)==len(f.outer_test)*8
    assert np.array_equal(np.unique(p.origin_index),f.outer_test)
    assert np.isfinite(p[['y_true','y_pred','y_pred_scaled','y_pred_unclipped']].to_numpy()).all()
    assert np.array_equal(p.target_index,p.origin_index+p.lead)
    assert np.array_equal(p.target_timestamp.to_numpy(),times[p.target_index.to_numpy()])
    assert np.array_equal(p.y_true,panel.loc[p.target_index,r.machine+'__memory_used'].to_numpy(dtype=np.float32))
    inverse=p.y_pred_scaled.to_numpy(dtype=float)*sc['transformed_iqr']+sc['transformed_median']
    assert np.array_equal(inverse,p.y_pred) and np.array_equal(inverse,p.y_pred_unclipped)
    pm=p.assign(error=np.abs(p.y_true-p.y_pred)).groupby('lead').error.mean()
    stored=metrics[metrics.run_id.eq(r.run_id)].sort_values('lead')
    assert len(stored)==8 and np.allclose(pm,stored.mae,rtol=1e-12,atol=0)
    for col in ['origin_index','target_index','sample_id','origin_timestamp','target_timestamp','support_hash','y_true']:
        key=(r.machine,r.fold,r.seed,col)
        if key in pair_targets:assert np.array_equal(pair_targets.pop(key),p[col].to_numpy())
        else:pair_targets[key]=p[col].to_numpy()
    fitchecks.append(dict(machine=r.machine,fold=r.fold,seed=r.seed,formulation=r.formulation,L=r.L,
        run_id=r.run_id,model_sha256=r.model_sha256,prediction_sha256=r.prediction_sha256,
        parameters=parameters,prediction_rows=len(p),prediction_min=float(p.y_pred.min()),prediction_max=float(p.y_pred.max()),
        target_min=float(p.y_true.min()),target_max=float(p.y_true.max()),scaler=sc,status='PASS'))
    if i%35==0:print('SAVED_MEMORY_ARTIFACTS_VERIFIED',i,flush=True)
assert not pair_targets
validation=record(ttroot+'/validation/validation.json');assert validation['status']=='PASS' and not validation['failures']
assert all(v==0 for v in validation['structural'].values())
diagnosis['artifact_checks']={'status':'PASS','final_checkpoints':210,'prediction_files':210,
    'memory_metric_rows':len(metrics),'distinct_reconstructed_final_memory_scalers':len(scalecache),
    'finite_weights_targets_predictions':True,'inverse_mapping_exact':True,'training_only_scaler_exact':True,
    'matched_target_support_exact':True,'existing_validation_status':'PASS',
    'no_training_or_model_inference':True,'limitations':'No gradient/clipping diagnostics or new optimisation experiment; finite artifacts do not prove optimal training.'}

capacity=rows('review_revision/experiments/m1_capacity_matched/posthoc_results.csv')
capacity=[r for r in capacity if r['block']=='TimeTrack' and r['resource']=='MEMORY'];assert len(capacity)==1
capacity=capacity[0]
frozen=rows(ttroot+'/comparisons/m1_vs_s2.csv')
frozen=[r for r in frozen if r['resource']=='MEMORY' and r['lead']=='OVERALL'];assert len(frozen)==1
assert np.isclose(float(frozen[0]['macro_mae_candidate']),float(capacity['M1_H64_MacroMAE']),rtol=1e-14,atol=0)
assert round(float(capacity['original_H64_vs_S2_gain_percent']),2)==round(float(capacity['H129_vs_S2_gain_percent']),2)==-18.48
used('manuscript/jss/tables/posthoc_controls.tex')
manuscript=used('manuscript/jss/manuscript.tex').read_text()
wording=[]
for old,new,scope in [
    ('Temporal heterogeneity confirmed.','The prespecified RQ4 criterion for temporal heterogeneity was met.','Required interpretation clarification; preserve frozen decision/counts.'),
    ('Figure~\\ref{fig:primary-gains} reveals heterogeneity at each prespecified\nlevel.',
     'Figure~\\ref{fig:primary-gains} describes variation in point estimates across resources, environments and dependent temporal blocks.','Optional precision; the existing sentence is not itself a false numerical claim.'),
    ('Temporal heterogeneity within the dependent\nMaterna blocks is distinct: M1-versus-S2 CPU changed from positive in T1 to\nnegative in T2--T3, moving from neutral or mixed to broadly negative and back\nto neutral or mixed.',
     'Across the dependent Materna blocks, frozen M1-versus-S2 CPU point estimates changed from positive in T1 to negative in T2--T3, while the frozen class changed from neutral or mixed to broadly negative and back to neutral or mixed.',
     'Optional point-estimate qualifier; T1 M1:S2 CPU is seed-variable. Preserve the recorded classes.')]:
    assert old in manuscript
    wording.append(dict(line_start=manuscript[:manuscript.index(old)].count('\n')+1,
        line_end=manuscript[:manuscript.index(old)+len(old)].count('\n')+1,current_exact=old,recommended=new,scope=scope))

save('analysis.json',dict(label='POST-HOC DIAGNOSTIC / EVIDENCE SURFACING',materna=materna,
    materna_per_vm=materna_rows,timetrack_memory=diagnosis,capacity_exact=capacity,
    original_frozen_memory_exact=frozen[0],rq4_wording_audit=wording,fit_checks=fitchecks,
    classification='PENDING_DESCRIPTIVE_REVIEW',training=0,model_inference=0))
payload={
    'm1_s2_robustness_24.csv':csv_payload(robust_out),
    'seed_sensitivity_48.csv':csv_payload(seed_out),
    'timetrack_memory_attribution.csv':csv_payload(attribution),
}
save('table_payload.json',payload)
save('input_sha256_inventory.json',dict(files=[dict(path=k,**v) for k,v in sorted(INPUTS.items())]))
print('ALL_EVIDENCE_CHECKS_PASS',json.dumps({'materna':materna,'memory':diagnosis,'capacity':capacity},indent=2),flush=True)
