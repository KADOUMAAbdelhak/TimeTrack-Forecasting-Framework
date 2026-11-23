"""Every amendment-A3 number used in the manuscript, as LaTeX macros, from the hash-checked A3 output.

    old_fgcs_rejected/.venv_legacy/bin/python manuscript/fgcs/tools/a3_numbers.py OUT.tex

Also writes the main-text table (a3_table.tex, next to OUT) and the supplement tables
(supplement_source/a3_supplement_tables.tex).

Reads only fgcs_strengthening_v04a3/runtime/analysis_a3.json and refuses on a digest mismatch. Prints each
macro with its value.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
A3 = ROOT / "fgcs_strengthening_v04a3/runtime/analysis_a3.json"
A3_SHA = "33e11a858ea338b3c3ff25bec2f59527a3a2100a386658443def77956501cee0"


def check(path, expected):
    if sha256(path.read_bytes()).hexdigest() != expected:
        sys.exit(f"{path.name} differs from its recorded SHA-256")


def pct(x, digits=0):
    return f"{100 * x:.{digits}f}"


def main():
    out = Path(sys.argv[1])
    check(A3, A3_SHA)
    d = json.loads(A3.read_text())
    v, rows, summaries, detection = d["verdicts"], d["rows"], d["summaries"], d["detection"]

    def models(tier, policy, backbone=None):
        chosen = [s for s in summaries if s["tier"] == tier and s["policy"] == policy
                  and (backbone is None or s["backbone"] == backbone)]
        return sum(s["mean_models"] * s["units"] for s in chosen) / sum(s["units"] for s in chosen)

    def params(policy, backbone="LSTM"):
        chosen = [s for s in summaries if s["tier"] == "tier2" and s["policy"] == policy and s["backbone"] == backbone]
        return float(np.mean([s["mean_parameters"] for s in chosen]))

    def select(tier, policy, backbone=None):
        return [r for r in rows if r["tier"] == tier and r["policy"] == policy
                and (backbone is None or r["backbone"] == backbone)]

    def below_zero(rs):
        return sum(r["macro_gain_vs_S2_interval"][1] < 0 for r in rs)

    m = {}
    a = v["H-A3a"]
    for tier, name in (("tier1", "One"), ("tier2", "Two")):
        m[f"AiiiRetained{name}"] = pct(a[tier]["savings_retained"])
        m[f"AiiiCost{name}"] = str(a[tier]["cost_cells"])
        m[f"AiiiRefCost{name}"] = str(a[tier]["reference_cost_cells"])
        m[f"AiiiCells{name}"] = str(a[tier]["cells"])
        m[f"AiiiVerdict{name}"] = a[tier]["verdict"]
        m[f"AiiiRetainedZero{name}"] = pct(a[tier]["by_tolerance"]["0%"]["savings_retained"])
        m[f"AiiiRetainedTwoPct{name}"] = pct(a[tier]["by_tolerance"]["2%"]["savings_retained"])
        m[f"AiiiCostAll{name}"] = str(max(t["cost_cells"] for t in a[tier]["by_tolerance"].values()))
    units = {"tier1": sum(s["units"] for s in summaries if s["tier"] == "tier1" and s["policy"] == "S2"),
             "tier2": sum(s["units"] for s in summaries if s["tier"] == "tier2" and s["policy"] == "S2")}
    m["AiiiUnitsOne"], m["AiiiUnitsTwo"] = f"{units['tier1']:,}".replace(",", "{,}"), f"{units['tier2']:,}".replace(",", "{,}")

    b = v["H-A3b"]
    m["AiiiDetects"] = str(b["counts"]["detects"])
    m["AiiiFrames"] = str(len(detection))
    rhos = [x["rho"] for x in detection]
    m["AiiiRhoMin"], m["AiiiRhoMax"] = f"{min(rhos):.2f}", f"{max(rhos):.2f}"
    m["AiiiNotDetected"] = " and ".join(f"{'tier-1' if x['tier'] == 'tier1' else 'tier-2 LSTM'} {x['block']}"
                                         for x in detection if x["verdict"] == "does not detect")
    m["AiiiValWorseMin"] = pct(min(x["validation_worse_share"] for x in detection))
    m["AiiiValWorseMax"] = pct(max(x["validation_worse_share"] for x in detection))
    m["AiiiOutWorseMin"] = pct(min(x["outer_worse_share"] for x in detection))
    m["AiiiOutWorseMax"] = pct(max(x["outer_worse_share"] for x in detection))
    ba = [x["balanced_accuracy"] for x in detection]
    m["AiiiBAMin"], m["AiiiBAMax"] = f"{min(ba):.2f}", f"{max(ba):.2f}"

    c = v["H-A3c"]
    group, share = "G-group@1%", "G-share@1%"
    m["AiiiGroupModels"] = f"{c['group_mean_models']:.1f}"
    m["AiiiShareModelsLSTM"] = f"{c['share_mean_models']:.1f}"
    m["AiiiGroupRetained"] = pct((4 - c["group_mean_models"]) / 3)
    m["AiiiGroupParams"] = f"{params(group):,.0f}".replace(",", "{,}")
    m["AiiiSTwoParams"] = f"{params('S2'):,.0f}".replace(",", "{,}")
    m["AiiiMOneParams"] = f"{params('M1'):,.0f}".replace(",", "{,}")
    m["AiiiGroupParamCut"] = pct(1 - params(group) / params("S2"))
    m["AiiiGroupCost"] = str(c["group_cost_cells"])
    m["AiiiGroupVerdict"] = c["verdict"]
    g_rows, m1_rows = select("tier2", group, "LSTM"), select("tier2", "M1", "LSTM")
    m["AiiiGroupMaxRatio"] = f"{max(r['median_ratio_vs_S2'] for r in g_rows):.3f}"
    m["AiiiMOneMaxRatio"] = f"{max(r['median_ratio_vs_S2'] for r in m1_rows):.3f}"
    m["AiiiMOneCostLSTM"] = str(sum(r["median_ratio_vs_S2"] > 1.01 for r in m1_rows))
    m["AiiiGroupMacroBelow"] = str(below_zero(g_rows))
    m["AiiiMOneMacroBelow"] = str(below_zero(m1_rows))
    m["AiiiGroupWorstGain"] = f"{min(r['macro_gain_vs_S2_percent'] for r in g_rows):.2f}"
    m["AiiiMOneWorstGain"] = f"{min(r['macro_gain_vs_S2_percent'] for r in m1_rows):.2f}"
    m["AiiiGroupWinMin"] = pct(min(r["win_rate_vs_S2"] for r in g_rows))
    m["AiiiGroupWinMax"] = pct(max(r["win_rate_vs_S2"] for r in g_rows))
    m["AiiiGroupTwoPctModels"] = f"{models('tier2', 'G-group@2%', 'LSTM'):.1f}"
    m["AiiiGroupTwoPctCost"] = str(sum(r["median_ratio_vs_S2"] > 1.01 for r in select("tier2", "G-group@2%", "LSTM")))
    m["AiiiOracleModels"] = f"{models('tier2', 'oracle-group', 'LSTM'):.1f}"
    m["AiiiOracleMinRatio"] = f"{min(r['median_ratio_vs_S2'] for r in select('tier2', 'oracle-group', 'LSTM')):.3f}"
    partitions = sorted({r["policy"] for r in rows if r["policy"].startswith("partition:")})
    best_fixed = [p for p in partitions if p.count("|") < 3
                  and sum(r["median_ratio_vs_S2"] > 1.01 for r in select("tier2", p, "LSTM")) == 0]
    m["AiiiFixedNoCost"] = str(len(best_fixed))
    m["AiiiFixedShared"] = str(sum(p.count("|") < 3 for p in partitions))

    f = v["fallback"]
    m["AiiiFallbackPositive"], m["AiiiFallbackCells"] = str(f["positive_skill"]), str(f["cells"])
    m["AiiiFallbackBefore"] = str(f["positive_skill_without_fallback"])

    lines = [f"% Generated by manuscript/fgcs/tools/a3_numbers.py from analysis_a3.json (SHA-256 {A3_SHA}).",
             "% Do not edit by hand."]
    for name, value in m.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")
        print(f"{name} = {value}")
    out.write_text("\n".join(lines) + "\n")
    tables(d, out.with_name("a3_table.tex"), ROOT / "manuscript/fgcs/supplement_source/a3_supplement_tables.tex")



# -- tables (written next to the macros; generated, never edited by hand) -------------------------

BACKBONE_LABEL = {"LSTM": "LSTM", "DLinear": "DLinear", "PatchTST": "PatchTST-style", "iTransformer": "iTransformer-style"}
RESOURCE_LABEL = {"CPU": "CPU", "THROUGHPUT": "Throughput", "MEMORY": "Memory", "DISK_WRITE": "Disk write"}


def tables(d, main_out, supplement_out):
    rows, summaries, detection, v = d["rows"], d["summaries"], d["detection"], d["verdicts"]

    def sel(tier, policy, backbone=None, block=None):
        return [r for r in rows if r["tier"] == tier and r["policy"] == policy
                and (backbone is None or r["backbone"] == backbone) and (block is None or r["block"] == block)]

    def models(tier, policy, backbone=None):
        chosen = [s for s in summaries if s["tier"] == tier and s["policy"] == policy
                  and (backbone is None or s["backbone"] == backbone)]
        return sum(s["mean_models"] * s["units"] for s in chosen) / sum(s["units"] for s in chosen)

    def params(policy):
        chosen = [s["mean_parameters"] for s in summaries
                  if s["tier"] == "tier2" and s["policy"] == policy and s["backbone"] == "LSTM"]
        return f"{np.mean(chosen):,.0f}".replace(",", "{,}")

    def cost(rs):
        return sum(r["median_ratio_vs_S2"] > 1.01 for r in rs)

    def share(tier, tolerance, backbone=None):
        return pct((4 - models(tier, f"G-share@{tolerance}", backbone)) / 3)

    # Main-text table.
    main = [r"\begin{table}[t]", r"\centering",
            r"\caption{Amendment A3 on existing fits. (A) Consolidation gate G-share: share of machine $\times$ fold "
            r"$\times$ seed units consolidated into one shared model at tolerance $\tau$, typical-cell cost cells "
            r"(policy:S2 median ratio above 1.01) and frames whose validation and test M1/S2 ratios are rank-correlated ($\rho\geq0.3$, interval above zero). (B) Tier-2 LSTM groupings at "
            r"$\tau=1\%$ and $2\%$: mean models and parameters per unit, cost cells and largest median ratio "
            r"(of 8 cells), and cells whose MacroMAE-gain interval lies below zero. The oracle uses the outer "
            r"test and is an upper bound, not a policy.}",
            r"\label{tab:a3}", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
            r"\begin{tabular}{@{}lccccc@{}}", r"\toprule",
            r"\multicolumn{6}{@{}l}{\emph{(A) G-share: units consolidated (\%), cost cells, ranking}} \\",
            r" & $\tau{=}0$ & $1\%$ & $2\%$ & Cost$_{1\%}$ (M1) & Ranks \\", r"\midrule"]
    for tier, label, frames in (("tier1", "Tier 1, LSTM", 6), ("tier2", "Tier 2, 4 backbones", 8)):
        det = [x for x in detection if x["tier"] == tier]
        main.append(f"{label} & {share(tier, '0%')} & {share(tier, '1%')} & {share(tier, '2%')} & "
                    f"{v['H-A3a'][tier]['cost_cells']} ({v['H-A3a'][tier]['reference_cost_cells']}) & "
                    f"{sum(x['verdict'] == 'detects' for x in det)}/{len(det)} \\\\")
    main += [r"\midrule",
             r"\multicolumn{6}{@{}l}{\emph{(B) Tier-2 LSTM, against S2}} \\",
             r"Policy & Models & Parameters & Cost & Max ratio & Macro${<}0$ \\", r"\midrule"]
    for name, label in (("S2", "S2 (independent)"), ("M1", "M1 (one shared)"), ("G-share@1%", r"G-share, $\tau{=}1\%$"),
                        ("G-group@1%", r"G-group, $\tau{=}1\%$"), ("G-group@2%", r"G-group, $\tau{=}2\%$"),
                        ("oracle-group", "Oracle grouping")):
        rs = sel("tier2", name, "LSTM")
        main.append(f"{label} & {models('tier2', name, 'LSTM'):.1f} & {params(name)} & {cost(rs)} & "
                    f"{max(r['median_ratio_vs_S2'] for r in rs):.3f} & "
                    f"{sum(r['macro_gain_vs_S2_interval'][1] < 0 for r in rs)} \\\\")
    main += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    main_out.write_text("% Generated by manuscript/fgcs/tools/a3_numbers.py; do not edit by hand.\n" + "\n".join(main) + "\n")

    # Supplement tables.
    s = []
    s += [r"\begin{table*}[t]\let\small\footnotesize", r"\centering",
          r"\caption{Amendment A3, consolidation policies per tier and backbone: savings retained "
          r"$R=(4-\text{models})/3$ (\%) and typical-cell cost cells (policy:S2 median ratio above 1.01; "
          r"of 4 cells per block) for G-share and G-full at each tolerance, and the reference M1 cost cells. "
          r"G-ctx keeps four models and chooses S1 or S2 per resource.}",
          r"\label{tab:S-A3-gate}", r"\small",
          r"\begin{tabular}{@{}llcccccccccc@{}}", r"\toprule",
          r" & & \multicolumn{4}{c}{G-share $R$ (cost) at $\tau$} & \multicolumn{4}{c}{G-full $R$ (cost) at $\tau$} & M1 & G-ctx \\",
          r"\cmidrule(lr){3-6}\cmidrule(lr){7-10}",
          r"Tier & Backbone, block & 0 & 0.5\% & 1\% & 2\% & 0 & 0.5\% & 1\% & 2\% & cost & cost \\", r"\midrule"]
    frames = [("tier1", "LSTM", b) for b in ("TimeTrack", "fastStorage", "Rnd", "Materna-T1", "Materna-T2", "Materna-T3")]
    frames += [("tier2", bb, b) for bb in ("LSTM", "DLinear", "PatchTST", "iTransformer") for b in ("fastStorage", "Rnd")]
    for tier, backbone, block in frames:
        def frame_models(policy):
            (summary,) = [x for x in summaries if x["tier"] == tier and x["policy"] == policy
                          and x["backbone"] == backbone and x["block"] == block]
            return summary["mean_models"]
        cells = []
        for family in ("G-share", "G-full"):
            for t in ("0%", "0.5%", "1%", "2%"):
                name = f"{family}@{t}"
                cells.append(f"{pct((4 - frame_models(name)) / 3)} ({cost(sel(tier, name, backbone, block))})")
        ctx = sel(tier, "G-ctx", backbone, block)
        s.append(f"{'1' if tier == 'tier1' else '2'} & {BACKBONE_LABEL[backbone]}, {block} & " + " & ".join(cells)
                 + f" & {cost(sel(tier, 'M1', backbone, block))} & {cost(ctx) if ctx else '--'} \\\\")
    s += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]

    s += [r"\begin{table}[t]\let\small\footnotesize", r"\centering",
          r"\caption{Amendment A3, H-A3b: rank correlation between the unit-level validation score and the "
          r"outer-test score of M1 against S2 (machine $\times$ fold $\times$ seed units), with VM-cluster "
          r"interval, the share of units in which M1 was worse on validation and on the outer test, and the "
          r"balanced accuracy of the validation sign.}",
          r"\label{tab:S-A3-detect}", r"\small", r"\setlength{\tabcolsep}{2.5pt}",
          r"\begin{tabular}{@{}lcccc@{}}", r"\toprule",
          r"Frame & $\rho$ [95\% interval] & Val./test worse & Bal. acc. & Verdict \\", r"\midrule"]
    for x in detection:
        label = f"{'T1' if x['tier'] == 'tier1' else 'T2'} {BACKBONE_LABEL[x['backbone']] if x['tier'] == 'tier2' else ''} {x['block']}".replace("  ", " ")
        s.append(f"{label} & {x['rho']:.2f} [{x['interval'][0]:.2f}, {x['interval'][1]:.2f}] & "
                 f"{pct(x['validation_worse_share'])}/{pct(x['outer_worse_share'])}\\% & {x['balanced_accuracy']:.2f} & "
                 f"{x['verdict']} \\\\")
    s += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    s += [r"\begin{table*}[t]\let\small\footnotesize", r"\centering",
          r"\caption{Amendment A3, tier-2 LSTM: G-group at $\tau=1\%$ and full sharing M1 against S2 per block and "
          r"resource: matched-cell median MAE ratio [VM-cluster interval], win rate, MacroMAE gain (\%) "
          r"[interval], and the share of units in which the resource stays in its own S2 model.}",
          r"\label{tab:S-A3-group}", r"\small",
          r"\begin{tabular}{@{}llccccc@{}}", r"\toprule",
          r"Block & Resource & G-group ratio & Win & G-group gain & Own model & M1 ratio / gain \\", r"\midrule"]
    for block in ("fastStorage", "Rnd"):
        for resource in ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE"):
            (g,) = [r for r in sel("tier2", "G-group@1%", "LSTM", block) if r["resource"] == resource]
            (m,) = [r for r in sel("tier2", "M1", "LSTM", block) if r["resource"] == resource]
            gi, gg = g["median_ratio_vs_S2_interval"], g["macro_gain_vs_S2_interval"]
            s.append(f"{block if resource == 'CPU' else ''} & {RESOURCE_LABEL[resource]} & "
                     f"{g['median_ratio_vs_S2']:.3f} [{gi[0]:.3f}, {gi[1]:.3f}] & {g['win_rate_vs_S2']:.2f} & "
                     f"${g['macro_gain_vs_S2_percent']:+.2f}$ [${gg[0]:+.2f}$, ${gg[1]:+.2f}$] & "
                     f"{pct(g['share_assigned'].get('S2', 0.0))}\\% & "
                     f"{m['median_ratio_vs_S2']:.3f} / ${m['macro_gain_vs_S2_percent']:+.2f}$ \\\\")
    s += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]

    s += [r"\begin{table}[t]\let\small\footnotesize", r"\centering",
          r"\caption{Amendment A3, tier-2 LSTM: each of the 15 groupings applied to every unit (descriptive). "
          r"Groups, cost cells and largest median ratio against S2 (of 8 cells), and the lowest MacroMAE gain (\%).}",
          r"\label{tab:S-A3-partitions}", r"\small", r"\setlength{\tabcolsep}{2.5pt}",
          r"\begin{tabular}{@{}lcccc@{}}", r"\toprule",
          r"Grouping & Groups & Cost & Max ratio & Lowest gain \\", r"\midrule"]
    short = {"CPU": "C", "THROUGHPUT": "T", "MEMORY": "M", "DISK_WRITE": "D"}
    partitions = sorted({r["policy"] for r in rows if r["policy"].startswith("partition:")},
                        key=lambda p: (p.count("|"), p))
    for p in partitions:
        rs = sel("tier2", p, "LSTM")
        label = " $\\mid$ ".join("".join(short[t] for t in g.split("+")) for g in p[len("partition:"):].split(" | "))
        s.append(f"{label} & {p.count('|') + 1} & {cost(rs)} & {max(r['median_ratio_vs_S2'] for r in rs):.3f} & "
                 f"${min(r['macro_gain_vs_S2_percent'] for r in rs):+.2f}$ \\\\")
    s += [r"\bottomrule", r"\end{tabular}", "",
          r"\vspace{2pt}\parbox{\columnwidth}{\footnotesize C, T, M, D: CPU, throughput, memory, disk write; "
          r"letters in one group share a model.}", r"\end{table}", ""]

    s += [r"\begin{table}[t]\let\small\footnotesize", r"\centering",
          r"\caption{Amendment A3, persistence fallback (tier~2): persistence skill of S2 and of S2 with the "
          r"validation-selected fallback for CPU and throughput, and the share of units sent to persistence.}",
          r"\label{tab:S-A3-fallback}", r"\small", r"\setlength{\tabcolsep}{2.5pt}",
          r"\begin{tabular}{@{}llccc@{}}", r"\toprule",
          r"Backbone, block & Resource & S2 & S2+fallback & Fallback units \\", r"\midrule"]
    for backbone in ("LSTM", "DLinear", "PatchTST", "iTransformer"):
        for block in ("fastStorage", "Rnd"):
            for resource in ("CPU", "THROUGHPUT"):
                (a,) = [r for r in sel("tier2", "S2", backbone, block) if r["resource"] == resource]
                (b,) = [r for r in sel("tier2", "S2+fallback", backbone, block) if r["resource"] == resource]
                s.append(f"{BACKBONE_LABEL[backbone]}, {block} & {RESOURCE_LABEL[resource]} & "
                         f"${a['persistence_skill']:+.3f}$ & ${b['persistence_skill']:+.3f}$ & "
                         f"{pct(b['share_assigned'].get('persistence', 0.0))}\\% \\\\")
    s += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    supplement_out.write_text("% Generated by manuscript/fgcs/tools/a3_numbers.py; do not edit by hand.\n" + "\n".join(s))


if __name__ == "__main__":
    main()
