"""Stage 19D source-scope and preservation audit. No model/metric execution."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import os
import re
import subprocess
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = "manuscript/jss/manuscript.tex"

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4194304), b""):
            digest.update(chunk)
    return digest.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

previous = read(ROOT / "review_revision/stage19c_evidence/verification.json")
before_path = OUT / "manuscript_before.tex"
assert sha(before_path) == previous["source_hashes"][SOURCE]
before = before_path.read_text()
after = (ROOT / SOURCE).read_text()
start, end = "\\section{Discussion}", "\\section*{Data availability}"
assert before[:before.index(start)] == after[:after.index(start)]
assert before[before.index(end):] == after[after.index(end):]
section = after[after.index(start):after.index(end)]
assert re.findall(r"\\label\{([^}]+)\}", before) == re.findall(r"\\label\{([^}]+)\}", after)
assert re.findall(r"\\section\{([^}]+)\}", section) == ["Discussion", "Threats to Validity", "Conclusion"]
for phrase in ("separate post-hoc controls", "not uniquely identify sharing",
               "concentrated in absolute-error magnitude", "finite five-alpha grid",
               "not IID replicates", "not a\nuniversal rejection", "not\nelapsed wall time"):
    assert phrase in section, phrase
for obsolete in ("models are not capacity matched", "catastrophic", "20.18", "R4_TEMPORAL"):
    assert obsolete not in section

# Trace prose to the existing authoritative synthesis; do not rebuild statistics.
evidence_path = ROOT / "review_revision/stage18c1_final_robustness_synthesis.md"
evidence = evidence_path.read_text()
checks = [
    ("Existing seed signs", "9/24", "S2:S1 has 15 sign-stable and 9 sign-variable"),
    ("Existing seed signs", "4/24", "M1:S2 has 20 stable and 4 variable"),
    ("All 24 matched-cell directions", "win rate below $50\\%$", "Every M1:S2 block/resource has median seed-mean ratio>1 and win rate<50%"),
    ("Separate controls", "all\nsix blocks", "Every throughput, memory and disk-write block/resource retains an adverse M1"),
    ("Ridge aggregate gain", "-838.45", "−838.449742%"),
    ("Ridge concentration", "99.93", "99.931577%"),
    ("Ridge improved pairs", "21/35", "Across 35 machine/fold pairs, ARX improves 21"),
    ("Ridge median", "0.9963", "0.996277043"),
    ("Materna disk medians", "1.025/1.035", "1.024565/1.034743"),
    ("Persistence boundary", "TimeTrack memory, Bitbrains CPU", "TimeTrack memory, Bitbrains CPU and fastStorage throughput"),
]
trace = []
for claim, displayed, anchor in checks:
    assert displayed in section and anchor in evidence, claim
    trace.append(dict(claim=claim, displayed=displayed, source=str(evidence_path.relative_to(ROOT)),
                      source_line=evidence[:evidence.index(anchor)].count("\n") + 1, anchor=anchor))
diagnosis = read(ROOT / "review_revision/stage18c1_evidence/timetrack_throughput_diagnosis.json")
assert diagnosis["better_groups"] == 21 and diagnosis["group_count"] == 35
assert format(diagnosis["median_ratio"], ".4f") == "0.9963"
top = diagnosis["top_positive_excess_groups"][0]
assert top["groups"][0]["machine"] == "machine06" and top["groups"][0]["fold"] == 3
assert format(Decimal(str(top["share_positive_excess"])) * 100, ".2f") == "99.93"
assert "74.5\\%" in before and "75\\%" in before
assert "74.5\\%" in section and "75\\%" in section

# Full historical protected-tree inventory, with authorised Stage 19C overlays.
baseline = read(ROOT / "review_revision/stage18c1_evidence/preservation_baseline.json")
manifest = ROOT / "review_revision/stage18c1_evidence/preservation_before.jsonl"
assert sha(manifest) == baseline["inventory_sha256"]
expected = {v["path"]: v for v in map(json.loads, manifest.open())}
assert len(expected) == baseline["files"] == 395785
for rel, digest in previous["source_hashes"].items():
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
    path = ROOT / rel
    paths = [path] if path.is_file() else (Path(base) / name for base, dirs, files in os.walk(path) for name in files)
    for path in paths:
        name = str(path.relative_to(ROOT))
        seen.add(name)
        if name == SOURCE:
            continue
        entry = expected.get(name)
        assert entry and path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"], name
        preserved += 1
        if preserved % 100000 == 0:
            print("PRESERVATION_CHECKED", preserved, flush=True)
assert seen == set(expected)
assert preserved == 395785
inventory = read(ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json")
for entry in inventory["files"]:
    assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
refs = {key: git("rev-parse", ref) for key, ref in {
    "HEAD": "HEAD", "main": "refs/heads/main", "paper_jss": "refs/heads/paper/jss",
    "scientific_tag_object": "refs/tags/phase4d-materna-final-scientific-freeze-v1",
    "scientific_tag_target": "phase4d-materna-final-scientific-freeze-v1^{}",
}.items()}
assert refs == baseline["refs"] == previous["refs"]
assert git("branch", "--show-current") == "paper/jss-review-revision"
assert set(git("diff", "--name-only").splitlines()) == set(previous["changed"])
assert not git("diff", "--cached", "--name-only")
assert sha(ROOT / SOURCE) == hashlib.sha256(after.encode()).hexdigest()
log = (OUT / "build/manuscript.log").read_text()
assert not re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references", log)
assert log.count("Overfull ") == 1 and "detected at line 87" in log
pdf = PdfReader(OUT / "build/manuscript.pdf")
assert len(pdf.pages) == 20
result = dict(status="STAGE_19D_PASS", changed=[SOURCE], before_sha256=sha(before_path),
    after_sha256=sha(ROOT / SOURCE), scope="Discussion, Threats to Validity and Conclusion only",
    prefix_and_suffix_byte_identical=True, all_labels_preserved=True,
    untouched="Abstract, Introduction, Related Work, Methods, Results, Cross-Dataset Synthesis, all figures/tables, bibliography and supplement",
    numerical_prose_trace=trace, trace_source_sha256=sha(evidence_path),
    protected_files_unchanged=preserved, protected_membership_verified=len(seen),
    stage18c1_output_hashes_verified=len(inventory["files"]), refs=refs,
    build="Tectonic exit 0 and desktop compiler success", pages=20,
    unresolved_references_citations=0, new_overfull_lines=0,
    visual_check="Rendered pages 16-19 inspected; no clipped or overlapping revised prose",
    warnings="Pre-existing CAS title overfull, empty anchors, underfull boxes and bibliography empty-pages fields",
    scientific_modifications=0, training=0, inference=0, new_statistics=0, commit="no", push="no")
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
