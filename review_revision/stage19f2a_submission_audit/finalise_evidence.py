"""Hash only audit outputs; do not touch manuscript, science or submission files."""
from pathlib import Path
import hashlib
import json
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as s:
        for b in iter(lambda:s.read(4194304), b''):
            h.update(b)
    return h.hexdigest()

v = json.loads((OUT/'verification.json').read_text())
signoff = json.loads((OUT/'visual_signoff.json').read_text())
assert sha(ROOT/'manuscript/jss/manuscript.tex') == v['manuscript_sha256'] == signoff['source_sha256']
assert sha(ROOT/'manuscript/jss/references.bib') == v['bibliography_sha256']
assert sha(OUT/'build/manuscript.pdf') == v['current_pdf_sha256'] == signoff['pdf_sha256']
assert signoff['pages_inspected'] == list(range(1,18))
assert v['protected_files_unchanged'] == 395786
assert v['float_issues']['table']['uncited'] == ['tab:efficiency']
assert all(h['within_85'] for h in v['highlights'])
assert subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines() == v['historical_tracked_dirty_files']
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
subprocess.check_call(['git','diff','--check'],cwd=ROOT)
report = (OUT/'STAGE19F2A_JSS_SUBMISSION_AUDIT.md').read_text()
assert report.rstrip().endswith('STAGE_19F2A_BLOCKED_METADATA_DECLARATIONS_AND_PACKAGE_READINESS')
assert '228 words' in report and '395,786' in report
inventory = [dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=sha(p))
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'output_sha256_inventory.json']
(OUT/'output_sha256_inventory.json').write_text(json.dumps(dict(files=inventory,
    exclusions=['self-referential output_sha256_inventory.json'],
    audit_complete=True, submission_readiness='BLOCKED', manuscript_modifications=0,
    scientific_modifications=0, submission_assets_created=0),indent=2)+'\n')
print(json.dumps(dict(audit_files_hashed=len(inventory),read_only_verification='PASS',
    submission_readiness='BLOCKED',source_unchanged=True,bibliography_unchanged=True,
    pages=17,commit='no',push='no'),indent=2))
