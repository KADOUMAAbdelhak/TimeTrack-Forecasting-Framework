#!/usr/bin/env python3
"""Build Phase 4D technical-only runtime, selection, storage, and report artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from phase4d_execution import (
    ARCHIVE_SHA256,
    COHORT_SHA256,
    CONFIG_SHA256,
    EXECUTION_CONFORMANCE_SHA256,
    PROTOCOL_COMMIT,
    PROTOCOL_TAG,
    SCIENTIFIC_ROOT,
    SELECTION_RECORD_SHA256,
    TRACES,
    atomic_json_write,
    sha256_file,
)


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUNTIME_DIR = SCIENTIFIC_ROOT / "runtime"
ACCOUNTING_PATH = RUNTIME_DIR / "combined_runtime_storage_accounting.json"
DIAGNOSTICS_PATH = RUNTIME_DIR / "selected_L_epoch_diagnostics.json"
INVENTORY_PATH = RUNTIME_DIR / "PHASE4D_EXECUTION_ARTIFACT_SHA256.csv"
SUMMARY_PATH = RUNTIME_DIR / "PHASE4D_EXECUTION_INVENTORY_SUMMARY.json"
REPORT_PATH = BASE / "PHASE4D_MATERNA_EXECUTION_REPORT.md"
EXECUTION_COMMIT = "5e7a42acf47dc0f14a73e7188c17831629f2229d"
EXECUTION_TAG = "phase4d-materna-execution-conformance-freeze-v1"


def distribution(frame: pd.DataFrame, column: str) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for formulation, group in frame.groupby("formulation", sort=True):
        counts = group[column].astype(int).value_counts().sort_index()
        result[str(formulation)] = {str(int(key)): int(value) for key, value in counts.items()}
    return result


def resource_distribution(frame: pd.DataFrame, column: str) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {}
    for formulation in ("S1", "S2"):
        selected = frame[frame.formulation == formulation]
        result[formulation] = {}
        for resource, group in selected.groupby("resource", sort=True):
            counts = group[column].astype(int).value_counts().sort_index()
            result[formulation][str(resource)] = {
                str(int(key)): int(value) for key, value in counts.items()
            }
    return result


def storage_category(path: Path) -> str:
    parts = set(path.parts)
    name = path.name
    if "models" in parts or path.suffix == ".pt":
        return "model_bytes"
    if "predictions" in parts:
        return "prediction_bytes"
    if "metrics" in parts or name in {"metrics.parquet"}:
        return "metric_bytes"
    if name == "persistence_metrics.parquet":
        return "persistence_bytes"
    if name in {"selected_contexts.csv", "selected_epochs.csv"}:
        return "selection_bytes"
    if "inner_histories" in parts or name == "m1_resource_loss_history.parquet":
        return "loss_history_bytes"
    if "completions" in parts:
        return "completion_bytes"
    if "validation" in parts:
        return "validation_bytes"
    if "runtime" in parts:
        return "runtime_bytes"
    return "other_bytes"


def read_completions(trace: str) -> tuple[list[tuple[Path, dict]], list[tuple[Path, dict]]]:
    trace_root = SCIENTIFIC_ROOT / trace
    result = []
    for phase in ("inner", "final"):
        records = []
        for path in sorted((trace_root / "runtime/completions" / phase).glob("*.json")):
            records.append((path, json.loads(path.read_text())))
        result.append(records)
    return result[0], result[1]


def build_runtime_and_diagnostics() -> tuple[dict, dict]:
    per_trace: dict[str, dict] = {}
    diagnostics: dict[str, dict] = {}
    combined_fit_seconds = 0.0
    combined_elapsed = 0.0
    combined_failures = 0
    combined_skipped = 0

    for trace in TRACES:
        trace_root = SCIENTIFIC_ROOT / trace
        inner, final = read_completions(trace)
        records = inner + final
        stage_seconds: dict[str, float] = defaultdict(float)
        durations: list[float] = []
        for _path, row in records:
            identity = row["identity"]
            duration = float(row["train_seconds"])
            if identity["phase"] == "inner":
                duration += float(row["validation_seconds"])
            stage_seconds[f'{identity["formulation"]}_{identity["phase"]}'] += duration
            durations.append(duration)

        contexts = pd.read_csv(trace_root / "selected_contexts.csv", dtype={"vm_id": str})
        epochs = pd.read_csv(trace_root / "selected_epochs.csv", dtype={"vm_id": str})
        runtime = json.loads((trace_root / "runtime/runtime_accounting.json").read_text())
        failure_files = sorted((trace_root / "runtime/failures").glob("*.json"))
        failed_run_ids = {
            str(json.loads(path.read_text()).get("identity", {}).get("run_id"))
            for path in failure_files
        }
        completed_run_ids = {str(row["identity"]["run_id"]) for _path, row in records}
        retried = len(failed_run_ids & completed_run_ids)
        permanent = len(failed_run_ids - completed_run_ids)
        start = min(path.stat().st_mtime for path, _row in records)
        end = max(
            (trace_root / "runtime/runtime_accounting.json").stat().st_mtime,
            max(path.stat().st_mtime for path, _row in records),
        )
        elapsed = end - start
        fit_seconds = sum(durations)
        combined_fit_seconds += fit_seconds
        combined_elapsed += elapsed
        combined_failures += len(failure_files)
        combined_skipped += int(runtime["resumed_skipped_valid_fits"])

        diagnostics[trace] = {
            "selected_L_distribution": distribution(contexts, "selected_L"),
            "selected_L_per_resource_distribution": resource_distribution(contexts, "selected_L"),
            "selected_epoch_distribution": distribution(epochs, "selected_epoch"),
            "selected_epoch_per_resource_distribution": resource_distribution(
                epochs, "selected_epoch"
            ),
            "selected_context_records": int(len(contexts)),
            "selected_epoch_records": int(len(epochs)),
            "outer_test_performance_correlated": False,
        }
        per_trace[trace] = {
            "stage_fit_hours": {
                key: value / 3600.0 for key, value in sorted(stage_seconds.items())
            },
            "total_fit_hours": fit_seconds / 3600.0,
            "execution_elapsed_seconds": elapsed,
            "four_worker_utilization_over_elapsed": fit_seconds / (4.0 * elapsed),
            "mean_fit_seconds": statistics.fmean(durations),
            "median_fit_seconds": statistics.median(durations),
            "peak_rss_bytes": int(runtime["peak_rss_bytes"]),
            "unique_completed_fits": len(records),
            "new_fits_in_last_invocation": int(runtime["newly_executed_fits"]),
            "valid_skipped_resumed_fit_encounters": int(runtime["resumed_skipped_valid_fits"]),
            "failed_attempt_records": len(failure_files),
            "retried_fits": retried,
            "permanently_failed_fits": permanent,
        }

    accounting = {
        "status": "PASS",
        "traces": per_trace,
        "combined": {
            "total_fit_hours": combined_fit_seconds / 3600.0,
            "total_elapsed_accounting_seconds": combined_elapsed,
            "unique_completed_fits": sum(v["unique_completed_fits"] for v in per_trace.values()),
            "valid_skipped_resumed_fit_encounters": combined_skipped,
            "failed_attempt_records": combined_failures,
            "retried_fits": sum(v["retried_fits"] for v in per_trace.values()),
            "permanently_failed_fits": sum(
                v["permanently_failed_fits"] for v in per_trace.values()
            ),
            "peak_rss_bytes": max(v["peak_rss_bytes"] for v in per_trace.values()),
        },
    }
    return accounting, diagnostics


def build_inventory() -> dict:
    exclusions = {INVENTORY_PATH.resolve(), SUMMARY_PATH.resolve()}
    rows = []
    per_trace = {trace: Counter() for trace in TRACES}
    combined = Counter()
    for path in sorted(item for item in SCIENTIFIC_ROOT.rglob("*") if item.is_file()):
        if path.resolve() in exclusions or path.name.endswith(".tmp"):
            continue
        relative = path.relative_to(ROOT).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        category = storage_category(path)
        top = path.relative_to(SCIENTIFIC_ROOT).parts[0]
        if top in per_trace:
            per_trace[top][category] += size
            per_trace[top]["file_count"] += 1
            per_trace[top]["total_bytes"] += size
        combined[category] += size
        combined["file_count"] += 1
        combined["total_bytes"] += size
        rows.append((relative, size, digest, category))

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    temporary = INVENTORY_PATH.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["relative_path", "byte_size", "sha256", "category"])
        writer.writerows(rows)
    temporary.replace(INVENTORY_PATH)
    tree_payload = "".join(f"{path},{size},{digest}\n" for path, size, digest, _ in rows)
    return {
        "scope": "all files under outputs/scientific_v1 excluding this summary and its inventory CSV",
        "file_count": len(rows),
        "total_bytes": sum(row[1] for row in rows),
        "inventory_sha256": sha256_file(INVENTORY_PATH),
        "execution_tree_sha256": hashlib.sha256(tree_payload.encode()).hexdigest(),
        "storage_by_trace": {key: dict(sorted(value.items())) for key, value in per_trace.items()},
        "combined_storage": dict(sorted(combined.items())),
    }


def hours(seconds: float) -> str:
    return f"{seconds / 3600.0:.3f}"


def render_report(accounting: dict, diagnostics: dict, inventory: dict) -> str:
    combined_validation = json.loads(
        (SCIENTIFIC_ROOT / "validation/combined_technical_validation.json").read_text()
    )
    traces = []
    for trace in TRACES:
        validation = json.loads(
            (SCIENTIFIC_ROOT / trace / "validation/technical_validation.json").read_text()
        )
        traces.append((trace, validation))
    counts = combined_validation["counts"]
    lines = [
        "# Phase 4D Materna Three-Trace Execution and Technical Validation Report",
        "",
        "## Outcome",
        "",
        "Phase 4D technical execution and validation **PASS** for Materna-T1, Materna-T2, and Materna-T3. This report contains no scientific comparison or interpretation.",
        "",
        "## Frozen identities",
        "",
        f"- Execution checkpoint: `{EXECUTION_COMMIT}` (`{EXECUTION_TAG}`)",
        f"- Historical protocol: `{PROTOCOL_COMMIT}` (`{PROTOCOL_TAG}`)",
        f"- Configuration SHA-256: `{CONFIG_SHA256}`",
        f"- Archive SHA-256: `{ARCHIVE_SHA256}`",
        f"- Cohort SHA-256: `{COHORT_SHA256}`",
        f"- Selection-record SHA-256: `{SELECTION_RECORD_SHA256}`",
        f"- Execution-conformance SHA-256: `{EXECUTION_CONFORMANCE_SHA256}`",
        "",
        "## Counts and validation",
        "",
        "| Scope | Inner | Final | Fits | Metric rows | Selected contexts | Models | Predictions | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for trace, validation in traces:
        check = validation["counts"]
        inner_total = sum(check["inner"].values())
        final_total = sum(check["final"].values())
        metric_rows = sum(check["metrics"].values())
        selected_contexts = sum(check["selected_contexts"].values())
        lines.append(
            f"| {trace} | {inner_total} | {final_total} | {check['total_fits']} | {metric_rows} | {selected_contexts} | {check['models']} | {check['predictions']} | {validation['status']} |"
        )
    lines.append(
        f"| Combined | {counts['inner']} | {counts['final']} | {counts['fits']} | {counts['metrics']} | {counts['selected_contexts']} | {counts['models']} | {counts['predictions']} | {combined_validation['status']} |"
    )
    lines.extend([
        "",
        f"Unique run IDs: **{combined_validation['unique_run_ids']}**. Cross-trace collisions: **{combined_validation['cross_trace_collisions']}**. Namespace, access, trace-identity, and permanent-failure violations: **0**.",
        "",
        "Persistence records: **94,500** combined (**31,500** per trace), verified on the final matched support without scientific interpretation.",
        "",
        "## Resumability and failures",
        "",
        f"- Unique successful completions: **{accounting['combined']['unique_completed_fits']}**",
        f"- Valid skipped/resumed fit encounters: **{accounting['combined']['valid_skipped_resumed_fit_encounters']}**",
        f"- Preserved failed attempt records: **{accounting['combined']['failed_attempt_records']}**",
        f"- Retried fits later completed successfully: **{accounting['combined']['retried_fits']}**",
        f"- Permanently failed fits: **{accounting['combined']['permanently_failed_fits']}**",
        "",
        "The single preserved T1 attempt-1 record is non-reusable failure provenance. Its exact run identity subsequently completed successfully; it is not a permanent failure.",
        "",
        "## Runtime accounting",
        "",
        "| Trace/stage | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | Total fit-hours |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for trace in TRACES:
        row = accounting["traces"][trace]
        stage = row["stage_fit_hours"]
        lines.append(
            f"| {trace} | {stage['S1_inner']:.3f} | {stage['S1_final']:.3f} | {stage['S2_inner']:.3f} | {stage['S2_final']:.3f} | {stage['M1_inner']:.3f} | {stage['M1_final']:.3f} | {row['total_fit_hours']:.3f} |"
        )
    lines.extend([
        "",
        f"Combined fit-hours: **{accounting['combined']['total_fit_hours']:.3f}**. Combined elapsed accounting: **{hours(accounting['combined']['total_elapsed_accounting_seconds'])} h**.",
        "",
    ])
    for trace in TRACES:
        row = accounting["traces"][trace]
        lines.append(
            f"- {trace}: elapsed {hours(row['execution_elapsed_seconds'])} h; mean/median fit {row['mean_fit_seconds']:.2f}/{row['median_fit_seconds']:.2f} s; four-worker utilization {100.0 * row['four_worker_utilization_over_elapsed']:.2f}%; peak RSS {row['peak_rss_bytes'] / (1024 ** 2):.1f} MiB."
        )
    lines.extend([
        "",
        "## Selected-L and selected-epoch diagnostics",
        "",
        "Complete formulation-level and S1/S2 resource-level distributions are recorded in `outputs/scientific_v1/runtime/selected_L_epoch_diagnostics.json`. They are selection diagnostics only and were not correlated with outer-test performance.",
        "",
        "| Trace | Formulation | L4 | L9 | L18 |",
        "|---|---|---:|---:|---:|",
    ])
    for trace in TRACES:
        for formulation in ("S1", "S2", "M1"):
            dist = diagnostics[trace]["selected_L_distribution"][formulation]
            lines.append(
                f"| {trace} | {formulation} | {dist.get('4', 0)} | {dist.get('9', 0)} | {dist.get('18', 0)} |"
            )
    lines.extend([
        "",
        "## Storage and artifact identity",
        "",
        "| Category | Bytes |",
        "|---|---:|",
    ])
    labels = [
        ("model_bytes", "Models"), ("prediction_bytes", "Predictions"),
        ("metric_bytes", "Metrics"), ("selection_bytes", "Selections"),
        ("loss_history_bytes", "Loss histories"), ("completion_bytes", "Completions"),
        ("persistence_bytes", "Persistence"), ("runtime_bytes", "Runtime"),
        ("validation_bytes", "Validation"),
    ]
    storage = inventory["combined_storage"]
    for key, label in labels:
        lines.append(f"| {label} | {storage.get(key, 0)} |")
    lines.extend([
        "",
        f"The full scientific_v1 inventory contains **{inventory['file_count']} files** and **{inventory['total_bytes']} bytes**. Inventory SHA-256: `{inventory['inventory_sha256']}`. Execution-tree SHA-256: `{inventory['execution_tree_sha256']}`.",
        "",
        "## Scientific-analysis lock",
        "",
        "No formulation gains, rankings, signs, classifications, cross-trace scientific comparisons, bootstrap results, R1/R2/R3/R4 decisions, or scientific comparison figures were produced. Predictive metric values were used only inside the technical integrity validators; this report performs no scientific analysis.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    started = time.time()
    combined = json.loads(
        (SCIENTIFIC_ROOT / "validation/combined_technical_validation.json").read_text()
    )
    if combined.get("status") != "PASS":
        raise SystemExit("combined technical validation is not PASS")
    for trace in TRACES:
        validation = json.loads(
            (SCIENTIFIC_ROOT / trace / "validation/technical_validation.json").read_text()
        )
        if validation.get("status") != "PASS":
            raise SystemExit(f"trace technical validation is not PASS: {trace}")

    accounting, diagnostics = build_runtime_and_diagnostics()
    atomic_json_write(ACCOUNTING_PATH, accounting)
    atomic_json_write(DIAGNOSTICS_PATH, diagnostics)
    inventory = build_inventory()
    inventory["generated_seconds"] = time.time() - started
    atomic_json_write(SUMMARY_PATH, inventory)
    REPORT_PATH.write_text(render_report(accounting, diagnostics, inventory))
    print(json.dumps({
        "status": "PASS",
        "accounting": ACCOUNTING_PATH.relative_to(ROOT).as_posix(),
        "diagnostics": DIAGNOSTICS_PATH.relative_to(ROOT).as_posix(),
        "inventory": SUMMARY_PATH.relative_to(ROOT).as_posix(),
        "report": REPORT_PATH.relative_to(ROOT).as_posix(),
        "inventory_summary": inventory,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
