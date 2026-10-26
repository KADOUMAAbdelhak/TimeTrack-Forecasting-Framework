"""Refresh stale root build artifacts only after preserving exact predecessors."""
from pathlib import Path
import hashlib,json,shutil
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
TITLE='Evaluating Contextual Input and Shared Representation in Multi-Metric Runtime Forecasting for Cloud Software Systems'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
reader=PdfReader(OUT/'build/manuscript.pdf')
assert reader.metadata.title==TITLE and len(reader.pages)==18
assert 'Disentangling' not in ' '.join(p.extract_text() for p in reader.pages)
records=[]
previous=json.loads((OUT/'root_refresh.json').read_text()) if (OUT/'root_refresh.json').exists() else None
for ext in ['abs','aux','bbl','blg','log','out','pdf']:
    rel='manuscript/jss/manuscript.'+ext
    archive=OUT/'archive'/rel;current=ROOT/rel;built=OUT/('build/manuscript.'+ext)
    assert archive.is_file() and built.is_file(),rel
    if sha(current)!=sha(archive):
        old=next(r for r in previous['files'] if r['path']==rel)
        assert sha(current)==old['refreshed_sha256'] and sha(archive)==old['predecessor_sha256'],rel
    shutil.copyfile(built,current)
    assert sha(current)==sha(built)
    records.append(dict(path=rel,predecessor_archive=str(archive.relative_to(ROOT)),
        predecessor_sha256=sha(archive),refreshed_sha256=sha(current)))
(OUT/'root_refresh.json').write_text(json.dumps(dict(status='PASS',files=records,
    historical_evidence_deleted=0,root_PDF_is_final=True),indent=2)+'\n')
print('ROOT_BUILD_ARTIFACTS_ARCHIVED_AND_REFRESHED',len(records))
