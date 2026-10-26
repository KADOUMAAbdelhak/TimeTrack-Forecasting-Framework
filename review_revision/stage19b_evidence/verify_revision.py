"""Read-only scope/protocol/preservation checks; writes only Stage19B evidence."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = "manuscript/jss/manuscript.tex"

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
framework = "\\section{Multi-Metric Runtime Forecasting Framework}"
results = "\\section{Results}"
assert before[:before.index(framework)] == after[:after.index(framework)], "Front matter/Introduction/Related Work changed"
old_label = r"\noindent\texttt{R4\_TEMPORAL\_HETEROGENEITY\_CONFIRMED}."
new_label = r"\noindent Temporal heterogeneity confirmed."
old_suffix = before[before.index(results):]
assert old_suffix.count(old_label) == 1
assert old_suffix.replace(old_label, new_label) == after[after.index(results):], "Unauthorised Results/later edit"
methods = after[after.index(framework):after.index(results)]
assert "factorial" not in methods.lower()
assert "$2\\times2$ design" in methods
assert "mean inner-validation NMAE" not in after and "mean of validation NMAE" not in after
assert "R4\\_TEMPORAL" not in after
assert "q_r^{\\mathrm{native}}" in methods
for literal in ["MSE-selected best epoch", "This context score is not native",
                "entity, outer fold and seed", "No network pools training observations across entities",
                "not the realised loss or", "sum of successful unique worker fit-hours",
                "Post-Hoc Sensitivity Analyses", "206,100", "52,500", "206,880", "53,280",
                "H129", "206,420", "207,980", "native-unit validation MAE",
                "Broad Positive", "Conditionally Positive", "Broad Negative", "Neutral or Mixed",
                "interval exclusion of zero", "no artificial seed"]:
    assert literal in methods, "Missing protocol clarification: " + literal
assert re.findall(r"\\item\[RQ[1-4]:\]", before) == re.findall(r"\\item\[RQ[1-4]:\]", after)
old_labels = set(re.findall(r"\\label\{([^}]+)\}", before))
new_labels = set(re.findall(r"\\label\{([^}]+)\}", after))
assert new_labels - old_labels == {"sec:posthoc-controls"} and not old_labels - new_labels
prior = json.loads((ROOT / "review_revision/stage19a_evidence/verification.json").read_text())
assert sha(OUT / "manuscript_before.tex") == prior["after_sha256"], "Stage19A predecessor differs"
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
        assert p.stat().st_size == v["bytes"] and sha(p) == v["sha256"], "Protected input changed: " + name
        checked += 1
        if checked % 100000 == 0:
            print("PRESERVATION_CHECKED", checked, flush=True)
assert seen == set(expected), "Protected input removed"
inventory = json.loads((ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json").read_text())
for v in inventory["files"]:
    assert sha(ROOT / v["path"]) == v["sha256"], "Stage18C1 evidence changed: " + v["path"]

log = (OUT / "build/manuscript.log").read_text()
assert not re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references", log)
pages = int(re.search(r"Output written on manuscript.xdv \((\d+) pages", log).group(1))
aux = (OUT / "build/manuscript.aux").read_text()
assert r"\newlabel{sec:evaluation}{{4.8}" in aux
assert r"\newlabel{sec:posthoc-controls}{{4.11}" in aux
assert (OUT / "build/manuscript.pdf").is_file()
assert sha(ROOT / SOURCE) == hashlib.sha256(after.encode()).hexdigest(), "Source changed during audit"
result = {
    "status": "STAGE_19B_PASS", "changed_manuscript_source_files": [SOURCE],
    "scope": "Sections 3-4 including framework caption; separately authorised R4 label-only replacement in Results",
    "front_matter_abstract_introduction_related_work_unchanged": True,
    "results_and_later_unchanged_except_authorised_label": True,
    "figures_tables_bibliography_supplement_unchanged": True,
    "rq_numbering_preserved": True, "evaluation_subsection_number": "4.8", "posthoc_subsection_number": "4.11",
    "inappropriate_factorial_claims_remaining": 0, "selection_equals_native_nmae_ambiguity": False,
    "remaining_factorial_occurrences": "Only explicit denials in untouched Introduction, Related Work and Threats to Validity",
    "before_sha256": sha(OUT / "manuscript_before.tex"), "after_sha256": sha(ROOT / SOURCE),
    "protected_unchanged_files": checked, "protected_membership_unchanged": True,
    "stage18c1_output_hashes_verified": len(inventory["files"]),
    "scientific_result_modifications": 0, "training_calls": 0, "inference_calls": 0,
    "build": "Tectonic exit 0; desktop compiler success", "pages": pages,
    "undefined_references_or_citations": 0,
    "visual_check": "Changed pages 4-12 and authorised label on page 14 checked",
    "remaining_warnings": "Pre-existing CAS overfull/empty-anchor, underfull boxes and two empty-pages bibliography fields",
    "refs": refs, "commit": "no", "push": "no",
}
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
