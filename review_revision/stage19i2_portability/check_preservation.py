"""Verify the I1 before-tree plus its completed audit; writes only I2 evidence."""
from pathlib import Path
import hashlib, json, os, stat, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'review_revision/stage19i1_reproducibility'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4194304),b''):h.update(block)
    return h.hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def refs():return dict(branch=git('branch','--show-current'),HEAD=git('rev-parse','HEAD'),
    refs=git('show-ref'),index=git('ls-files','--stage'),tracked_status=git('status','--porcelain=v1','--untracked-files=no'))
def expected():
    meta=json.loads((PRIOR/'preservation_before.json').read_text())
    assert sha(PRIOR/'working_tree_before.jsonl')==meta['inventory_sha256']
    result={v['path']:v for v in map(json.loads,(PRIOR/'working_tree_before.jsonl').open())}
    inventory=json.loads((PRIOR/'output_sha256_inventory.json').read_text())
    for row in inventory['files']:
        p=ROOT/row['path'];assert sha(p)==row['sha256'],row['path']
        result[row['path']]=dict(path=row['path'],bytes=row['bytes'],mode=stat.S_IMODE(p.lstat().st_mode),kind='file',sha256=row['sha256'])
    p=PRIOR/'output_sha256_inventory.json';rel=str(p.relative_to(ROOT))
    result[rel]=dict(path=rel,bytes=p.stat().st_size,mode=stat.S_IMODE(p.lstat().st_mode),kind='file',sha256=sha(p))
    assert len(result)==443484
    return result
def paths():
    for base,dirs,files in os.walk(ROOT,followlinks=False):
        dirs[:]=sorted(d for d in dirs if Path(base)/d not in [ROOT/'.git',OUT])
        for name in sorted(files):yield Path(base)/name
        for name in dirs[:]:
            p=Path(base)/name
            if p.is_symlink():dirs.remove(name);yield p
def record(p):
    s=p.lstat();r=dict(path=str(p.relative_to(ROOT)),bytes=s.st_size,mode=stat.S_IMODE(s.st_mode))
    if p.is_symlink():r.update(kind='symlink',target=os.readlink(p))
    else:r.update(kind='file',sha256=sha(p))
    return r
def main():
    phase=sys.argv[1];assert phase in ['before','after']
    target=OUT/f'preservation_{phase}.json'
    if phase=='before':assert not target.exists()
    initial=refs();assert initial['branch']=='paper/jss-review-revision'
    if phase=='after':assert initial==json.loads((OUT/'preservation_before.json').read_text())['git']
    wanted=expected();seen=set();total=0
    for p in paths():
        row=record(p);rel=row['path'];assert wanted.get(rel)==row,rel
        seen.add(rel);total+=row['bytes']
        if len(seen)%100000==0:print(phase.upper(),len(seen),flush=True)
    assert seen==set(wanted)
    result=dict(status='PASS',phase=phase,protected_files_unchanged=len(seen),protected_bytes=total,
        git=initial,changes_outside_I2=0,historical_seals_changed=0,manuscript_modifications=0,
        scientific_modifications=0,training=0,inference=0,commit='no',tag='no',push='no')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='git'},indent=2))
if __name__=='__main__':main()
