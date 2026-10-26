"""Literal-source integration and build checks only; no new scientific analysis."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import csv,difflib,hashlib,json,re
from pypdf import PdfReader
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
TARGETS=['manuscript/jss/manuscript.tex','manuscript/jss/supplementary/final_evidence_supplement.tex',
         'manuscript/jss/tables/posthoc_controls.tex']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=[(OUT/f'before_{n}.tex').read_text() for n in range(3)]
after=[(ROOT/r).read_text() for r in TARGETS]
def mask_main(text):
    for start,end in [(r'\begin{abstract}',r'\end{abstract}'),
                      (r'\section{Introduction}',r'\section{Related Work}'),
                      (r'\subsection{RQ1 Cross-Resource Context}',r'\subsection{RQ3 Full Joint-System Performance}')]:
        head,tail=text.split(start,1);middle,tail=tail.split(end,1);text=head+start+'ALLOWED'+end+tail
    return text
assert mask_main(before[0])==mask_main(after[0])
assert before[0].split(r'\begin{enumerate}')[1].split(r'\end{enumerate}')[0]==after[0].split(r'\begin{enumerate}')[1].split(r'\end{enumerate}')[0]
assert before[1].split(r'\section*{Existing-seed sensitivity}')[0]==after[1].split(r'\section*{Existing-seed sensitivity}')[0]
def source_rows(t):return [line for line in t.splitlines() if '&' in line and (r'\evidencevalue{' in line or r'$[' in line)]
assert source_rows(before[1])==source_rows(after[1]) and len(source_rows(after[1]))==72
assert source_rows(before[2])==source_rows(after[2]) and len(source_rows(after[2]))==12
assert before[1].split(r'\label{tab:supp-seed-sensitivity}')[1]==after[1].split(r'\label{tab:supp-seed-sensitivity}')[1]
table_note='  For TimeTrack memory, both H64 and H129 gains round to $-18.48\\%$; they are distinct before rounding.\n'
assert after[2].replace(table_note,'')==before[2]
for command in ['label','citep','citet','input','includegraphics']:
    pattern=r'\\'+command+r'(?:\[[^]]*\])?\{([^}]+)\}'
    assert re.findall(pattern,before[0])==re.findall(pattern,after[0])
abstract=after[0].split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
assert len(abstract.split())<=250 and 'small' not in abstract.lower()
assert 'close to one in many comparisons' in abstract
assert 'tail-concentrated' in abstract and 'per-entity' in abstract
assert 'Ridge indicates' in abstract
phrase='no sign flip across the three recorded seeds'
normal=[' '.join(t.split()) for t in after]
assert phrase in normal[0] and normal[1].count(phrase)==2
assert 'Sign stability does not imply magnitude stability' in normal[0] and 'Sign stability does not imply magnitude stability' in normal[1]
assert 'Unusually small training IQRs are therefore not supported as an' in after[0]
assert 'large scale caused the errors or that sharing is causal' in normal[0]
g1=ROOT/'review_revision/stage19g1_evidence'
with (g1/'seed_sensitivity_48.csv').open(newline='') as s:seeds=list(csv.DictReader(s))
example=next(r for r in seeds if r['block']=='Materna-T3' and r['resource']=='DISK_WRITE' and r['comparison']=='M1_vs_S2')
assert [format(Decimal(example[f'seed{k}_gain_percent']),'.2f') for k in range(3)]==['-54.65','-71.55','-87.84']
for text in after[:2]:
    for gain in ['-54.65','-71.55','-87.84']:assert gain+r'\%' in text
memory=[]
for block in ['fastStorage','Rnd','Materna-T2','Materna-T3']:
    row=next(r for r in seeds if r['block']==block and r['resource']=='MEMORY' and r['comparison']=='S2_vs_S1')
    assert all(Decimal(row[f'seed{k}_gain_percent'])>0 for k in range(3));memory.append(row)
with (ROOT/'review_revision/experiments/m1_capacity_matched/posthoc_results.csv').open(newline='') as s:
    capacity=next(r for r in csv.DictReader(s) if r['block']=='TimeTrack' and r['resource']=='MEMORY')
assert capacity['original_H64_vs_S2_gain_percent']=='-18.476885757816117'
assert capacity['H129_vs_S2_gain_percent']=='-18.484754219705916'
assert '[-18.48/-17.79/-18.48]' in after[2]
h1=ROOT/'review_revision/stage19h1_scale_context'
scale=json.loads((h1/'analysis.json').read_text())
for trace,expected in [('Materna-T1',['7.86','8.19']),('Materna-T3',['7.59','7.75'])]:
    summary=scale['summaries'][trace]
    assert [format(v,'.2f') for v in summary['M1_selected_log_iqr_relative_median_range']]==expected
    actual=[r for r in scale['selected_context_cohort_comparisons'] if r['trace']==trace and r['formulation']=='M1']
    assert all(r['metrics']['native_iqr']['ascending_rank_min']==35 for r in actual)
    assert set(summary['M1_selected_log_iqr_ranks'])==({33,34} if trace=='Materna-T1' else {35})
for phrase in ['33--34/35','7.86--8.19','35/35','7.59--7.75']:
    assert phrase in after[0]
for n,rel in enumerate(TARGETS):
    (OUT/f'source_change_{n}.diff').write_text(''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='before/'+rel,tofile='after/'+rel)))
pdfs=[OUT/'build/manuscript.pdf',OUT/'build/supplement/final_evidence_supplement.pdf']
readers=[PdfReader(p) for p in pdfs]
assert len(readers[0].pages)<=18 and len(readers[1].pages)==3
for stem,reader in zip(['main','supplement'],readers):
    path=OUT/'build'/('manuscript.log' if stem=='main' else 'supplement/final_evidence_supplement.log')
    log=path.read_text()
    assert not re.search(r'(Reference|Citation).*undefined|There were undefined|multiply defined|Missing character',log)
    aux=path.with_suffix('.aux').read_text()
    labels=re.findall(r'\\newlabel\{([^}]+)\}',aux);assert len(labels)==len(set(labels))
    text=after[0] if stem=='main' else after[1]
    refs=re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',text)
    assert not(set(refs)-set(labels))
    images=sorted((OUT/'render'/stem).glob('page-*.png'))
    assert len(images)==len(reader.pages)
    if stem=='main':
        for first in range(0,len(images),6):
            sheet=Image.new('RGB',(1800,3900),'#ddd');draw=ImageDraw.Draw(sheet)
            for n,p in enumerate(images[first:first+6]):
                im=Image.open(p).convert('RGB');im.thumbnail((880,1250))
                x,y=(n%2)*900+10,(n//2)*1300+32;sheet.paste(im,(x,y));draw.text((x,y-25),f'Page {first+n+1}',fill='black')
            sheet.save(OUT/'render'/f'main_contact_{first//6+1}.png')
supp_aux=(OUT/'build/supplement/final_evidence_supplement.aux').read_text()
assert r'\newlabel{tab:supp-m1-robustness}{{S1}{1}' in supp_aux
assert r'\newlabel{tab:supp-seed-sensitivity}{{S2}{2}' in supp_aux
result=dict(status='CHECKS_PASS_AWAITING_VISUAL_AND_PRESERVATION',abstract_words=len(abstract.split()),
    main_pages=len(readers[0].pages),supplement_pages=len(readers[1].pages),main_scope_exact=True,
    supplement_24_48_rows_and_all_312_numeric_strings_unchanged=True,Table3_numeric_rows_unchanged=True,
    H64_H129_gains=[capacity['original_H64_vs_S2_gain_percent'],capacity['H129_vs_S2_gain_percent']],
    scale_ranks_ratios_match_H1=True,all_four_named_memory_gains_positive_each_seed=True,
    seed_disk_example_matches_existing_values=True,stable_explicitly_sign_only=True,
    unchanged_methods_figures_bibliography_declarations=True,unresolved_refs_citations=0,
    source_sha256={r:sha(ROOT/r) for r in TARGETS},pdf_sha256={str(p.relative_to(ROOT)):sha(p) for p in pdfs},
    new_analysis=0,training=0,inference=0,scientific_modifications=0,commit='no',push='no')
(OUT/'integration_checks.json').write_text(json.dumps(result,indent=2)+'\n')
inputs=[h1/'STAGE19H1_DOMINANT_VM_SCALE_CONTEXT_REPORT.md',h1/'analysis.json',h1/'verification.json',
    g1/'STAGE19G1_EVIDENCE_SURFACING_REPORT.md',g1/'seed_sensitivity_48.csv',g1/'m1_s2_robustness_24.csv',
    ROOT/'review_revision/stage18c1_final_robustness_synthesis.md',
    ROOT/'review_revision/experiments/m1_capacity_matched/posthoc_results.csv']
(OUT/'input_sha256_inventory.json').write_text(json.dumps(dict(files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in inputs]),indent=2)+'\n')
print(json.dumps(result,indent=2))
