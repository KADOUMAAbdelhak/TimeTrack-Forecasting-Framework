"""Check integration by literal source equality and document QA, not new analysis."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import csv
import hashlib
import json
import re
from pypdf import PdfReader
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
G1 = ROOT / 'review_revision/stage19g1_evidence'
MAIN = ROOT / 'manuscript/jss/manuscript.tex'
SUPP = ROOT / 'manuscript/jss/supplementary/final_evidence_supplement.tex'
before = (OUT / 'manuscript_before.tex').read_text()
after = MAIN.read_text()
supp = SUPP.read_text()
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(name):
    with (G1 / name).open(newline='') as stream:
        return list(csv.DictReader(stream))
def span(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]

robust = rows('m1_s2_robustness_24.csv')
seeds = rows('seed_sensitivity_48.csv')
assert len(robust) == len({(r['block'], r['resource']) for r in robust}) == 24
assert len(seeds) == len({(r['comparison'], r['block'], r['resource']) for r in seeds}) == 48
names = dict(CPU='CPU', THROUGHPUT='Throughput', MEMORY='Memory', DISK_WRITE='Disk write')
numeric_fields = [['frozen_MacroMAE_gain_percent', 'median_candidate_reference_MAE_ratio', 'candidate_win_percent'],
                  ['seed0_gain_percent', 'seed1_gain_percent', 'seed2_gain_percent',
                   'range_percentage_points', 'population_SD_percentage_points']]
ordered_seeds = [r for c in ['S2_vs_S1', 'M1_vs_S2'] for r in seeds if r['comparison'] == c]
table_lines = [line for line in supp.splitlines() if r'\evidencevalue{' in line and ' & ' in line]
assert len(table_lines) == 72
raw_values_checked = 0
for line, row, fields in zip(table_lines, robust + ordered_seeds,
                              [numeric_fields[0]] * 24 + [numeric_fields[1]] * 48):
    assert line.startswith(row['block'] + ' / ' + names[row['resource']] + ' & ')
    values = re.findall(r'\\evidencevalue\{([^}]+)\}\{([^}]+)\}', line)
    assert [v[0] for v in values] == [row[key] for key in fields], line
    assert [v[1] for v in values] == [format(Decimal(row[key]), '.6f') for key in fields]
    assert line.endswith(' & ' + row.get('ties', row.get('status')) + r' \\')
    raw_values_checked += len(values)
counts = {c: dict(Counter(r['status'] for r in seeds if r['comparison'] == c))
          for c in ['S2_vs_S1', 'M1_vs_S2']}
assert counts == {'S2_vs_S1': {'stable': 15, 'FLIP': 9}, 'M1_vs_S2': {'stable': 20, 'FLIP': 4}}

abstract = span(after, r'\begin{abstract}', r'\end{abstract}')
assert len(abstract.split()) <= 250
assert 'Ridge indicates' in abstract and 'Ridge confirms' not in abstract
assert 'per-entity model consolidation' in abstract
assert '838' not in abstract and '99.93' not in abstract
assert 'Temporal heterogeneity confirmed' not in after
assert 'The prespecified RQ4 criterion for temporal heterogeneity was met.' in after
assert 'descriptive criterion, not an IID or' in after
assert before.split(r'\begin{abstract}')[0] == after.split(r'\begin{abstract}')[0]
assert span(before, r'\end{abstract}', r'\section{Results}') == span(after, r'\end{abstract}', r'\section{Results}')
assert before.split(r'\section*{Data availability}')[1] == after.split(r'\section*{Data availability}')[1]
assert span(before, r'\section{Cross-Dataset Synthesis}', r'\section{Discussion}') == span(after, r'\section{Cross-Dataset Synthesis}', r'\section{Discussion}')
for command in ['label', 'input', 'includegraphics']:
    assert re.findall(r'\\' + command + r'(?:\[[^]]*\])?\{([^}]+)\}', before) == re.findall(r'\\' + command + r'(?:\[[^]]*\])?\{([^}]+)\}', after)
old_cites = re.findall(r'\\cite\w*\{([^}]+)\}', before)
assert old_cites == re.findall(r'\\cite\w*\{([^}]+)\}', after)
assert re.findall(r'\\begin\{equation\}.*?\\end\{equation\}', before, re.S) == re.findall(r'\\begin\{equation\}.*?\\end\{equation\}', after, re.S)
old_numbers = Counter(re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?', before))
new_numbers = Counter(re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?', after))
assert not (old_numbers - new_numbers), old_numbers - new_numbers

g1 = json.loads((G1 / 'analysis.json').read_text())
for block, vm, largest, top3, worse in [('Materna-T1', '266', '82.10', '91.72', 28),
                                       ('Materna-T3', '272', '86.97', '92.93', 32)]:
    record = g1['materna'][block]
    assert record['worse'] == worse and record['units'] == 35
    assert record['largest']['units'][0]['vm_id'] == vm
    assert format(record['largest']['share_positive_percent'], '.2f') == largest
    assert format(record['top3']['share_positive_percent'], '.2f') == top3
    assert largest + r'\%' in after and top3 + r'\%' in after
report = (G1 / 'STAGE19G1_EVIDENCE_SURFACING_REPORT.md').read_text()
mf = g1['timetrack_memory']['machine_fold']
assert mf['worse'] == 31 and mf['units'] == 35
assert g1['timetrack_memory']['machine']['worse'] == g1['timetrack_memory']['machine']['units'] == 7
assert format(mf['median_ratio'], '.6f') == '1.195276'
assert format(mf['largest']['share_positive_percent'], '.2f') == '21.80'
assert format(mf['top3']['share_positive_percent'], '.2f') == '51.06'
for token in ['31/35', '1.195276', '21.80', '51.06']:
    assert token in after
assert g1['frozen_RQ4_check'] == dict(resource_comparison_pairs=12, classification_variable=7,
                                    raw_sign_reversal=5, frozen_rule_unchanged=True)
assert len(rows('timetrack_memory_attribution.csv')) == 47

capacity_path = ROOT / 'review_revision/experiments/m1_capacity_matched/posthoc_results.csv'
with capacity_path.open(newline='') as stream:
    cap = next(r for r in csv.DictReader(stream) if r['block'] == 'TimeTrack' and r['resource'] == 'MEMORY')
assert '-18.476885757816117' in cap.values() and '-18.484754219705916' in cap.values()
assert format(Decimal('-18.476885757816117'), '.2f') == format(Decimal('-18.484754219705916'), '.2f') == '-18.48'
table_a = ROOT / 'manuscript/jss/tables/posthoc_controls.tex'
assert '[-18.48/-17.79/-18.48]' in table_a.read_text()

main_pdf = OUT / 'build/manuscript.pdf'
supp_pdf = OUT / 'build/supplement/final_evidence_supplement.pdf'
main_reader, supp_reader = PdfReader(main_pdf), PdfReader(supp_pdf)
assert len(main_reader.pages) <= 18 and len(supp_reader.pages) == 3
main_text = '\n'.join(p.extract_text() for p in main_reader.pages)
supp_text = '\n'.join(p.extract_text() for p in supp_reader.pages)
assert 'Supplementary Table S1' in main_text.replace('\n', ' ')
assert 'Supplementary Table S2' in main_text.replace('\n', ' ')
assert 'Panel A: S2:S1' in supp_reader.pages[1].extract_text()
assert 'Panel B: M1:S2' in supp_reader.pages[2].extract_text()
supp_aux = (OUT / 'build/supplement/final_evidence_supplement.aux').read_text()
assert r'\newlabel{tab:supp-m1-robustness}{{S1}{1}' in supp_aux
assert r'\newlabel{tab:supp-seed-sensitivity}{{S2}{2}' in supp_aux
for log_path in [OUT / 'build/manuscript.log', OUT / 'build/supplement/final_evidence_supplement.log']:
    log = log_path.read_text()
    assert not re.search(r'(?:Reference|Citation).*undefined|There were undefined|multiply defined|Missing character', log)
assert 'Overfull' not in (OUT / 'build/supplement/final_evidence_supplement.log').read_text()
main_aux = (OUT / 'build/manuscript.aux').read_text()
labels = re.findall(r'\\newlabel\{([^}]+)\}', main_aux)
assert len(labels) == len(set(labels))
refs = re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}', after)
assert not (set(refs) - set(labels))
bib = (ROOT / 'manuscript/jss/references.bib').read_text()
entries = set(re.findall(r'@\w+\s*\{\s*([^,]+),', bib))
cited = {key.strip() for group in old_cites for key in group.split(',')}
assert entries == cited

for name in ['main', 'supplement']:
    images = sorted((OUT / 'render' / name).glob('page-*.png'))
    assert len(images) == (len(main_reader.pages) if name == 'main' else len(supp_reader.pages))
    if name == 'main':
        for first in range(0, len(images), 6):
            sheet = Image.new('RGB', (1800, 3900), '#d8d8d8')
            draw = ImageDraw.Draw(sheet)
            for n, path in enumerate(images[first:first+6]):
                im = Image.open(path).convert('RGB')
                im.thumbnail((880, 1250))
                x, y = (n % 2) * 900 + 10, (n // 2) * 1300 + 32
                sheet.paste(im, (x, y))
                draw.text((x, y-25), 'Page ' + str(first+n+1), fill='black')
            sheet.save(OUT / 'render' / ('main_contact_' + str(first//6+1) + '.png'))

result = dict(status='CHECKS_PASS_AWAITING_VISUAL_SIGNOFF_AND_PRESERVATION',
    changed_manuscript_sources=['manuscript/jss/manuscript.tex', 'manuscript/jss/supplementary/final_evidence_supplement.tex'],
    robustness_rows=24, seed_rows=48, exact_source_decimal_strings=raw_values_checked,
    display_precision='six decimal places only; full CSV strings retained in LaTeX macro arguments',
    seed_status_counts=counts, main_pages=len(main_reader.pages), supplement_pages=len(supp_reader.pages),
    abstract_words=len(abstract.split()), preserved_main_numeric_literals=True,
    all_old_equations_labels_citations_inputs_preserved=True, all_35_bibliography_entries_cited=True,
    methods_protocol_introduction_related_work_synthesis_declarations_unchanged=True,
    table_A_memory_exact_gains=['-18.476885757816117', '-18.484754219705916'],
    table_A_memory_two_decimal_rounding='-18.48 for both; table unchanged',
    unresolved_refs_citations=0, supplementary_table_identifiers_verified={'S1': '24 rows, page 1', 'S2': '48 rows, pages 2-3'},
    build='Tectonic cached-only exit 0 for both documents',
    main_pdf_sha256=sha(main_pdf), supplement_pdf_sha256=sha(supp_pdf),
    source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [MAIN, SUPP]},
    training=0, inference=0, new_statistics=0, scientific_modifications=0, commit='no', push='no')
(OUT / 'integration_checks.json').write_text(json.dumps(result, indent=2) + '\n')
inputs = [G1 / name for name in ['STAGE19G1_EVIDENCE_SURFACING_REPORT.md', 'analysis.json', 'verification.json',
    'm1_s2_robustness_24.csv', 'seed_sensitivity_48.csv', 'timetrack_memory_attribution.csv',
    'output_sha256_inventory.json', 'preservation.json']]
inputs += [ROOT / 'review_revision/stage18c1_final_robustness_synthesis.md', capacity_path, table_a,
    ROOT / 'manuscript/jss/references.bib', OUT / 'manuscript_before.tex']
(OUT / 'input_sha256_inventory.json').write_text(json.dumps({'files': [dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in inputs]}, indent=2) + '\n')
print(json.dumps(result, indent=2))
