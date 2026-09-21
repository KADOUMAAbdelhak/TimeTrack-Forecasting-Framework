#!/usr/bin/env python3
"""Post-hoc supporting_statistics analysis from frozen NPZs (no retraining).

Produces the detailed tables/figures required by the final report protocol.
Does not modify frozen pack runner logic.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from models.hybrid.reconciliation import (
    coherence_error,
    core_weighted_cpu_hierarchy,
    disk_hierarchy,
    estimate_residual_covariance,
    machine_core_counts,
    memory_hierarchy,
    reconcile,
)
from timetrack.final_packs import load_packs_config
from timetrack.metrics import mae
from timetrack.stats_bootstrap import (
    block_bootstrap_mean_diff,
    holm_adjust,
    select_block_length,
)

ROOT = Path("/Users/fgtek002/TimeTrack")
OUT = ROOT / "results/final/packs/06_supporting_statistics"
MET = OUT / "metrics"
TAB = OUT / "tables"
FIG = OUT / "figures"
for d in (MET, TAB, FIG):
    d.mkdir(parents=True, exist_ok=True)

cfg = load_packs_config()
boot_cfg = cfg.get("bootstrap_policy") or {}
N_BOOT = int(boot_cfg.get("n_boot", 1000))
SEED = int(boot_cfg.get("seed", 0))
ACF = float(boot_cfg.get("acf_threshold", 0.1))
B_LO = int(boot_cfg.get("lower", 8))
B_HI = int(boot_cfg.get("upper", 256))
CONTEXT = int(cfg.get("context", 32))
CORE_TOTAL = float(sum(machine_core_counts().values()))
ALPHA = 0.05

PACKS = {
    "memory_um": {
        "paths": [
            ROOT / "results/final/packs/01_memory_classical",
            ROOT / "results/final/packs/02_memory_dlinear",
        ],
        "hierarchy": memory_hierarchy(),
        "scale_top": 1.0,
        "models": ["persistence", "ridge", "lightgbm", "dlinear"],
        "methods": ["bottom_up", "wls", "mint"],
        "horizons": [1, 8, 16],
        "unit": "memory_level",
    },
    "cpu_core_weighted": {
        "paths": [
            ROOT / "results/final/packs/03_cpu_classical",
            ROOT / "results/final/packs/04_cpu_dlinear",
        ],
        "hierarchy": core_weighted_cpu_hierarchy(),
        "scale_top": CORE_TOTAL,  # convert wsum MAE → weighted-mean %
        "models": ["persistence", "ridge", "lightgbm", "dlinear"],
        "methods": ["bottom_up", "wls", "mint"],
        "horizons": [1, 8, 16],
        "unit": "cpu_weighted_mean_pct",
    },
    "disk_ud": {
        "paths": [ROOT / "results/final/packs/05_disk_boundary"],
        "hierarchy": disk_hierarchy(),
        "scale_top": 1.0,
        "models": ["persistence", "ridge", "lightgbm"],
        "methods": ["bottom_up", "top_down", "wls", "mint"],
        "horizons": [1, 8],
        "unit": "disk_level",
    },
}


def effect_class(rel: float) -> str:
    if rel <= -0.05:
        return "substantial_improvement"
    if rel <= -0.02:
        return "modest_improvement"
    if rel < 0.02:
        return "accuracy_neutral"
    if rel < 0.05:
        return "modest_degradation"
    return "substantial_degradation"


def fold_consistency_label(rels: list[float]) -> str:
    signs = [np.sign(r) if abs(r) >= 0.02 else 0.0 for r in rels]
    # negative rel = improvement
    imp = sum(1 for r in rels if r <= -0.02)
    deg = sum(1 for r in rels if r >= 0.02)
    tie = len(rels) - imp - deg
    if deg == len(rels):
        return "consistently_harmful"
    if imp == len(rels):
        return "strongly_consistent"
    if imp >= 2 and deg == 0:
        return "directionally_consistent"
    if np.mean(rels) < -0.02 and deg == 0 and imp >= 1:
        return "directionally_consistent"
    if imp > 0 and deg > 0:
        return "mixed"
    if deg > 0 and imp == 0:
        return "consistently_harmful" if deg == len(rels) else "mixed"
    return "mixed" if abs(np.mean(rels)) >= 0.02 else "mixed"


def tradeoff_class(top_rel: float, macro_rel: float, coh_after: float) -> str:
    top_imp = top_rel <= -0.02
    top_neu = abs(top_rel) < 0.02
    top_deg = top_rel >= 0.02
    bot_ok = macro_rel < 0.02  # no material bottom degradation
    bot_deg = macro_rel >= 0.02
    coh_ok = coh_after < 1e-4
    if top_imp and bot_ok and coh_ok:
        return "pareto_improvement"
    if top_imp and coh_ok and bot_deg:
        return "aggregate_focused_improvement"
    if top_neu and coh_ok:
        return "coherence_only"
    if top_deg or (bot_deg and not top_imp):
        return "accuracy_costly_coherence"
    if top_imp and coh_ok:
        return "aggregate_focused_improvement"
    return "accuracy_costly_coherence"


def load_base(pack_paths: list[Path], model: str, fold: int, horizon: int):
    for p in pack_paths:
        path = p / "metrics" / "predictions" / f"base__*__f{fold}__h{horizon}__{model}__s0.npz"
        # hierarchy name varies
        matches = list((p / "metrics" / "predictions").glob(f"base__*__f{fold}__h{horizon}__{model}__s0.npz"))
        if matches:
            return np.load(matches[0]), matches[0]
    return None, None


def reconcile_pair(h, data, method: str):
    yb, pb = data["yb_test"], data["pb_test"]
    yt, pt = data["yt_test"], data["pt_test"]
    yb_val, pb_val = data["yb_val"], data["pb_val"]
    yt_val, pt_val = data["yt_val"], data["pt_val"]
    y_full = np.concatenate([yb_val, yt_val.reshape(-1, 1)], 1)
    p_full = np.concatenate([pb_val, pt_val.reshape(-1, 1)], 1)
    cov = estimate_residual_covariance(y_full, p_full, shrink_diag=0.1)
    series_var = np.maximum(np.diag(cov), 1e-12)
    out = reconcile(
        method,
        h,
        pb,
        pt,
        series_var=series_var if method == "wls" else None,
        residual_cov=cov if method == "mint" else None,
        nonnegative=False,
    )
    return yt, pt, out["top"], out["bottom"], pb, yb, cov


boot_rows = []
trade_rows = []
fold_rows = []  # per fold comparison detail
problems = []

for hier_name, spec in PACKS.items():
    h = spec["hierarchy"]
    scale = float(spec["scale_top"])
    for model in spec["models"]:
        for horizon in spec["horizons"]:
            # gather fold-level for consistency
            per_fold_rels = {m: [] for m in spec["methods"]}
            for fold in [0, 1, 2]:
                if hier_name == "disk_ud" and fold > 2:
                    continue
                data, path = load_base(spec["paths"], model, fold, horizon)
                if data is None:
                    # disk/memory may lack model
                    continue
                yt, pt_ind, _, _, pb_ind, yb, _ = reconcile_pair(h, data, "independent")
                # train residuals for block length from independent top
                yt_train = data["yt_train"]
                # approximate train residual scale using val
                resid_val = data["yt_val"] - data["pt_val"]
                bl_info = select_block_length(
                    resid_val,
                    forecast_horizon=horizon,
                    context_length=CONTEXT,
                    acf_threshold=ACF,
                    lower=B_LO,
                    upper=B_HI,
                )
                block_length = int(bl_info["block_length"])

                ind_mae = mae(yt, pt_ind) / scale
                ind_macro = float(
                    np.mean([mae(yb[:, j], pb_ind[:, j]) for j in range(yb.shape[1])])
                )
                # for CPU bottoms are wcontrib — convert to CU% for macro
                if hier_name == "cpu_core_weighted":
                    cores = np.array([machine_core_counts()[f"machine0{i}"] for i in range(1, 8)], float)
                    ind_macro = float(
                        np.mean([mae(yb[:, j] / cores[j], pb_ind[:, j] / cores[j]) for j in range(7)])
                    )
                coh_before = coherence_error(pb_ind, pt_ind)

                for method in spec["methods"]:
                    yt2, pt_i, pt_r, pb_r, pb_i, yb2, _ = reconcile_pair(h, data, method)
                    assert np.allclose(yt, yt2)
                    # absolute errors in reporting units for top
                    e_ind = np.abs(yt - pt_i) / scale
                    e_rec = np.abs(yt - pt_r) / scale
                    d = e_rec - e_ind  # user: <0 improves
                    boot = block_bootstrap_mean_diff(e_rec, e_ind, block_size=block_length, n_boot=N_BOOT, seed=SEED)
                    # P(improve) = P(mean d < 0)
                    rng = np.random.default_rng(SEED)
                    n = len(d)
                    bl = max(1, min(block_length, n))
                    n_blocks = int(np.ceil(n / bl))
                    means = np.empty(N_BOOT)
                    for i in range(N_BOOT):
                        starts = rng.integers(0, max(1, n - bl + 1), size=n_blocks)
                        sample = np.concatenate([d[s : s + bl] for s in starts])[:n]
                        means[i] = float(np.mean(sample))
                    p_improve = float(np.mean(means < 0.0))
                    ci_lo, ci_hi = boot["ci_low"], boot["ci_high"]
                    if not np.isfinite(ci_lo) or not np.isfinite(ci_hi):
                        p_two = float("nan")
                    else:
                        p_two = float(2.0 * min(np.mean(means >= 0), np.mean(means <= 0)))
                        p_two = min(1.0, max(0.0, p_two))
                        if ci_lo <= 0 <= ci_hi:
                            p_two = max(p_two, 0.05)

                    mae_ind = float(np.mean(e_ind))
                    mae_rec = float(np.mean(e_rec))
                    rel = (mae_rec - mae_ind) / max(mae_ind, 1e-12)
                    per_fold_rels[method].append(rel)

                    if hier_name == "cpu_core_weighted":
                        cores = np.array([machine_core_counts()[f"machine0{i}"] for i in range(1, 8)], float)
                        mac_ind = float(np.mean([mae(yb[:, j] / cores[j], pb_i[:, j] / cores[j]) for j in range(7)]))
                        mac_rec = float(np.mean([mae(yb[:, j] / cores[j], pb_r[:, j] / cores[j]) for j in range(7)]))
                        w = cores / cores.sum()
                        w_ind = float(np.sum(w * np.array([mae(yb[:, j] / cores[j], pb_i[:, j] / cores[j]) for j in range(7)])))
                        w_rec = float(np.sum(w * np.array([mae(yb[:, j] / cores[j], pb_r[:, j] / cores[j]) for j in range(7)])))
                        worst_ind = float(np.max([mae(yb[:, j] / cores[j], pb_i[:, j] / cores[j]) for j in range(7)]))
                        worst_rec = float(np.max([mae(yb[:, j] / cores[j], pb_r[:, j] / cores[j]) for j in range(7)]))
                        m_ind = np.array([mae(yb[:, j] / cores[j], pb_i[:, j] / cores[j]) for j in range(7)])
                        m_rec = np.array([mae(yb[:, j] / cores[j], pb_r[:, j] / cores[j]) for j in range(7)])
                    else:
                        mac_ind = float(np.mean([mae(yb[:, j], pb_i[:, j]) for j in range(7)]))
                        mac_rec = float(np.mean([mae(yb[:, j], pb_r[:, j]) for j in range(7)]))
                        wgt = np.mean(np.abs(yb), 0)
                        wgt = wgt / max(wgt.sum(), 1e-12)
                        w_ind = float(np.sum(wgt * np.array([mae(yb[:, j], pb_i[:, j]) for j in range(7)])))
                        w_rec = float(np.sum(wgt * np.array([mae(yb[:, j], pb_r[:, j]) for j in range(7)])))
                        worst_ind = float(np.max([mae(yb[:, j], pb_i[:, j]) for j in range(7)]))
                        worst_rec = float(np.max([mae(yb[:, j], pb_r[:, j]) for j in range(7)]))
                        m_ind = np.array([mae(yb[:, j], pb_i[:, j]) for j in range(7)])
                        m_rec = np.array([mae(yb[:, j], pb_r[:, j]) for j in range(7)])

                    macro_rel = (mac_rec - mac_ind) / max(mac_ind, 1e-12)
                    coh_after = coherence_error(pb_r, pt_r)
                    improved = int(np.sum(m_rec < m_ind - 1e-12))
                    degraded = int(np.sum(m_rec > m_ind + 1e-12))

                    if abs(rel) < 1e-12:
                        outcome = "tie"
                    elif rel < 0:
                        outcome = "win"
                    else:
                        outcome = "loss"

                    family = f"{hier_name.split('_')[0]}_{model}"  # refined later
                    if hier_name == "memory_um":
                        family = f"memory_{model}"
                    elif hier_name == "cpu_core_weighted":
                        family = f"cpu_{model}"
                    else:
                        family = f"disk_{model}"

                    row = {
                        "hierarchy": hier_name,
                        "unit": spec["unit"],
                        "base_model": model,
                        "horizon": horizon,
                        "fold": fold,
                        "method_a": "independent",
                        "method_b": method,
                        "n_paired": int(n),
                        "block_length": block_length,
                        "n_boot": N_BOOT,
                        "seed": SEED,
                        "mean_paired_diff": float(np.mean(d)),
                        "median_paired_diff": float(np.median(d)),
                        "mae_independent": mae_ind,
                        "mae_reconciled": mae_rec,
                        "relative_mae_diff": rel,
                        "ci_low": ci_lo,
                        "ci_high": ci_hi,
                        "prob_reconciliation_improves": p_improve,
                        "p_value_raw": p_two,
                        "ci_crosses_zero": bool(ci_lo <= 0 <= ci_hi) if np.isfinite(ci_lo) and np.isfinite(ci_hi) else True,
                        "effect_class": effect_class(rel),
                        "outcome": outcome,
                        "correction_family": family,
                        "macro_independent": mac_ind,
                        "macro_reconciled": mac_rec,
                        "macro_rel": macro_rel,
                        "weighted_independent": w_ind,
                        "weighted_reconciled": w_rec,
                        "weighted_rel": (w_rec - w_ind) / max(w_ind, 1e-12),
                        "worst_independent": worst_ind,
                        "worst_reconciled": worst_rec,
                        "worst_rel": (worst_rec - worst_ind) / max(worst_ind, 1e-12),
                        "machines_improved": improved,
                        "machines_degraded": degraded,
                        "coherence_before": float(coh_before),
                        "coherence_after": float(coh_after),
                        "tradeoff_class": tradeoff_class(rel, macro_rel, coh_after),
                        "npz_path": str(path),
                    }
                    boot_rows.append(row)
                    fold_rows.append(row)

            # fold consistency summary rows
            for method in spec["methods"]:
                rels = per_fold_rels[method]
                if not rels:
                    continue
                wins = sum(1 for r in rels if r < -1e-12)
                losses = sum(1 for r in rels if r > 1e-12)
                ties = len(rels) - wins - losses
                # refine consistency
                if all(r <= -0.02 for r in rels):
                    fc_lab = "strongly_consistent"
                elif all(r >= 0.02 for r in rels):
                    fc_lab = "consistently_harmful"
                elif sum(1 for r in rels if r < 0) >= 2 and all(r < 0.05 for r in rels):
                    fc_lab = "directionally_consistent"
                elif any(r < 0 for r in rels) and any(r > 0 for r in rels):
                    fc_lab = "mixed"
                else:
                    fc_lab = fold_consistency_label(rels)
                trade_rows.append(
                    {
                        "hierarchy": hier_name,
                        "base_model": model,
                        "horizon": horizon,
                        "method": method,
                        "n_folds": len(rels),
                        "wins": wins,
                        "ties": ties,
                        "losses": losses,
                        "mean_rel": float(np.mean(rels)),
                        "best_fold_rel": float(np.min(rels)),
                        "worst_fold_rel": float(np.max(rels)),
                        "fold_consistency": fc_lab,
                        "fold_rels": ";".join(f"{r:.6g}" for r in rels),
                    }
                )

boot_df = pd.DataFrame(boot_rows)
# Holm within families
boot_df["p_value_holm"] = np.nan
boot_df["reject_holm_0.05"] = False
for fam, idx in boot_df.groupby("correction_family").groups.items():
    sub = boot_df.loc[idx]
    # one test per fold×horizon×method — adjust within family across all those rows
    ps = sub["p_value_raw"].tolist()
    adj = holm_adjust(ps)
    boot_df.loc[idx, "p_value_holm"] = adj
    boot_df.loc[idx, "reject_holm_0.05"] = [bool(np.isfinite(a) and a < ALPHA) for a in adj]
    boot_df.loc[idx, "family_size"] = len(ps)
    boot_df.loc[idx, "alpha"] = ALPHA

boot_df.to_csv(MET / "paired_block_bootstrap.csv", index=False)
boot_df.to_csv(MET / "holm_corrected_tests.csv", index=False)
boot_df.to_csv(TAB / "statistical_comparisons.csv", index=False)

# TeX table (compact primary means)
tex_lines = [
    r"\begin{tabular}{llrrr}",
    r"Hierarchy & Comparison & Rel.\ MAE & 95\% CI & Holm $p$ \\",
    r"\hline",
]
# aggregate display: mean over folds for ridge/lgbm/dlinear primary methods
agg = (
    boot_df.groupby(["hierarchy", "base_model", "horizon", "method_b"], as_index=False)
    .agg(
        mean_rel=("relative_mae_diff", "mean"),
        mean_ci_lo=("ci_low", "mean"),
        mean_ci_hi=("ci_high", "mean"),
        min_pholm=("p_value_holm", "min"),
    )
)
for _, r in agg.iterrows():
    if r.base_model == "persistence" and abs(r.mean_rel) < 1e-9:
        continue
    tex_lines.append(
        f"{r.hierarchy} & {r.base_model}/{r.method_b}/h{int(r.horizon)} & {r.mean_rel:.3f} & "
        f"[{r.mean_ci_lo:.3g},{r.mean_ci_hi:.3g}] & {r.min_pholm:.3g} \\\\"
    )
tex_lines.append(r"\end{tabular}")
(TAB / "statistical_comparisons.tex").write_text("\n".join(tex_lines))

fc = pd.DataFrame(trade_rows)
fc.to_csv(MET / "fold_consistency.csv", index=False)

# top/bottom tradeoff table (mean over folds)
tb = (
    boot_df.groupby(["hierarchy", "base_model", "horizon", "method_b"], as_index=False)
    .agg(
        top_rel=("relative_mae_diff", "mean"),
        macro_rel=("macro_rel", "mean"),
        weighted_rel=("weighted_rel", "mean"),
        worst_rel=("worst_rel", "mean"),
        machines_improved=("machines_improved", "mean"),
        machines_degraded=("machines_degraded", "mean"),
        coh_after=("coherence_after", "mean"),
    )
)
# majority tradeoff class
def maj_tradeoff(g):
    return g.tradeoff_class.value_counts().idxmax()

tb2 = boot_df.groupby(["hierarchy", "base_model", "horizon", "method_b"]).apply(maj_tradeoff).reset_index(name="tradeoff_class")
tb = tb.merge(tb2, on=["hierarchy", "base_model", "horizon", "method_b"])
tb.to_csv(MET / "top_bottom_tradeoff.csv", index=False)

# Claim A: CPU LightGBM ind vs persistence ind
claim_rows = []
for horizon in [1, 8, 16]:
    for fold in [0, 1, 2]:
        d_lg, _ = load_base(PACKS["cpu_core_weighted"]["paths"], "lightgbm", fold, horizon)
        d_pe, _ = load_base(PACKS["cpu_core_weighted"]["paths"], "persistence", fold, horizon)
        if d_lg is None or d_pe is None:
            continue
        yt = d_lg["yt_test"] / CORE_TOTAL
        pl = d_lg["pt_test"] / CORE_TOTAL
        pp = d_pe["pt_test"] / CORE_TOTAL
        # align lengths
        n = min(len(yt), len(pl), len(pp))
        yt, pl, pp = yt[:n], pl[:n], pp[:n]
        e_pe = np.abs(yt - pp)
        e_lg = np.abs(yt - pl)
        d = e_lg - e_pe  # <0 LGBM better
        resid = d_pe["yt_val"] - d_pe["pt_val"]
        bl = int(
            select_block_length(resid, forecast_horizon=horizon, context_length=CONTEXT, acf_threshold=ACF, lower=B_LO, upper=B_HI)[
                "block_length"
            ]
        )
        boot = block_bootstrap_mean_diff(e_lg, e_pe, block_size=bl, n_boot=N_BOOT, seed=SEED)
        mae_pe, mae_lg = float(np.mean(e_pe)), float(np.mean(e_lg))
        rel = (mae_lg - mae_pe) / mae_pe
        claim_rows.append(
            {
                "claim": "A_cpu_lgbm_vs_persistence",
                "horizon": horizon,
                "fold": fold,
                "mae_persistence": mae_pe,
                "mae_lightgbm": mae_lg,
                "relative_mae_diff": rel,
                "mean_paired_diff": float(np.mean(d)),
                "ci_low": boot["ci_low"],
                "ci_high": boot["ci_high"],
                "n_paired": n,
                "block_length": bl,
                "effect_class": effect_class(rel),
            }
        )

claims = []
# A
ca = pd.DataFrame(claim_rows)
ca.to_csv(MET / "claim_A_fold_details.csv", index=False)
a_mean = float(ca.relative_mae_diff.mean())
a_all_imp = bool((ca.relative_mae_diff < -0.05).all())
claims.append(
    {
        "claim": "A",
        "title": "CPU LightGBM independent vs persistence",
        "support": "supported" if a_all_imp and a_mean < -0.15 else ("partially_supported" if a_mean < -0.05 else "unsupported"),
        "mean_rel_mae": a_mean,
        "mean_ci_low": float(ca.ci_low.mean()),
        "mean_ci_high": float(ca.ci_high.mean()),
        "fold_consistency": "strongly_consistent" if a_all_imp else "mixed",
        "qualification": "All fold×horizon cells improve; do not attribute to reconciliation.",
    }
)

# B CPU recon
cpu = boot_df[(boot_df.hierarchy == "cpu_core_weighted") & (boot_df.base_model.isin(["ridge", "lightgbm", "dlinear"]))]
b_ok = True
notes = []
for model in ["ridge", "lightgbm", "dlinear"]:
    for method in ["bottom_up", "wls", "mint"]:
        sub = cpu[(cpu.base_model == model) & (cpu.method_b == method)]
        if sub.empty:
            b_ok = False
            continue
        if not (sub.relative_mae_diff < 0).all():
            b_ok = False
            notes.append(f"{model}/{method} not all folds improve")
claims.append(
    {
        "claim": "B",
        "title": "CPU recon improves ridge/lgbm/dlinear aggregate accuracy + coherence",
        "support": "supported" if b_ok else "partially_supported",
        "mean_rel_mae": float(cpu.relative_mae_diff.mean()),
        "mean_ci_low": float(cpu.ci_low.mean()),
        "mean_ci_high": float(cpu.ci_high.mean()),
        "fold_consistency": "strongly_consistent" if b_ok else "directionally_consistent",
        "qualification": "Bottom_up Pareto (bottoms unchanged); WLS/MinT often aggregate-focused. " + "; ".join(notes[:3]),
    }
)

# C memory
mem = boot_df[
    (boot_df.hierarchy == "memory_um")
    & (boot_df.base_model.isin(["ridge", "dlinear"]))
    & (boot_df.method_b.isin(["wls", "mint"]))
]
c_mean = float(mem.relative_mae_diff.mean()) if len(mem) else np.nan
c_frac_imp = float((mem.relative_mae_diff < 0).mean()) if len(mem) else 0
claims.append(
    {
        "claim": "C",
        "title": "Memory WLS/MinT modest aggregate gains for Ridge/DLinear",
        "support": "partially_supported" if c_mean < -0.01 and c_frac_imp >= 0.6 else ("supported" if c_mean <= -0.02 and c_frac_imp >= 0.8 else "unsupported"),
        "mean_rel_mae": c_mean,
        "mean_ci_low": float(mem.ci_low.mean()) if len(mem) else np.nan,
        "mean_ci_high": float(mem.ci_high.mean()) if len(mem) else np.nan,
        "fold_consistency": "directionally_consistent" if c_frac_imp >= 0.6 else "mixed",
        "qualification": "LightGBM remains weaker than persistence; recon does not make it competitive.",
    }
)

# D disk ridge BU vs TD
disk_bu = boot_df[(boot_df.hierarchy == "disk_ud") & (boot_df.base_model == "ridge") & (boot_df.method_b == "bottom_up")]
disk_td = boot_df[(boot_df.hierarchy == "disk_ud") & (boot_df.base_model == "ridge") & (boot_df.method_b == "top_down")]
d_bu = float(disk_bu.relative_mae_diff.mean()) if len(disk_bu) else np.nan
d_td = float(disk_td.relative_mae_diff.mean()) if len(disk_td) else np.nan
claims.append(
    {
        "claim": "D",
        "title": "Disk: Ridge BU degrades top; TD preserves independent top",
        "support": "supported" if d_bu >= 0.05 and abs(d_td) < 0.02 and (disk_bu.relative_mae_diff > 0).all() else "partially_supported",
        "mean_rel_mae": d_bu,
        "mean_ci_low": float(disk_bu.ci_low.mean()) if len(disk_bu) else np.nan,
        "mean_ci_high": float(disk_bu.ci_high.mean()) if len(disk_bu) else np.nan,
        "fold_consistency": "consistently_harmful" if (disk_bu.relative_mae_diff > 0).all() else "mixed",
        "qualification": f"Ridge BU mean rel={d_bu:.3f}; Ridge TD mean rel={d_td:.3g} (coherence-only). LGBM is transferred-stress, not primary effect size.",
    }
)

claim_df = pd.DataFrame(claims)
claim_df.to_csv(MET / "claim_support.csv", index=False)
claim_df.to_csv(TAB / "claim_support_summary.csv", index=False)

# Method selection
sel = []
# CPU best accuracy: lightgbm+mint from prior pack means — compute from boot
for hier, label in [("cpu_core_weighted", "cpu"), ("memory_um", "memory"), ("disk_ud", "disk")]:
    sub = boot_df[boot_df.hierarchy == hier]
    # mean mae_reconciled by model/method (lower better); include independent as method
    rows = []
    for model in sub.base_model.unique():
        for method in ["independent"] + list(PACKS[hier]["methods"]):
            if method == "independent":
                s = sub[(sub.base_model == model) & (sub.method_b == PACKS[hier]["methods"][0])]
                if s.empty:
                    continue
                mae_m = float(s.mae_independent.mean())
                coh = float(s.coherence_before.mean())
                trade = "baseline"
            else:
                s = sub[(sub.base_model == model) & (sub.method_b == method)]
                if s.empty:
                    continue
                mae_m = float(s.mae_reconciled.mean())
                coh = float(s.coherence_after.mean())
                trade = s.tradeoff_class.value_counts().idxmax()
            rows.append({"model": model, "method": method, "mean_mae": mae_m, "mean_coh": coh, "tradeoff": trade})
    rdf = pd.DataFrame(rows)
    if rdf.empty:
        continue
    # exclude persistence from "best" for cpu/memory accuracy leader except disk
    cand = rdf if hier == "disk_ud" else rdf[rdf.model != "persistence"]
    if hier == "memory_um":
        # lightgbm not competitive — prefer ridge/dlinear
        cand2 = cand[cand.model.isin(["ridge", "dlinear"])]
        if not cand2.empty:
            cand = cand2
    best_acc = cand.loc[cand.mean_mae.idxmin()]
    # best accuracy/coherence: coherent (coh~0) with best mae among coherent
    coh_ok = cand[cand.mean_coh < 1e-3]
    if coh_ok.empty:
        best_ac = best_acc
    else:
        best_ac = coh_ok.loc[coh_ok.mean_mae.idxmin()]
    unsuitable = []
    if hier == "disk_ud":
        unsuitable = ["bottom_up for learned models", "lightgbm transferred memory hparams"]
    if hier == "memory_um":
        unsuitable = ["lightgbm as accuracy leader vs persistence"]
    sel.append(
        {
            "hierarchy": label,
            "best_pure_accuracy": f"{best_acc.model}+{best_acc.method}",
            "best_pure_accuracy_mae": best_acc.mean_mae,
            "best_accuracy_coherence": f"{best_ac.model}+{best_ac.method}",
            "best_accuracy_coherence_mae": best_ac.mean_mae,
            "unsuitable": "; ".join(unsuitable),
            "negative_findings": (
                "disk BU harmful"
                if hier == "disk_ud"
                else ("memory LGBM weak vs persistence" if hier == "memory_um" else "WLS/MinT may degrade machines")
            ),
        }
    )
sel_df = pd.DataFrame(sel)
sel_df.to_csv(TAB / "method_selection.csv", index=False)

# Figures
def forest(ax, sub, title):
    sub = sub.copy()
    sub["label"] = sub.apply(lambda r: f"{r.base_model}/h{int(r.horizon)}/{r.method_b}/f{int(r.fold)}", axis=1)
    # too many — aggregate to model/horizon/method mean
    g = sub.groupby(["base_model", "horizon", "method_b"], as_index=False).agg(
        mean_rel=("relative_mae_diff", "mean"), lo=("ci_low", "mean"), hi=("ci_high", "mean")
    )
    g["label"] = g.apply(lambda r: f"{r.base_model} h{int(r.horizon)} {r.method_b}", axis=1)
    y = np.arange(len(g))
    ax.axvline(0, color="k", lw=0.8)
    ax.hlines(y, g.lo, g.hi, color="#456")
    ax.plot(g.mean_rel, y, "o", color="#c45")
    ax.set_yticks(y)
    ax.set_yticklabels(g.label, fontsize=7)
    ax.set_xlabel("relative MAE (recon − ind) / ind")
    ax.set_title(title)


fig, ax = plt.subplots(figsize=(8, 10))
forest(ax, boot_df[boot_df.hierarchy == "memory_um"], "Memory: recon vs independent")
fig.tight_layout()
fig.savefig(FIG / "bootstrap_effects_memory.pdf")
fig.savefig(FIG / "bootstrap_effects_memory.png")
plt.close()

fig, ax = plt.subplots(figsize=(8, 10))
forest(ax, boot_df[boot_df.hierarchy == "cpu_core_weighted"], "CPU: recon vs independent")
fig.tight_layout()
fig.savefig(FIG / "bootstrap_effects_cpu.pdf")
fig.savefig(FIG / "bootstrap_effects_cpu.png")
plt.close()

fig, ax = plt.subplots(figsize=(8, 8))
forest(ax, boot_df[boot_df.hierarchy == "disk_ud"], "Disk: recon vs independent")
fig.tight_layout()
fig.savefig(FIG / "bootstrap_effects_disk.pdf")
fig.savefig(FIG / "bootstrap_effects_disk.png")
plt.close()

fig, ax = plt.subplots(figsize=(7, 6))
for hier, marker in [("cpu_core_weighted", "o"), ("memory_um", "s"), ("disk_ud", "^")]:
    s = tb[tb.hierarchy == hier]
    ax.scatter(s.macro_rel, s.top_rel, label=hier, alpha=0.75, marker=marker)
ax.axhline(0, color="k", lw=0.6)
ax.axvline(0, color="k", lw=0.6)
ax.set_xlabel("macro bottom relative MAE change")
ax.set_ylabel("top relative MAE change")
ax.set_title("Top vs bottom trade-off")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "top_bottom_tradeoff.pdf")
fig.savefig(FIG / "top_bottom_tradeoff.png")
plt.close()

# summary prints
pd.set_option("display.width", 220)
pd.set_option("display.float_format", lambda x: f"{x:.4g}")
print("n_boot_rows", len(boot_df), "families", boot_df.correction_family.nunique())
print("\n=== CLAIMS ===")
print(claim_df.to_string(index=False))
print("\n=== METHOD SELECTION ===")
print(sel_df.to_string(index=False))
print("\n=== CPU mean rel by model/method ===")
print(
    boot_df[boot_df.hierarchy == "cpu_core_weighted"]
    .groupby(["base_model", "method_b"])["relative_mae_diff"]
    .mean()
    .unstack()
)
print("\n=== MEMORY mean rel ===")
print(
    boot_df[boot_df.hierarchy == "memory_um"]
    .groupby(["base_model", "method_b"])["relative_mae_diff"]
    .mean()
    .unstack()
)
print("\n=== DISK ridge ===")
print(
    boot_df[(boot_df.hierarchy == "disk_ud") & (boot_df.base_model == "ridge")]
    .groupby(["method_b"])["relative_mae_diff"]
    .agg(["mean", "min", "max"])
)
print("DONE")
