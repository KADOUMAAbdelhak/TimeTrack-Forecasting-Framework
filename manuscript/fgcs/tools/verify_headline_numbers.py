"""Recompute every number in the abstract and contribution list from hash-checked outputs and print a ledger.

    old_fgcs_rejected/.venv_legacy/bin/python manuscript/fgcs/tools/verify_headline_numbers.py

Sources: tier-1 published matched cells (stage18c1), the frozen tier-2 analysis (analysis_v04.json), the A1 analysis
(analysis_a1.json) and the A3 analysis (analysis_a3.json). The A3 macros in latex_source/a3_numbers.tex are also
regenerated in memory and compared with the committed file. Exits non-zero on any mismatch with the text.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FILES = {
    "tier1": ("review_revision/stage18c1_evidence/matched_seed_mean_errors.csv",
              "0cc4488c8fbdbe9e8195db710a33932e9e287c99676ab2dcad2603a9c2db9ce9"),
    "tier2": ("fgcs_strengthening_v04/runtime/analysis/analysis_v04.json",
              "308841865ec87b04e10ecb64f20bc13ce2e671511a1574056028f7b5710dd17a"),
    "a1": ("fgcs_strengthening_v04a1/runtime/analysis/analysis_a1.json",
           "ad0c4151dc9283c90336794f82bc3b5e7e2b9d90e92d52b416c55c6c7d720062"),
    "a3": ("fgcs_strengthening_v04a3/runtime/analysis_a3.json",
           "33e11a858ea338b3c3ff25bec2f59527a3a2100a386658443def77956501cee0"),
}
failures = []


def load(key):
    path, expected = FILES[key]
    data = (ROOT / path).read_bytes()
    if sha256(data).hexdigest() != expected:
        sys.exit(f"{path} differs from its recorded SHA-256")
    return data


def check(label, value, expected, source):
    ok = value == expected
    print(f"{'OK ' if ok else 'BAD'} {label}: {value}  [{source}]")
    if not ok:
        failures.append(label)


def main():
    cells = pd.read_csv(pd.io.common.BytesIO(load("tier1")), dtype={"entity": str})
    m1s2 = cells[cells.comparison == "M1_vs_S2"].groupby(["block", "resource"]).apply(
        lambda g: float(np.median(g.candidate_mae / g.reference_mae)))
    check("tier-1 M1:S2 cells with median ratio > 1", f"{int((m1s2 > 1).sum())} of {len(m1s2)}", "24 of 24",
          "matched_seed_mean_errors.csv")
    check("tier-1 M1:S2 cells above 1.01", f"{int((m1s2 > 1.01).sum())} of {len(m1s2)}", "22 of 24",
          "matched_seed_mean_errors.csv")

    t2 = json.loads(load("tier2"))["results"]["P4"]
    contrasts = t2["contrasts"]
    share = [r for r in contrasts if r["contrast"] == "M1:S2"]
    check("tier-2 M1:S2 cells above 1", f"{sum(r['median_ratio'] > 1 for r in share)} of {len(share)}", "30 of 32",
          "analysis_v04.json P4")
    check("tier-2 M1:S2 cells above 1.01", sum(r["median_ratio"] > 1.01 for r in share), 13, "analysis_v04.json P4")
    check("tier-2 LSTM M1:S2 cells above 1.01", sum(r["median_ratio"] > 1.01 for r in share if r["backbone"] == "LSTM"),
          6, "analysis_v04.json P4")
    check("54 of 56 typical cells", 24 + sum(r["median_ratio"] > 1 for r in share), 54, "tier 1 + tier 2")
    context = [r["median_ratio"] for r in contrasts if r["contrast"] == "S2:S1"]
    check("tier-2 S2:S1 ratio range across backbones", f"{min(context):.3f}-{max(context):.3f}", "0.981-1.035", "analysis_v04.json P4")
    skills = [entry["persistence_skill"] for row in t2["baseline_accuracy"] if row["resource"] in ("CPU", "THROUGHPUT")
              for entry in row["backbones"].values()]
    check("tier-2 CPU/throughput cells with positive persistence skill", sum(s > 0 for s in skills), 0,
          "analysis_v04.json P4 baseline_accuracy")

    a1 = json.loads(load("a1"))["results"]
    uw = [row for row in a1["endpoints"] if row.get("comparison") == "M1-UW:M1"] if isinstance(a1["endpoints"], list) else []
    check("A1 uncertainty-weighting verdict", a1["decision"]["uncertainty"]["verdict"], "supported", "analysis_a1.json")
    check("A1 cells at or below S2 (penalty removed)", a1["decision"]["uncertainty"]["at_most_S2"], 0, "analysis_a1.json")

    a3 = json.loads(load("a3"))
    v = a3["verdicts"]
    check("A3 H-A3a tier 1", v["H-A3a"]["tier1"]["verdict"], "rarely consolidates", "analysis_a3.json")
    check("A3 H-A3a tier 2", v["H-A3a"]["tier2"]["verdict"], "rarely consolidates", "analysis_a3.json")
    check("A3 H-A3b detects", f"{v['H-A3b']['counts']['detects']} of {len(v['H-A3b']['frames'])}", "12 of 14",
          "analysis_a3.json")
    check("A3 H-A3c", v["H-A3c"]["verdict"], "grouping adds savings", "analysis_a3.json")
    check("A3 fallback", v["fallback"]["verdict"], "fallback does not restore positive skill", "analysis_a3.json")

    # The committed macros must equal a fresh regeneration.
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "a3_numbers.tex"
        subprocess.run([sys.executable, str(ROOT / "manuscript/fgcs/tools/a3_numbers.py"), str(out)], check=True,
                       capture_output=True)
        committed = (ROOT / "manuscript/fgcs/latex_source/a3_numbers.tex").read_text()
        check("a3_numbers.tex reproduces", out.read_text() == committed, True, "tools/a3_numbers.py")
        macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", committed))
    for name in ("AiiiValWorseMin", "AiiiValWorseMax", "AiiiDetects", "AiiiFrames", "AiiiRetainedOne",
                 "AiiiRetainedTwo", "AiiiGroupRetained", "AiiiGroupMaxRatio", "AiiiMOneMaxRatio", "AiiiGroupMacroBelow"):
        print(f"    macro {name} = {macros[name]}")
    if failures:
        sys.exit(f"Mismatches: {failures}")


if __name__ == "__main__":
    main()
