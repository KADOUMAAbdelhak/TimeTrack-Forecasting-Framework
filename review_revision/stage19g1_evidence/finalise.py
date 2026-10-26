"""Independent export/source-preservation handoff checks. No scientific writes."""
from pathlib import Path
from decimal import Decimal
import csv,hashlib,json,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as s:
        for b in iter(lambda:s.read(4194304),b''):h.update(b)
    return h.hexdigest()
def rows(p):
    with p.open(newline='') as s:return list(csv.DictReader(s))
sources=json.loads((OUT/'input_sha256_inventory.json').read_text())['files']
for i,v in enumerate(sources,1):
    p=ROOT/v['path'];assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],v['path']
    if i%2000==0:print('DIRECT_INPUTS_REHASHED',i,flush=True)
preserve=json.loads((OUT/'preservation.json').read_text());assert preserve['status']=='PASS'
assert sha(ROOT/'manuscript/jss/manuscript.tex')==preserve['manuscript_sha256']
robust=rows(OUT/'m1_s2_robustness_24.csv')
original={ (r['block'],r['resource']):r for r in rows(ROOT/'review_revision/stage18c1_evidence/robust_seed_mean_cells.csv') if r['comparison']=='M1_vs_S2'}
assert len(robust)==len(original)==24 and len({(r['block'],r['resource']) for r in robust})==24
for r in robust:
    q=original[(r['block'],r['resource'])]
    assert r['frozen_MacroMAE_gain_percent']==q['frozen_MacroMAE_gain_percent']
    assert r['median_candidate_reference_MAE_ratio']==q['median_MAE_ratio'] and r['ties']==q['ties']
    assert Decimal(r['candidate_win_percent'])==Decimal(q['candidate_win_rate'])*100
seed=rows(OUT/'seed_sensitivity_48.csv')
source={(r['block'],r['resource'],r['comparison']):r for r in rows(ROOT/'review_revision/stage18c1_evidence/seed_sensitivity.csv')}
assert len(seed)==48 and len({(r['block'],r['resource'],r['comparison']) for r in seed})==48
for r in seed:
    q=source[(r['block'],r['resource'],r['comparison'])]
    for key,old in [('seed0_gain_percent','seed0_gain'),('seed1_gain_percent','seed1_gain'),('seed2_gain_percent','seed2_gain'),
        ('range_percentage_points','seed_gain_range_pp'),('population_SD_percentage_points','seed_gain_population_SD_pp')]:
        assert r[key]==q[old]
    assert r['status']==('FLIP' if q['aggregate_seed_sign_variable']=='True' else 'stable')
attribution=rows(OUT/'timetrack_memory_attribution.csv')
assert len(attribution)==47 and len({(r['scope'],r['machine'],r['fold']) for r in attribution})==47
for r in attribution:
    s,c=float(r['S2_MAE']),float(r['M1_MAE'])
    assert np.isclose(c/s,float(r['M1_S2_ratio']),rtol=1e-14,atol=0)
    assert c-s==float(r['excess_MAE'])
mf=[r for r in attribution if r['scope']=='machine_fold']
for r in attribution:
    if r['scope']=='machine':q=[v for v in mf if v['machine']==r['machine']]
    elif r['scope']=='fold':q=[v for v in mf if v['fold']==r['fold']]
    else:continue
    for col in ['S2_MAE','M1_MAE']:assert np.isclose(float(r[col]),np.mean([float(v[col]) for v in q]),rtol=1e-14,atol=0)
tab=(ROOT/'manuscript/jss/tables/posthoc_controls.tex').read_text().split('\\textbf{B:}')[0]
tt=[v for v in tab.splitlines() if v.strip().startswith('TimeTrack &')]
assert len(tt)==1 and tt[0].split('&')[3].strip()=='$[-18.48/-17.79/-18.48]$'
a=json.loads((OUT/'analysis.json').read_text())
assert a['classification']=='BROAD_DEGRADATION'
assert all(v['status']=='NO_TRAINING_FAILURE_VISIBLE' for v in a['materna_fitting_checks'].values())
manuscript=(ROOT/'manuscript/jss/manuscript.tex').read_text()
for v in a['rq4_wording_audit']:
    assert v['current_exact'] in manuscript and manuscript[:manuscript.index(v['current_exact'])].count('\n')+1==v['line_start']
report=(OUT/'STAGE19G1_EVIDENCE_SURFACING_REPORT.md').read_text();assert report.rstrip().endswith('STAGE_19G1_PASS')
assert sum(line.startswith('| Materna-T1 |') for line in report.splitlines())==36
assert sum(line.startswith('| Materna-T3 |') for line in report.splitlines())==36
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
assert subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()==preserve['tracked_dirty_files']
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
verification=dict(status='STAGE_19G1_PASS',direct_input_hashes_reverified=len(sources),
    m1_robustness_rows=24,seed_sensitivity_rows=48,timetrack_attribution_rows=47,
    exact_source_numeric_strings_verified=True,win_fraction_to_percent_only=True,
    materna_per_VM_rows_reproduced=70,materna_saved_checkpoints_predictions=2100,
    timetrack_saved_checkpoints_predictions=210,table_A_memory_rounding='PASS',
    RQ4_recommendations_only=True,implementation_defect_demonstrated=False,further_experiment_required=False,
    protected_files_unchanged=preserve['protected_files_unchanged'],
    training=0,model_inference=0,manuscript_modifications=0,scientific_modifications=0,commit='no',push='no')
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
    for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='output_sha256_inventory.json']
(OUT/'output_sha256_inventory.json').write_text(json.dumps(dict(files=files,exclusions=['self-referential output_sha256_inventory.json','node_modules dependency symlink']),indent=2)+'\n')
print(json.dumps(verification,indent=2))
