"""Authoring-time snapshot of the already audited compact replay inputs."""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PATHS=[
 'review_revision/stage19g1_evidence/table_payload.json',
 'review_revision/stage19g1_evidence/m1_s2_robustness_24.csv',
 'review_revision/stage19g1_evidence/seed_sensitivity_48.csv',
 'review_revision/stage19g1_evidence/timetrack_memory_attribution.csv',
 'review_revision/stage18c1_evidence/robust_seed_mean_cells.csv',
 'review_revision/stage18c1_evidence/seed_sensitivity.csv',
 'review_revision/stage18c1_evidence/sharing_sensitivity.csv',
 'review_revision/stage18c1_evidence/contextual_evidence.csv',
 'review_revision/stage19g1_evidence/analysis.json',
 'review_revision/stage19h1_scale_context/analysis.json',
 'manuscript/jss/supplementary/final_evidence_supplement.tex']
def sha(b):return hashlib.sha256(b).hexdigest()
files=[dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=sha((ROOT/p).read_bytes())) for p in PATHS]
tex=(ROOT/PATHS[-1]).read_text()
fragments=[section.split(r'\endlastfoot'+'\n',1)[1].split(r'\end{longtable}',1)[0]
           for section in tex.split(r'\begin{longtable}')[1:]]
if len(fragments)!=2:raise RuntimeError('Expected exactly two authoritative supplement tables')
obj=dict(schema=1,scope='Compact derived-only replay; no raw data, checkpoints or inference',
    files=files,expected_csv_rows={'m1_s2_robustness_24.csv':24,'seed_sensitivity_48.csv':48,'timetrack_memory_attribution.csv':47},
    authoritative_supplement_fragment_sha256={name:sha(fragment.encode('utf-8')) for name,fragment in
        zip(['m1_s2_robustness_rows.tex','seed_sensitivity_rows.tex'],fragments)},
    note='Authoring snapshot, not a new scientific seal. Preserve original experiment seals separately.')
target=OUT/'replay_sources.json'
if target.exists():raise RuntimeError('Do not refresh hashes silently; review and version any future update')
target.write_text(json.dumps(obj,indent=2)+'\n')
print('MANIFEST_SHA256',sha(target.read_bytes()))
