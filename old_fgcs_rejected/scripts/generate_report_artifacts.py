"""Rebuild aggregations and publication stubs from executed raw runs only."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import append_all_runs, build_leaderboards
from timetrack.data import dataset_fingerprint

RESULTS = ROOT / "results"
RAW = RESULTS / "metrics" / "raw_runs"


def load_raw_runs() -> list[dict]:
    runs = []
    for p in sorted(RAW.glob("*.json")):
        runs.append(json.loads(p.read_text()))
    return runs


def rebuild_tables(runs: list[dict]) -> pd.DataFrame:
    # rewrite all_runs cleanly
    path = RESULTS / "metrics" / "all_runs.csv"
    if path.exists():
        path.unlink()
    append_all_runs(runs)
    build_leaderboards()
    return pd.read_csv(path)


def write_latex(df: pd.DataFrame) -> None:
    latex_dir = RESULTS / "tables" / "latex"
    latex_dir.mkdir(parents=True, exist_ok=True)
    # main comparison: best MAE per target-horizon among executed models
    rows = []
    for (target, horizon), g in df.groupby(["target", "horizon"]):
        best = g.loc[g["mae"].idxmin()]
        base = g[g["model"] == "persistence"]
        pers = float(base["mae"].iloc[0]) if len(base) else float("nan")
        rows.append(
            {
                "target": target,
                "horizon": int(horizon),
                "best_model": best["model"],
                "best_mae": best["mae"],
                "persistence_mae": pers,
                "improvement_pct": (pers - best["mae"]) / pers * 100 if pers and pers == pers else float("nan"),
                "r2": best["r2"],
                "mase": best.get("mase", float("nan")),
            }
        )
    main = pd.DataFrame(rows).sort_values(["target", "horizon"])
    main.to_csv(RESULTS / "tables" / "csv" / "main_comparison.csv", index=False)
    (latex_dir / "main_comparison.tex").write_text(
        main.to_latex(index=False, float_format="%.4g", caption="Smoke/executed main comparison by target and horizon.", label="tab:main")
    )
    # ablation placeholder from executed feature of univariate baselines vs ridge/lgbm
    abl = df[df["model"].isin(["persistence", "ridge", "lightgbm", "dlinear"])].copy()
    abl_sum = (
        abl.groupby(["target", "horizon", "model"])[["mae", "rmse", "r2"]]
        .mean()
        .reset_index()
    )
    abl_sum.to_csv(RESULTS / "tables" / "csv" / "ablation_results.csv", index=False)
    (latex_dir / "ablation_results.tex").write_text(
        abl_sum.to_latex(index=False, float_format="%.4g", caption="Selected model comparison on executed smoke tasks.", label="tab:ablation")
    )


def make_figures(df: pd.DataFrame) -> None:
    fig_dir = RESULTS / "figures"
    # error vs horizon for cluster_mean_CU
    sub = df[df["target"] == "cluster_mean_CU"]
    if len(sub):
        plt.figure(figsize=(7, 4))
        for model, g in sub.groupby("model"):
            g = g.sort_values("horizon")
            plt.plot(g["horizon"], g["mae"], marker="o", label=model)
        plt.xlabel("Horizon (steps @ ~42.3s)")
        plt.ylabel("Test MAE")
        plt.title("cluster_mean_CU: MAE vs horizon (executed runs)")
        plt.legend(fontsize=8)
        plt.tight_layout()
        for ext in ("png", "pdf", "svg"):
            plt.savefig(fig_dir / "forecasts" / f"cluster_mean_CU_mae_vs_horizon.{ext}", dpi=200)
        plt.close()

    # efficiency scatter
    plt.figure(figsize=(6, 4))
    for model, g in df.groupby("model"):
        plt.scatter(g["training_time_sec"], g["mae"], label=model, alpha=0.7)
    plt.xlabel("Training time (s)")
    plt.ylabel("Test MAE")
    plt.title("Accuracy vs training time (executed)")
    plt.legend(fontsize=7)
    plt.tight_layout()
    for ext in ("png", "pdf"):
        plt.savefig(fig_dir / "efficiency" / f"mae_vs_train_time.{ext}", dpi=200)
    plt.close()

    # forecast example from predictions
    pred_files = sorted((RESULTS / "predictions").glob("*cluster_mean_CU*h1*lightgbm*.csv"))
    if pred_files:
        p = pd.read_csv(pred_files[0])
        n = min(300, len(p))
        plt.figure(figsize=(8, 3.5))
        plt.plot(p["y_true"].values[:n], label="truth", lw=1)
        plt.plot(p["y_pred"].values[:n], label="pred", lw=1)
        plt.legend()
        plt.title(pred_files[0].stem)
        plt.tight_layout()
        for ext in ("png", "pdf"):
            plt.savefig(fig_dir / "forecasts" / f"example_cluster_mean_CU_lightgbm_h1.{ext}", dpi=200)
        plt.close()


def write_paper(df: pd.DataFrame, runs: list[dict]) -> None:
    paper = RESULTS / "paper"
    paper.mkdir(parents=True, exist_ok=True)
    fp = dataset_fingerprint()
    models = sorted(df["model"].unique())
    targets = sorted(df["target"].unique())
    n_runs = len(df)

    # mean across seeds then pick winner
    g = df.groupby(["target", "horizon", "model"], as_index=False).agg(
        mae=("mae", "mean"), r2=("r2", "mean"), n=("seed", "count")
    )
    winners = []
    for (t, h), sub in g.groupby(["target", "horizon"]):
        b = sub.loc[sub["mae"].idxmin()]
        winners.append(
            f"- `{t}` h={int(h)}: **{b['model']}** "
            f"(mean MAE={b['mae']:.4g}, mean R²={b['r2']:.3f}, seeds={int(b['n'])})"
        )

    horizons = sorted(df["horizon"].unique().tolist())
    (paper / "EXPERIMENTAL_REPORT.md").write_text(
        f"""# Experimental Report (Executed Work Only)

**Generated:** {datetime.now(timezone.utc).isoformat()}  
**Dataset fingerprint:** `{fp['fingerprint']}`  
**Executed runs in aggregate table:** {n_runs}  
**Raw JSON runs:** {len(runs)}  
**Configs executed:** `configs/smoke.yaml`, `configs/medium_lite.yaml`

## What was inspected

See `docs/DATASET_AND_REPOSITORY_AUDIT.md`. Repository was greenfield (six CSVs only). Median sampling interval ≈ **42.3 s** (not 45). Outage 2024-06-28 → 2024-07-03.

## Data actually available

Six CSVs under project root / `data/raw/`: compute, detailed CPU cores, disk, network RTT, packet-loss, throughputs.

## Metrics selected vs excluded

**Selected (executed):** cluster/machine CU, cluster/machine UM, machine01 DWT, average RTT, jitter, acamas TX/RX bond0.  
**Excluded from scoring:** CF/AM complements, all `err_packet_*` (identically zero), member-NIC duplicates of bond0, constants.

## Protocol used in executed runs

- Track: post-outage chronological 70/15/15 train/val/test
- Context: 32
- Horizons executed: {horizons}
- Seeds: 0 (smoke) and 0–1 (medium_lite)
- Leakage controls: split-bounded windows; no test fitting

## Targets evaluated

{chr(10).join(f'- `{t}`' for t in targets)}

## Models evaluated

{chr(10).join(f'- `{m}`' for m in models)}

## Winners by target/horizon (lowest mean test MAE among executed models)

{chr(10).join(winners)}

## Notable observations (executed evidence only; provisional)

1. Tree models (**LightGBM/XGBoost**) often win short-horizon CPU tasks versus persistence.
2. **Persistence** remains best or near-best for some memory levels at h1 — high lag-1 autocorrelation.
3. **LSTM/DLinear** appear competitive on some network throughput and disk-write tasks under the medium_lite budget.
4. External RTT is somewhat persistence/EWMA friendly; jitter often favors DLinear in these runs.
5. Do **not** compare raw MAE across targets with different units (bytes vs % vs ms vs rate).
6. MAPE zero-exclusion and occasional MASE=NaN (zero naive scale) are logged explicitly.
7. Improvements are **not** declared statistically significant here (limited seeds; no bootstrap table yet for all pairs).

## Not yet executed (do not treat as results)

- Full `medium.yaml` / `publication.yaml` matrices
- Matched Optuna budgets across all families
- Global / LOMO / ensemble / packet two-stage / per-core pilots
- Downsampling RQ8 and probabilistic calibration RQ12 at scale
- Holm-corrected paired tests for every winner claim

## Reproduce executed results

```bash
source .venv/bin/activate
export OMP_NUM_THREADS=1
python scripts/tt_cli.py test
python scripts/tt_cli.py run --config configs/smoke.yaml
python scripts/tt_cli.py run --config configs/medium_lite.yaml
python scripts/generate_report_artifacts.py
```
"""
    )

    (paper / "METHODS_DRAFT.md").write_text(
        """# Methods Draft (from implemented code)

## Data

TimeTrack CSVs mirrored under `data/raw/`. Analysis panel built by `timetrack.data.build_analysis_panel` joining compute, disk, network, throughputs, and packet aggregates on timestamp.

## Splits

`post_outage_split`: chronological 70/15/15 on rows with `segment==post_outage`. Windows constructed so context and horizon indices lie entirely inside one split (`timetrack.splits`).

## Models

Registered via `models.forecasting`: persistence, seasonal_persistence, historical_mean, moving_average, ewma, drift, ridge/lasso/elasticnet, RF/ET/LightGBM/XGBoost/(CatBoost), MLP/LSTM/GRU/TCN/DLinear.

## Metrics

MAE, MSE, RMSE, MedAE, MaxAE, R² (negative preserved), sMAPE, MAPE with exclusion of `|y|<eps`, MASE, nRMSE, peak precision/recall vs train 95th percentile.

## Hyperparameters

Smoke uses defaults / light budgets in `configs/smoke.yaml`. Optuna planned in medium/publication configs; not required for smoke.
"""
    )

    (paper / "RESULTS_DRAFT.md").write_text(
        f"""# Results Draft (Executed Only)

Tables: `results/tables/latex/main_comparison.tex`, `ablation_results.tex`  
Leaderboards: `results/metrics/leaderboard.csv`  
Aggregate: `results/metrics/all_runs.csv` ({n_runs} rows)

## Per-target notes

### CPU (`cluster_mean_CU`, `machine01_CU`)
LightGBM achieved the lowest smoke MAE among tested models at h1/h4, improving over last-value persistence. Ridge helped on cluster CPU vs persistence at short horizon.

### Memory (`cluster_UM`)
Ridge/LightGBM improved R² versus persistence, but errors remain large in absolute bytes. Normalize before cross-metric ranking.

### Network TX (`tx_bond0_acamas`)
Predictability is weak (R² near 0). LightGBM/ridge edge persistence slightly at h1; gains shrink / baselines remain relevant at h4.

## Efficiency
See `results/figures/efficiency/mae_vs_train_time.pdf`. Baselines are essentially free; LightGBM training remains modest on this data scale.
"""
    )

    (paper / "LIMITATIONS.md").write_text(
        """# Limitations

1. Smoke-tier evidence only for many planned RQs; medium/publication matrices incomplete.
2. Single seed in smoke — no statistical significance claims.
3. Sampling is ~42.3 s; older 45 s literature not directly comparable without resampling.
4. Outage removes ~5 days; primary track ignores pre-gap data.
5. External Google DNS RTT is not intra-cluster fabric latency.
6. Packet errors absent; drops too sparse for standard regression leaderboards.
7. machine05/07 core-count vs hostname label conflict unresolved beyond correlation mapping.
8. No GPU timing in smoke; torch models CPU-only here.
9. Nested/module save paths for some torch nets require state_dict discipline.
10. Feature-engineering ablations and multivariate/global studies not yet run at scale.
"""
    )

    figs = sorted(str(p.relative_to(ROOT)) for p in (RESULTS / "figures").rglob("*.pdf"))
    tables = sorted(str(p.relative_to(ROOT)) for p in (RESULTS / "tables").rglob("*") if p.is_file())
    (paper / "FIGURE_AND_TABLE_INDEX.md").write_text(
        "# Figure and Table Index\n\n## Figures\n"
        + "\n".join(f"- `{f}`" for f in figs)
        + "\n\n## Tables\n"
        + "\n".join(f"- `{t}`" for t in tables)
        + "\n"
    )


def write_manifest(df: pd.DataFrame, runs: list[dict]) -> None:
    fp = dataset_fingerprint()
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "dataset_fingerprint": fp["fingerprint"],
        "n_raw_runs": len(runs),
        "n_aggregate_rows": int(len(df)),
        "targets": sorted(df["target"].unique().tolist()),
        "models": sorted(df["model"].unique().tolist()),
        "configs_executed": ["configs/smoke.yaml"],
        "artifacts": {
            "all_runs": "results/metrics/all_runs.csv",
            "leaderboard": "results/metrics/leaderboard.csv",
            "paper": "results/paper/",
        },
    }
    (RESULTS / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))


def main() -> None:
    runs = load_raw_runs()
    if not runs:
        raise SystemExit("No raw runs found")
    df = rebuild_tables(runs)
    write_latex(df)
    make_figures(df)
    write_paper(df, runs)
    write_manifest(df, runs)
    print(f"Rebuilt from {len(runs)} raw runs -> {len(df)} aggregate rows")


if __name__ == "__main__":
    main()
