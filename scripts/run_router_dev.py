"""C2 adaptive router development evaluation (claim-ineligible)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.ensembles.constrained_mixture import apply_mixture, fit_constrained_mixture
from models.ensembles.router import RegimeRouter, RouterConfig, StaticRouter, oracle_selector
from models.ensembles.strategies import ensemble_predict
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase_result, rmse, r2_score, peak_metrics
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

TARGETS = (
    "cluster_mean_CU",
    "machine01_CU",
    "machine06_CU",
    "cluster_UM",
    "machine01_UM",
    "machine01_tx_bond0",
    "machine01_rx_bond0",
    "averageRttWithGoogleDns",
    "jitterWithGoogleDns",
    "machine01_DWT",
)
CONSTITUENTS = ("persistence", "ewma", "ridge", "lightgbm")
HORIZONS = (1, 4, 8, 16)
CONTEXT = 32
SEED = 0


def _flat(name: str) -> bool:
    return name in {"ridge", "lightgbm", "ewma"}


def _first(y, h):
    y = np.asarray(y, dtype=float)
    return y[:, 0] if y.ndim > 1 else y.reshape(-1)


def fit_constituents(panel, split, target, horizon):
    out = {}
    for name in CONSTITUENTS:
        windows = prepare_split_windows(panel, split, target, horizon, CONTEXT, flat=_flat(name))
        model = F.build_model(name, horizon=horizon, context_length=CONTEXT, seed=SEED)
        model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
        out[name] = {
            "X_val": windows["val"].X,
            "y_val": _first(windows["val"].y, horizon),
            "p_val": _first(model.predict(windows["val"].X), horizon),
            "X_test": windows["test"].X,
            "y_test": _first(windows["test"].y, horizon),
            "p_test": _first(model.predict(windows["test"].X), horizon),
            "origins_val": windows["val"].origin_idx,
            "origins_test": windows["test"].origin_idx,
            "infer_s": model.metadata.inference_time_sec or 0.0,
        }
    # align
    n_val = min(len(out[n]["y_val"]) for n in CONSTITUENTS)
    n_test = min(len(out[n]["y_test"]) for n in CONSTITUENTS)
    for n in CONSTITUENTS:
        for k in ("X_val", "y_val", "p_val", "origins_val"):
            out[n][k] = out[n][k][:n_val]
        for k in ("X_test", "y_test", "p_test", "origins_test"):
            out[n][k] = out[n][k][:n_test]
    return out


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    sel_rows = []

    for fold in folds:
        split = fold_to_split_spec(fold)
        for target in TARGETS:
            if target not in panel.columns:
                print("skip", target, flush=True)
                continue
            for horizon in HORIZONS:
                print(f"{fold.fold_id} {target} h={horizon}", flush=True)
                t0 = time.perf_counter()
                packs = fit_constituents(panel, split, target, horizon)
                train_s = time.perf_counter() - t0
                y_val = packs["persistence"]["y_val"]
                y_test = packs["persistence"]["y_test"]
                y_train = panel.loc[split.train_idx, target].to_numpy(float)
                preds_val = {n: packs[n]["p_val"] for n in CONSTITUENTS}
                preds_test = {n: packs[n]["p_test"] for n in CONSTITUENTS}
                key = (target, horizon)

                # calendar features at origins
                hours_val = panel["hour"].to_numpy()[packs["persistence"]["origins_val"]]
                week_val = panel["is_weekend"].to_numpy()[packs["persistence"]["origins_val"]]
                hours_te = panel["hour"].to_numpy()[packs["persistence"]["origins_test"]]
                week_te = panel["is_weekend"].to_numpy()[packs["persistence"]["origins_test"]]

                cfg = RouterConfig(constituent_names=CONSTITUENTS, seed=SEED)
                static = StaticRouter(cfg).fit([key], {key: y_val}, {key: preds_val})
                regime = RegimeRouter(cfg).fit(
                    [key],
                    {key: packs["persistence"]["X_val"]},
                    {key: y_val},
                    {key: preds_val},
                    hours={key: hours_val},
                    weekends={key: week_val},
                )
                mix = fit_constrained_mixture(y_val, [preds_val[n] for n in CONSTITUENTS])

                methods = {}
                for n in CONSTITUENTS:
                    methods[n] = preds_test[n]
                # fixed target best / target-horizon best = static selection
                p_static, name_static = static.predict_key(key, preds_test)
                methods["static_router"] = p_static
                p_reg, names_reg = regime.predict_key(
                    key, packs["persistence"]["X_test"], preds_test, hours=hours_te, weekends=week_te
                )
                methods["regime_router"] = p_reg
                methods["constrained_mixture"] = apply_mixture([preds_test[n] for n in CONSTITUENTS], mix["weights"])
                for ens in ("mean", "inverse_mae", "stacking"):
                    methods[f"ens_{ens}"] = ensemble_predict(
                        ens, [preds_test[n] for n in CONSTITUENTS], y_val=y_val, preds_val=[preds_val[n] for n in CONSTITUENTS]
                    )["pred"]
                # oracle upper bound (analysis only)
                p_oracle, names_oracle = oracle_selector(y_test, preds_test)
                methods["oracle_upper_bound"] = p_oracle

                best_fixed_mae = min(mae(y_test, preds_test[n]) for n in CONSTITUENTS)
                for mname, pred in methods.items():
                    mr = mase_result(y_test, pred, y_train)
                    pk = peak_metrics(y_test, pred, y_train, quantile=0.95)
                    rows.append(
                        {
                            "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                            "eligible_for_final_claims": False,
                            "target": target,
                            "horizon": horizon,
                            "outer_fold": fold.fold_id,
                            "method": mname,
                            "mae": mae(y_test, pred),
                            "rmse": rmse(y_test, pred),
                            "r2": r2_score(y_test, pred),
                            "mase": mr["mase"],
                            "mase_valid": mr["mase_valid"],
                            "peak_recall": pk.get("peak_recall"),
                            "peak_precision": pk.get("peak_precision"),
                            "beats_best_constituent": bool(mae(y_test, pred) < best_fixed_mae - 1e-12)
                            if mname != "oracle_upper_bound"
                            else False,
                            "best_constituent_mae": best_fixed_mae,
                            "train_seconds": train_s,
                            "is_oracle": mname == "oracle_upper_bound",
                        }
                    )
                # selection frequency
                for n in CONSTITUENTS:
                    sel_rows.append(
                        {
                            "target": target,
                            "horizon": horizon,
                            "outer_fold": fold.fold_id,
                            "router": "static",
                            "selected": name_static,
                            "constituent": n,
                            "selected_flag": int(name_static == n),
                        }
                    )
                for n in CONSTITUENTS:
                    sel_rows.append(
                        {
                            "target": target,
                            "horizon": horizon,
                            "outer_fold": fold.fold_id,
                            "router": "regime",
                            "selected": "per_timestep",
                            "constituent": n,
                            "selected_flag": float(np.mean(names_reg == n)),
                        }
                    )

    df = pd.DataFrame(rows)
    metrics = ROOT / "results" / "development" / "metrics"
    tables = ROOT / "results" / "development" / "tables"
    figs = ROOT / "results" / "development" / "figures"
    for d in (metrics, tables, figs):
        d.mkdir(parents=True, exist_ok=True)
    df.to_csv(metrics / "router_all_runs.csv", index=False)
    summary = (
        df[~df["is_oracle"]]
        .groupby(["target", "horizon", "method"], as_index=False)
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            beat_rate=("beats_best_constituent", "mean"),
            peak_recall_mean=("peak_recall", "mean"),
        )
    )
    summary.to_csv(metrics / "router_summary.csv", index=False)
    summary.to_csv(tables / "router_comparison.csv", index=False)
    pd.DataFrame(sel_rows).to_csv(tables / "router_selection_frequency.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # gain vs best constituent
    gains = []
    for keys, g in df[~df.is_oracle].groupby(["target", "horizon", "outer_fold"]):
        best = g[g.method.isin(CONSTITUENTS)]["mae"].min()
        for m in ("static_router", "regime_router", "constrained_mixture", "ens_inverse_mae"):
            sub = g[g.method == m]
            if sub.empty:
                continue
            gains.append({"target": keys[0], "horizon": keys[1], "method": m, "gain": best - float(sub.iloc[0]["mae"])})
    gdf = pd.DataFrame(gains)
    if not gdf.empty:
        piv = gdf.groupby(["target", "method"])["gain"].mean().unstack()
        fig, ax = plt.subplots(figsize=(10, 4))
        piv.plot(kind="bar", ax=ax)
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_ylabel("MAE gain vs best constituent (>0 better)")
        ax.set_title("Router gain by target (dev)")
        fig.tight_layout()
        fig.savefig(figs / "router_gain_by_target_horizon.pdf")
        fig.savefig(figs / "router_gain_by_target_horizon.png", dpi=120)
        plt.close(fig)

    sel = pd.DataFrame(sel_rows)
    freq = sel[sel.router == "static"].groupby("constituent")["selected_flag"].mean()
    fig, ax = plt.subplots(figsize=(6, 3))
    freq.plot(kind="bar", ax=ax)
    ax.set_title("Static router selection frequency")
    fig.tight_layout()
    fig.savefig(figs / "router_selection_frequency.pdf")
    fig.savefig(figs / "router_selection_frequency.png", dpi=120)
    plt.close(fig)

    # switch timeline proxy: regime switch rate
    switch = (
        sel[sel.router == "regime"]
        .groupby(["target", "horizon"])["selected_flag"]
        .apply(lambda s: 1.0 - s.max())  # diversity proxy
        .reset_index(name="switch_proxy")
    )
    fig, ax = plt.subplots(figsize=(8, 3))
    if not switch.empty:
        ax.plot(switch.index, switch["switch_proxy"], marker="o")
    ax.set_title("Regime router selection diversity proxy")
    fig.tight_layout()
    fig.savefig(figs / "router_switch_timeline.pdf")
    fig.savefig(figs / "router_switch_timeline.png", dpi=120)
    plt.close(fig)

    (metrics / "router_all_runs.meta.json").write_text(
        json.dumps(
            {
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
                "dataset_fingerprint": fp["fingerprint"],
                "oracle_note": "oracle_upper_bound uses outer labels; analysis only",
                "n_rows": len(df),
            },
            indent=2,
        )
    )
    print(summary.head(30).to_string(index=False))
    print("wrote router metrics", len(df))


if __name__ == "__main__":
    main()
