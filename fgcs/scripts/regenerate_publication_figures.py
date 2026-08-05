#!/usr/bin/env python3
"""Regenerate publication figures from frozen final CSV artifacts only."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
FGCS = Path(__file__).resolve().parents[1]
AGG = ROOT / "results" / "final" / "aggregate"
ROB = ROOT / "results" / "final" / "robustness" / "04_robustness_statistics"
STATS = ROOT / "results" / "final" / "packs" / "06_supporting_statistics" / "metrics"
FIGS = FGCS / "figs"
SUP = FIGS / "supplementary"

# Colorblind-safe model palette (consistent across figures)
COLORS = {
    "persistence": "#000000",
    "ewma": "#4D4D4D",
    "ridge": "#0072B2",
    "lightgbm": "#E69F00",
    "dlinear": "#009E73",
}
MARKERS = {
    "independent": "o",
    "bottom_up": "s",
    "wls": "^",
    "mint": "D",
    "top_down": "v",
}
METHOD_LABEL = {
    "independent": "Independent",
    "bottom_up": "Bottom-up",
    "wls": "WLS",
    "mint": "MinT",
    "top_down": "Top-down",
}


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", alpha=0.25, linewidth=0.6)
    ax.tick_params(labelsize=8)


def save(fig, name: Path):
    name.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(name, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", name.relative_to(FGCS))


def fig_architecture():
    fig, ax = plt.subplots(figsize=(3.45, 2.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8.0)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.015,rounding_size=0.05",
                facecolor=fc,
                edgecolor=ec,
                linewidth=1.0,
                zorder=2,
            )
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.5, zorder=3)

    # Row 1: observations
    box(0.4, 6.3, 4.2, 1.3, "Observed machine telemetry\n(7 nodes)", "#F4F7FA", "#2F5D8C")
    box(5.4, 6.3, 4.2, 1.3, "Observed cluster aggregate\n(exact sum / weighted)", "#F4F7FA", "#2F5D8C")
    # Row 2: independent forecasts (full width)
    box(0.4, 4.2, 9.2, 1.3, "Independent forecasts at machine and cluster levels\n(may violate summing constraints)", "#FFF4E5", "#B36B00")
    # Row 3: S and reconciliation side-by-side with gap
    box(0.4, 2.2, 4.2, 1.4, "Summing matrix $S$\nCPU / memory / disk\nexact relations", "#F7F0FA", "#6A3D9A")
    box(5.4, 2.2, 4.2, 1.4, "Reconciliation\nBU / WLS / MinT\n(+ TD for disk)", "#EAF7EA", "#2E7D32")
    # Row 4: coherent outputs
    box(2.0, 0.3, 6.0, 1.3, "Coherent forecasts: top + bottoms\n(exact $S$-consistency)", "#EAF7EA", "#2E7D32")
    ax.annotate("", xy=(2.5, 5.5), xytext=(2.5, 6.3), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    ax.annotate("", xy=(7.5, 5.5), xytext=(7.5, 6.3), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    ax.annotate("", xy=(5.0, 3.6), xytext=(5.0, 4.2), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    ax.annotate("", xy=(2.5, 2.2), xytext=(2.5, 3.6), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    ax.annotate("", xy=(7.5, 2.2), xytext=(7.5, 3.6), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    ax.annotate("", xy=(5.0, 1.6), xytext=(2.5, 2.2), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    ax.annotate("", xy=(5.0, 1.6), xytext=(7.5, 2.2), arrowprops=dict(arrowstyle="->", lw=1.0, color="#333"))
    save(fig, FIGS / "architecture_or_hierarchy.pdf")


def fig_cpu_accuracy():
    cpu = pd.read_csv(AGG / "tables" / "table02_cpu_forecasting_results.csv")
    seed = pd.read_csv(AGG / "tables" / "table05_seed_robustness.csv")
    fig, ax = plt.subplots(figsize=(3.45, 2.4))
    series = [
        ("persistence", "independent", "Persistence", "-", COLORS["persistence"]),
        ("ewma", "independent", "EWMA", "--", COLORS["ewma"]),
        ("ridge", "independent", "Ridge", "-.", COLORS["ridge"]),
        ("lightgbm", "independent", "LightGBM", "-", COLORS["lightgbm"]),
        ("lightgbm", "mint", "LightGBM + MinT", "--", COLORS["lightgbm"]),
        ("dlinear", "independent", "DLinear", "-", COLORS["dlinear"]),
    ]
    for model, method, label, ls, color in series:
        g = cpu[(cpu.base_model == model) & (cpu.reconciliation_method == method)].groupby("horizon").mae.mean()
        ax.plot(g.index, g.values, ls=ls, color=color, marker="o", ms=3.5, label=label, lw=1.2)
        if model == "dlinear":
            ss = seed[(seed.hierarchy == "cpu_core_weighted") & (seed.model == "dlinear") & (seed.method == method)]
            if len(ss):
                band = ss.groupby("horizon").agg(lo=("min_mae", "mean"), hi=("max_mae", "mean"))
                ax.fill_between(band.index, band.lo, band.hi, color=color, alpha=0.15, linewidth=0)
    ax.set_xlabel("Horizon")
    ax.set_ylabel("MAE (weighted-mean %)")
    ax.set_xticks([1, 8, 16])
    style_axes(ax)
    ax.legend(fontsize=6, frameon=False, loc="upper left")
    save(fig, FIGS / "cpu_accuracy_vs_horizon.pdf")


def fig_seed_recon():
    rel = pd.read_csv(ROB / "metrics" / "robustness_relative_effects.csv")
    sub = rel[
        (rel.hierarchy == "cpu_core_weighted")
        & (rel.model_a == rel.model_b)
        & (rel.method_b == "independent")
        & (rel.method_a.isin(["bottom_up", "wls", "mint"]))
        & (rel.model_a.isin(["lightgbm", "dlinear"]))
    ].copy()
    g = sub.groupby(["model_a", "method_a", "seed"], as_index=False).relative_mae_diff.mean()
    fig, ax = plt.subplots(figsize=(3.45, 2.4))
    x_methods = ["bottom_up", "wls", "mint"]
    x = np.arange(len(x_methods))
    offsets = {-0.2: 0, 0.0: 1, 0.2: 2}
    for model, color in [("lightgbm", COLORS["lightgbm"]), ("dlinear", COLORS["dlinear"])]:
        for seed in [0, 1, 2]:
            vals = []
            for m in x_methods:
                row = g[(g.model_a == model) & (g.method_a == m) & (g.seed == seed)]
                vals.append(float(row.relative_mae_diff.iloc[0]) * 100 if len(row) else np.nan)
            ax.plot(
                x + (seed - 1) * 0.08,
                vals,
                marker=MARKERS[["bottom_up", "wls", "mint"][0]] if False else "o",
                ms=4,
                color=color,
                alpha=0.35 + 0.25 * seed,
                lw=1.0,
                label=f"{'LightGBM' if model=='lightgbm' else 'DLinear'} seed {seed}",
            )
    # emphasize LightGBM invariance by plotting mean as dashed
    lg = g[g.model_a == "lightgbm"].groupby("method_a").relative_mae_diff.mean()
    ax.plot(x, [lg[m] * 100 for m in x_methods], "s--", color=COLORS["lightgbm"], ms=5, lw=1.3, label="LightGBM mean (identical)")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABEL[m] for m in x_methods])
    ax.set_ylabel("Relative MAE vs independent (%)")
    style_axes(ax)
    ax.legend(fontsize=5.5, frameon=False, ncol=1, loc="lower right")
    save(fig, FIGS / "cpu_reconciliation_effect_by_seed.pdf")


def fig_coherence():
    cpu = pd.read_csv(AGG / "tables" / "table02_cpu_forecasting_results.csv")
    # Main: LightGBM and Ridge only (no OLS). Use log10(error + eps).
    eps = 1e-3
    methods = ["independent", "bottom_up", "wls", "mint"]
    models = ["ridge", "lightgbm"]
    fig, ax = plt.subplots(figsize=(3.45, 2.5))
    width = 0.18
    xpos = np.arange(len(methods))
    for i, model in enumerate(models):
        before, after = [], []
        for m in methods:
            g = cpu[(cpu.base_model == model) & (cpu.reconciliation_method == m)]
            before.append(g.coherence_before.mean())
            after.append(g.coherence_after.mean())
        bx = xpos + (i - 0.5) * width
        ax.plot(bx, np.log10(np.array(before) + eps), "o", color=COLORS[model], ms=5, label=f"{model.capitalize()} before")
        ax.plot(bx, np.log10(np.array(after) + eps), "x", color=COLORS[model], ms=5, label=f"{model.capitalize()} after")
        for j, (b, a) in enumerate(zip(before, after)):
            ax.plot([bx[j], bx[j]], [np.log10(b + eps), np.log10(a + eps)], color=COLORS[model], lw=0.9, alpha=0.7)
            if a == 0 and methods[j] != "independent":
                ax.text(bx[j], np.log10(eps) + 0.15, "exact 0", ha="center", va="bottom", fontsize=5.5, color=COLORS[model])
    ax.axhline(np.log10(eps), color="0.5", ls=":", lw=0.7)
    ax.set_xticks(xpos)
    ax.set_xticklabels([METHOD_LABEL[m] for m in methods], fontsize=7)
    ax.set_ylabel(r"$\log_{10}(\mathrm{error}+\varepsilon)$, $\varepsilon=10^{-3}$")
    style_axes(ax)
    ax.legend(fontsize=5.5, frameon=False, ncol=2)
    save(fig, FIGS / "coherence_before_after.pdf")


def fig_memory_vs_ewma():
    rel = pd.read_csv(ROB / "metrics" / "robustness_relative_effects.csv")
    # Correct aggregation: model+method vs EWMA independent
    sub = rel[(rel.hierarchy == "memory_um") & (rel.model_b == "ewma") & (rel.method_b == "independent")]
    focus = sub[sub.model_a.isin(["dlinear", "lightgbm"])].copy()
    g = focus.groupby(["model_a", "method_a", "seed"], as_index=False).relative_mae_diff.mean()
    fig, ax = plt.subplots(figsize=(3.45, 2.5))
    # Panel-like grouping on x
    keys = [
        ("dlinear", "independent"),
        ("dlinear", "wls"),
        ("dlinear", "mint"),
        ("lightgbm", "independent"),
    ]
    x = np.arange(len(keys))
    for seed in [0, 1, 2]:
        ys = []
        for model, method in keys:
            row = g[(g.model_a == model) & (g.method_a == method) & (g.seed == seed)]
            ys.append(float(row.relative_mae_diff.iloc[0]) * 100 if len(row) else np.nan)
        ax.plot(x, ys, marker="o", ms=4, lw=1.0, label=f"Seed {seed}")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(["DLinear\nindep.", "DLinear\nWLS", "DLinear\nMinT", "LightGBM\nindep."], fontsize=6.5)
    ax.set_ylabel("Relative MAE vs EWMA (%)")
    style_axes(ax)
    ax.legend(fontsize=6, frameon=False)
    save(fig, FIGS / "memory_reconciliation_vs_ewma.pdf")


def fig_disk():
    disk = pd.read_csv(AGG / "tables" / "table04_disk_boundary.csv")
    fig, ax = plt.subplots(figsize=(3.45, 2.5))
    ridge = (
        disk[disk.base_model == "ridge"]
        .groupby("reconciliation_method")
        .mae.mean()
        .reindex(["independent", "bottom_up", "top_down", "wls", "mint"])
    )
    pers = disk[disk.base_model == "persistence"].mae.mean()
    ewma = disk[disk.base_model == "ewma"].mae.mean()
    x = np.arange(len(ridge))
    colors = ["#0072B2", "#D55E00", "#56B4E9", "#CC79A7", "#009E73"]
    ax.bar(x, ridge.values / 1e9, color=colors, width=0.7)
    ax.axhline(pers / 1e9, color="k", ls="-", lw=1.2, label="Persistence")
    ax.axhline(ewma / 1e9, color="k", ls="--", lw=1.2, label="EWMA")
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABEL[m] for m in ridge.index], rotation=20, ha="right", fontsize=7)
    ax.set_ylabel(r"MAE ($\times 10^9$ disk units)")
    style_axes(ax)
    ax.legend(fontsize=6, frameon=False)
    save(fig, FIGS / "disk_boundary.pdf")


def fig_bootstrap_main_and_supp():
    rel = pd.read_csv(ROB / "metrics" / "robustness_relative_effects.csv")
    # Main: claim-relevant comparisons only
    wanted = [
        ("cpu_core_weighted", "lightgbm", "independent", "ridge", "independent", "LGBM indep. vs Ridge"),
        ("cpu_core_weighted", "lightgbm", "mint", "lightgbm", "independent", "LGBM MinT vs indep."),
        ("cpu_core_weighted", "dlinear", "bottom_up", "dlinear", "independent", "DLinear BU vs indep."),
        ("memory_um", "dlinear", "wls", "dlinear", "independent", "DLinear WLS vs indep."),
        ("memory_um", "dlinear", "wls", "ewma", "independent", "DLinear WLS vs EWMA"),
        ("memory_um", "lightgbm", "independent", "ewma", "independent", "LGBM vs EWMA"),
    ]
    rows = []
    for hier, ma, mta, mb, mtb, label in wanted:
        s = rel[
            (rel.hierarchy == hier)
            & (rel.model_a == ma)
            & (rel.method_a == mta)
            & (rel.model_b == mb)
            & (rel.method_b == mtb)
        ]
        if not len(s):
            continue
        rows.append(
            {
                "label": label,
                "rel": s.relative_mae_diff.mean() * 100,
                "lo": s.rel_ci_low.mean() * 100,
                "hi": s.rel_ci_high.mean() * 100,
            }
        )
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(3.45, 2.8))
    y = np.arange(len(df))[::-1]
    ax.axvline(0, color="k", lw=0.7)
    ax.hlines(y, df.lo, df.hi, color="#444", lw=1.2)
    ax.plot(df.rel, y, "o", color="#D55E00", ms=4.5)
    ax.set_yticks(y)
    ax.set_yticklabels(df.label, fontsize=6.5)
    ax.set_xlabel("Relative MAE effect (%); negative favors first method")
    style_axes(ax)
    ax.grid(True, axis="x", alpha=0.25)
    save(fig, FIGS / "bootstrap_relative_effects.pdf")

    # Supplementary fuller forest
    g = (
        rel.groupby(["hierarchy", "model_a", "method_a", "model_b", "method_b"], as_index=False)
        .agg(rel=("relative_mae_diff", "mean"), lo=("rel_ci_low", "mean"), hi=("rel_ci_high", "mean"))
        .head(30)
    )
    fig, ax = plt.subplots(figsize=(6.5, 7.5))
    y = np.arange(len(g))[::-1]
    ax.axvline(0, color="k", lw=0.7)
    ax.hlines(y, g.lo * 100, g.hi * 100, color="#456", lw=1.0)
    ax.plot(g.rel * 100, y, "o", color="#c45", ms=3.5)
    labels = [
        f"{a} {METHOD_LABEL.get(b,b)} vs {c} {METHOD_LABEL.get(d,d)} ({h.replace('_',' ')})"
        for h, a, b, c, d in zip(g.hierarchy, g.model_a, g.method_a, g.model_b, g.method_b)
    ]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xlabel("Relative MAE effect (%)")
    style_axes(ax)
    save(fig, SUP / "bootstrap_relative_effects_full.pdf")


def fig_tradeoff():
    tb = pd.read_csv(STATS / "top_bottom_tradeoff.csv")
    # Main-paper single-column stacked panels
    fig, axes = plt.subplots(2, 1, figsize=(3.45, 4.6))
    for ax, hiers, title in [
        (axes[0], ["cpu_core_weighted", "memory_um"], "CPU and memory"),
        (axes[1], ["disk_ud"], "Disk boundary"),
    ]:
        for hier, marker in zip(hiers, ["o", "s"][: len(hiers)]):
            s = tb[tb.hierarchy == hier]
            if "base_model" in s.columns:
                s = s[s.base_model != "lightgbm"] if hier == "disk_ud" else s
            ax.scatter(s.macro_rel * 100, s.top_rel * 100, marker=marker, alpha=0.75, s=22, label=hier.replace("_", " "))
        ax.axhline(0, color="k", lw=0.5)
        ax.axvline(0, color="k", lw=0.5)
        ax.set_xlabel("Bottom macro relative MAE (%)")
        ax.set_ylabel("Top relative MAE (%)")
        ax.set_title(title, fontsize=9)
        ax.text(0.02, 0.98, "Desired:\ntop↓ bottom↓", transform=ax.transAxes, va="top", fontsize=6, color="#009E73")
        style_axes(ax)
        ax.legend(fontsize=6, frameon=False)
    fig.tight_layout()
    save(fig, FIGS / "top_bottom_tradeoff.pdf")
    # Wide supplementary copy
    fig2, axes2 = plt.subplots(1, 2, figsize=(7.0, 2.7))
    for ax, hiers, title in [
        (axes2[0], ["cpu_core_weighted", "memory_um"], "CPU and memory"),
        (axes2[1], ["disk_ud"], "Disk boundary"),
    ]:
        for hier, marker in zip(hiers, ["o", "s"][: len(hiers)]):
            s = tb[tb.hierarchy == hier]
            if "base_model" in s.columns:
                s = s[s.base_model != "lightgbm"] if hier == "disk_ud" else s
            ax.scatter(s.macro_rel * 100, s.top_rel * 100, marker=marker, alpha=0.75, s=22, label=hier.replace("_", " "))
        ax.axhline(0, color="k", lw=0.5)
        ax.axvline(0, color="k", lw=0.5)
        ax.set_xlabel("Bottom macro relative MAE (%)")
        ax.set_ylabel("Top relative MAE (%)")
        ax.set_title(title, fontsize=9)
        ax.text(0.02, 0.98, "Desired:\ntop↓ bottom↓", transform=ax.transAxes, va="top", fontsize=6, color="#009E73")
        style_axes(ax)
        ax.legend(fontsize=6, frameon=False)
    fig2.tight_layout()
    save(fig2, SUP / "top_bottom_tradeoff_wide.pdf")


def fig_cpu_peaks():
    """Single-column stacked q90/q95 panels for cas-dc column width."""
    t8 = pd.read_csv(AGG / "tables" / "table08_peak_operational_evidence.csv")
    fig, axes = plt.subplots(2, 1, figsize=(3.45, 4.6), sharex=False)
    methods = ["independent", "bottom_up", "wls", "mint"]
    for ax, thr in zip(axes, ["q90", "q95"]):
        s = t8[(t8.hierarchy == "cpu_core_weighted") & (t8.threshold == thr)]
        for model in ["persistence", "ridge", "lightgbm", "dlinear"]:
            for method in methods:
                m = s[(s.base_model == model) & (s.method == method)]
                if not len(m):
                    continue
                ax.scatter(
                    m.recall,
                    m.high_load_mae,
                    c=COLORS[model],
                    marker=MARKERS.get(method, "o"),
                    s=26,
                    alpha=0.85,
                )
        ax.set_title(f"CPU high-load {thr}", fontsize=9)
        ax.set_xlabel("Recall")
        ax.set_ylabel("High-load MAE")
        style_axes(ax)
    from matplotlib.lines import Line2D

    model_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS[m], markersize=6, label=m)
        for m in ["persistence", "ridge", "lightgbm", "dlinear"]
    ]
    method_handles = [
        Line2D([0], [0], marker=MARKERS[m], color="k", linestyle="None", markersize=6, label=METHOD_LABEL[m])
        for m in ["independent", "bottom_up", "wls", "mint"]
    ]
    axes[0].legend(handles=model_handles, fontsize=5.5, frameon=False, title="Model", title_fontsize=6, loc="best")
    axes[1].legend(handles=method_handles, fontsize=5.5, frameon=False, title="Method", title_fontsize=6, loc="best")
    fig.tight_layout()
    save(fig, FIGS / "cpu_peak_results.pdf")
    # Keep a wide supplementary copy for the full side-by-side view
    fig2, axes2 = plt.subplots(1, 2, figsize=(7.0, 2.7))
    for ax, thr in zip(axes2, ["q90", "q95"]):
        s = t8[(t8.hierarchy == "cpu_core_weighted") & (t8.threshold == thr)]
        for model in ["persistence", "ridge", "lightgbm", "dlinear"]:
            for method in methods:
                m = s[(s.base_model == model) & (s.method == method)]
                if not len(m):
                    continue
                ax.scatter(
                    m.recall,
                    m.high_load_mae,
                    c=COLORS[model],
                    marker=MARKERS.get(method, "o"),
                    s=28,
                    alpha=0.85,
                )
        ax.set_title(f"CPU high-load {thr}", fontsize=9)
        ax.set_xlabel("Recall")
        ax.set_ylabel("High-load MAE")
        style_axes(ax)
    axes2[0].legend(handles=model_handles, fontsize=6, frameon=False, title="Model", title_fontsize=6, loc="best")
    axes2[1].legend(handles=method_handles, fontsize=6, frameon=False, title="Method", title_fontsize=6, loc="best")
    fig2.tight_layout()
    save(fig2, SUP / "cpu_peak_results_wide.pdf")


def fig_dlinear_bias():
    """Single-column stacked bias panels; wide copy in supplementary."""
    pc = pd.read_csv(ROB / "metrics" / "dlinear_peak_compression.csv")
    mem = pc[pc.hierarchy == "memory_um"]
    methods = ["independent", "bottom_up", "wls", "mint"]
    colors = [COLORS["dlinear"], "#56B4E9", "#CC79A7", "#E69F00"]

    fig, axes = plt.subplots(2, 1, figsize=(3.45, 4.4))
    for ax, thr in zip(axes, ["q90", "q95"]):
        g = mem[mem.threshold_name == thr].groupby(["seed", "method"]).signed_bias.mean().unstack()
        g = g.reindex(columns=methods)
        g.plot(kind="bar", ax=ax, color=colors, width=0.8)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"DLinear memory peak bias ({thr})", fontsize=9)
        ax.set_xlabel("Seed")
        ax.set_ylabel("Signed bias (bytes)")
        ax.legend([METHOD_LABEL[m] for m in methods], fontsize=5.5, frameon=False)
        style_axes(ax)
        ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    save(fig, FIGS / "dlinear_memory_peak_bias_by_seed.pdf")

    fig2, axes2 = plt.subplots(1, 2, figsize=(7.0, 2.7))
    for ax, thr in zip(axes2, ["q90", "q95"]):
        g = mem[mem.threshold_name == thr].groupby(["seed", "method"]).signed_bias.mean().unstack()
        g = g.reindex(columns=methods)
        g.plot(kind="bar", ax=ax, color=colors, width=0.8)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"DLinear memory peak bias ({thr})", fontsize=9)
        ax.set_xlabel("Seed")
        ax.set_ylabel("Signed bias (bytes)")
        ax.legend([METHOD_LABEL[m] for m in methods], fontsize=5.5, frameon=False)
        style_axes(ax)
        ax.tick_params(axis="x", rotation=0)
    fig2.tight_layout()
    save(fig2, SUP / "dlinear_memory_peak_bias_wide.pdf")


def fig_memory_accuracy_supp():
    mem = pd.read_csv(AGG / "tables" / "table03_memory_forecasting_results.csv")
    fig, ax = plt.subplots(figsize=(3.45, 2.4))
    for model, method, label, ls, color in [
        ("persistence", "independent", "Persistence", "-", COLORS["persistence"]),
        ("ewma", "independent", "EWMA", "-", COLORS["ewma"]),
        ("ridge", "independent", "Ridge", "--", COLORS["ridge"]),
        ("dlinear", "independent", "DLinear", "-", COLORS["dlinear"]),
        ("dlinear", "mint", "DLinear + MinT", "--", COLORS["dlinear"]),
        ("lightgbm", "independent", "LightGBM", ":", COLORS["lightgbm"]),
    ]:
        # Prefer seed_mean when present
        g = mem[(mem.base_model == model) & (mem.reconciliation_method == method)]
        vals = g.groupby("horizon")["seed_mean"].mean() if "seed_mean" in g else g.groupby("horizon").mae.mean()
        ax.plot(vals.index, vals.values / 1e9, ls=ls, color=color, marker="o", ms=3, label=label, lw=1.1)
    ax.set_xlabel("Horizon")
    ax.set_ylabel(r"MAE ($\times 10^9$ bytes)")
    ax.set_xticks([1, 8, 16])
    style_axes(ax)
    ax.legend(fontsize=6, frameon=False)
    save(fig, SUP / "memory_accuracy_vs_horizon.pdf")


def main():
    SUP.mkdir(parents=True, exist_ok=True)
    fig_architecture()
    fig_cpu_accuracy()
    fig_seed_recon()
    fig_coherence()
    fig_memory_vs_ewma()
    fig_disk()
    fig_bootstrap_main_and_supp()
    fig_tradeoff()
    fig_cpu_peaks()
    fig_dlinear_bias()
    fig_memory_accuracy_supp()
    # Keep method_selection_map.pdf as a non-main artifact note file removed from main
    # Write a tiny placeholder stating converted to table (optional PDF not used)
    print("regenerate_publication_figures: OK")


if __name__ == "__main__":
    main()
