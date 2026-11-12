"""C4 feasibility: synthetic real-shape timing and a runtime projection for N = 1..8 workers.

Reads frozen metadata only (support counts, frozen contexts) and v1 operational columns (epochs and
train seconds). It never reads a validation or test metric. Every timed workload uses generated
tensors. Invoke from the repository root:

    python -m fgcs_strengthening_v03.feasibility --output fgcs_strengthening_v03/feasibility/estimate.json
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

import numpy as np

from .src.identity import RESOURCES, ROOT, ScientificIdentity, read_config

CONFIG = read_config()
EXTERNAL = ("fastStorage", "Rnd", "Materna-T1", "Materna-T2", "Materna-T3")
SAMPLE = 1024


def _threads():
    import torch
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


# -- metadata ------------------------------------------------------------------------------------
def partition_shapes():
    """(block, entity, fold) -> frozen L and origin counts at L, from the sealed support manifests."""
    import pandas as pd

    from .src.data_adapters import frozen_contexts
    from .src.provenance import verified_reference

    shapes = {}
    for block, spec in CONFIG["blocks"].items():
        contexts = frozen_contexts(block)
        frame = pd.read_parquet(verified_reference(spec["support_manifest"]))
        if block == "TimeTrack":
            entity, length, suffix = "machine", "context_length", "_n"
        else:
            entity, length, suffix = "vm_id", "L", "_count"
            if "environment" in frame:
                frame = frame.loc[frame.environment.eq(spec["environment"])]
        for row in frame.to_dict("records"):
            local = (str(row[entity]), int(row["fold"]))
            if local in contexts and int(row[length]) == contexts[local]:
                shapes[(block, *local)] = {"L": contexts[local], **{
                    name: int(row[name + suffix]) for name in
                    ("inner_train", "inner_validation", "outer_train", "outer_test")}}
    expected = {(block, entity, fold) for block, spec in CONFIG["blocks"].items()
                for entity in spec["entities"] for fold in CONFIG["folds"]}
    if set(shapes) != expected:
        raise RuntimeError("Support manifest does not cover every registered partition at its frozen L")
    return shapes


def v1_operations():
    """Mean v1 inner epochs, final selected epochs and final train seconds per (block, formulation)."""
    import pandas as pd

    epochs = defaultdict(dict)
    finals = []
    for block, spec in CONFIG["blocks"].items():
        inner = pd.read_csv(ROOT / spec["v1_registries"]["inner"]["path"],
                            usecols=["formulation", "epochs_trained"])
        entity = "machine" if block == "TimeTrack" else "vm_id"
        final = pd.read_csv(ROOT / spec["v1_registries"]["final"]["path"], dtype={entity: str},
                            usecols=[entity, "fold", "formulation", "L", "selected_epoch", "train_seconds"])
        for formulation in ("S1", "S2", "M1"):
            epochs[block][formulation] = {
                "inner": float(inner.loc[inner.formulation.eq(formulation), "epochs_trained"].mean()),
                "final": float(final.loc[final.formulation.eq(formulation), "selected_epoch"].mean())}
        finals += [{"block": block, "entity": row[entity], **row} for row in final.to_dict("records")]
    return epochs, finals


# -- synthetic timing ----------------------------------------------------------------------------
def _identity(kind, block):
    width = CONFIG["lstm"]["primary_hidden_size"]
    entity = CONFIG["blocks"][block]["entities"][0]
    base = (block, entity, 1, 0, "final")
    if kind in ("S1", "S2"):
        return ScientificIdentity(*base, "core", kind, ("CPU",), "own" if kind == "S1" else "all", width, "baseline")
    if kind in ("M0", "M1"):
        return ScientificIdentity(*base, "core", kind, RESOURCES, "own" if kind == "M0" else "all", width, "baseline")
    if kind == "H128":
        return ScientificIdentity(*base, "capacity", "M0", RESOURCES, "own", 128, "baseline")
    if kind in ("pcgrad", "gradnorm"):
        return ScientificIdentity(*base, kind, "M1", RESOURCES, "all", width, kind)
    family, variant = kind.split("/")
    entity = CONFIG["modern"]["cohorts"][block][0]
    tasks = ("CPU",) if variant == "independent" else RESOURCES
    return ScientificIdentity(block, entity, 1, 0, "final", "modern", family, tasks,
                              CONFIG["modern"]["families"][family]["scope"], None, variant)


def time_epoch(kind, block, L, n=SAMPLE):
    """Seconds per training window (one optimisation pass) and per validation window."""
    import torch

    from .src.models.lstm import LSTM
    from .src.models.registry import REGISTRY
    from .src.optim import gradnorm
    from .src.training import _intervention_epoch, _optimise_epoch

    _threads()
    identity = _identity(kind, block)
    horizons = len(CONFIG["blocks"][block]["horizons"])
    generator = torch.Generator().manual_seed(0)
    torch.manual_seed(0)
    if identity.arm == "modern":
        model = REGISTRY[identity.formulation].build(L, identity.tasks)
        optimizer = REGISTRY[identity.formulation].make_optimizer(model)
        channels = 1 if identity.input_scope == "own" and identity.variant == "independent" else 4
    else:
        model = LSTM(formulation=identity.formulation, block=block, tasks=identity.tasks,
                     hidden_size=identity.hidden_size)
        optimizer = torch.optim.Adam(model.parameters(), lr=CONFIG["lstm"]["learning_rate"])
        channels = 4
    inputs = torch.randn(n, L, channels, generator=generator)
    targets = torch.randn(n, len(identity.tasks), horizons, generator=generator)
    controller = gradnorm.GradNorm(model) if kind == "gradnorm" else None
    seconds = []
    for epoch in (1, 2):
        model.train()
        start = time.perf_counter()
        if identity.arm in ("pcgrad", "gradnorm"):
            _intervention_epoch(model, optimizer, (inputs, targets), generator, identity, epoch, kind,
                                controller, [], {})
        else:
            _optimise_epoch(model, optimizer, (inputs, targets), generator)
        seconds.append(time.perf_counter() - start)
    model.eval()
    start = time.perf_counter()
    with torch.inference_mode():
        for batch in inputs.split(CONFIG["lstm"]["batch_size"]):
            model(batch)
    validation = time.perf_counter() - start
    return seconds[-1] / n, validation / n


def time_extraction(block, L, repeats=20):
    """Seconds per diagnostic task-gradient extraction (M1, batch 128, shared encoder only)."""
    import torch

    from .src.models.lstm import LSTM

    _threads()
    identity = _identity("M1", block)
    model = LSTM(formulation="M1", block=block, tasks=RESOURCES, hidden_size=identity.hidden_size)
    inputs = torch.randn(128, L, 4)
    targets = torch.randn(128, 4, len(CONFIG["blocks"][block]["horizons"]))
    parameters = [p for name, p in model.named_parameters() if name.startswith("encoder")]
    start = time.perf_counter()
    for index in range(repeats):
        loss = (model(inputs)[:, index % 4] - targets[:, index % 4]).square().mean()
        torch.autograd.grad(loss, parameters)
    return (time.perf_counter() - start) / repeats


def time_lightgbm(L, scope, rows):
    """Seconds per scalar LightGBM fit for each registered grid configuration."""
    from .src.models.lightgbm import FeatureLayout, fit_horizon
    from .src.tree.design import GRID

    layout = FeatureLayout(L, "CPU", scope)
    generator = np.random.default_rng(0)
    X = layout.flatten(generator.normal(size=(rows, L, 4)).astype("float32"))
    y = generator.normal(size=rows)
    seconds = {}
    for config in GRID:
        start = time.perf_counter()
        fit_horizon(config, X, y, layout.names)
        seconds[config.variant] = time.perf_counter() - start
    return seconds


_WORKER = """
import json, time
from fgcs_strengthening_v03.feasibility import time_epoch
time_epoch("M1", "fastStorage", 18, n=512)
start = time.perf_counter()
for _ in range(8):
    time_epoch("M1", "fastStorage", 18, n=4096)
print(json.dumps(time.perf_counter() - start))
"""


def concurrency(levels=(1, 2, 4, 6, 8)):
    """Aggregate throughput of k simultaneous single-thread workers on an identical synthetic load.

    Each worker times its own compute span after imports and a warm-up, so interpreter start-up is excluded.
    """
    env = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    import os
    env = {**os.environ, **env}
    results = {}
    for k in levels:
        start = time.perf_counter()
        processes = [subprocess.Popen([sys.executable, "-B", "-c", _WORKER], cwd=ROOT, env=env,
                                      stdout=subprocess.PIPE, text=True) for _ in range(k)]
        outputs = [json.loads(process.communicate()[0]) for process in processes]
        wall = time.perf_counter() - start
        results[k] = {"wall_seconds": wall, "worker_seconds": outputs}
    base = results[1]["worker_seconds"][0]
    for k, record in results.items():
        record["speedup"] = k * base / max(record["worker_seconds"])
    return results


# -- projection ----------------------------------------------------------------------------------
def project(shapes, epochs, timing, lightgbm, extraction, speedups):
    from .plan_execution import fit_identities, overhead_identities

    def v1_epochs(block, formulation, phase):
        key = formulation if formulation in ("S1", "S2", "M1") else "M1"
        return epochs[block][key][phase]

    def kind(identity):
        if identity.arm == "modern":
            return f"{identity.formulation}/{identity.variant}"
        if identity.arm == "capacity":
            return "H128"
        if identity.arm in ("pcgrad", "gradnorm"):
            return identity.arm
        if identity.formulation in ("S1", "S2"):
            return identity.formulation
        return identity.formulation  # core M0/M1 and transfer subsets share the four-task cost scale

    totals = defaultdict(float)
    for identity in fit_identities():
        shape = shapes[identity.block, identity.entity, identity.fold]
        if identity.arm == "lightgbm":
            seconds = lightgbm[shape["L"], identity.input_scope]
            fits = seconds[identity.variant] if identity.phase == "inner" else statistics.mean(seconds.values())
            totals[f"{identity.phase}:lightgbm"] += 5 * fits * shape["outer_train" if identity.phase == "final"
                                                                       else "inner_train"] / 2048
            continue
        train, validation = timing[kind(identity), identity.block, shape["L"]]
        formulation = identity.formulation if identity.arm != "modern" else "M1"
        if identity.phase == "inner":
            cost = v1_epochs(identity.block, formulation, "inner") * (
                shape["inner_train"] * train + shape["inner_validation"] * validation)
        else:
            cost = v1_epochs(identity.block, formulation, "final") * shape["outer_train"] * train
        totals[f"{identity.phase}:{identity.arm}"] += cost
    for identity in overhead_identities():
        shape = shapes[identity.block, identity.entity, identity.fold]
        if identity.arm == "diagnostic":
            pairs = CONFIG["diagnostics"]["pairs"] * len(CONFIG["diagnostics"]["batches"])
            totals["diagnostics"] += pairs * CONFIG["diagnostics"]["tasks_per_batch"] * extraction[identity.block, shape["L"]]
        _, validation = timing["M1", identity.block, shape["L"]]
        totals["evaluation"] += shape["outer_test"] * validation
    for identity in fit_identities():
        if identity.phase == "final" and identity.arm != "lightgbm":
            shape = shapes[identity.block, identity.entity, identity.fold]
            totals["evaluation"] += shape["outer_test"] * timing[kind(identity), identity.block, shape["L"]][1]
    single = sum(totals.values())
    return {"single_worker_seconds_by_component": dict(totals), "single_worker_seconds": single,
            "single_worker_days": single / 86400,
            "projected_wall_days": {k: single / record["speedup"] / 86400 for k, record in speedups.items()}}


def cross_check(shapes, finals, timing):
    """v1 measured final train seconds versus this model's prediction at the v1 row's own L."""
    from .src.data_adapters import frozen_contexts  # noqa: F401  (support at L is shared across L in v1)

    ratios = defaultdict(list)
    for row in finals:
        key = row["block"], str(row["entity"]), int(row["fold"])
        if key not in shapes or row["formulation"] not in ("S1", "S2", "M1"):
            continue
        timed = timing.get((row["formulation"], row["block"], int(row["L"])))
        if timed is None or not row["train_seconds"]:
            continue
        predicted = row["selected_epoch"] * shapes[key]["outer_train"] * timed[0]
        ratios[row["block"], row["formulation"]].append(row["train_seconds"] / predicted)
    return {f"{block}/{formulation}": {"median_measured_over_predicted": statistics.median(values), "n": len(values)}
            for (block, formulation), values in sorted(ratios.items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    _threads()
    shapes = partition_shapes()
    epochs, finals = v1_operations()
    timing = {}
    for block, spec in CONFIG["blocks"].items():
        if block not in ("TimeTrack", "fastStorage"):
            continue  # identical architectures and horizon counts across the external blocks
        for L in spec["contexts"]:
            kinds = ["S1", "S2", "M0", "M1", "H128"]
            if block == "fastStorage":
                kinds += ["pcgrad", "gradnorm"] + [f"{family}/{variant}" for family in CONFIG["modern"]["families"]
                                                   for variant in ("independent", "shared")]
            for kind in kinds:
                timing[kind, block, L] = time_epoch(kind, block, L)
    for (kind, block, L), value in list(timing.items()):
        if block == "fastStorage":
            for other in EXTERNAL[1:]:
                timing[kind, other, L] = value
    extraction = {}
    for block in CONFIG["blocks"]:
        for L in CONFIG["blocks"][block]["contexts"]:
            source = "TimeTrack" if block == "TimeTrack" else "fastStorage"
            if (source, L) not in extraction:
                extraction[source, L] = time_extraction(source, L)
            extraction[block, L] = extraction[source, L]
    lightgbm = {(L, scope): time_lightgbm(L, scope, 2048) for L in (4, 9, 18) for scope in ("own", "all")}
    speedups = concurrency()
    projection = project(shapes, epochs, timing, lightgbm, extraction, speedups)
    report = {
        "method": "generated tensors at frozen per-partition L and support counts; v1 mean epochs; "
                  "LightGBM scaled linearly from 2,048 rows; systems benchmarks excluded (bounded, measured later)",
        "sample_windows": SAMPLE,
        "timing_seconds_per_window": {f"{k}|{b}|{L}": v for (k, b, L), v in timing.items()},
        "diagnostic_extraction_seconds": {f"{b}|{L}": v for (b, L), v in extraction.items()},
        "lightgbm_scalar_fit_seconds_2048_rows": {f"{L}|{s}": v for (L, s), v in lightgbm.items()},
        "concurrency": {str(k): v for k, v in speedups.items()},
        "calibration": {"factor": statistics.median(v["median_measured_over_predicted"]
                                                    for v in cross_check(shapes, finals, timing).values()),
                        "basis": "median over block/formulation of v1 measured final train seconds / model"},
        "v1_cross_check": cross_check(shapes, finals, timing),
        "projection": projection,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"projection": projection, "v1_cross_check": report["v1_cross_check"]}, indent=2))


if __name__ == "__main__":
    main()
