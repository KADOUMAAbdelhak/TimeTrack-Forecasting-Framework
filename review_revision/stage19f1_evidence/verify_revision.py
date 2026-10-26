"""Editorial scope, literal result preservation and protected-file audit; no science."""
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
BIB = "manuscript/jss/references.bib"
ALLOWED = {SOURCE, BIB}

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

before = (OUT / "before/manuscript.tex").read_text()
after = (ROOT / SOURCE).read_text()
previous = read(ROOT / "review_revision/stage19e_evidence/verification.json")
assets = read(ROOT / "review_revision/stage19c_evidence/verification.json")
assert sha(OUT / "before/manuscript.tex") == previous["after_sha256"][SOURCE]

def between(text, start, end):
    return text[text.index(start):text.index(end)]

# Author metadata/front matter, availability, funding, abstract and keywords are immutable.
assert between(before, "\\shorttitle", "\\section{Introduction}") == between(after, "\\shorttitle", "\\section{Introduction}")
assert before[before.index("\\section*{Data availability}"):] == after[after.index("\\section*{Data availability}"):]
assert before[:before.index("\\shorttitle")].split("\\documentclass", 1)[1].split("% Future figure constraints:")[0].strip() in after
for env in ("equation", "figure\\*", "enumerate", "description"):
    pattern = r"\\begin\{" + env + r"\}.*?\\end\{" + env + r"\}"
    assert re.findall(pattern, before, re.S) == re.findall(pattern, after, re.S), env
assert re.findall(r"\\label\{([^}]+)\}", before) == re.findall(r"\\label\{([^}]+)\}", after)
assert re.findall(r"\\(?:sub)*section\{[^}]+\}", before) == re.findall(r"\\(?:sub)*section\{[^}]+\}", after)

# Detailed protocol/results blocks are unchanged; compression removes repeated interpretation.
blocks = [
    ("\\subsection{Datasets}", "\\subsection{Target Construction and Preprocessing}"),
    ("\\subsection{Target Construction and Preprocessing}", "\\subsection{Model Architecture and Training}"),
    ("\\subsection{Evaluation Metrics and Statistical Analysis}", "\\subsection{External and Temporal Replication Design}"),
    ("\\subsection{Post-Hoc Sensitivity Analyses}", "\\section{Results}"),
    ("\\section{Related Work}", "\\section{Multi-Metric Runtime Forecasting Framework}"),
    ("The Bitbrains environments did not reproduce one common direction.", "Memory therefore"),
]
for start, end in blocks[:-1]:
    assert between(before, start, end) == between(after, start, end), start
assert between(before, blocks[-1][0], "Memory therefore") == between(after, blocks[-1][0], "Memory has the clearest")
same_spans = [
    ("\\paragraph{Post-hoc cross-model and seed checks.}", "\\subsection{RQ2 Operational"),
    ("\\subsection{RQ2 Operational", "Within the controlled shared-LSTM"),
    ("\\paragraph{Post-hoc sharing controls and matched cells.}", "\\subsection{RQ3 Full"),
    ("\\subsection{RQ3 Full", "The complete-system comparison"),
    ("\\subsection{RQ4 Resource", "Three boundaries follow"),
    ("\\subsection{Accuracy-Efficiency Trade-Off}", "\\section{Cross-Dataset Synthesis}"),
]
new_end = {"Within the controlled shared-LSTM":"Degradation recurred outside",
           "The complete-system comparison":"RQ3 combines both design changes.",
           "Three boundaries follow":"Thus relative gain, overall persistence skill"}
for start, end in same_spans:
    assert between(before, start, end) == between(after, start, new_end.get(end, end)), start

# Preserve every scientific numeric literal; only obsolete hard-coded section numbers disappear.
def numerals(text):
    text = re.sub(r"(?m)%.*$", "", text)
    text = re.sub(r"Section~\d+(?:\.\d+)?", "", text)
    text = re.sub(r"\\(?:cite\w*|ref|label|input|includegraphics)(?:\[[^]]*\])?\{[^}]*\}", "", text)
    return set(re.findall(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?", text))
missing_numbers = sorted(numerals(before) - numerals(after))
assert not missing_numbers, missing_numbers
assert not (numerals(after) - numerals(before)), "New numeric literal introduced"

def all_text(main):
    texts = [main]
    for name in re.findall(r"\\input\{([^}]+)\}", main):
        texts.append((ROOT / "manuscript/jss" / (name + ".tex")).read_text())
    return "\n".join(texts)

def cited(text):
    return {key.strip() for block in re.findall(r"\\cite\w*\{([^}]+)\}", text) for key in block.split(",")}

def entries(text):
    return {m.group(1): m.group(0) for m in re.finditer(r"(?ms)^@\w+\{([^,]+),.*?^\}", text)}

old_bib = entries((OUT / "before/references.bib").read_text())
new_bib = entries((ROOT / BIB).read_text())
old_cites, new_cites = cited(all_text(before)), cited(all_text(after))
removed = set(old_bib) - set(new_bib)
assert removed == {"Bergmeir2018CrossValidation", "Islam2012Provisioning", "Toka2021KubernetesScaling", "Zeng2023LinearForecasting"}
assert not removed & old_cites
assert all(old_bib[key] == value for key, value in new_bib.items())
assert new_cites == old_cites | {"Hochreiter1997LSTM"}
assert set(new_bib) == new_cites and len(new_bib) == 35
assert not re.search(r"\b[Ss]ections?\s*~?\s*\d", after)
assert not re.search(r"factorial|R4_[A-Z]|R[0-9]+_[A-Z]|STAGE_|Stage [0-9]", after)

# Cross-reference ledger for retained qualifications after duplicate prose removal.
anchors = {
    "entity-specific complement": "Models are entity-specific",
    "equal weights not equal gradients": "Equal coefficients do not imply equal realised losses or gradients",
    "selection space": "This context score is not native",
    "local model inventory": "not a globally deployed four-versus-one",
    "fit-hour semantics": "Summed worker fit-hours are not",
    "separate controls": "the\ntwo LSTM controls are separate, not a jointly matched intervention",
    "common context scope": "not necessarily the newly selected H129 contexts",
    "Ridge design boundary": "not equality of LSTM/Ridge selection objectives",
    "Ridge concentration": "99.93",
    "all matched-cell directions": "In all 24 original M1:S2",
    "seed sensitivity": "9/24",
    "M1 seed sensitivity": "4/24",
    "causal boundary": "without identifying sharing alone",
    "post-hoc uncertainty": "not prespecified confirmation",
    "non-IID": "are not IID replicates",
    "Materna dependence": "not independent datasets",
    "population": "not make the cohort\na probability sample",
    "absolute skill": "Undefined zero-denominator skills",
    "no production measurement": "benefits were not measured",
    "universal rejection excluded": "do not universally reject multi-task",
}
for claim, anchor in anchors.items():
    assert anchor in after, claim

# Historical protected tree, overlaying the authorised Stage 19C/19E asset revisions.
baseline = read(ROOT / "review_revision/stage18c1_evidence/preservation_baseline.json")
manifest = ROOT / "review_revision/stage18c1_evidence/preservation_before.jsonl"
assert sha(manifest) == baseline["inventory_sha256"]
expected = {v["path"]:v for v in map(json.loads, manifest.open())}
assert sha(OUT / "before/references.bib") == expected[BIB]["sha256"]
overlays = dict(assets["source_hashes"])
overlays.update(previous["after_sha256"])
for rel, digest in overlays.items():
    if rel not in ALLOWED:
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
    for p in paths:
        name = str(p.relative_to(ROOT)); seen.add(name)
        if name in ALLOWED:
            continue
        v = expected.get(name)
        assert v and p.stat().st_size == v["bytes"] and sha(p) == v["sha256"], name
        preserved += 1
        if preserved % 100000 == 0:
            print("PRESERVATION_CHECKED", preserved, flush=True)
assert seen == set(expected) and preserved == 395784
inventory = read(ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json")
for v in inventory["files"]:
    assert sha(ROOT / v["path"]) == v["sha256"], v["path"]
refs = {key:git("rev-parse", ref) for key, ref in {
    "HEAD":"HEAD", "main":"refs/heads/main", "paper_jss":"refs/heads/paper/jss",
    "scientific_tag_object":"refs/tags/phase4d-materna-final-scientific-freeze-v1",
    "scientific_tag_target":"phase4d-materna-final-scientific-freeze-v1^{}",
}.items()}
assert refs == baseline["refs"] == previous["refs"]
assert git("branch", "--show-current") == "paper/jss-review-revision"
assert set(git("diff", "--name-only").splitlines()) == set(assets["changed"]) | {"manuscript/jss/tables/related_work_comparison.tex", BIB}
assert not git("diff", "--cached", "--name-only")
assert sha(ROOT / SOURCE) == hashlib.sha256(after.encode()).hexdigest()
log = (OUT / "build/manuscript.log").read_text()
assert not re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get cross-references", log)
assert log.count("Overfull ") == 1 and "123.62721pt" in log
pdf = PdfReader(OUT / "build/manuscript.pdf")
assert len(pdf.pages) == 17
signoff_path = OUT / "visual_signoff.json"
signoff = read(signoff_path) if signoff_path.exists() else None
if signoff:
    assert signoff["status"] == "PASS" and signoff["pages_inspected"] == list(range(1,18))
    assert signoff["pdf_sha256"] == sha(OUT / "build/manuscript.pdf")
    assert signoff["source_sha256"] == sha(ROOT / SOURCE)
result = dict(status="STAGE_19F1_PASS", changed=sorted(ALLOWED), pages_before=20, pages_after=len(pdf.pages),
    raw_source_words_before=len(before.split()), raw_source_words_after=len(after.split()),
    equations_byte_identical=len(re.findall(r"\\begin\{equation\}", after)),
    figures_captions_byte_identical=True, all_table_sources_and_artwork_unchanged=True,
    all_labels_and_section_structure_preserved=True, contributions_and_RQs_byte_identical=True,
    abstract_author_funding_data_availability_unchanged=True,
    all_scientific_numeric_literals_retained=True, detailed_result_spans_byte_identical=len(same_spans),
    bibliography_before=len(old_bib), bibliography_after=len(new_bib), uncited_removed=sorted(removed),
    retained_and_now_cited="Hochreiter1997LSTM, foundational reference at the backbone definition",
    new_references=0, uncited_entries_after=[], original_cited_keys_preserved=True,
    hardcoded_section_references=0, internal_stage_tokens=0, causal_factorial_effect_language=0,
    qualification_ledger={claim:after[:after.index(anchor)].count("\n")+1 for claim,anchor in anchors.items()},
    protected_files_unchanged=preserved, protected_membership_verified=len(seen),
    stage18c1_output_hashes_verified=len(inventory["files"]), refs=refs,
    before_sha256={SOURCE:sha(OUT / "before/manuscript.tex"), BIB:sha(OUT / "before/references.bib")},
    after_sha256={rel:sha(ROOT / rel) for rel in ALLOWED}, pdf_sha256=sha(OUT / "build/manuscript.pdf"),
    build="Tectonic exit 0 and desktop compiler success" if signoff else "Tectonic exit 0",
    unresolved_references_citations=0, new_overfull_lines=0,
    visual_check="All 17 final pages inspected; see hash-bound visual_signoff.json" if signoff else "Pending separate all-page visual sign-off",
    scientific_modifications=0, training=0, inference=0, new_statistics=0, commit="no", push="no")
(OUT / "verification.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2), flush=True)
