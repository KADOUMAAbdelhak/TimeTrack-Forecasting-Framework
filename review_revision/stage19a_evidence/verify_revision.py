"""Stage19A source-scope, build and SHA256 preservation checks; no model calls."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = "manuscript/jss/manuscript.tex"
TITLE = "Evaluating Contextual Input and Shared Representation in Multi-Metric Runtime Forecasting for Cloud Software Systems"

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4194304), b""):
            h.update(chunk)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

before = (OUT / "manuscript_before.tex").read_text()
after = (ROOT / SOURCE).read_text()
marker = "\\section{Related Work}"
assert before[before.index(marker):] == after[after.index(marker):], "Out-of-scope body edit"

def frontmatter_without_allowlist(text):
    text = text[:text.index("\\section{Introduction}")]
    text = re.sub(r"\\shorttitle\{[^}]*\}", "SHORTTITLE", text)
    text = re.sub(r"\\title\[mode=title\]\{[^}]*\}", "TITLE", text)
    for block in ("abstract", "keywords"):
        text = re.sub(r"\\begin\{" + block + r"\}[\s\S]*?\\end\{" + block + r"\}", block.upper(), text)
    return text

assert frontmatter_without_allowlist(before) == frontmatter_without_allowlist(after)
assert "\\title[mode=title]{" + TITLE + "}" in after
assert "Disentangling Information Sharing" not in after
abstract = re.search(r"\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}", after).group(1).strip()
abstract_words = len(abstract.split())  # whitespace-separated, compounds retained
assert abstract_words <= 250
keywords = re.search(r"\\begin\{keywords\}([\s\S]*?)\\end\{keywords\}", after).group(1).split("\\sep")
assert 1 <= len(keywords) <= 7
assert git("branch", "--show-current") == "paper/jss-review-revision"
assert git("diff", "--name-only").splitlines() == [SOURCE]
assert not git("diff", "--cached", "--name-only")

baseline = json.loads((ROOT / "review_revision/stage18c1_evidence/preservation_baseline.json").read_text())
manifest = ROOT / "review_revision/stage18c1_evidence/preservation_before.jsonl"
assert sha(manifest) == baseline["inventory_sha256"]
refs = {key: git("rev-parse", ref) for key, ref in {
    "HEAD": "HEAD", "main": "refs/heads/main", "paper_jss": "refs/heads/paper/jss",
    "scientific_tag_object": "refs/tags/phase4d-materna-final-scientific-freeze-v1",
    "scientific_tag_target": "phase4d-materna-final-scientific-freeze-v1^{}",
}.items()}
assert refs == baseline["refs"]
expected = {v["path"]: v for v in map(json.loads, manifest.open())}
assert sha(OUT / "manuscript_before.tex") == expected[SOURCE]["sha256"]
protected = ["multiresource/04_lstm_factorial", "independent_validation/05_bitbrains_factorial",
    "independent_validation/06_materna_replication", "manuscript/jss", "benchmark/src",
    *["review_revision/experiments/" + name for name in (
        "s2_common_context", "s2_common_context_predecessor_stage18b1r", "m1_capacity_matched",
        "ar_arx_baseline", "ar_arx_baseline_predecessor_stage18b3")],
    "review_revision/stage18a1_diagnostic_audit.md"]
seen = set()
checked = 0
for rel in protected:
    path = ROOT / rel
    paths = [path] if path.is_file() else (Path(base) / name for base, dirs, files in os.walk(path) for name in files)
    for p in paths:
        name = str(p.relative_to(ROOT))
        assert name in expected, "Unexpected protected file: " + name
        seen.add(name)
        if name == SOURCE:
            continue
        v = expected[name]
        assert p.stat().st_size == v["bytes"] and sha(p) == v["sha256"], "Changed protected input: " + name
        checked += 1
        if checked % 100000 == 0:
            print("PRESERVATION_CHECKED", checked, flush=True)
assert seen == set(expected), "Removed protected input"
inventory = json.loads((ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json").read_text())
for v in inventory["files"]:
    assert sha(ROOT / v["path"]) == v["sha256"], "Stage18C1 evidence changed: " + v["path"]

log = (OUT / "build/manuscript.log").read_text()
assert not re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references", log)
assert "Output written on manuscript.xdv (18 pages" in log
assert (OUT / "build/manuscript.pdf").is_file()
result = {
    "status": "STAGE_19A_PASS", "changed_manuscript_source_files": [SOURCE],
    "allowed_sections": ["title", "shorttitle", "abstract", "keywords", "Introduction"],
    "title": TITLE, "abstract_word_count": abstract_words, "word_count_method": "whitespace-separated; hyphenated compounds retained",
    "keywords": [k.strip() for k in keywords], "keyword_count": len(keywords),
    "unmodified_body_from_related_work_to_eof": True,
    "before_sha256": sha(OUT / "manuscript_before.tex"), "after_sha256": sha(ROOT / SOURCE),
    "stage18c1_manifest_sha256": sha(manifest), "protected_unchanged_files": checked,
    "protected_membership_unchanged": True, "stage18c1_output_hashes_verified": len(inventory["files"]),
    "scientific_result_modifications": 0, "training_calls": 0, "inference_calls": 0,
    "build": "Tectonic exit 0; desktop compiler also success", "pages": 18,
    "undefined_references_or_citations": 0, "visual_check": "pages 1-3 clean",
    "layout_warnings": "pre-existing CAS 123.62721pt and body 0.70636pt overfull hboxes; empty anchors; underfull boxes",
    "remaining_work_outside_scope": "Later integration of post-hoc controls and selection terminology into Methods/Results/Discussion; unchanged here",
    "refs": refs, "commit": "no", "push": "no",
}
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
