"""Editorial inventory only; no experiment data or model execution."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
source = (ROOT / "manuscript/jss/manuscript.tex").read_text()
files = [(ROOT / "manuscript/jss/manuscript.tex", source)]
for name in re.findall(r"\\input\{([^}]+)\}", source):
    path = ROOT / "manuscript/jss" / (name + ".tex")
    files.append((path, path.read_text()))
cited = {key.strip() for _, text in files for block in re.findall(r"\\cite\w*\{([^}]+)\}", text) for key in block.split(",")}
bib = (ROOT / "manuscript/jss/references.bib").read_text()
keys = set(re.findall(r"@\w+\{([^,]+),", bib))
sections = re.split(r"(?=\\section\{)", source)
result = dict(bibliography_entries=len(keys), cited_keys=sorted(cited),
    unused_keys=sorted(keys-cited), missing_keys=sorted(cited-keys),
    section_raw_word_counts={re.search(r"\\section\{([^}]+)", s).group(1):len(s.split())
        for s in sections if s.startswith("\\section{")})
(OUT / "usage_before.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
