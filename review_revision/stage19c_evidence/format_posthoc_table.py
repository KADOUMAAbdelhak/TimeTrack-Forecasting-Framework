"""Format existing gains only; no metrics, fitting or statistical recomputation."""
from pathlib import Path
import csv
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BLOCKS = ["TimeTrack", "fastStorage", "Rnd", "Materna-T1", "Materna-T2", "Materna-T3"]
RESOURCES = ["CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE"]
sources = {}
for name in ("s2_common_context", "m1_capacity_matched", "ar_arx_baseline"):
    p = ROOT / "review_revision/experiments" / name / "posthoc_results.csv"
    rows = list(csv.DictReader(p.open()))
    index = {(r["block"], r["resource"]): r for r in rows}
    assert len(rows) == len(index) == 24
    assert set(index) == {(b, r) for b in BLOCKS for r in RESOURCES}
    assert all(r["label"] == "POST-HOC SENSITIVITY RESULT" for r in rows)
    sources[name] = (p, index, hashlib.sha256(p.read_bytes()).hexdigest())

trace = []
def entry(name, block, resource, field, panel):
    p, rows, h = sources[name]
    raw = rows[block, resource][field]
    value = Decimal(raw)
    assert value.is_finite()
    shown = format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN), "+.2f")
    trace.append(dict(panel=panel, block=block, resource=resource,
                      source=str(p.relative_to(ROOT)), source_sha256=h,
                      field=field, raw=raw, displayed=shown))
    return shown

lines = [r"% Formatting-only projection of authoritative post-hoc CSV fields.",
    r"\begin{table*}[t]",
    r"  \caption{POST-HOC sensitivity comparisons alongside frozen reference gains (\%).}",
    r"  \label{tab:posthoc-controls}", r"  \centering", r"  \small",
    r"  \setlength{\tabcolsep}{2pt}", r"  \renewcommand{\arraystretch}{1.12}",
    r"  \begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrr@{}}", r"    \toprule",
    r"    \multicolumn{5}{l}{\textbf{A:} [H64 M1:S2 / H64 M1:common-S2 / H129 M1:S2]} \\",
    r"    Block & CPU & Throughput & Memory & Disk write \\", r"    \midrule"]
for b in BLOCKS:
    cells = []
    for r in RESOURCES:
        vals = [entry("m1_capacity_matched", b, r, "original_H64_vs_S2_gain_percent", "A"),
                entry("s2_common_context", b, r, "M1_vs_S2_common_gain_percent", "A"),
                entry("m1_capacity_matched", b, r, "H129_vs_S2_gain_percent", "A")]
        cells.append("$[" + "/".join(vals) + "]$")
    lines.append("    " + b.replace("-", " ") + " & " + " & ".join(cells) + r" \\")
lines += [r"    \midrule", r"    \multicolumn{5}{l}{\textbf{B:} [frozen LSTM S2:S1 / Ridge ARX:AR]} \\",
          r"    Block & CPU & Throughput & Memory & Disk write \\", r"    \midrule"]
for b in BLOCKS:
    cells = []
    for r in RESOURCES:
        vals = [entry("ar_arx_baseline", b, r, "frozen_S2_vs_S1_gain_percent", "B"),
                entry("ar_arx_baseline", b, r, "ARX_vs_AR_gain_percent", "B")]
        cell = "$[" + "/".join(vals) + "]$"
        if (b, r) == ("TimeTrack", "THROUGHPUT"):
            cell += r"\textsuperscript{a}"
        cells.append(cell)
    lines.append("    " + b.replace("-", " ") + " & " + " & ".join(cells) + r" \\")
lines += [r"    \bottomrule", r"  \end{tabular*}", r"  \vspace{2pt}",
    r"  \parbox{\textwidth}{\footnotesize Positive means lower candidate MacroMAE; values are rounded to two decimals.",
    r"  Frozen H64 M1:S2 and LSTM S2:S1 references are repeated unchanged, not replaced by controls.",
    r"  Common-S2 uses H64-M1 contexts; H129 selects its own contexts. These are separate controls, not joint causal isolation.",
    r"  \textsuperscript{a}The TimeTrack Ridge throughput penalty is concentrated in machine06/fold3:",
    r"  99.93\% of positive excess error; ARX improves 21/35 machine/fold pairs, median ARX/AR ratio $0.9963$ (Section~\ref{sec:results-rq1}).",
    r"  Point signs imply neither significance nor model-independent benefit; Materna T1--T3 remain dependent blocks.}",
    r"\end{table*}", ""]
target = ROOT / "manuscript/jss/tables/posthoc_controls.tex"
target.write_text("\n".join(lines))
assert len(trace) == 120
(OUT / "posthoc_table_trace.json").write_text(json.dumps(trace, indent=2) + "\n")
print("FORMATTED_EXISTING_VALUES", len(trace), target)
