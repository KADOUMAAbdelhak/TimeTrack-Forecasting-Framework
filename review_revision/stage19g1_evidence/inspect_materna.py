from pathlib import Path
import pandas as pd,json
R=Path(__file__).resolve().parents[2]
base=R/'independent_validation/06_materna_replication'
f=pd.read_csv(base/'outputs/scientific_v1/Materna-T1/run_registry.csv',dtype={'vm_id':str})
r=f[f.vm_id.eq('266')&f.formulation.eq('M1')].iloc[0]
comp=base/'outputs/scientific_v1/Materna-T1/runtime/completions/final'/f'{r.run_id}.json'
c=json.loads(comp.read_text());print('KEYS',list(c));print('SCALER',c['scaler']);print('SPLIT',c['scaler_fit_split']);print('IDENTITY',c['identity'])
print('PRED',list(pd.read_parquet(base/r.prediction_path)))
print('LOG',c.get('epoch_logs',[])[:1])
