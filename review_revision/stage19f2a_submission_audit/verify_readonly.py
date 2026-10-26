"""Read-only submission audit. Writes diagnostic evidence only in this directory."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4194304), b''):
            h.update(chunk)
    return h.hexdigest()

def read(rel):
    return json.loads((ROOT / rel).read_text())

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

base = read('review_revision/stage18c1_evidence/preservation_baseline.json')
manifest = ROOT / 'review_revision/stage18c1_evidence/preservation_before.jsonl'
assert sha(manifest) == base['inventory_sha256']
expected = {v['path']:v for v in map(json.loads, manifest.open())}
overlays = dict(read('review_revision/stage19c_evidence/verification.json')['source_hashes'])
overlays.update(read('review_revision/stage19e_evidence/verification.json')['after_sha256'])
overlays.update(read('review_revision/stage19f1_evidence/verification.json')['after_sha256'])
for rel, digest in overlays.items():
    assert sha(ROOT / rel) == digest, rel
    expected[rel] = dict(path=rel, bytes=(ROOT / rel).stat().st_size, sha256=digest)

source_path = ROOT / 'manuscript/jss/manuscript.tex'
tex = source_path.read_text()
main = re.sub(r'(?m)(?<!\\)%.*$', '', tex)
inputs = re.findall(r'\\input\{([^}]+)\}', main)
all_text = main + '\n' + '\n'.join((source_path.parent / (v+'.tex')).read_text() for v in inputs)
cites = {k.strip() for block in re.findall(r'\\cite\w*\{([^}]+)\}', all_text) for k in block.split(',')}
bib = (source_path.parent / 'references.bib').read_text()
entries = set(re.findall(r'(?m)^@\w+\{([^,]+),', bib))
assert cites == entries and len(entries) == 35
labels = re.findall(r'\\label\{([^}]+)\}', all_text)
refs = re.findall(r'\\(?:eqref|ref)\{([^}]+)\}', all_text)
assert not (set(refs)-set(labels))
assert len(labels) == len(set(labels))
abstract = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', main, re.S).group(1)
abstract_words = len(abstract.split())
assert abstract_words <= 250
keywords = re.search(r'\\begin\{keywords\}(.*?)\\end\{keywords\}', main, re.S).group(1).split('\\sep')
assert 1 <= len(keywords) <= 7
highlights_source = (source_path.parent / 'highlights.tex').read_text()
highlights = re.findall(r'\\item\s+(.*?)(?=\\item|\\end\{itemize\})', highlights_source, re.S)
highlights = [' '.join(h.replace('\\%', '%').split()) for h in highlights]
expanded = main
for item in inputs:
    expanded = expanded.replace('\\input{'+item+'}', (source_path.parent / (item+'.tex')).read_text())
float_order = {}
float_issues = {}
for kind, prefix in [('figure', 'fig:'), ('table', 'tab:')]:
    names = [v for v in re.findall(r'\\label\{([^}]+)\}', expanded) if v.startswith(prefix)]
    first_refs = sorted(set(v for v in refs if v.startswith(prefix)), key=lambda v: expanded.index('\\ref{'+v+'}'))
    float_order[kind] = names
    float_issues[kind] = {'uncited': sorted(set(names)-set(first_refs)),
        'first_reference_order': first_refs,
        'cited_items_in_display_order': [v for v in names if v in first_refs] == first_refs}
assert len(float_order['figure']) == 2 and len(float_order['table']) == 5
assert not re.search(r'\b(?:STAGE_\w+|Stage\s+\d+|R4_[A-Z_]+|TODO|FIXME)\b', main)
assert not re.search(r'\\(?:section|subsection)\*?\{[^}]*(?:biograph|generative|AI-assisted)', main, re.I)
supp = {}
for p in sorted((source_path.parent / 'supplementary').glob('*.tex')):
    text = p.read_text()
    supp[str(p.relative_to(ROOT))] = {'sha256': sha(p), 'standalone_document': '\\documentclass' in text,
        'internal_comments': [v for v in text.splitlines() if v.startswith('%') and re.search(r'Stage|future', v, re.I)]}

protected = ['multiresource/04_lstm_factorial', 'independent_validation/05_bitbrains_factorial',
    'independent_validation/06_materna_replication', 'manuscript/jss', 'benchmark/src',
    *['review_revision/experiments/' + name for name in (
        's2_common_context', 's2_common_context_predecessor_stage18b1r', 'm1_capacity_matched',
        'ar_arx_baseline', 'ar_arx_baseline_predecessor_stage18b3')],
    'review_revision/stage18a1_diagnostic_audit.md']
seen = set()
for rel in protected:
    p = ROOT / rel
    paths = [p] if p.is_file() else (Path(b)/n for b, ds, fs in os.walk(p) for n in fs)
    for p in paths:
        name = str(p.relative_to(ROOT)); seen.add(name)
        v = expected.get(name)
        assert v and p.stat().st_size == v['bytes'] and sha(p) == v['sha256'], name
        if len(seen) % 100000 == 0:
            print('PROTECTED_FILES_VERIFIED', len(seen), flush=True)
assert seen == set(expected) and len(seen) == 395786
inventory = read('review_revision/stage18c1_evidence/output_sha256_inventory.json')
for v in inventory['files']:
    assert sha(ROOT / v['path']) == v['sha256'], v['path']
refs_now = {key: git('rev-parse', value) for key, value in {
    'HEAD': 'HEAD', 'main':'refs/heads/main', 'paper_jss':'refs/heads/paper/jss',
    'scientific_tag_object':'refs/tags/phase4d-materna-final-scientific-freeze-v1',
    'scientific_tag_target':'phase4d-materna-final-scientific-freeze-v1^{}'}.items()}
assert refs_now == base['refs']
assert git('branch', '--show-current') == 'paper/jss-review-revision'
assert not git('diff', '--cached', '--name-only')
subprocess.check_call(['git', 'diff', '--check'], cwd=ROOT)
pdf = OUT / 'build/manuscript.pdf'
reader = PdfReader(pdf)
old_reader = PdfReader(source_path.parent / 'manuscript.pdf')
assert len(reader.pages) == 17
log = (OUT / 'build/manuscript.log').read_text()
assert not re.search(r'(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references', log)
aux = (OUT / 'build/manuscript.aux').read_text()
assert set(re.findall(r'\\bibcite\{([^}]+)\}', aux)) == entries
figures = {}
for name in ('framework_s1_s2_m1.pdf', 'results_signed_matrix.pdf'):
    p = source_path.parent / 'figures' / name
    r = PdfReader(p)
    fonts = []
    for pg in r.pages:
        resource = pg['/Resources'].get_object()
        for font in resource.get('/Font', {}).get_object().values():
            f = font.get_object()
            fdesc = f.get('/FontDescriptor')
            descendants = f.get('/DescendantFonts')
            if not fdesc and descendants:
                fdesc = descendants[0].get_object().get('/FontDescriptor')
            fd = fdesc.get_object() if fdesc else {}
            fonts.append({'name': str(f.get('/BaseFont')), 'embedded': any(v in fd for v in ('/FontFile','/FontFile2','/FontFile3'))})
    figures[name] = {'sha256':sha(p), 'pages':len(r.pages), 'fonts':fonts}
result = dict(status='READ_ONLY_VERIFICATION_PASS', checked_utc=datetime.now(timezone.utc).isoformat(),
    protected_files_unchanged=len(seen), stage18c1_output_hashes_verified=len(inventory['files']),
    refs=refs_now, branch=git('branch','--show-current'), manuscript_sha256=sha(source_path),
    bibliography_sha256=sha(source_path.parent/'references.bib'), abstract_words_whitespace=abstract_words,
    keywords=[v.strip() for v in keywords], bibliography_entries=len(entries), all_entries_cited=True,
    unresolved_citations_references=0, duplicate_labels=0, float_citation_order=float_order, float_issues=float_issues,
    highlights=[{'text':v,'characters_including_spaces':len(v),'within_85':len(v)<=85} for v in highlights],
    supplementary=supp, current_pdf_pages=len(reader.pages), current_pdf_sha256=sha(pdf),
    root_pdf_pages=len(old_reader.pages), root_pdf_sha256=sha(source_path.parent/'manuscript.pdf'),
    figures=figures, historical_tracked_dirty_files=git('diff','--name-only').splitlines(),
    manuscript_edits=0, scientific_modifications=0, training=0, inference=0,
    submission_assets_created=0, commit='no', push='no')
(OUT/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
