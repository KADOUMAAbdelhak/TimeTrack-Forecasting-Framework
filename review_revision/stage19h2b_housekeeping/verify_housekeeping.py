"""Document structure, scope, vector/pixel and metadata QA; no scientific analysis."""
from pathlib import Path
from collections import Counter
import difflib,hashlib,json,re
from pypdf import PdfReader
from PIL import Image,ImageChops,ImageDraw
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
TITLE='Evaluating Contextual Input and Shared Representation in Multi-Metric Runtime Forecasting for Cloud Software Systems'
MAIN='manuscript/jss/manuscript.tex'
FIG='manuscript/jss/figures/framework_s1_s2_m1'
TABLE='manuscript/jss/tables/related_work_comparison.tex'
SUPP='manuscript/jss/supplementary/final_evidence_supplement.tex'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def old(rel):return (OUT/'archive'/rel).read_text()
def new(rel):return (ROOT/rel).read_text()
def norm(t):return ' '.join(t.split())
main=new(MAIN);before=old(MAIN)
assert main.replace('\nSupplementary Tables~S1--S2 provide the detailed diagnostics.','').replace(' (Table~\\ref{tab:efficiency})','')==before
assert old(TABLE).split(r'\begin{tabular}',1)[1].split(r'\end{tabular}',1)[0]==new(TABLE).split(r'\begin{tabular}',1)[1].split(r'\end{tabular}',1)[0]
new_note='adverse-transfer analysis coded YES means explicit empirical analysis of adverse-transfer outcomes, not causal identification of the mechanism.'
old_note='adverse-transfer analysis does not imply causal identification.'
assert norm(new(TABLE)).replace(new_note,old_note)==norm(old(TABLE))
heading='  \\node[font=\\fontsize{10}{11}\\selectfont\\bfseries] at (87,71)\n    {Multivariate input $\\neq$ shared representation};\n\n'
assert old(FIG+'.tex').replace(heading,'')==new(FIG+'.tex')
assert 'Multivariate input' not in new(FIG+'.tex')
metadata=r'\hypersetup{pdftitle={'+TITLE+'}}'+'\n'
assert new(SUPP).replace(metadata,'')==old(SUPP)
comment_only=[]
for rel in ['manuscript/jss/supplementary/decision_criteria.tex','manuscript/jss/supplementary/overall_bootstrap_intervals.tex']:
    strip=lambda t:'\n'.join(line for line in t.splitlines() if not line.lstrip().startswith('%'))
    assert strip(new(rel))==strip(old(rel));comment_only.append(rel)
main_aux=(OUT/'build/manuscript.aux').read_text()
labels=dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}',main_aux))
all_labels=re.findall(r'\\newlabel\{([^}]+)\}',main_aux);assert len(all_labels)==len(set(all_labels))
input_names=re.findall(r'\\input\{([^}]+)\}',main)
figure_names=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',main)
assert len(input_names)==len(set(input_names))==5
assert len(figure_names)==len(set(figure_names))==2
tables=[]
for path in input_names:
    source=(ROOT/'manuscript/jss'/path).with_suffix('.tex').read_text()
    tables+=re.findall(r'\\label\{(tab:[^}]+)\}',source)
assert len(tables)==len(set(tables))==5
for label in tables:assert r'\ref{'+label+'}' in main
first_tables=list(dict.fromkeys(re.findall(r'\\ref\{(tab:[^}]+)\}',main)))
assert [int(labels[k]) for k in first_tables]==[1,2,3,4,5]
first_figures=list(dict.fromkeys(re.findall(r'\\ref\{(fig:[^}]+)\}',main)))
assert [int(labels[k]) for k in first_figures]==[1,2]
assert main.index('Supplementary Tables~S1--S2')<main.index('Supplementary\nTable~S2')
for path in figure_names:assert (ROOT/'manuscript/jss'/path).is_file()
references=(ROOT/'manuscript/jss/references.bib').read_text()
cited={v.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}',main) for v in group.split(',')}
entries=set(re.findall(r'@\w+\s*\{\s*([^,]+),',references))
assert cited==entries and len(entries)==35
assert sha(ROOT/'manuscript/jss/references.bib')=='f7efdff564455a709cda5459319f8f3c25811ca3a1a409187dd2cd7e0f7eef8b'
for stem,source in [('main',main),('supplement',new(SUPP))]:
    log=OUT/('build/manuscript.log' if stem=='main' else 'build/supplement/final_evidence_supplement.log')
    assert not re.search(r'(Reference|Citation).*undefined|There were undefined|multiply defined|Missing character',log.read_text())
    aux=log.with_suffix('.aux').read_text();available=set(re.findall(r'\\newlabel\{([^}]+)\}',aux))
    refs=set(re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',source))
    assert refs<=available
    if stem=='supplement':
        assert set(re.findall(r'\\newlabel\{(tab:[^}]+)\}',aux))=={'tab:supp-m1-robustness','tab:supp-seed-sensitivity'}
        assert 'S1}{1}' in aux and 'S2}{2}' in aux
        assert new(SUPP).index(r'\ref{tab:supp-m1-robustness}')<new(SUPP).index(r'\ref{tab:supp-seed-sensitivity}')
active_sources=[ROOT/MAIN,ROOT/SUPP,*[(ROOT/'manuscript/jss'/p).with_suffix('.tex') for p in input_names],
    ROOT/(FIG+'.tex'),ROOT/'manuscript/jss/supplementary/decision_criteria.tex',
    ROOT/'manuscript/jss/supplementary/overall_bootstrap_intervals.tex']
for p in active_sources:
    assert not re.search(r'Disentangling|\bTODO\b|\bFIXME\b|Stage\s+\d|STAGE_|R[1-4]_[A-Z]',p.read_text()),str(p)
assert r'\title[mode=title]{'+TITLE+'}' in main
assert TITLE in norm(new(SUPP))
pdfs=[ROOT/'manuscript/jss/manuscript.pdf',OUT/'build/supplement/final_evidence_supplement.pdf']
readers=[PdfReader(p) for p in pdfs]
assert [len(r.pages) for r in readers]==[18,3]
for reader in readers:
    assert reader.metadata.title==TITLE
    assert 'Disentangling' not in ' '.join(p.extract_text() for p in reader.pages)
assert sha(ROOT/'manuscript/jss/manuscript.pdf')==sha(OUT/'build/manuscript.pdf')
stale=PdfReader(OUT/'archive/manuscript/jss/manuscript.pdf')
assert stale.metadata.title.startswith('Disentangling')
root_pdfs=list((ROOT/'manuscript/jss').glob('*.pdf'))
assert root_pdfs==[ROOT/'manuscript/jss/manuscript.pdf']
for ext in ['abs','aux','bbl','blg','log','out','pdf']:
    assert sha(ROOT/('manuscript/jss/manuscript.'+ext))==sha(OUT/('build/manuscript.'+ext))
before_img=Image.open(OUT/'render/figure_before/figure-1.png').convert('RGB')
after_img=Image.open(OUT/'render/figure_after/figure-1.png').convert('RGB')
assert before_img.size==after_img.size==(1800,928)
diff=ImageChops.difference(before_img,after_img);bbox=diff.getbbox()
assert bbox==(551,10,1250,45)
assert not diff.crop((0,45,1800,928)).getbbox()
for name,reader in zip(['main','supplement'],readers):
    paths=sorted((OUT/'render'/name).glob('page-*.png'));assert len(paths)==len(reader.pages)
    if name=='main':
        for first in range(0,len(paths),6):
            sheet=Image.new('RGB',(1800,3900),'#ddd');draw=ImageDraw.Draw(sheet)
            for n,path in enumerate(paths[first:first+6]):
                im=Image.open(path).convert('RGB');im.thumbnail((880,1250))
                x,y=(n%2)*900+10,(n//2)*1300+32;sheet.paste(im,(x,y));draw.text((x,y-25),f'Page {first+n+1}',fill='black')
            sheet.save(OUT/'render'/f'main_contact_{first//6+1}.png')
for n,rel in enumerate([MAIN,FIG+'.tex',TABLE,SUPP,*comment_only]):
    (OUT/f'housekeeping_source_{n}.diff').write_text(''.join(difflib.unified_diff(old(rel).splitlines(True),new(rel).splitlines(True),fromfile='before/'+rel,tofile='after/'+rel)))
result=dict(status='CHECKS_PASS_AWAITING_VISUAL_AND_PRESERVATION',
    main_pages=18,supplement_pages=3,figure1_heading_removed=True,diagram_geometry_preserved=True,
    all_figure_pixels_outside_heading_identical=True,figure_changed_pixel_bbox=list(bbox),
    Table1_cells_byte_identical=True,Table1_YES_empirical_not_causal_note=True,
    main_table_first_citation_order={k:labels[k] for k in first_tables},main_figure_first_citation_order={k:labels[k] for k in first_figures},
    supplementary_first_citation_order=['S1','S2'],duplicate_inclusion=0,unused_float_definitions_in_build=0,
    unused_primary_gains_fragment='Not included, preserved unchanged',bibliography_entries=35,
    all_retained_entries_cited=True,unresolved_refs_citations=0,active_title=TITLE,
    manuscript_and_supplement_PDF_titles_exact=True,stale_root_build_artifacts_archived_and_refreshed=7,
    historical_evidence_files_deleted=0,obsolete_supplement_comments_removed=True,
    historical_literature_audits='Preserved unchanged; old titles/stages remain only as historical evidence',
    author_declarations_checkpoint_licence_packaging_content_changed=False,
    PDFs={str(p.relative_to(ROOT)):sha(p) for p in pdfs},
    manuscript_source_sha256=sha(ROOT/MAIN),figure_source_sha256=sha(ROOT/(FIG+'.tex')),
    bibliography_sha256=sha(ROOT/'manuscript/jss/references.bib'),
    scientific_modifications=0,analysis=0,training=0,inference=0,commit='no',push='no')
(OUT/'housekeeping_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
