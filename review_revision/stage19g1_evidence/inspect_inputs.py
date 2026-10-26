"""Read-only schema inspection; no model imports or model execution."""
from pathlib import Path
import pandas as pd
import json
ROOT=Path(__file__).resolve().parents[2]
paths=['multiresource/04_lstm_factorial/outputs/scientific/run_registry.csv',
'multiresource/04_lstm_factorial/outputs/scientific/selected_contexts.csv',
'multiresource/04_lstm_factorial/outputs/scientific/comparisons/m1_vs_s2.csv',
'multiresource/04_lstm_factorial/outputs/scientific/comparisons/m1_vs_s2_cells.csv',
'independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T1/analysis/matched_vm_fold_cells.csv',
'review_revision/experiments/m1_capacity_matched/posthoc_results.csv']
for rel in paths:
    p=ROOT/rel
    if not p.exists():print('MISSING',rel);continue
    f=pd.read_csv(p)
    print(rel,len(f),list(f.columns));print(f.head(1).to_dict('records'))
for rel in ['multiresource/04_lstm_factorial/outputs/scientific/metrics.parquet']:
    p=ROOT/rel
    if not p.exists():continue
    f=pd.read_parquet(p);print(rel,len(f),list(f.columns));print(f.head(1).to_dict('records'))
    if 'metrics' in rel:
        r=pd.read_csv(ROOT/'multiresource/04_lstm_factorial/outputs/scientific/run_registry.csv').iloc[0]
        c=json.loads((ROOT/'multiresource/04_lstm_factorial/outputs/scientific/runtime/completions/final'/f'{r.run_id}.json').read_text())
        print('COMPLETION_KEYS',list(c));print('COMPLETION_METADATA',{k:v for k,v in c.items() if 'scal' in k or k in ['identity','record','spec','parameter_count','counts']})
        p=pd.read_parquet(ROOT/r.prediction_path);print('PREDICTION_SCHEMA',list(p),p.head(1).to_dict('records'))
        import torch
        ck=torch.load(ROOT/r.model_path,map_location='cpu',weights_only=True)
        print('CHECKPOINT_KEYS',list(ck));print('CHECKPOINT_METADATA',{k:v for k,v in ck.items() if k!='state_dict'})
for rel in ['multiresource/04_lstm_factorial/outputs/scientific/s2','multiresource/04_lstm_factorial/outputs/scientific/m1']:
    p=ROOT/rel
    print('MEMBERS',rel,[str(v.relative_to(ROOT)) for v in list(p.iterdir())[:5]])
