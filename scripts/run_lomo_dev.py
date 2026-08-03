"""Leave-one-machine-out (LOMO) development benchmark.

Rules:
- train on six machines only
- scalers / selection never see held-out targets
- calibration samples strictly before evaluation block
- unseen identity → UNK embedding / zero one-hot / global-only residual
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import forecasting as F
from models.hybrid.residual_adaptation import GlobalResidualAdaptationForecaster
from models.multivariate.entity_features import TargetScaler
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase
from timetrack.splits import build_windows, fold_to_split_spec, make_outer_chronological_folds, origins_for_split

MACHINES = [f"machine0{i}" for i in range(1, 8)]
TARGETS = {
    "CU": [f"{m}_CU" for m in MACHINES],
    "UM": [f"{m}_UM" for m in MACHINES],
}
CALIBRATION_SIZES = (0, 64, 256, 1024)
HORIZONS = (1, 8)
CONTEXT = 32
SEED = 0


def _metric_cols(family: str) -> list[str]:
    return TARGETS[family]


def build_entity_dataset(
    panel: pd.DataFrame,
    machine_cols: dict[str, str],
    origins: np.ndarray,
    context: int,
    horizon: int,
    flat: bool = True,
) -> dict[str, np.ndarray | list]:
    """
    machine_cols: entity_key -> column name in panel.
    Returns stacked X, y, entity_keys, timestamps (origin timestamps), sources, origin_idx.
    """
    Xs, ys, keys, ts_list, sources, oidxs = [], [], [], [], [], []
    for entity, col in machine_cols.items():
        values = panel[[col]].to_numpy(dtype=float)
        try:
            ds = build_windows(
                values,
                origins,
                context=context,
                horizon=horizon,
                feature_names=[col],
                flat=flat,
                panel_for_gap_check=panel,
            )
        except ValueError:
            continue
        Xs.append(ds.X)
        ys.append(ds.y)
        n = len(ds.X)
        keys.extend([entity] * n)
        sources.extend([entity] * n)
        oidxs.append(ds.origin_idx)
        for o in ds.origin_idx:
            ts_list.append(panel["timestamp"].iloc[int(o)])
    if not Xs:
        return {
            "X": np.zeros((0, context if flat else 1)),
            "y": np.zeros((0,)),
            "entity_keys": [],
            "timestamps": [],
            "sources": [],
            "origin_idx": np.zeros((0,), dtype=int),
        }
    return {
        "X": np.concatenate(Xs, axis=0),
        "y": np.concatenate(ys, axis=0),
        "entity_keys": keys,
        "timestamps": ts_list,
        "sources": sources,
        "origin_idx": np.concatenate(oidxs, axis=0),
    }


def _first_step(y, horizon):
    y = np.asarray(y, dtype=float)
    return y[:, 0] if y.ndim > 1 else y.reshape(-1)


def run_lomo_once(
    panel: pd.DataFrame,
    split,
    outer_fold: int,
    family: str,
    held_out: str,
    horizon: int,
    base_model: str = "ridge",
) -> list[dict]:
    cols = {m: c for m, c in zip(MACHINES, _metric_cols(family))}
    train_machines = [m for m in MACHINES if m != held_out]
    train_cols = {m: cols[m] for m in train_machines}
    held_col = {held_out: cols[held_out]}

    origins_train = origins_for_split(split.train_idx, CONTEXT, horizon, len(panel))
    origins_val = origins_for_split(split.val_idx, CONTEXT, horizon, len(panel))
    origins_test = origins_for_split(split.test_idx, CONTEXT, horizon, len(panel))

    flat = base_model in {"ridge", "lightgbm", "xgboost"}
    tr = build_entity_dataset(panel, train_cols, origins_train, CONTEXT, horizon, flat=flat)
    va = build_entity_dataset(panel, train_cols, origins_val, CONTEXT, horizon, flat=flat)
    # held-out: local persistence + global eval on identical test timestamps
    te_hold = build_entity_dataset(panel, held_col, origins_test, CONTEXT, horizon, flat=flat)
    # calibration pool: held-out samples from train+val origins only (before test)
    cal_origins = np.concatenate([origins_train, origins_val])
    cal_pool = build_entity_dataset(panel, held_col, cal_origins, CONTEXT, horizon, flat=flat)

    y_train_series = panel.loc[split.train_idx, cols[held_out]].to_numpy(dtype=float)
    rows = []

    # 1) Persistence on held-out history (local)
    local = F.build_model("persistence", horizon=horizon, context_length=CONTEXT, seed=SEED)
    # fit on held-out train windows only
    tr_local = build_entity_dataset(panel, held_col, origins_train, CONTEXT, horizon, flat=False)
    va_local = build_entity_dataset(panel, held_col, origins_val, CONTEXT, horizon, flat=False)
    te_local = build_entity_dataset(panel, held_col, origins_test, CONTEXT, horizon, flat=False)
    if len(tr_local["X"]):
        local.fit(tr_local["X"], tr_local["y"], va_local["X"] if len(va_local["X"]) else None, va_local["y"] if len(va_local["X"]) else None)
        pred = local.predict(te_local["X"])
        yt = _first_step(te_local["y"], horizon)
        yp = _first_step(pred, horizon)
        rows.append(_row("persistence_local", family, held_out, horizon, outer_fold, yt, yp, y_train_series, 0, 0))

    entities = train_machines

    def _eval_global(name, model, pred, yt, cal_n=0, note=""):
        rows.append(
            _row(name, family, held_out, horizon, outer_fold, yt, pred, y_train_series, cal_n, getattr(model, "metadata", type("M", (), {"inference_time_sec": 0})).inference_time_sec or 0, note=note)
        )

    yt = _first_step(te_hold["y"], horizon)
    if len(yt) == 0:
        return rows

    # 2) Pooled global
    pooled = F.build_model(
        "global_pooled",
        horizon=horizon,
        context_length=CONTEXT,
        seed=SEED,
        base_model=base_model,
        scaler_mode="per_entity",
    )
    t0 = time.perf_counter()
    pooled.fit(tr["X"], tr["y"], va["X"], va["y"], entity_keys=tr["entity_keys"], entity_keys_val=va["entity_keys"])
    # leakage check
    pooled.scaler_.assert_entity_excluded(held_out)
    pred = pooled.predict(te_hold["X"], entity_keys=te_hold["entity_keys"])
    _eval_global("global_pooled", pooled, _first_step(pred, horizon), yt)

    # 3) Global one-hot (held-out → zeros)
    onehot = F.build_model(
        "global_onehot",
        horizon=horizon,
        context_length=CONTEXT,
        seed=SEED,
        base_model=base_model,
        entities=entities,
        scaler_mode="per_entity",
    )
    onehot.fit(tr["X"], tr["y"], va["X"], va["y"], entity_keys=tr["entity_keys"], entity_keys_val=va["entity_keys"])
    onehot.scaler_.assert_entity_excluded(held_out)
    pred = onehot.predict(te_hold["X"], entity_keys=te_hold["entity_keys"])
    _eval_global("global_onehot", onehot, _first_step(pred, horizon), yt, note="unknown_entity_zero_onehot")

    # 4) Global residual without held-out head
    resid = GlobalResidualAdaptationForecaster(
        horizon=horizon,
        context_length=CONTEXT,
        seed=SEED,
        base_model=base_model,
        entities=entities,
        scaler_mode="per_entity",
    )
    resid.fit(tr["X"], tr["y"], va["X"], va["y"], entity_keys=tr["entity_keys"], entity_keys_val=va["entity_keys"])
    resid.scaler_.assert_entity_excluded(held_out)
    assert held_out not in resid.residual_heads_
    pred = resid.predict(te_hold["X"], entity_keys=te_hold["entity_keys"], allow_residual=True)
    _eval_global("global_residual_no_head", resid, _first_step(pred, horizon), yt, note="global_only_for_unseen")

    # 5) Calibration curve
    n_cal_avail = len(cal_pool["X"])
    for n_cal in CALIBRATION_SIZES:
        if n_cal > 0 and n_cal_avail < n_cal:
            continue
        model = GlobalResidualAdaptationForecaster(
            horizon=horizon,
            context_length=CONTEXT,
            seed=SEED,
            base_model=base_model,
            entities=entities,
            scaler_mode="per_entity",
        )
        model.fit(tr["X"], tr["y"], va["X"], va["y"], entity_keys=tr["entity_keys"], entity_keys_val=va["entity_keys"])
        model.scaler_.assert_entity_excluded(held_out)
        if n_cal > 0:
            # last n_cal samples before eval (chronological: highest indices in cal_pool follow time if origins sorted)
            Xc, yc = cal_pool["X"][-n_cal:], cal_pool["y"][-n_cal:]
            model.fit_calibration(Xc, yc, held_out)
        pred = model.predict(te_hold["X"], entity_keys=te_hold["entity_keys"])
        _eval_global(
            f"global_residual_cal{n_cal}",
            model,
            _first_step(pred, horizon),
            yt,
            cal_n=n_cal,
            note=f"cal_available={n_cal_avail}",
        )

    # Record exclusions
    for r in rows:
        r["n_train_entities"] = len(train_machines)
        r["n_test"] = len(yt)
        r["n_cal_available"] = n_cal_avail
        r["missing_timestamps"] = int(len(origins_test) - len(te_hold["X"]))
        r["base_model"] = base_model
        r["train_seconds"] = time.perf_counter() - t0
    return rows


def _row(method, family, held_out, horizon, fold, yt, yp, y_train, cal_n, infer_s, note=""):
    return {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "method": method,
        "family": family,
        "held_out_machine": held_out,
        "horizon": horizon,
        "context": CONTEXT,
        "outer_fold": fold,
        "calibration_n": cal_n,
        "mae": mae(yt, yp),
        "mase": mase(yt, yp, y_train),
        "infer_seconds": infer_s,
        "note": note,
    }


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["family", "method", "horizon"], as_index=False).agg(
        mae_macro=("mae", "mean"),
        mae_std=("mae", "std"),
        mae_worst_machine=("mae", "max"),
        mase_macro=("mase", "mean"),
        n=("mae", "count"),
    )
    return g


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for family in ("CU", "UM"):
            for held in MACHINES:
                for horizon in HORIZONS:
                    print(f"{fold.fold_id} {family} hold={held} h={horizon}", flush=True)
                    rows += run_lomo_once(panel, split, fold.fold_id, family, held, horizon, base_model="ridge")

    df = pd.DataFrame(rows)
    metrics = ROOT / "results" / "development" / "metrics"
    tables = ROOT / "results" / "development" / "tables"
    figs = ROOT / "results" / "development" / "figures"
    metrics.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)

    df.to_csv(metrics / "lomo_all_runs.csv", index=False)
    summary = summarize(df)
    summary.to_csv(metrics / "lomo_summary.csv", index=False)

    per_m = (
        df.groupby(["family", "held_out_machine", "method", "horizon"], as_index=False)
        .agg(mae=("mae", "mean"), mase=("mase", "mean"))
    )
    per_m.to_csv(tables / "lomo_per_machine.csv", index=False)

    cal = df[df["method"].str.startswith("global_residual_cal")].copy()
    cal_curve = (
        cal.groupby(["family", "horizon", "calibration_n"], as_index=False)
        .agg(mae_macro=("mae", "mean"), mae_worst=("mae", "max"), mase_macro=("mase", "mean"))
    )
    cal_curve.to_csv(tables / "lomo_calibration_curve.csv", index=False)

    # Figures
    fig, ax = plt.subplots(figsize=(9, 4))
    sub = per_m[(per_m["horizon"] == 1) & (per_m["family"] == "CU") & (per_m["method"].isin(["persistence_local", "global_pooled", "global_residual_no_head"]))]
    for method, g in sub.groupby("method"):
        ax.plot(g["held_out_machine"], g["mae"], marker="o", label=method)
    ax.set_title("LOMO per-machine MAE (CU, h=1)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figs / "lomo_per_machine.pdf")
    fig.savefig(figs / "lomo_per_machine.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for (fam, h), g in cal_curve.groupby(["family", "horizon"]):
        ax.plot(g["calibration_n"], g["mae_macro"], marker="o", label=f"{fam} h={h}")
    ax.set_xlabel("calibration samples")
    ax.set_ylabel("macro MAE")
    ax.set_title("LOMO calibration curve")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figs / "lomo_calibration_curve.pdf")
    fig.savefig(figs / "lomo_calibration_curve.png", dpi=120)
    plt.close(fig)

    meta = {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "dataset_fingerprint": fp["fingerprint"],
        "unknown_entity_policy": "one_hot zeros; embed index 0 UNK; residual global-only without calibration",
        "calibration_sizes": list(CALIBRATION_SIZES),
        "n_rows": len(df),
    }
    (metrics / "lomo_all_runs.meta.json").write_text(json.dumps(meta, indent=2))
    print(summary.to_string(index=False))
    print("wrote lomo metrics", len(df))


if __name__ == "__main__":
    main()
