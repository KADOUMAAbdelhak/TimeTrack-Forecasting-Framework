"""Record the completed manual visual review and bind the verified final outputs."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):
    return json.loads((OUT / name).read_text())
def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')

checks = read('integration_checks.json')
preservation = read('preservation_after.json')
assert preservation['status'] == 'PASS' and preservation['protected_files_unchanged'] == 395785
assert preservation['manuscript_sha256'] == checks['source_sha256']['manuscript/jss/manuscript.tex']
for rel, digest in checks['source_sha256'].items():
    assert sha(ROOT / rel) == digest
for name, key in [('build/manuscript.pdf', 'main_pdf_sha256'),
                  ('build/supplement/final_evidence_supplement.pdf', 'supplement_pdf_sha256')]:
    assert sha(OUT / name) == checks[key]
before = (OUT / 'manuscript_before.tex').read_text()
after = (ROOT / 'manuscript/jss/manuscript.tex').read_text()
(OUT / 'manuscript_g2.diff').write_text(''.join(difflib.unified_diff(
    before.splitlines(True), after.splitlines(True), fromfile='before/manuscript.tex',
    tofile='after/manuscript.tex')))
visual = dict(status='PASS', reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
    review='Manual inspection by the agent of rendered page layouts and focused full-page images',
    main_layout_pages=list(range(1, 19)), main_focused_pages=[1, 12, 13, 15, 16],
    supplement_full_pages=[1, 2, 3],
    inspected=['all main-page contact sheets', 'full-page attribution and RQ4',
               'full-page abstract, discussion and conclusion', 'all 24 robustness rows',
               'all 48 seed rows and panel/page boundaries'],
    result='Readable; no clipping, overlap, new overfull body lines or missing rows',
    main_pdf_sha256=checks['main_pdf_sha256'], supplement_pdf_sha256=checks['supplement_pdf_sha256'],
    image_sha256={str(p.relative_to(OUT)): sha(p) for p in sorted((OUT / 'render').rglob('*.png'))})
write('visual_signoff.json', visual)
checks.update(status='STAGE_19G2_PASS', visual_check='PASS, all 18+3 page layouts reviewed',
    protected_files_unchanged=preservation['protected_files_unchanged'],
    protected_membership=preservation['protected_membership'],
    prior_evidence_outputs_reverified=preservation['additional_output_inventories_verified'],
    refs=preservation['refs'], integration_blockers=[],
    existing_nonfatal_warnings=['CAS front matter/empty anchor, underfull lines, PDF version',
                              'Liu2024iTransformer and Nie2023PatchTST empty bibliography pages'])
write('verification.json', checks)
outputs = [p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'output_sha256_inventory.json']
write('output_sha256_inventory.json', dict(files=[dict(path=str(p.relative_to(ROOT)),
      bytes=p.stat().st_size, sha256=sha(p)) for p in outputs]))
inventory = read('output_sha256_inventory.json')
for record in inventory['files']:
    assert sha(ROOT / record['path']) == record['sha256']
print(json.dumps(dict(status=checks['status'], manuscript_pages=checks['main_pages'],
    supplement_pages=checks['supplement_pages'], abstract_words=checks['abstract_words'],
    output_hashes_verified=len(outputs), scientific_modifications=0, commit='no', push='no'), indent=2))
