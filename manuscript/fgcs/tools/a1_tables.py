"""Render the amendment A1 supplement tables and main-text numbers from the frozen A1 analysis output.

    python manuscript/fgcs/tools/a1_tables.py ANALYSIS_JSON OUT_TEX

Refuses unless ANALYSIS_JSON has the SHA-256 recorded below. Prints the main-text summary numbers.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

EXPECTED = "ad0c4151dc9283c90336794f82bc3b5e7e2b9d90e92d52b416c55c6c7d720062"
BLOCKS = ("fastStorage", "Rnd")
RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
NAMES = {"CPU": "CPU", "THROUGHPUT": "Throughput", "MEMORY": "Memory", "DISK_WRITE": "Disk write"}
CLASS = {"Broad Positive": "BP", "Conditionally Positive": "CP", "Broad Negative": "BN", "Neutral or Mixed": "N/M",
         "Undefined": "U"}
COMPARISONS = ("M1-UW:M1", "M1-GN:M1", "M1-UW:S2", "M1-GN:S2", "M1:S2", "M1-UW:S1", "M1-GN:S1")

path, out = Path(sys.argv[1]), Path(sys.argv[2])
encoded = path.read_bytes()
if sha256(encoded).hexdigest() != EXPECTED:
    sys.exit("A1 analysis output differs from the frozen digest")
results = json.loads(encoded)["results"]
rows = {(r["contrast"], r["block"], r["resource"]): r for r in results["endpoints"]}
manipulation = {(m["cell"], m["block"]): m for m in results["manipulation"]}
decision = results["decision"]


def f(value, digits=3):
    return "--" if value is None else f"{value:.{digits}f}"


def g(value):
    return "--" if value is None else f"{value:+.2f}"


lines = [r"\begin{longtable}{@{}llrrrll@{}}",
         r"\caption{Amendment A1 endpoints per comparison, block and resource: matched-cell median MAE ratio "
         r"(candidate/reference) and win rate over seed-averaged entity $\times$ fold $\times$ horizon cells, "
         r"MacroMAE gain $G$ (\%) with its VM-cluster bootstrap 95\% interval, and consistency class "
         r"(BP, CP, BN, N/M). M1:S2 is the existing equal-loss tier-2 contrast, repeated for comparison.}"
         r"\label{tab:a1-endpoints}\\",
         r"\toprule", r"Comparison & Block / resource & Ratio & Win & $G$ (\%) & 95\% interval & Class \\",
         r"\midrule", r"\endfirsthead", r"\toprule",
         r"Comparison & Block / resource & Ratio & Win & $G$ (\%) & 95\% interval & Class \\",
         r"\midrule", r"\endhead"]
for comparison in COMPARISONS:
    first = True
    for block in BLOCKS:
        for resource in RESOURCES:
            r = rows[comparison, block, resource]
            interval = "--" if r["interval"] is None else f"[{g(r['interval'][0])}, {g(r['interval'][1])}]"
            label = comparison if first else ""
            first = False
            lines.append(f"{label} & {block} {NAMES[resource]} & {f(r['median_ratio'])} & {f(r['win_rate'], 2)} & "
                         f"{g(r['gain_percent'])} & {interval} & {CLASS[r['class']]} \\\\")
    lines.append(r"\addlinespace")
lines[-1] = r"\bottomrule"
lines.append(r"\end{longtable}")

lines += ["", r"\begin{longtable}{@{}llrrrrl@{}}",
          r"\caption{Amendment A1 manipulation checks at the selected epoch. Medians over the ten VMs of each "
          r"block of per-VM mean D-4 statistics: excess sign-conflict rate $K$, max/min task-gradient norm ratio "
          r"(unweighted) and the effective ratio (each norm times the task's training weight), with the mean "
          r"task weights (CPU/throughput/memory/disk write) of the final fits. Equal-loss M1 is the published "
          r"tier-2 D-4 result; its weights are all 1.}\label{tab:a1-manipulation}\\",
          r"\toprule", r"Block & Cell & $K$ & Norm ratio & Effective ratio & Check & Mean weights \\",
          r"\midrule", r"\endfirsthead", r"\toprule",
          r"Block & Cell & $K$ & Norm ratio & Effective ratio & Check & Mean weights \\", r"\midrule", r"\endhead"]
for block in BLOCKS:
    for cell, mode in (("M1", None), ("M1-UW", "uncertainty"), ("M1-GN", "gradnorm")):
        m = manipulation[cell, block]
        check = "reference" if mode is None else (
            "passed" if decision[mode]["manipulation_check"]["blocks"][block]["passed"] else "failed")
        weights = m["mean_weights_at_E"]
        shown = "1/1/1/1" if weights is None else "/".join(f"{weights[t]:.2f}" for t in RESOURCES)
        lines.append(f"{block} & {cell} & {m['median_K']:+.3f} & {m['median_norm_ratio']:.2f} & "
                     f"{m['median_effective_norm_ratio']:.2f} & {check} & {shown} \\\\")
lines += [r"\bottomrule", r"\end{longtable}"]

lines += ["", r"\begin{longtable}{@{}lrrrrl@{}}",
          r"\caption{Amendment A1 decisions under the frozen rule: cells (of 8) in which the arm beat equal-loss "
          r"M1 (median ratio below 1 and win rate above 0.5), cells with a median ratio above 1, cells with a "
          r"median ratio against S2 of at most 1, and the manipulation check.}\label{tab:a1-decision}\\",
          r"\toprule", r"Arm & Better & Worse & $\le$ S2 & Check & Verdict \\", r"\midrule", r"\endhead"]
for mode, label in (("uncertainty", "M1-UW"), ("gradnorm", "M1-GN")):
    d = decision[mode]
    check = ", ".join(f"{b} {'passed' if v['passed'] else 'failed'}" for b, v in d["manipulation_check"]["blocks"].items())
    lines.append(f"{label} & {d['better_than_equal_loss']} & {d['worse_than_equal_loss']} & {d['at_most_S2']} & "
                 f"{check} & {d['verdict']} \\\\")
lines += [r"\bottomrule", r"\end{longtable}"]
out.write_text("\n".join(lines) + "\n")

# Main-text numbers.
for comparison in COMPARISONS[:5]:
    values = [rows[comparison, b, r] for b in BLOCKS for r in RESOURCES]
    ratios = [v["median_ratio"] for v in values]
    wins = [v["win_rate"] for v in values]
    classes = [CLASS[v["class"]] for v in values]
    zero = sum(v["interval"][0] <= 0 <= v["interval"][1] for v in values)
    print(f"{comparison}: ratio {min(ratios):.3f}-{max(ratios):.3f}, win {min(wins):.2f}-{max(wins):.2f}, "
          f"classes {dict((c, classes.count(c)) for c in set(classes))}, intervals with 0: {zero}/8")
for b in BLOCKS:
    for r in RESOURCES:
        print(f"  {b} {r}: M1:S2 {rows['M1:S2', b, r]['median_ratio']:.3f} UW:S2 {rows['M1-UW:S2', b, r]['median_ratio']:.3f} "
              f"GN:S2 {rows['M1-GN:S2', b, r]['median_ratio']:.3f} | G M1:S2 {rows['M1:S2', b, r]['gain_percent']:+.2f} "
              f"UW:S2 {rows['M1-UW:S2', b, r]['gain_percent']:+.2f} GN:S2 {rows['M1-GN:S2', b, r]['gain_percent']:+.2f}")
print({mode: (d["verdict"], d["better_than_equal_loss"], d["at_most_S2"]) for mode, d in decision.items()})
