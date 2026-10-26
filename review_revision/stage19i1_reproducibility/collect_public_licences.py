"""Capture public dataset metadata and match local bytes; no data download."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent

def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'TimeTrack-reproducibility-licence-audit/1.0'})
    with urllib.request.urlopen(request,timeout=30) as response:
        return json.load(response)

zenodo_url='https://zenodo.org/api/records/15442251'
kaggle_url='https://www.kaggle.com/api/v1/datasets/list?search=open-air-interface-cicd-timeseries-dataset'
z=get(zenodo_url)
k=get(kaggle_url)
meta=z['metadata']
record=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
    Zenodo=dict(url=zenodo_url,title=meta['title'],doi=meta['doi'],license=meta['license'],
        access_right=meta['access_right'],files=[{key:f[key] for key in ['key','size','checksum']} for f in z['files']]),
    Kaggle=dict(url=kaggle_url,records=[{key:r.get(key) for key in ['ref','title','licenseName','lastUpdated']} for r in k]))
assert meta['license']['id']=='cc-by-4.0'
assert len(k)==1 and k[0]['ref']=='abdelghanimeliani/open-air-interface-cicd-timeseries-dataset'
checks=[]
for f in z['files']:
    p=ROOT/'data/raw'/f['key']
    h=hashlib.md5()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(4194304),b''):
            h.update(block)
    assert p.stat().st_size==f['size']
    assert 'md5:'+h.hexdigest()==f['checksum']
    checks.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,Zenodo_checksum=f['checksum'],exact_match=True))
record['local_raw_matches_Zenodo']=checks
(OUT/'dataset_licence_metadata.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
