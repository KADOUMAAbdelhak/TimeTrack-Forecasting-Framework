"""Bind completed source, visual and preservation checks; no manuscript edits."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as s:
        for b in iter(lambda:s.read(4194304),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads((OUT/p).read_text())
def write(p,v):(OUT/p).write_text(json.dumps(v,indent=2)+'\n')
checks=read('integration_checks.json');preservation=read('preservation_after.json')
assert preservation['status']=='PASS' and preservation['protected_files_unchanged']==395784
assert preservation['source_sha256']==checks['source_sha256']
for rel,h in (checks['source_sha256']|checks['pdf_sha256']).items():assert sha(ROOT/rel)==h,rel
for v in read('input_sha256_inventory.json')['files']:assert sha(ROOT/v['path'])==v['sha256']
visual=dict(status='PASS',reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
    review='Manual rendered-page inspection by agent',main_layout_pages=list(range(1,19)),
    main_full_page_checks=[1,2,11,12,13],supplement_full_page_checks=[2,3],
    supplement_page_1='Source byte-identical through complete Table S1; existing visual check reused',
    result='Readable; no clipping, overlap, table overflow or new overfull body text',
    pdf_sha256=checks['pdf_sha256'],
    rendered_image_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted((OUT/'render').rglob('*.png'))})
write('visual_signoff.json',visual)
checks.update(status='STAGE_19H2A_PASS',visual_check='PASS',
    protected_membership=preservation['protected_membership'],protected_files_unchanged=preservation['protected_files_unchanged'],
    prior_output_hashes_verified=preservation['prior_output_hashes_verified'],refs=preservation['refs'],
    integration_blockers=[],existing_nonfatal_warnings=['CAS front matter/empty anchor, underfull lines, PDF version',
    'Liu2024iTransformer and Nie2023PatchTST empty bibliography pages'])
write('verification.json',checks)
paths=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='output_sha256_inventory.json']
write('output_sha256_inventory.json',dict(files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]))
for v in read('output_sha256_inventory.json')['files']:assert sha(ROOT/v['path'])==v['sha256']
print(json.dumps(dict(status=checks['status'],abstract_words=checks['abstract_words'],main_pages=checks['main_pages'],
    supplement_pages=checks['supplement_pages'],output_hashes_verified=len(paths),scientific_modifications=0,commit='no',push='no'),indent=2))
