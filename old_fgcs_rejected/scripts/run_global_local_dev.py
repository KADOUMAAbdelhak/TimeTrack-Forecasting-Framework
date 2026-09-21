"""In-distribution local vs global forecasting (development stage).

All machines appear in training; evaluate on later chronological outer folds.
Not LOMO. Claim-ineligible.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import forecasting as F
from models.hybrid.residual_adaptation import GlobalResidualAdaptationForecaster
from scripts.run_lomo_dev import MACHINES, build_entity_dataset
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase_result, nanmean_valid
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds, origins_for_split

FAMILIES = {
    "CU": [f"{m}_CU" for m in MACHINES],
    "UM": [f"{m}_UM" for m in MACHINES],
}
HORIZONS = (1, 4, 8, 16)
CONTEXT = 32
SEED = 0
# LightGBM can SIGSEGV in this process when pooled n is large + OpenMP; prefer ridge
# and optional lgbm via env TIMETRACK_GLOBAL_LOCAL_LGBM=1 with OMP_NUM_THREADS=1.
import os

BASE_MODELS = ("ridge",)
if os.environ.get("TIMETRACK_GLOBAL_LOCAL_LGBM", "0") == "1":
    BASE_MODELS = ("ridge", "lightgbm")
INCLUDE_LSTM = False
INCLUDE_DLINEAR = False
INCLUDE_EMBED = True


def _flat(name: str) -> bool:
    return name in {"ridge", "lightgbm", "xgboost"}


def _first(y, horizon):
    y = np.asarray(y, dtype=float)
    return y[:, 0] if y.ndim > 1 else y.reshape(-1)


def _align_test_by_origin(local_packs: dict[str, dict], global_pack: dict) -> dict[str, np.ndarray]:
    """Intersect test origins across machines for identical timestamps."""
    common = None
    for m, p in local_packs.items():
        s = set(map(int, p["origin_idx"]))
        common = s if common is None else common & s
    if global_pack is not None:
        common &= set(map(int, global_pack["origin_idx"]))
    origins = np.array(sorted(common or []), dtype=int)
    return {"origins": origins}


def run_once(panel, split, fold_id, family, horizon, base_model):
    cols = {m: c for m, c in zip(MACHINES, FAMILIES[family])}
    flat = _flat(base_model)
    o_tr = origins_for_split(split.train_idx, CONTEXT, horizon, len(panel))
    o_va = origins_for_split(split.val_idx, CONTEXT, horizon, len(panel))
    o_te = origins_for_split(split.test_idx, CONTEXT, horizon, len(panel))

    # Local models
    local_test = {}
    local_rows_meta = []
    t_local = 0.0
    for m, col in cols.items():
        tr = build_entity_dataset(panel, {m: col}, o_tr, CONTEXT, horizon, flat=flat)
        va = build_entity_dataset(panel, {m: col}, o_va, CONTEXT, horizon, flat=flat)
        te = build_entity_dataset(panel, {m: col}, o_te, CONTEXT, horizon, flat=flat)
        if len(tr["X"]) == 0 or len(te["X"]) == 0:
            continue
        kwargs = {}
        if base_model == "lstm":
            kwargs = {"epochs": 8, "patience": 3}
        if base_model == "dlinear":
            kwargs = {"epochs": 5, "timeout_sec": 120}
        model = F.build_model(base_model, horizon=horizon, context_length=CONTEXT, seed=SEED, **kwargs)
        t0 = time.perf_counter()
        model.fit(tr["X"], tr["y"], va["X"] if len(va["X"]) else None, va["y"] if len(va["X"]) else None)
        t_local += time.perf_counter() - t0
        pred = model.predict(te["X"])
        local_test[m] = {
            "y": _first(te["y"], horizon),
            "p": _first(pred, horizon),
            "origin_idx": te["origin_idx"],
            "y_train": panel.loc[split.train_idx, col].to_numpy(float),
            "n_params": model.metadata.n_parameters,
            "infer_s": model.metadata.inference_time_sec or 0.0,
        }

    # Global packs
    tr_g = build_entity_dataset(panel, cols, o_tr, CONTEXT, horizon, flat=flat)
    va_g = build_entity_dataset(panel, cols, o_va, CONTEXT, horizon, flat=flat)
    te_g = build_entity_dataset(panel, cols, o_te, CONTEXT, horizon, flat=flat)

    variants = {}

    def _fit_global(name, factory):
        t0 = time.perf_counter()
        model = factory()
        model.fit(
            tr_g["X"],
            tr_g["y"],
            va_g["X"],
            va_g["y"],
            entity_keys=tr_g["entity_keys"],
            entity_keys_val=va_g["entity_keys"],
        )
        train_s = time.perf_counter() - t0
        pred = model.predict(te_g["X"], entity_keys=te_g["entity_keys"])
        variants[name] = {
            "y": _first(te_g["y"], horizon),
            "p": _first(pred, horizon),
            "origin_idx": te_g["origin_idx"],
            "entity_keys": te_g["entity_keys"],
            "train_s": train_s,
            "infer_s": model.metadata.inference_time_sec or 0.0,
            "n_params": model.metadata.n_parameters,
        }

    bk = {}
    if base_model == "lstm":
        bk = {"epochs": 8, "patience": 3}
    if base_model == "dlinear":
        bk = {"epochs": 5, "timeout_sec": 120}

    _fit_global(
        "global_pooled",
        lambda: F.build_model(
            "global_pooled",
            horizon=horizon,
            context_length=CONTEXT,
            seed=SEED,
            base_model=base_model,
            base_kwargs=bk,
            scaler_mode="per_entity",
        ),
    )
    _fit_global(
        "global_onehot",
        lambda: F.build_model(
            "global_onehot",
            horizon=horizon,
            context_length=CONTEXT,
            seed=SEED,
            base_model=base_model,
            entities=list(MACHINES),
            base_kwargs=bk,
            scaler_mode="per_entity",
        ),
    )
    if base_model in {"ridge", "lightgbm"}:
        # residual adaptation uses same base
        t0 = time.perf_counter()
        resid = GlobalResidualAdaptationForecaster(
            horizon=horizon,
            context_length=CONTEXT,
            seed=SEED,
            base_model=base_model,
            entities=list(MACHINES),
            scaler_mode="per_entity",
            base_kwargs=bk,
        )
        resid.fit(
            tr_g["X"],
            tr_g["y"],
            va_g["X"],
            va_g["y"],
            entity_keys=tr_g["entity_keys"],
            entity_keys_val=va_g["entity_keys"],
        )
        train_s = time.perf_counter() - t0
        pred = resid.predict(te_g["X"], entity_keys=te_g["entity_keys"])
        variants["global_residual"] = {
            "y": _first(te_g["y"], horizon),
            "p": _first(pred, horizon),
            "origin_idx": te_g["origin_idx"],
            "entity_keys": te_g["entity_keys"],
            "train_s": train_s,
            "infer_s": resid.metadata.inference_time_sec or 0.0,
            "n_params": resid.metadata.n_parameters,
        }

    if INCLUDE_EMBED and base_model == "ridge":
        # Train embed once per family/horizon on ridge-scale flat features only
        try:
            t0 = time.perf_counter()
            emb = F.build_model(
                "global_embed",
                horizon=horizon,
                context_length=CONTEXT,
                seed=SEED,
                entities=list(MACHINES),
                epochs=12,
                scaler_mode="per_entity",
            )
            emb.fit(
                tr_g["X"],
                tr_g["y"],
                va_g["X"],
                va_g["y"],
                entity_keys=tr_g["entity_keys"],
                entity_keys_val=va_g["entity_keys"],
            )
            train_s = time.perf_counter() - t0
            pred = emb.predict(te_g["X"], entity_keys=te_g["entity_keys"])
            variants["global_embed"] = {
                "y": _first(te_g["y"], horizon),
                "p": _first(pred, horizon),
                "origin_idx": te_g["origin_idx"],
                "entity_keys": te_g["entity_keys"],
                "train_s": train_s,
                "infer_s": emb.metadata.inference_time_sec or 0.0,
                "n_params": emb.metadata.n_parameters,
            }
        except Exception as e:
            print("embed failed", e, flush=True)

    # Align origins
    common = None
    for m, p in local_test.items():
        s = set(map(int, p["origin_idx"]))
        common = s if common is None else common & s
    for v in variants.values():
        common &= set(map(int, v["origin_idx"]))
    origins = np.array(sorted(common or []), dtype=int)
    if len(origins) == 0:
        return []

    def take(pack, origins, key_y="y", key_p="p"):
        idx = {int(o): i for i, o in enumerate(pack["origin_idx"])}
        ii = [idx[int(o)] for o in origins]
        return pack[key_y][ii], pack[key_p][ii]

    rows = []
    # Local per machine + macro
    local_maes = []
    for m, p in local_test.items():
        yt, yp = take(p, origins)
        mr = mase_result(yt, yp, p["y_train"])
        mae_m = mae(yt, yp)
        local_maes.append(mae_m)
        rows.append(
            {
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
                "family": family,
                "method": "local",
                "base_model": base_model,
                "horizon": horizon,
                "outer_fold": fold_id,
                "machine": m,
                "mae": mae_m,
                "mase": mr["mase"],
                "mase_valid": mr["mase_valid"],
                "nmae_train_range": mr["nmae_train_range"],
                "n_parameters": p["n_params"],
                "train_seconds": t_local / max(len(local_test), 1),
                "infer_seconds": p["infer_s"],
                "n_test": len(yt),
            }
        )

    # Global per machine (origin × entity alignment)
    for vname, vp in variants.items():
        keys = np.asarray(vp["entity_keys"])
        o_to_rows: dict[int, dict[str, int]] = {}
        for i, o in enumerate(vp["origin_idx"]):
            o_to_rows.setdefault(int(o), {})[str(keys[i])] = i
        for m in MACHINES:
            yt_list, yp_list = [], []
            y_train = panel.loc[split.train_idx, cols[m]].to_numpy(float)
            for o in origins:
                j = o_to_rows.get(int(o), {}).get(m)
                if j is None:
                    continue
                yt_list.append(vp["y"][j])
                yp_list.append(vp["p"][j])
            if not yt_list:
                continue
            yt, yp = np.asarray(yt_list), np.asarray(yp_list)
            mr = mase_result(yt, yp, y_train)
            rows.append(
                {
                    "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                    "eligible_for_final_claims": False,
                    "family": family,
                    "method": vname,
                    "base_model": base_model,
                    "horizon": horizon,
                    "outer_fold": fold_id,
                    "machine": m,
                    "mae": mae(yt, yp),
                    "mase": mr["mase"],
                    "mase_valid": mr["mase_valid"],
                    "nmae_train_range": mr["nmae_train_range"],
                    "n_parameters": vp["n_params"],
                    "train_seconds": vp["train_s"],
                    "infer_seconds": vp["infer_s"],
                    "n_test": len(yt),
                }
            )
    return rows


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    models = list(BASE_MODELS)
    if INCLUDE_LSTM:
        models.append("lstm")
    if INCLUDE_DLINEAR:
        models.append("dlinear")

    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for family in FAMILIES:
            for horizon in HORIZONS:
                for base in models:
                    print(f"{fold.fold_id} {family} h={horizon} base={base}", flush=True)
                    rows.extend(run_once(panel, split, fold.fold_id, family, horizon, base))

    df = pd.DataFrame(rows)
    metrics = ROOT / "results" / "development" / "metrics"
    tables = ROOT / "results" / "development" / "tables"
    figs = ROOT / "results" / "development" / "figures"
    for d in (metrics, tables, figs):
        d.mkdir(parents=True, exist_ok=True)

    df.to_csv(metrics / "global_local_all_runs.csv", index=False)

    # Macro / worst / weighted summaries
    summary_rows = []
    for keys, g in df.groupby(["family", "method", "base_model", "horizon"]):
        # weight by n_test
        w = g["n_test"].to_numpy(float)
        mae_w = float(np.sum(g["mae"] * w) / np.sum(w)) if w.sum() else float("nan")
        summary_rows.append(
            {
                "family": keys[0],
                "method": keys[1],
                "base_model": keys[2],
                "horizon": keys[3],
                "mae_macro": float(g["mae"].mean()),
                "mae_weighted": mae_w,
                "mae_worst_machine": float(g["mae"].max()),
                "mae_std_fold_machine": float(g["mae"].std()),
                "mase_macro": nanmean_valid(g["mase"].to_numpy(), g["mase_valid"].to_numpy()),
                "train_seconds_mean": float(g["train_seconds"].mean()),
                "infer_seconds_mean": float(g["infer_seconds"].mean()),
                "n_parameters_mean": float(pd.to_numeric(g["n_parameters"], errors="coerce").mean()),
                "n": len(g),
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(metrics / "global_local_summary.csv", index=False)

    # vs local table
    comps = []
    for keys, g in df.groupby(["family", "base_model", "horizon", "outer_fold", "machine"]):
        loc = g[g.method == "local"]
        if loc.empty:
            continue
        base_mae = float(loc.iloc[0]["mae"])
        for _, r in g.iterrows():
            comps.append(
                {
                    "family": keys[0],
                    "base_model": keys[1],
                    "horizon": keys[2],
                    "outer_fold": keys[3],
                    "machine": keys[4],
                    "method": r["method"],
                    "mae": r["mae"],
                    "mae_vs_local": r["mae"] - base_mae,
                    "mae_rel": r["mae"] / base_mae if base_mae else np.nan,
                }
            )
    comp = pd.DataFrame(comps)
    comp.to_csv(tables / "global_vs_local.csv", index=False)
    pivot = (
        comp.groupby(["family", "method", "base_model"], as_index=False)
        .agg(mae_rel_mean=("mae_rel", "mean"), mae_vs_local_mean=("mae_vs_local", "mean"))
        .sort_values(["family", "mae_rel_mean"])
    )
    md = ["# Global vs local (in-distribution, development)", "", pivot.to_markdown(index=False), ""]
    md.append("eligible_for_final_claims: false")
    (tables / "global_vs_local.md").write_text("\n".join(md))

    # Figures (lazy matplotlib import to avoid sandbox/font-cache issues at import time)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sub = (
        df[(df.horizon == 1) & (df.base_model == "ridge") & (df.family == "CU")]
        .groupby(["machine", "method"], as_index=False)["mae"]
        .mean()
    )
    fig, ax = plt.subplots(figsize=(9, 4))
    for method, g in sub.groupby("method"):
        ax.plot(g["machine"], g["mae"], marker="o", label=method)
    ax.set_title("In-distribution CU MAE by machine (ridge, h=1)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figs / "global_vs_local_per_machine.pdf")
    fig.savefig(figs / "global_vs_local_per_machine.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for (fam, method), g in summary[summary.base_model == "ridge"].groupby(["family", "method"]):
        ax.plot(g["horizon"], g["mae_macro"], marker="o", label=f"{fam}:{method}")
    ax.set_xlabel("horizon")
    ax.set_ylabel("macro MAE")
    ax.set_title("In-distribution macro MAE vs horizon (ridge)")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(figs / "global_vs_local_macro.pdf")
    fig.savefig(figs / "global_vs_local_macro.png", dpi=120)
    plt.close(fig)

    (metrics / "global_local_all_runs.meta.json").write_text(
        json.dumps(
            {
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
                "dataset_fingerprint": fp["fingerprint"],
                "setting": "in_distribution_all_machines_in_train",
                "n_rows": len(df),
            },
            indent=2,
        )
    )
    print(summary.head(20).to_string(index=False))
    print("wrote global_local", len(df))


if __name__ == "__main__":
    main()
