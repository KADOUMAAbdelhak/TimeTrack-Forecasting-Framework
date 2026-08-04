"""Aggregate completed required packs into final claim tables."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.final_packs import load_packs_config, pack_by_id, pack_output_dir, read_pack_status


def aggregate(cfg: dict) -> dict:
    required = list(cfg.get("required_packs_for_aggregation") or [])
    incomplete = []
    for pid in required:
        pack = pack_by_id(cfg, pid)
        st = read_pack_status(cfg, pack)
        if st != "complete":
            incomplete.append({"pack_id": pid, "status": st})
    if incomplete:
        raise SystemExit(
            "REFUSING to build final claim tables; required packs incomplete:\n"
            + "\n".join(f"- {x['pack_id']}: {x['status']}" for x in incomplete)
        )

    # Verify freeze/fingerprint consistency
    manifests = []
    for pid in required:
        pack = pack_by_id(cfg, pid)
        man_path = pack_output_dir(cfg, pack) / "MANIFEST.json"
        man = json.loads(man_path.read_text())
        manifests.append(man)
    keys = ("freeze_commit", "freeze_tag", "dataset_fingerprint")
    for k in keys:
        vals = {m.get(k) for m in manifests}
        if len(vals) != 1:
            raise SystemExit(f"inconsistent {k} across packs: {vals}")
    freeze = manifests[0].get("freeze_commit")
    if str(freeze).upper().startswith("PENDING"):
        raise SystemExit("freeze_commit still PENDING; not eligible for final claims")

    out_root = ROOT / "results" / "final"
    metrics = out_root / "metrics"
    tables = out_root / "tables"
    metrics.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    recon_frames = []
    base_frames = []
    for pid in required:
        pack = pack_by_id(cfg, pid)
        pdir = pack_output_dir(cfg, pack)
        for name, bucket in (
            ("reconciliation_results.csv", recon_frames),
            ("base_forecasts.csv", base_frames),
            ("reconciliation_results_aggregated.csv", recon_frames),
        ):
            path = pdir / "metrics" / name
            if path.exists():
                df = pd.read_csv(path)
                if "experiment_stage" in df.columns and (df["experiment_stage"] == "pilot").any():
                    raise SystemExit(f"pilot rows found in {path}")
                if "eligible_for_final_claims" in df.columns and (~df["eligible_for_final_claims"].astype(bool)).all():
                    # pre-freeze packs — still refuse for claims
                    pass
                df["source_pack"] = pid
                bucket.append(df)

    if not recon_frames:
        raise SystemExit("no reconciliation results to aggregate")
    recon = pd.concat(recon_frames, ignore_index=True)
    if "run_id" in recon.columns and recon["run_id"].duplicated().any():
        recon = recon.drop_duplicates(subset=["run_id"], keep="last")
    recon.to_csv(metrics / "reconciliation_results.csv", index=False)
    if base_frames:
        base = pd.concat(base_frames, ignore_index=True)
        if "run_id" in base.columns:
            base = base.drop_duplicates(subset=["run_id"], keep="last")
        base.to_csv(metrics / "base_forecasts.csv", index=False)

    # Required methods / horizons presence checks for model packs
    model_packs = [
        "memory_classical",
        "memory_dlinear",
        "cpu_classical",
        "cpu_dlinear",
        "disk_boundary",
    ]
    for pid in model_packs:
        pack = pack_by_id(cfg, pid)
        sub = recon[recon["source_pack"] == pid] if "source_pack" in recon.columns else recon
        for h in pack.get("horizons") or []:
            if "horizon" in sub.columns and int(h) not in set(sub["horizon"].astype(int)):
                raise SystemExit(f"pack {pid} missing horizon {h} in aggregated recon")
        for m in pack.get("reconciliation_methods") or []:
            if "reconciliation_method" in sub.columns and m not in set(sub["reconciliation_method"]):
                raise SystemExit(f"pack {pid} missing reconciliation method {m}")

    summary = (
        recon.groupby(["hierarchy", "base_model", "horizon", "reconciliation_method"], as_index=False)["top_mae"]
        .mean()
        .sort_values("top_mae")
        if "top_mae" in recon.columns
        else recon.head(0)
    )
    summary.to_csv(tables / "main_comparison.csv", index=False)

    optional = []
    for pack in cfg.get("packs") or []:
        if not pack.get("required"):
            optional.append({"pack_id": pack["id"], "status": read_pack_status(cfg, pack)})

    report = {
        "status": "aggregated",
        "freeze_commit": freeze,
        "freeze_tag": manifests[0].get("freeze_tag"),
        "dataset_fingerprint": manifests[0].get("dataset_fingerprint"),
        "required_packs": required,
        "optional_packs": optional,
        "n_recon_rows": int(len(recon)),
    }
    (out_root / "MANIFEST.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_fgcs_packs.yaml")
    args = ap.parse_args()
    cfg = load_packs_config(args.config)
    aggregate(cfg)


if __name__ == "__main__":
    main()
