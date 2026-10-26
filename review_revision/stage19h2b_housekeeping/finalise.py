"""Bind completed housekeeping, rendered-page and preservation checks; no science."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as source:
        for block in iter(lambda: source.read(4194304), b''):
            h.update(block)
    return h.hexdigest()

def read(name):
    return json.loads((OUT / name).read_text())

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')

checks = read('housekeeping_checks.json')
before = read('preservation_before.json')
after = read('preservation_after.json')
assert before['status'] == after['status'] == 'PASS'
assert before['protected_files_unchanged'] == after['protected_membership'] == 395787
assert after['protected_files_unchanged'] == 395773
assert len(after['allowed_manuscript_housekeeping']) == len(after['archived_predecessors']) == 14
for rel, digest in after['source_sha256'].items():
    assert sha(ROOT / rel) == digest, rel
for row in after['archived_predecessors']:
    assert sha(ROOT / row['archive_path']) == row['sha256'], row['original_path']
assert after['refs'] == before['refs']
assert checks['status'] == 'CHECKS_PASS_AWAITING_VISUAL_AND_PRESERVATION'
assert checks['main_pages'] == 18 and checks['supplement_pages'] == 3
assert checks['scientific_modifications'] == checks['unresolved_refs_citations'] == 0
assert checks['manuscript_source_sha256'] == after['source_sha256']['manuscript/jss/manuscript.tex']
assert checks['figure_source_sha256'] == after['source_sha256']['manuscript/jss/figures/framework_s1_s2_m1.tex']
assert read('figure_vector_check.json')['after_sha256'] == after['source_sha256']['manuscript/jss/figures/framework_s1_s2_m1.pdf']
for rel, digest in checks['PDFs'].items():
    assert sha(ROOT / rel) == digest, rel
for row in read('root_refresh.json')['files']:
    assert sha(ROOT / row['path']) == row['refreshed_sha256']
    assert sha(ROOT / row['predecessor_archive']) == row['predecessor_sha256']
assert sha(ROOT / 'manuscript/jss/references.bib') == checks['bibliography_sha256']

supplement_comparison = []
for page in range(1, 4):
    previous = ROOT / f'review_revision/stage19h2a_evidence/render/supplement/page-{page}.png'
    current = OUT / f'render/supplement/page-{page}.png'
    a, b = Image.open(previous).convert('RGB'), Image.open(current).convert('RGB')
    assert a.size == b.size
    assert ImageChops.difference(a, b).getbbox() is None
    supplement_comparison.append(dict(page=page, pixels_identical=True, previous_sha256=sha(previous), current_sha256=sha(current)))

visual = dict(status='PASS', reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
    review='Manual rendered-page inspection by agent', main_layout_pages=list(range(1, 19)),
    main_full_page_checks=[4, 5, 10, 14], figure1_heading_only_pixel_change=True,
    supplement_visible_pages_identical_to_prior_verified_build=supplement_comparison,
    result='Readable; no clipping, overlap or new overfull body text', pdf_sha256=checks['PDFs'],
    rendered_image_sha256={str(p.relative_to(OUT)): sha(p) for p in sorted((OUT / 'render').rglob('*.png'))})
write('visual_signoff.json', visual)

input_paths = [
    'review_revision/stage18c1_evidence/preservation_baseline.json',
    'review_revision/stage18c1_evidence/preservation_before.jsonl',
    'review_revision/stage19c_evidence/verification.json',
    'review_revision/stage19e_evidence/verification.json',
    'review_revision/stage19f1_evidence/verification.json',
    *[f'review_revision/{stage}/output_sha256_inventory.json' for stage in
      ['stage18c1_evidence', 'stage19g1_evidence', 'stage19g2_evidence', 'stage19h1_scale_context', 'stage19h2a_evidence']],
    'manuscript/jss/references.bib',
    *[row['archive_path'] for row in after['archived_predecessors']],
]
write('input_sha256_inventory.json', dict(files=[dict(path=rel, sha256=sha(ROOT / rel)) for rel in input_paths]))
checks.update(status='STAGE_19H2B_PASS', visual_check='PASS',
    protected_membership=after['protected_membership'], protected_files_unchanged=after['protected_files_unchanged'],
    source_sha256=after['source_sha256'], prior_output_hashes_verified=after['prior_output_hashes_verified'],
    refs=after['refs'], housekeeping_blockers=[],
    historical_residue_retained=['Historical literature audit titles/stage labels', 'Bibliography provenance comments'],
    existing_nonfatal_warnings=['CAS front-matter overfull box and empty anchors', 'Underfull lines',
        'Liu2024iTransformer and Nie2023PatchTST empty bibliography pages'])
write('verification.json', checks)
report = OUT / 'STAGE19H2B_FINAL_HOUSEKEEPING_REPORT.md'
assert 'STAGE_19H2B_PASS' in report.read_text()
paths = [p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'output_sha256_inventory.json']
write('output_sha256_inventory.json', dict(files=[dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=sha(p)) for p in paths]))
for row in read('output_sha256_inventory.json')['files']:
    assert sha(ROOT / row['path']) == row['sha256'], row['path']
print(json.dumps(dict(status=checks['status'], main_pages=18, supplement_pages=3,
    output_hashes_verified=len(paths), protected_files_unchanged=395773,
    scientific_modifications=0, training=0, inference=0, analysis=0, commit='no', push='no'), indent=2))
