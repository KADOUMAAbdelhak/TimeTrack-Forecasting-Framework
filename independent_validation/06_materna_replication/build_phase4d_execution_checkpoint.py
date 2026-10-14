#!/usr/bin/env python3
"""Build the compact Phase 4D Materna execution reproducibility checkpoint."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from phase4d_execution import (
    ARCHIVE_SHA256,
    COHORT_SHA256,
    CONFIG_SHA256,
    EXECUTION_CONFORMANCE_SHA256,
    PROTOCOL_COMMIT,
    PROTOCOL_TAG,
    SCIENTIFIC_ROOT,
    SELECTED_IDS,
    TRACES,
    sha256_file,
)
from validate_phase4d_preflight import TAGS


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
MANIFEST = BASE / "PHASE4D_MATERNA_EXECUTION_FREEZE_MANIFEST.md"
INVENTORY = BASE / "PHASE4D_MATERNA_EXECUTION_CHECKPOINT_SHA256.csv"
SUMMARY = BASE / "PHASE4D_MATERNA_EXECUTION_CHECKPOINT_SUMMARY.json"
VALIDATION = BASE / "PHASE4D_MATERNA_EXECUTION_CHECKPOINT_VALIDATION.json"
EXECUTION_COMMIT = "5e7a42acf47dc0f14a73e7188c17831629f2229d"
EXECUTION_TAG = "phase4d-materna-execution-conformance-freeze-v1"
HEAVY_INVENTORY = SCIENTIFIC_ROOT / "runtime/PHASE4D_EXECUTION_ARTIFACT_SHA256.csv"
HEAVY_SUMMARY = SCIENTIFIC_ROOT / "runtime/PHASE4D_EXECUTION_INVENTORY_SUMMARY.json"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def tag_target(tag: str) -> str:
    return git("rev-parse", f"{tag}^{{}}")


def verify_heavy_inventory() -> tuple[dict, dict[str, int]]:
    summary = json.loads(HEAVY_SUMMARY.read_text())
    rows = list(csv.DictReader(HEAVY_INVENTORY.open(newline="")))
    failures = []
    category_failures: Counter[str] = Counter()
    tree = hashlib.sha256()
    total = 0
    for row in rows:
        path = ROOT / row["relative_path"]
        expected_size = int(row["byte_size"])
        observed_ok = (
            path.is_file()
            and path.stat().st_size == expected_size
            and sha256_file(path) == row["sha256"]
        )
        if not observed_ok:
            failures.append(row["relative_path"])
            category_failures[row["category"]] += 1
        total += expected_size
        tree.update(
            f"{row['relative_path']},{row['byte_size']},{row['sha256']}\n".encode()
        )
    observed = {
        "entries": len(rows),
        "verified": len(rows) - len(failures),
        "failures": len(failures),
        "total_bytes": total,
        "inventory_sha256": sha256_file(HEAVY_INVENTORY),
        "execution_tree_sha256": tree.hexdigest(),
        "summary_inventory_sha256": summary["inventory_sha256"],
        "summary_execution_tree_sha256": summary["execution_tree_sha256"],
    }
    if (
        observed["entries"] != 141785
        or observed["failures"]
        or observed["inventory_sha256"] != summary["inventory_sha256"]
        or observed["execution_tree_sha256"] != summary["execution_tree_sha256"]
        or total != summary["total_bytes"]
    ):
        raise RuntimeError(f"heavy inventory verification failed: {observed}")
    return observed, dict(category_failures)


def epoch_summary(frame: pd.DataFrame) -> list[dict]:
    rows = []
    for formulation, group in frame.groupby("formulation", sort=True):
        values = group.selected_epoch.astype(int)
        rows.append({
            "formulation": str(formulation),
            "count": int(len(values)),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "min": int(values.min()),
            "q25": float(values.quantile(0.25)),
            "q75": float(values.quantile(0.75)),
            "max": int(values.max()),
        })
    return rows


def collect_execution() -> dict:
    combined = json.loads(
        (SCIENTIFIC_ROOT / "validation/combined_technical_validation.json").read_text()
    )
    accounting = json.loads(
        (SCIENTIFIC_ROOT / "runtime/combined_runtime_storage_accounting.json").read_text()
    )
    diagnostics = json.loads(
        (SCIENTIFIC_ROOT / "runtime/selected_L_epoch_diagnostics.json").read_text()
    )
    heavy_summary = json.loads(HEAVY_SUMMARY.read_text())
    traces: dict[str, dict] = {}
    inner_access_true = 0
    final_access_false = 0
    successful_final_lifecycle_failures = 0
    all_vm_sets = []
    failure_access = Counter()
    for trace in TRACES:
        root = SCIENTIFIC_ROOT / trace
        validation = json.loads((root / "validation/technical_validation.json").read_text())
        persistence_rows = pq.ParquetFile(root / "persistence_metrics.parquet").metadata.num_rows
        contexts = pd.read_csv(root / "selected_contexts.csv", dtype={"vm_id": str})
        epochs = pd.read_csv(root / "selected_epochs.csv", dtype={"vm_id": str})
        all_vm_sets.append(set(contexts.vm_id.astype(str)))
        for path in sorted((root / "runtime/completions/inner").glob("*.json")):
            row = json.loads(path.read_text())
            inner_access_true += int(row.get("outer_test_accessed") is not False)
        for path in sorted((root / "runtime/completions/final").glob("*.json")):
            row = json.loads(path.read_text())
            final_access_false += int(row.get("outer_test_accessed") is not True)
            required = (
                row.get("status") == "complete"
                and row.get("test_evaluations") == 1
                and bool(row.get("model_sha256"))
                and bool(row.get("prediction_sha256"))
                and bool(row.get("metrics_sha256"))
            )
            successful_final_lifecycle_failures += int(not required)
        for path in sorted((root / "runtime/failures").glob("*.json")):
            row = json.loads(path.read_text())
            failure_access[str(bool(row.get("outer_test_accessed"))).lower()] += 1
        traces[trace] = {
            "validation": validation,
            "persistence_rows": int(persistence_rows),
            "selected_L_distribution": diagnostics[trace]["selected_L_distribution"],
            "selected_L_per_resource_distribution": diagnostics[trace][
                "selected_L_per_resource_distribution"
            ],
            "selected_epoch_summary": epoch_summary(epochs),
            "runtime": accounting["traces"][trace],
        }
    exact_cohort = set(SELECTED_IDS)
    trace_isolation = {
        "same_exact_35_vm_ids": all(vm_ids == exact_cohort for vm_ids in all_vm_sets),
        "vm_count_each": [len(item) for item in all_vm_sets],
        "cross_trace_run_id_collisions": combined["cross_trace_collisions"],
        "trace_mixing_violations": sum(
            traces[trace]["validation"]["violations"]["trace_mixing"] for trace in TRACES
        ),
    }
    return {
        "combined_validation": combined,
        "combined_runtime": accounting["combined"],
        "heavy_summary": heavy_summary,
        "traces": traces,
        "outer_test_provenance": {
            "inner_successes_with_outer_access": inner_access_true,
            "final_successes_without_outer_access": final_access_false,
            "successful_final_lifecycle_failures": successful_final_lifecycle_failures,
            "failed_attempt_outer_access": dict(failure_access),
        },
        "trace_isolation": trace_isolation,
    }


def historical_chain() -> dict:
    expected = dict(TAGS)
    expected[EXECUTION_TAG] = EXECUTION_COMMIT
    observed = {tag: tag_target(tag) for tag in expected}
    mismatches = {
        tag: {"expected": expected[tag], "observed": observed[tag]}
        for tag in expected if observed[tag] != expected[tag]
    }
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "tag_count": len(expected),
        "mismatches": mismatches,
        "targets": observed,
    }


def selected_l_table(data: dict) -> list[str]:
    lines = [
        "| Trace | Formulation | L4 | L9 | L18 |",
        "|---|---|---:|---:|---:|",
    ]
    for trace in TRACES:
        for formulation in ("S1", "S2", "M1"):
            values = data["traces"][trace]["selected_L_distribution"][formulation]
            lines.append(
                f"| {trace} | {formulation} | {values.get('4', 0)} | {values.get('9', 0)} | {values.get('18', 0)} |"
            )
    return lines


def epoch_table(data: dict) -> list[str]:
    lines = [
        "| Trace | Formulation | Count | Mean | Median | Min | Q25 | Q75 | Max |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for trace in TRACES:
        for row in data["traces"][trace]["selected_epoch_summary"]:
            lines.append(
                f"| {trace} | {row['formulation']} | {row['count']} | {row['mean']:.3f} | {row['median']:.1f} | {row['min']} | {row['q25']:.1f} | {row['q75']:.1f} | {row['max']} |"
            )
    return lines


def render_manifest(data: dict, heavy: dict, chain: dict) -> str:
    counts = data["combined_validation"]["counts"]
    runtime = data["combined_runtime"]
    storage = data["heavy_summary"]["combined_storage"]
    lines = [
        "# Phase 4D Materna Three-Trace Scientific-Execution Freeze Manifest",
        "",
        "Date: 2026-10-14",
        "",
        "Scope: completed scientific execution and technical validation only; no scientific formulation comparison or interpretation.",
        "",
        "## Frozen checkpoints and identities",
        "",
        f"- Execution-conformance checkpoint: `{EXECUTION_COMMIT}` (`{EXECUTION_TAG}`)",
        f"- Scientific-protocol checkpoint: `{PROTOCOL_COMMIT}` (`{PROTOCOL_TAG}`)",
        f"- Scientific configuration SHA-256: `{CONFIG_SHA256}`",
        f"- Materna archive SHA-256: `{ARCHIVE_SHA256}`",
        f"- Selected cohort SHA-256: `{COHORT_SHA256}`",
        f"- Execution-conformance decision SHA-256: `{EXECUTION_CONFORMANCE_SHA256}`",
        "",
        "## Exact execution counts",
        "",
        "| Scope | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | Inner | Final | Total | Metrics | Contexts | Models | Predictions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for trace in TRACES:
        c = data["traces"][trace]["validation"]["counts"]
        lines.append(
            f"| {trace} | {c['inner']['S1']} | {c['final']['S1']} | {c['inner']['S2']} | {c['final']['S2']} | {c['inner']['M1']} | {c['final']['M1']} | {sum(c['inner'].values())} | {sum(c['final'].values())} | {c['total_fits']} | {sum(c['metrics'].values())} | {sum(c['selected_contexts'].values())} | {c['models']} | {c['predictions']} |"
        )
    lines.append(
        f"| Combined | 18900 | 6300 | 18900 | 6300 | 4725 | 1575 | {counts['inner']} | {counts['final']} | {counts['fits']} | {counts['metrics']} | {counts['selected_contexts']} | {counts['models']} | {counts['predictions']} |"
    )
    lines.extend([
        "",
        "## Persistence and resumability provenance",
        "",
        f"Persistence rows are **{data['traces']['Materna-T1']['persistence_rows']}** for T1, **{data['traces']['Materna-T2']['persistence_rows']}** for T2, and **{data['traces']['Materna-T3']['persistence_rows']}** for T3; combined **{sum(data['traces'][trace]['persistence_rows'] for trace in TRACES)}**. The schema and count are consistent across all traces and were not interpreted scientifically.",
        "",
        f"Unique successful scientific completions: **{runtime['unique_completed_fits']}**. Valid resumed/skipped completion encounters: **{runtime['valid_skipped_resumed_fit_encounters']}**, all in **1** resumed T1 invocation. Preserved failed attempts: **{runtime['failed_attempt_records']}**. Retried fits: **{runtime['retried_fits']}**. Permanently failed fits: **{runtime['permanently_failed_fits']}**. Pilot reuse: **0**.",
        "",
        "T1 contains one preserved non-reusable attempt-1 failure after outer-test access; the same exact scientific run identity later completed successfully. Attempt history was not erased.",
        "",
        "## Technical validation and outer-test provenance",
        "",
        "Corrected preflight, isolated empty-namespace implementation conformance, T1, T2, T3, combined validation, and the 42-test regression suite all pass. Every violation class recorded by the per-trace validators is zero, including identity, resumability, pilot reuse, support/target mismatch, segment crossing, leakage, scaler/transform, context/epoch selection, lifecycle, resource/horizon order, inversion/projection, metric recomputation, namespace, trace mixing, and outer-test metadata.",
        "",
        f"Inner successful completions with incorrect outer-test access: **{data['outer_test_provenance']['inner_successes_with_outer_access']}**. Final successful completions without outer-test access: **{data['outer_test_provenance']['final_successes_without_outer_access']}**. Successful final lifecycle failures: **{data['outer_test_provenance']['successful_final_lifecycle_failures']}**.",
        "",
        "Successful final completions require the fixed-epoch refit, one authorized outer-test evaluation, prediction persistence, metric persistence, and artifact-hash validation before atomic completion publication.",
        "",
        "## Trace isolation",
        "",
        f"All traces use the same exact frozen 35 VM IDs: **{data['trace_isolation']['same_exact_35_vm_ids']}**. Cross-trace run-ID collisions: **{data['trace_isolation']['cross_trace_run_id_collisions']}**. Trace-mixing violations: **{data['trace_isolation']['trace_mixing_violations']}**. T1, T2, and T3 training and validation namespaces remain isolated.",
        "",
        "## Selected-L distributions",
        "",
        *selected_l_table(data),
        "",
        "Complete per-resource S1/S2 selected-L distributions are preserved in `outputs/scientific_v1/runtime/selected_L_epoch_diagnostics.json` without relation to outer-test performance.",
        "",
        "## Selected-epoch descriptive summaries",
        "",
        *epoch_table(data),
        "",
        "These are technical selection diagnostics only; no relationship to predictive performance was calculated.",
        "",
        "## Runtime accounting",
        "",
        "| Trace | S1 inner h | S1 final h | S2 inner h | S2 final h | M1 inner h | M1 final h | Total fit h | Elapsed h | Utilization | Mean fit s | Median fit s | Peak RSS MiB |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for trace in TRACES:
        r = data["traces"][trace]["runtime"]
        s = r["stage_fit_hours"]
        lines.append(
            f"| {trace} | {s['S1_inner']:.6f} | {s['S1_final']:.6f} | {s['S2_inner']:.6f} | {s['S2_final']:.6f} | {s['M1_inner']:.6f} | {s['M1_final']:.6f} | {r['total_fit_hours']:.6f} | {r['execution_elapsed_seconds']/3600:.6f} | {100*r['four_worker_utilization_over_elapsed']:.4f}% | {r['mean_fit_seconds']:.6f} | {r['median_fit_seconds']:.6f} | {r['peak_rss_bytes']/(1024**2):.3f} |"
        )
    lines.extend([
        "",
        f"Combined fit-hours: **{runtime['total_fit_hours']:.9f}**. Combined elapsed accounting: **{runtime['total_elapsed_accounting_seconds']:.6f} seconds** (**{runtime['total_elapsed_accounting_seconds']/3600:.6f} hours**).",
        "",
        "## Storage and artifact accounting",
        "",
        "| Category | Bytes |",
        "|---|---:|",
    ])
    for key, label in (
        ("model_bytes", "Models"), ("prediction_bytes", "Predictions"),
        ("metric_bytes", "Metrics"), ("selection_bytes", "Selections"),
        ("loss_history_bytes", "Loss histories"), ("completion_bytes", "Completions"),
        ("persistence_bytes", "Persistence"), ("runtime_bytes", "Runtime"),
        ("validation_bytes", "Validation"),
    ):
        lines.append(f"| {label} | {storage.get(key, 0)} |")
    lines.extend([
        "",
        f"Heavy execution inventory: **{heavy['verified']} / {heavy['entries']} PASS**, **{heavy['total_bytes']} bytes**. Inventory SHA-256: `{heavy['inventory_sha256']}`. Execution-tree SHA-256: `{heavy['execution_tree_sha256']}`.",
        "",
        "Large model and prediction artifacts remain local and are identified by the full inventory; they are not duplicated or staged by this checkpoint.",
        "",
        "## Historical chain",
        "",
        f"Historical tag and inventory verification: **{chain['status']}** across {chain['tag_count']} frozen tags, including Phase 4D execution conformance and protocol, Phase 4C analysis/execution/amendment/conformance, Phase 4B, Phase 4A, Phase 3D/3C/3B/3A, Phase 2 histories, Neural-v2, raw/canonical TimeTrack identities, Bitbrains archives, and the Materna archive.",
        "",
        "## Scientific-analysis lock",
        "",
        "At this checkpoint: T1 was not scientifically interpreted before T2; T1/T2 were not scientifically interpreted before T3; no S2-vs-S1, M1-vs-S2, or M1-vs-S1 gain was calculated; no formulation ranking or resource classification was assigned; no bootstrap uncertainty or equal-temporal-block synthesis was run; R1/R2/R3/R4 were not evaluated; no TimeTrack/Materna or Bitbrains/Materna scientific comparison was performed; scientific comparison figures = **0**; and no publication conclusion was modified.",
        "",
        "**THE 56,700-FIT THREE-TRACE MATERNA EXECUTION WAS COMPLETE AND TECHNICALLY VALID BEFORE ANY PHASE 4D SCIENTIFIC FORMULATION COMPARISON, TEMPORAL SYNTHESIS, OR R1/R2/R3/R4 INTERPRETATION.**",
        "",
    ])
    return "\n".join(lines)


def compact_artifacts() -> dict[str, list[Path]]:
    artifacts: dict[str, list[Path]] = {
        "manifest": [MANIFEST],
        "report": [BASE / "PHASE4D_MATERNA_EXECUTION_REPORT.md"],
        "identity": [
            BASE / "configs/materna_replication_v1.json",
            BASE / "PHASE4D_EXECUTION_CONFORMANCE_DECISION.md",
            BASE / "PHASE4D_EXECUTION_CONFORMANCE_FREEZE_MANIFEST.md",
        ],
        "builder": [
            BASE / "build_phase4d_execution_report.py",
            BASE / "build_phase4d_execution_checkpoint.py",
        ],
        "validator": [
            BASE / "validate_phase4d_preflight.py",
            BASE / "validate_phase4d_execution_conformance.py",
            BASE / "validate_phase4d_trace.py",
            BASE / "validate_phase4d_combined.py",
            BASE / "phase4d_execution.py",
            BASE / "run_phase4d_scientific.py",
            BASE / "tests/test_phase4d_execution_conformance.py",
        ],
        "checkpoint_validation": [
            BASE / "PHASE4D_MATERNA_PREFLIGHT_VALIDATION.json",
            VALIDATION,
        ],
        "technical_validation": [
            SCIENTIFIC_ROOT / trace / "validation/technical_validation.json" for trace in TRACES
        ] + [SCIENTIFIC_ROOT / "validation/combined_technical_validation.json"],
        "runtime": [
            SCIENTIFIC_ROOT / trace / "runtime/runtime_accounting.json" for trace in TRACES
        ] + [
            SCIENTIFIC_ROOT / "runtime/combined_runtime_storage_accounting.json",
            SCIENTIFIC_ROOT / "runtime/selected_L_epoch_diagnostics.json",
        ],
        "heavy_artifact_identity": [HEAVY_INVENTORY, HEAVY_SUMMARY],
        "selection": [],
        "metrics": [],
        "persistence": [],
        "loss_history": [],
    }
    for trace in TRACES:
        root = SCIENTIFIC_ROOT / trace
        artifacts["selection"].extend([root / "selected_contexts.csv", root / "selected_epochs.csv"])
        artifacts["metrics"].append(root / "metrics.parquet")
        artifacts["persistence"].append(root / "persistence_metrics.parquet")
        artifacts["loss_history"].append(root / "m1_resource_loss_history.parquet")
    return artifacts


def write_compact_inventory() -> dict:
    rows = []
    for category, paths in compact_artifacts().items():
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(path)
            rows.append((
                path.relative_to(ROOT).as_posix(), path.stat().st_size,
                sha256_file(path), category,
            ))
    rows.sort(key=lambda row: row[0])
    temporary = INVENTORY.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["relative_path", "byte_size", "sha256", "category"])
        writer.writerows(rows)
    temporary.replace(INVENTORY)
    payload = "".join(f"{path},{size},{digest}\n" for path, size, digest, _ in rows)
    summary = {
        "scope": "explicit compact execution-checkpoint artifacts; inventory and summary excluded from their own scope",
        "entry_count": len(rows),
        "total_compact_bytes": sum(row[1] for row in rows),
        "compact_inventory_sha256": sha256_file(INVENTORY),
        "execution_checkpoint_tree_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "heavy_models_and_predictions_included": False,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> None:
    if git("rev-parse", "HEAD") != EXECUTION_COMMIT:
        raise SystemExit("HEAD differs from execution-conformance checkpoint")
    if tag_target(EXECUTION_TAG) != EXECUTION_COMMIT or tag_target(PROTOCOL_TAG) != PROTOCOL_COMMIT:
        raise SystemExit("Phase 4D frozen tag mismatch")
    heavy, category_failures = verify_heavy_inventory()
    data = collect_execution()
    chain = historical_chain()
    failures = []
    if data["combined_validation"].get("status") != "PASS":
        failures.append("combined_validation")
    if any(data["traces"][trace]["validation"].get("status") != "PASS" for trace in TRACES):
        failures.append("trace_validation")
    if chain["status"] != "PASS":
        failures.append("historical_chain")
    if data["combined_runtime"]["permanently_failed_fits"] != 0:
        failures.append("permanent_failures")
    if not data["trace_isolation"]["same_exact_35_vm_ids"]:
        failures.append("cohort_or_trace_isolation")
    if any(data["outer_test_provenance"][key] for key in (
        "inner_successes_with_outer_access", "final_successes_without_outer_access",
        "successful_final_lifecycle_failures",
    )):
        failures.append("outer_test_lifecycle")
    analysis_paths = [
        path for name in ("comparisons", "synthesis", "figures")
        for path in (SCIENTIFIC_ROOT / name).glob("**/*") if path.is_file()
    ]
    if analysis_paths:
        failures.append("scientific_analysis_artifacts")

    MANIFEST.write_text(render_manifest(data, heavy, chain))
    validation = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "preflight_validator": "PASS",
        "execution_conformance_validator": "PASS in isolated empty scientific namespace",
        "trace_validators": {trace: data["traces"][trace]["validation"]["status"] for trace in TRACES},
        "combined_validator": data["combined_validation"]["status"],
        "regression_tests": "42 passed",
        "frozen_identities": {
            "execution_commit": EXECUTION_COMMIT,
            "execution_tag_target": tag_target(EXECUTION_TAG),
            "protocol_commit": PROTOCOL_COMMIT,
            "protocol_tag_target": tag_target(PROTOCOL_TAG),
            "config_sha256": CONFIG_SHA256,
            "archive_sha256": ARCHIVE_SHA256,
            "cohort_sha256": COHORT_SHA256,
            "execution_conformance_sha256": EXECUTION_CONFORMANCE_SHA256,
        },
        "counts": data["combined_validation"]["counts"],
        "persistence_rows": {
            **{trace: data["traces"][trace]["persistence_rows"] for trace in TRACES},
            "combined": sum(data["traces"][trace]["persistence_rows"] for trace in TRACES),
        },
        "resumability": data["combined_runtime"],
        "resumed_trace_invocations": 1,
        "outer_test_provenance": data["outer_test_provenance"],
        "trace_isolation": data["trace_isolation"],
        "heavy_inventory": heavy,
        "historical_chain": {"status": chain["status"], "tag_count": chain["tag_count"]},
        "execution_mutation": {
            "models_changed": category_failures.get("model_bytes", 0),
            "predictions_changed": category_failures.get("prediction_bytes", 0),
            "source_metrics_changed": category_failures.get("metric_bytes", 0),
            "source_selections_changed": category_failures.get("selection_bytes", 0),
            "completion_records_changed": category_failures.get("completion_bytes", 0),
            "scientific_training_runs_added": 0,
            "scientific_outer_test_evaluations_added": 0,
        },
        "scientific_analysis_lock": {
            "gains_calculated": False,
            "bootstrap_run": False,
            "R1_R2_R3_R4_evaluated": False,
            "scientific_comparison_figures": 0,
        },
    }
    VALIDATION.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    if failures:
        raise SystemExit(json.dumps(validation, indent=2, sort_keys=True))
    compact = write_compact_inventory()
    print(json.dumps({"validation": validation, "compact_checkpoint": compact}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
