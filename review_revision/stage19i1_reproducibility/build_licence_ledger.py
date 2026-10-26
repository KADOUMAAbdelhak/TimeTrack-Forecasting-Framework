"""Record local notices and runtime metadata; no licence is granted or changed."""
from pathlib import Path
from importlib.metadata import distributions
import hashlib, json, re, zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
site=ROOT/'old_fgcs_rejected/.venv_legacy/lib/python3.13/site-packages'
wanted={'numpy','pandas','scipy','scikit-learn','torch','pyarrow','matplotlib','lightgbm','seaborn','statsmodels','pytest'}
dependencies=[]
for dist in distributions(path=[str(site)]):
    name=dist.metadata['Name']
    if name.lower() not in wanted:continue
    dependencies.append(dict(name=name,installed_version=dist.version,
        licence_expression=dist.metadata.get('License-Expression'),
        licence_header=(dist.metadata.get('License') or '').splitlines()[:2],
        licence_classifiers=[c for c in dist.metadata.get_all('Classifier',[]) if c.startswith('License ::')],
        scope='Local installed dependency; not a grant over project code, data or article'))
vendor=[]
for name,licence in [('cas-dc.cls','LPPL-1.2-or-later'),('cas-common.sty','LPPL-1.3c-or-later'),('cas-model2-names.bst','LPPL-1.3c-or-later')]:
    p=ROOT/'manuscript/jss'/name
    assert 'LaTeX Project Public' in p.read_text()[:1400]
    vendor.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),header_licence=licence,
        scope='Separate third-party CAS/Elsevier template; must retain upstream notices',
        upstream_modification_comparison='Not established; resolve distribution/modification obligations before release'))
archives=[]
for p in sorted((ROOT/'data/external/raw').glob('*.zip')):
    with zipfile.ZipFile(p) as z:
        notices=[name for name in z.namelist() if any(s in name.lower() for s in ['licence','license','copying','notice','readme'])]
        documents=[f for f in z.infolist() if not f.is_dir() and f.file_size<200000 and
                   Path(f.filename).suffix.lower() not in ['.csv','.log','.gz'] and '__MACOSX' not in f.filename]
        document_hits={f.filename:[line for line in z.read(f).decode('utf-8',errors='replace').splitlines()
                       if re.search(r'licen[sc]|copyright|redistribut|acknowledg|permission',line,re.I)] for f in documents}
    archives.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),licence_or_readme_members=notices,
                         auxiliary_document_licence_keyword_scan=document_hits))
toolpath=Path('/Users/fgtek002/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/package.json')
tool=json.loads(toolpath.read_text())
root_notices=[p.name for p in ROOT.iterdir() if p.is_file() and any(s in p.name.lower() for s in ['license','licence','copying','notice'])]
assert not root_notices
result=dict(status='AUDIT_COMPLETE_NOT_LEGAL_CLEARANCE',repository_wide_licence_present=False,
    root_licence_files=root_notices,
    existing_owner_decision_record='old_fgcs_rejected/docs/VERSION_CONTROL_POLICY.md:113',
    dataset_metadata='dataset_licence_metadata.json',external_archive_notice_scan=archives,
    third_party_template_files=vendor,local_dependency_metadata=sorted(dependencies,key=lambda r:r['name'].lower()),
    private_export_dependency=dict(name=tool['name'],version=tool['version'],private=tool.get('private'),
        licence=tool.get('license'),redistribution_permission_established=False,
        node_modules_symlink='review_revision/stage19g1_evidence/node_modules',
        action='Exclude dependency/symlink; retain CSV/payload; authorise portable exporter later'),
    recommended_author_owned_code_licence='Apache-2.0, conditional on all relevant rights-holder approval',
    blanket_repository_relicensing_recommended=False,
    original_upstream_terms_survive_for=['TimeTrack data','Bitbrains data','Materna data','CAS templates','Dependency packages'],
    manuscript_publication_rights='Separate author/publisher decision; no article reuse licence selected',
    user_actions=['Approve code licence and exact author-owned scope/copyright holders',
        'Approve any derived-data/model/prediction archive redistribution and hosting',
        'Resolve CAS licence/bundle manifest and any modified-template obligations',
        'Approve portable environment/replay/export documentation follow-up'],
    sources=[
        'https://www.apache.org/licenses/LICENSE-2.0.html',
        'https://opensource.org/license/mit',
        'https://opensource.org/license/bsd-3-clause',
        'https://www.latex-project.org/lppl/lppl-1-3c/',
        'https://creativecommons.org/licenses/by/4.0/',
        'https://atlarge-research.com/gwa-t-12/',
        'https://atlarge-research.com/gwa-t-13/',
        'https://zenodo.org/api/records/15442251',
        'https://www.kaggle.com/api/v1/datasets/list?search=open-air-interface-cicd-timeseries-dataset'],
    licence_files_created=0,manuscript_modifications=0,scientific_modifications=0)
(OUT/'licence_findings.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],repo_licence=False,vendor_files=len(vendor),
    dependency_records=len(dependencies),external_archive_notice_files=sum(len(r['licence_or_readme_members']) for r in archives),
    private_export_dependency_licence_found=False),indent=2))
