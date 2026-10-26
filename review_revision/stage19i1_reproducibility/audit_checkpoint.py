"""Read-only repository inventory and preservation audit; writes only audit outputs."""
from pathlib import Path
from collections import Counter
import hashlib, json, os, stat, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4194304), b''):
            h.update(block)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def paths():
    for base, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = sorted(d for d in dirs if Path(base)/d != ROOT/'.git' and Path(base)/d != OUT)
        for name in sorted(files):
            yield Path(base)/name
        for name in dirs[:]:
            p=Path(base)/name
            if p.is_symlink():
                dirs.remove(name)
                yield p

def row(path):
    info=path.lstat()
    result=dict(path=str(path.relative_to(ROOT)), bytes=info.st_size, mode=stat.S_IMODE(info.st_mode))
    if path.is_symlink():
        result.update(kind='symlink', target=os.readlink(path))
    else:
        result.update(kind='file', sha256=digest(path))
    return result

def refs():
    return dict(branch=git('branch','--show-current'), HEAD=git('rev-parse','HEAD'),
                refs=git('show-ref'), index=git('ls-files','--stage'),
                tracked_status=git('status','--porcelain=v1','--untracked-files=no'))

def preserve(phase):
    if phase=='before':
        assert not (OUT/'working_tree_before.jsonl').exists()
        initial=refs()
        assert initial['branch']=='paper/jss-review-revision'
        assert initial['HEAD']=='f6936cd111d911e40ec2725a18fdfc53768d9ccf'
        (OUT/'git_before.json').write_text(json.dumps(initial,indent=2)+'\n')
        count=size=0
        with (OUT/'working_tree_before.jsonl').open('w') as output:
            for p in paths():
                item=row(p);output.write(json.dumps(item,separators=(',',':'))+'\n')
                count+=1;size+=item['bytes']
                if count%100000==0: print('BEFORE',count,flush=True)
        result=dict(status='PASS',files=count,bytes=size,inventory_sha256=digest(OUT/'working_tree_before.jsonl'))
        (OUT/'preservation_before.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        initial=json.loads((OUT/'git_before.json').read_text())
        assert refs()==initial,'Git state changed'
        meta=json.loads((OUT/'preservation_before.json').read_text())
        assert digest(OUT/'working_tree_before.jsonl')==meta['inventory_sha256']
        expected={r['path']:r for r in map(json.loads,(OUT/'working_tree_before.jsonl').open())}
        seen=set()
        for p in paths():
            item=row(p);rel=item['path'];seen.add(rel)
            assert rel in expected and item==expected[rel],rel
            if len(seen)%100000==0: print('AFTER',len(seen),flush=True)
        assert seen==set(expected),'Membership changed'
        result=dict(status='PASS',files_unchanged=len(seen),bytes_unchanged=meta['bytes'],
                    git_refs_index_and_status_unchanged=True,changes_outside_audit=0,
                    manuscript_modifications=0,scientific_modifications=0,commit='no',tag='no',push='no')
        (OUT/'preservation_after.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    preserve(sys.argv[1])
