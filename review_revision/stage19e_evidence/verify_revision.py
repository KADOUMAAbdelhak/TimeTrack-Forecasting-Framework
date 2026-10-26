"""Stage 19E source, literature-cell trace and preservation checks; no science run."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = "manuscript/jss/manuscript.tex"
TABLE = "manuscript/jss/tables/related_work_comparison.tex"
ALLOWED = {SOURCE, TABLE}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4194304), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

previous = read(ROOT / "review_revision/stage19d_evidence/verification.json")
assets = read(ROOT / "review_revision/stage19c_evidence/verification.json")
before = (OUT / "before/manuscript.tex").read_text()
after = (ROOT / SOURCE).read_text()
assert sha(OUT / "before/manuscript.tex") == previous["after_sha256"]
start, end = "\\section{Related Work}", "\\section{Multi-Metric Runtime Forecasting Framework}"
assert before[:before.index(start)] == after[:after.index(start)]
assert before[before.index(end):] == after[after.index(end):]
section = after[after.index(start):after.index(end)]
assert re.findall(r"\\label\{([^}]+)\}", before) == re.findall(r"\\label\{([^}]+)\}", after)
def cited(text):
    return {key.strip() for block in re.findall(r"\\cite\w*\{([^}]+)\}", text) for key in block.split(",")}
table = (ROOT / TABLE).read_text()
bib = (ROOT / "manuscript/jss/references.bib").read_text()
bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
assert len(bibkeys) == 39 and cited(after) <= bibkeys
assert cited(after) == cited(before), "Citation library/usage changed outside intended existing-key scope"
assert cited(table) <= cited(section)
assert len(cited(table)) == 6
assert "literature-wide priority claim" in section and "not an architecture" in section
assert "not pure causal interventions" in section and "post-hoc common-context" in section
assert not re.search(r"\bfirst\b|no prior (?:work|study)|none of the prior", section, re.I)

# One source locator for every table dimension; readings are described in the accompanying note.
columns = ["contextual_input_and_target_organisation", "independent_all_input_targets",
           "shared_cross_target_parameters", "single_task_vs_shared_comparison",
           "adverse_transfer_analysis", "efficiency_consolidation_evidence"]
spec = {
    "Ullah2023CloudBiLSTM": (["YES", "NO", "YES", "NO", "NO", "PARTIAL"],
        ["U3 pp.5-6", "U4-U5 pp.7,11-12", "U4 pp.5-7 Fig.3", "U5/U9 pp.11-20", "U5/U8/U9 pp.11-20", "U9 pp.12-13"]),
    "DiMenna2026RuntimeForecasting": (["NO", "NO", "NO", "NO", "NO", "PARTIAL"],
        ["D3-D4 pp.5-7", "D3-D4 pp.5-7", "D3-D4/D7 pp.5-7", "D3/D9 pp.5-15", "D3/D9 pp.5-15", "D10 pp.5-7"]),
    "Tripathi2025MMRP": (["YES", "PARTIAL", "NO", "NO", "NO", "PARTIAL"],
        ["M3-M5 pp.3-7,9-16", "M3/M5 pp.3-4,15-16", "M3-M4/M12 pp.3-7,17-21", "M3-M4/M9/M12 pp.3-7,10-21", "M3/M10/M12 pp.3-4,11,19-21", "M11 pp.14-17"]),
    "Nikentari2022NARMAXLSTM": (["YES", "Not established", "YES", "YES", "YES", "PARTIAL"],
        ["N2 Eq.(3), paper p.3", "N2-N3: no verified all-input independent-fit inventory", "N2 paper p.3", "N1 contribution 3; N3 Fig.2", "N1/N3 paper pp.1,5", "N1 paper p.1"]),
    "Nochumsohn2025MTLinear": (["NO", "NO", "YES", "PARTIAL", "YES", "YES"],
        ["T1 Eq.(4), T2 Sec.4.4", "T1-T3: own-history linear maps, not all-input target models", "T2 Sec.4.2", "T3 Sec.5.2 Fig.4", "T2 Sec.4.1 Fig.1", "T3 Table6; T4 Sec.5.3/App.C.4"]),
    "Bi2019CloudMultitask": (["Not established", "Not established", "Not established", "Not established", "Not established", "PARTIAL"],
        ["B1: does not settle cross-resource inputs", "B1: does not settle fit inventory", "B1: does not settle resource-target sharing", "B1: does not settle comparator organisation", "B1: does not settle transfer analysis", "B1: training-speed comparison"]),
    "This study": (["YES", "YES", "YES", "YES", "YES", "YES"],
        ["O Sec.3/Fig.1", "O Sec.3/Fig.1", "O Sec.3/Fig.1", "O Sec.3 and Sec.5.2", "O Sec.5.2", "O Sec.4 fit-time definitions; Sec.5.6/Table4"]),
}
source_map = {
    "U": "manuscript/jss/literature/closest_papers_fulltext_clearance.md#6-ullah-2023--full-text-evidence-ledger",
    "D": "manuscript/jss/literature/closest_papers_fulltext_clearance.md#7-di-menna-jss-2026--full-text-evidence-ledger",
    "M": "manuscript/jss/literature/closest_papers_fulltext_clearance.md#8-mmrp-2025--full-text-evidence-ledger",
    "N": "https://etheses.whiterose.ac.uk/id/eprint/36236/1/Multitask%20Learning%20Using%20Nonlinear%20Model%20for%20Forecasting%20Task.pdf",
    "T": "https://arxiv.org/html/2502.03571v2",
    "B": "https://digitalcommons.njit.edu/fac_pubs/7495/",
    "O": SOURCE,
}
body = table[table.index("\\midrule") + len("\\midrule"):table.index("\\bottomrule")]
trace, found = [], []
for row in re.split(r"\\\\", body):
    row = re.sub(r"\\addlinespace", "", row).strip()
    if not row:
        continue
    cells = [re.sub(r"\s+", " ", cell).strip() for cell in row.split("&")]
    assert len(cells) == 7
    match = re.search(r"\\citet\{([^}]+)\}", cells[0])
    key = match.group(1) if match else cells[0]
    codes, locators = spec[key]
    found.append(key)
    for col, cell, code, locator in zip(columns, cells[1:], codes, locators):
        assert cell.startswith(code), (key, col, cell, code)
        trace.append(dict(study=key, column=col, displayed_tex=cell, code=code,
                          source=source_map[locator[0]], locator=locator))
assert found == list(spec) and len(trace) == 42
assert table.count("\\begin{table*}") == 1
assert "Not established: available evidence does not settle the cell" in table
assert "pretrained reuse" in table and "horizons alone" in table

# Full protected-tree scan, overlaying only previously authorised Stage 19 assets.
baseline = read(ROOT / "review_revision/stage18c1_evidence/preservation_baseline.json")
manifest = ROOT / "review_revision/stage18c1_evidence/preservation_before.jsonl"
assert sha(manifest) == baseline["inventory_sha256"]
expected = {v["path"]: v for v in map(json.loads, manifest.open())}
assert sha(OUT / "before/related_work_comparison.tex") == expected[TABLE]["sha256"]
for rel, digest in assets["source_hashes"].items():
    if rel != SOURCE:
        assert sha(ROOT / rel) == digest, rel
        expected[rel] = dict(path=rel, bytes=(ROOT / rel).stat().st_size, sha256=digest)
protected = ["multiresource/04_lstm_factorial", "independent_validation/05_bitbrains_factorial",
    "independent_validation/06_materna_replication", "manuscript/jss", "benchmark/src",
    *["review_revision/experiments/" + name for name in (
        "s2_common_context", "s2_common_context_predecessor_stage18b1r", "m1_capacity_matched",
        "ar_arx_baseline", "ar_arx_baseline_predecessor_stage18b3")],
    "review_revision/stage18a1_diagnostic_audit.md"]
seen, preserved = set(), 0
for rel in protected:
    p = ROOT / rel
    paths = [p] if p.is_file() else (Path(base) / name for base, dirs, files in os.walk(p) for name in files)
    for path in paths:
        name = str(path.relative_to(ROOT)); seen.add(name)
        if name in ALLOWED:
            continue
        v = expected.get(name)
        assert v and path.stat().st_size == v["bytes"] and sha(path) == v["sha256"], name
        preserved += 1
        if preserved % 100000 == 0:
            print("PRESERVATION_CHECKED", preserved, flush=True)
assert seen == set(expected) and preserved == 395784
inventory = read(ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json")
for v in inventory["files"]:
    assert sha(ROOT / v["path"]) == v["sha256"], v["path"]
refs = {key: git("rev-parse", ref) for key, ref in {
    "HEAD": "HEAD", "main": "refs/heads/main", "paper_jss": "refs/heads/paper/jss",
    "scientific_tag_object": "refs/tags/phase4d-materna-final-scientific-freeze-v1",
    "scientific_tag_target": "phase4d-materna-final-scientific-freeze-v1^{}",
}.items()}
assert refs == baseline["refs"] == previous["refs"]
assert git("branch", "--show-current") == "paper/jss-review-revision"
assert set(git("diff", "--name-only").splitlines()) == set(assets["changed"]) | {TABLE}
assert not git("diff", "--cached", "--name-only")
assert sha(ROOT / SOURCE) == hashlib.sha256(after.encode()).hexdigest()
assert sha(ROOT / TABLE) == hashlib.sha256(table.encode()).hexdigest()
log = (OUT / "build/manuscript.log").read_text()
assert not re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references", log)
assert log.count("Overfull ") == 1 and "detected at line 87" in log
pdf = PdfReader(OUT / "build/manuscript.pdf")
assert len(pdf.pages) == 20
assert "tab:related-work-comparison}{{1}" in (OUT / "build/manuscript.aux").read_text()
assert "Closest inspected designs" in pdf.pages[3].extract_text()
result = dict(status="STAGE_19E_PASS", changed=sorted(ALLOWED),
    before_sha256={SOURCE:sha(OUT / "before/manuscript.tex"), TABLE:sha(OUT / "before/related_work_comparison.tex")},
    after_sha256={rel:sha(ROOT / rel) for rel in ALLOWED},
    scope="Related Work and its comparison table/caption only", prefix_suffix_byte_identical=True,
    all_labels_preserved=True, table_rows=7, literature_rows=6, table_dimensions=6, traced_cells=len(trace),
    table_rows_discussed_in_prose=True, bibliography_entries=len(bibkeys), new_citation_keys=0, bibliography_unchanged=True,
    gaps="NARMAX all-input independent-fit inventory; Bi resource-sharing/method/comparator detail; MMRP exact channel/fit inventory",
    build="Tectonic exit 0 and desktop compiler success", pages=20, unresolved_references_citations=0,
    new_overfull_lines=0, visual_check="Final pages 2-5 inspected; Table 1 readable at full page",
    protected_files_unchanged=preserved, protected_membership_verified=len(seen),
    stage18c1_output_hashes_verified=len(inventory["files"]), refs=refs,
    scientific_modifications=0, training=0, inference=0, new_statistics=0, commit="no", push="no")
(OUT / "table_cell_evidence.json").write_text(json.dumps(trace, indent=2) + "\n")
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
