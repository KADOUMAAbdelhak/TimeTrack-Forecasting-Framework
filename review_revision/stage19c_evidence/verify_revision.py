"""Stage19C formatting, scope and preservation audit; no science is rerun."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_EVEN
import ast
import csv
import hashlib
import json
import os
import re
import subprocess
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = "manuscript/jss/manuscript.tex"
CHANGED = [SOURCE, "manuscript/jss/figures/results_signed_matrix.py",
           "manuscript/jss/figures/results_signed_matrix.pdf",
           "manuscript/jss/tables/efficiency_summary.tex"]
NEW = "manuscript/jss/tables/posthoc_controls.tex"
BLOCKS = ["TimeTrack", "fastStorage", "Rnd", "Materna-T1", "Materna-T2", "Materna-T3"]
RESOURCES = ["CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE"]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4194304), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    return list(csv.DictReader(Path(path).open()))

def fmt(value, places=2):
    return format(Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN), f"+.{places}f")

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

before = (OUT / "before/manuscript.tex").read_text()
after = (ROOT / SOURCE).read_text()
result_marker, discussion_marker = "\\section{Results}", "\\section{Discussion}"
assert before[:before.index(result_marker)] == after[:after.index(result_marker)]
assert before[before.index(discussion_marker):] == after[after.index(discussion_marker):]
section = after[after.index(result_marker):after.index(discussion_marker)]
assert not re.search(r"20\.178|20\.18", section)
assert "9/24" in section and "4/24" in section
assert "POST-HOC" in section and "sharing alone" in section
assert "1.0246/1.0347" in section and "Concentrated Degradation" in section
assert "0.9963" in section and "99.93" in section and "21/35" in section
assert sha(OUT / "before/manuscript.tex") == read(ROOT / "review_revision/stage19b_evidence/verification.json")["after_sha256"]

def assignments(path):
    tree = ast.parse(Path(path).read_text())
    return {n.targets[0].id: (ast.dump(n.value) if n.targets[0].id == "SOURCE_SHA256" else ast.literal_eval(n.value)) for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id in ("SOURCE_VALUES", "SOURCE_SHA256", "BLOCKS", "COMPARISONS", "RESOURCES")}

old = assignments(OUT / "before/results_signed_matrix.py")
new = assignments(ROOT / CHANGED[1])
assert new == old, "Primary figure values/identities changed"
expected_labels = [fmt(v) for panel in old["SOURCE_VALUES"] for row in panel for v in row]
for p in (ROOT / CHANGED[2], OUT / "before/results_signed_matrix.pdf"):
    text = PdfReader(p).pages[0].extract_text().replace("\u2212", "-")
    assert re.findall(r"[+-]\d+\.\d{2}", text) == expected_labels
assert len(expected_labels) == 72
old_eff = (OUT / "before/efficiency_summary.tex").read_text()
new_eff = (ROOT / CHANGED[3]).read_text()
assert re.findall(r"(?m)^\s*(?:S1|S2|M1)\s*&.*$", old_eff) == re.findall(r"(?m)^\s*(?:S1|S2|M1)\s*&.*$", new_eff)

# Independently parse displayed table entries and compare to source fields.
data = {}
for name in ("s2_common_context", "m1_capacity_matched", "ar_arx_baseline"):
    p = ROOT / "review_revision/experiments" / name / "posthoc_results.csv"
    rr = rows(p)
    data[name] = {(r["block"], r["resource"]): r for r in rr}
    assert len(rr) == len(data[name]) == 24
columns = {
    "A": [("m1_capacity_matched", "original_H64_vs_S2_gain_percent"),
          ("s2_common_context", "M1_vs_S2_common_gain_percent"),
          ("m1_capacity_matched", "H129_vs_S2_gain_percent")],
    "B": [("ar_arx_baseline", "frozen_S2_vs_S1_gain_percent"),
          ("ar_arx_baseline", "ARX_vs_AR_gain_percent")],
}
panel, checked_table, table_rows = None, 0, set()
for line in (ROOT / NEW).read_text().splitlines():
    match = re.search(r"\\textbf\{([AB]):\}", line)
    if match:
        panel = match.group(1)
    if not re.match(r"\s*(TimeTrack|fastStorage|Rnd|Materna T[123])\s*&", line):
        continue
    cells = line.split("&")
    b = cells[0].strip().replace("Materna T", "Materna-T")
    assert len(cells) == 5 and (panel, b) not in table_rows
    table_rows.add((panel, b))
    for resource, cell in zip(RESOURCES, cells[1:]):
        displayed = re.search(r"\$\[([^]]+)\]\$", cell).group(1).split("/")
        expected = [fmt(data[name][b, resource][field]) for name, field in columns[panel]]
        assert displayed == expected, (panel, b, resource)
        # Frozen references additionally reconcile with the unchanged primary figure.
        comparison = 1 if panel == "A" else 0
        assert displayed[0] == fmt(old["SOURCE_VALUES"][comparison][RESOURCES.index(resource)][BLOCKS.index(b)])
        checked_table += len(displayed)
assert len(table_rows) == 12 and checked_table == 120
trace = read(OUT / "posthoc_table_trace.json")
assert len(trace) == 120
for t in trace:
    p = ROOT / t["source"]
    assert sha(p) == t["source_sha256"]
    name = p.parent.name
    assert data[name][t["block"], t["resource"]][t["field"]] == t["raw"]
    assert t["displayed"] == fmt(t["raw"])

# Verify only already-published diagnostic facts; do not rebuild metrics.
seed = rows(ROOT / "review_revision/stage18c1_evidence/seed_sensitivity.csv")
for comp, expected_count in (("S2_vs_S1", 9), ("M1_vs_S2", 4)):
    selected = [r for r in seed if r["comparison"] == comp]
    assert len(selected) == 24
    assert sum(r["aggregate_seed_sign_variable"] == "True" for r in selected) == expected_count
robust = [r for r in rows(ROOT / "review_revision/stage18c1_evidence/robust_seed_mean_cells.csv") if r["comparison"] == "M1_vs_S2"]
assert len(robust) == 24
assert all(Decimal(r["median_MAE_ratio"]) > 1 and Decimal(r["candidate_win_rate"]) < Decimal("0.5") for r in robust)
for b, ratio in (("Materna-T1", "1.0246"), ("Materna-T3", "1.0347")):
    r = next(r for r in robust if (r["block"], r["resource"]) == (b, "DISK_WRITE"))
    assert fmt(r["median_MAE_ratio"], 4).lstrip("+") == ratio
d = read(ROOT / "review_revision/stage18c1_evidence/timetrack_throughput_diagnosis.json")
top = d["top_positive_excess_groups"][0]
assert top["groups"][0]["machine"] == "machine06" and top["groups"][0]["fold"] == 3
assert fmt(str(Decimal(str(top["share_positive_excess"])) * 100)) == "+99.93"
assert d["better_groups"] == 21 and d["group_count"] == 35 and fmt(str(d["median_ratio"]), 4) == "+0.9963"
assert fmt(data["ar_arx_baseline"]["TimeTrack", "THROUGHPUT"]["ARX_vs_AR_gain_percent"]) == "-838.45"
for b in BLOCKS:
    for resource in RESOURCES[1:]:
        assert Decimal(data["s2_common_context"][b, resource]["M1_vs_S2_common_gain_percent"]) < 0
        assert Decimal(data["m1_capacity_matched"][b, resource]["H129_vs_S2_gain_percent"]) < 0

# Full protected-tree SHA256 comparison, allowing only the requested artwork/source edits.
baseline = read(ROOT / "review_revision/stage18c1_evidence/preservation_baseline.json")
manifest = ROOT / "review_revision/stage18c1_evidence/preservation_before.jsonl"
assert sha(manifest) == baseline["inventory_sha256"]
expected = {v["path"]: v for v in map(json.loads, manifest.open())}
for rel in CHANGED[1:]:
    assert sha(OUT / "before" / Path(rel).name) == expected[rel]["sha256"]
protected = ["multiresource/04_lstm_factorial", "independent_validation/05_bitbrains_factorial",
    "independent_validation/06_materna_replication", "manuscript/jss", "benchmark/src",
    *["review_revision/experiments/" + name for name in (
        "s2_common_context", "s2_common_context_predecessor_stage18b1r", "m1_capacity_matched",
        "ar_arx_baseline", "ar_arx_baseline_predecessor_stage18b3")],
    "review_revision/stage18a1_diagnostic_audit.md"]
seen, preserved = set(), 0
for rel in protected:
    path = ROOT / rel
    paths = [path] if path.is_file() else (Path(base) / name for base, dirs, files in os.walk(path) for name in files)
    for p in paths:
        name = str(p.relative_to(ROOT)); seen.add(name)
        if name in CHANGED or name == NEW:
            continue
        v = expected.get(name)
        assert v and p.stat().st_size == v["bytes"] and sha(p) == v["sha256"], "Protected input changed: " + name
        preserved += 1
        if preserved % 100000 == 0:
            print("PRESERVATION_CHECKED", preserved, flush=True)
assert seen == set(expected) | {NEW}
inventory = read(ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json")
for v in inventory["files"]:
    assert sha(ROOT / v["path"]) == v["sha256"]
refs = {key: git("rev-parse", ref) for key, ref in {
    "HEAD": "HEAD", "main": "refs/heads/main", "paper_jss": "refs/heads/paper/jss",
    "scientific_tag_object": "refs/tags/phase4d-materna-final-scientific-freeze-v1",
    "scientific_tag_target": "phase4d-materna-final-scientific-freeze-v1^{}",
}.items()}
assert refs == baseline["refs"] and git("branch", "--show-current") == "paper/jss-review-revision"
assert set(git("diff", "--name-only").splitlines()) == set(CHANGED)
assert not git("diff", "--cached", "--name-only")
assert sha(ROOT / SOURCE) == hashlib.sha256(after.encode()).hexdigest()
log = (OUT / "build/manuscript.log").read_text()
assert not re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references", log)
pdf = PdfReader(OUT / "build/manuscript.pdf")
assert len(pdf.pages) == 20
assert "tab:posthoc-controls}{{3}" in (OUT / "build/manuscript.aux").read_text()
result = dict(status="STAGE_19C_PASS", changed=CHANGED, added=NEW,
    scope="Only Sections 5-6 and associated primary-figure renderer/artwork, new post-hoc table and efficiency caption/notes",
    untouched="Front matter, Abstract, Introduction, Related Work, Sections 3-4, Discussion, Threats, Conclusion, bibliography, supplement",
    frozen_primary_labels_verified=72, posthoc_table_entries_verified=120,
    primary_and_cross_study_table_sources_unchanged=True, efficiency_table_numeric_rows_unchanged=True,
    existing_seed_sign_flip_counts={"S2:S1": 9, "M1:S2": 4}, matched_cell_summaries_verified=24,
    ridge_throughput_classification="CONCENTRATED_DEGRADATION", new_statistics=0, training_calls=0, inference_calls=0,
    preserved_files=preserved, permitted_added_files=1, stage18c1_output_hashes_verified=len(inventory["files"]),
    scientific_modifications=0, refs=refs, build="Tectonic exit 0 and desktop compiler success", pages=20,
    unresolved_references_citations=0, visual_check="Pages 12-16, Figure 2 colour and greyscale; table readable",
    warnings="Pre-existing CAS overfull/empty-anchor, underfull boxes and two empty-pages bibliography fields",
    source_hashes={rel: sha(ROOT / rel) for rel in CHANGED + [NEW]}, commit="no", push="no")
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
