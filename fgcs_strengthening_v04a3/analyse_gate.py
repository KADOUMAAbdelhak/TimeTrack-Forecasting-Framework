"""Amendment A3 analysis: validation-gated consolidation and task grouping on existing fits.

Invoke from the repository root:
    python -m fgcs_strengthening_v04a3.analyse_gate               # plan only; reads no data
    python -m fgcs_strengthening_v04a3.analyse_gate --run OUTPUT  # reads the frozen inputs, writes OUTPUT

Inputs (all read only, each checked against a recorded digest or seal):
- tier 1: per block, the LSTM S1, S2 and M1 outer metrics, inner-run registry and selected contexts;
- tier 2: the closed v0.4 journal (final and inner fits, outer evaluations) and v1 persistence;
- the published tier-1 matched cells and tier-2 analysis output, for the reproduction guards.

No model is fitted. Everything is descriptive: no p-values.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

from . import gate
from .gate import RESOURCES, Frame

ROOT = Path(__file__).resolve().parents[1]
HOME = Path(__file__).resolve().parent
CONFIG_PATH = HOME / "configs/protocol_v04a3.json"
CONFIG = json.loads(CONFIG_PATH.read_text())
FORMAT = "fgcs-v04-a3-analysis/1"
TOLERANCES = tuple(CONFIG["tolerances"])
PRIMARY = CONFIG["primary_tolerance"]
TIER1_BLOCKS = tuple(CONFIG["tier1"]["blocks"])
SEED, REPLICATES = 20261007, 10000


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def tag(tolerance):
    return f"{100 * tolerance:g}%"


class BlockDraws:
    """VM-cluster draw matrices, one per block, from one generator in the configured block order."""

    def __init__(self, sizes, *, seed=SEED, replicates=REPLICATES):
        generator = np.random.Generator(np.random.PCG64(seed))
        self._indices = {block: generator.integers(0, size, size=(replicates, size), dtype=np.int64)
                         for block, size in sizes.items()}

    def indices(self, block):
        return self._indices[block]


# -- tier 1 -------------------------------------------------------------------------------------

def tier1_frame(block, spec):
    import pandas as pd

    root = ROOT / spec["root"]
    for name, expected in spec["sha256"].items():
        if digest(root / name) != expected:
            sys.exit(f"{block}/{name} differs from its recorded SHA-256")
    entity = spec["entity_column"]
    metrics = pd.read_parquet(root / "metrics.parquet")
    metrics[entity] = metrics[entity].astype(str)
    inner = pd.read_csv(root / "inner_run_registry.csv", dtype={entity: str})
    selected = pd.read_csv(root / "selected_contexts.csv", dtype={entity: str})
    entities = tuple(sorted(metrics[entity].unique()))
    folds = tuple(sorted(metrics.fold.unique()))
    seeds = tuple(sorted(metrics.seed.unique()))
    leads = tuple(spec["leads"])
    if (len(entities), len(folds), len(seeds), tuple(sorted(metrics.lead.unique()))) != (spec["entities"], 5, 3, leads):
        sys.exit(f"{block}: tier-1 metrics grid differs from the configuration")
    shape = (len(entities), len(folds), len(seeds), len(RESOURCES), len(leads))
    index = {"e": {v: i for i, v in enumerate(entities)}, "f": {v: i for i, v in enumerate(folds)},
             "s": {v: i for i, v in enumerate(seeds)}, "r": {v: i for i, v in enumerate(RESOURCES)},
             "h": {v: i for i, v in enumerate(leads)}}

    chosen = {}
    for row in selected.itertuples(index=False):
        resource = None if row.formulation == "M1" else row.resource
        chosen[row.formulation, resource, getattr(row, entity), int(row.fold)] = int(row.selected_L)

    outer, val = {}, {}
    for cell in CONFIG["tier1"]["cells"]:
        frame = metrics[metrics.formulation == cell]
        values = np.full(shape, np.nan)
        for row in frame.itertuples(index=False):
            key = (cell, None if cell == "M1" else row.resource, getattr(row, entity), int(row.fold))
            if chosen.get(key) != int(row.selected_L):
                sys.exit(f"{block}: outer run at a context other than the selected one: {key}")
            values[index["e"][getattr(row, entity)], index["f"][row.fold], index["s"][row.seed],
                   index["r"][row.resource], index["h"][row.lead]] = row.mae
        if np.isnan(values).any():
            sys.exit(f"{block}/{cell}: incomplete outer metrics")
        outer[cell] = values

        rows = inner[inner.formulation == cell]
        errors = np.full(shape[:4], np.nan)
        for row in rows.itertuples(index=False):
            resource = None if cell == "M1" else row.resource
            if chosen.get((cell, resource, getattr(row, entity), int(row.fold))) != int(row.L):
                continue
            nmae = np.asarray(json.loads(row.validation_nmae), dtype=np.float64)
            where = (index["e"][getattr(row, entity)], index["f"][row.fold], index["s"][row.seed])
            if cell == "M1":
                if nmae.shape != (len(RESOURCES), len(leads)) or not np.isnan(errors[where]).all():
                    sys.exit(f"{block}: malformed or duplicate M1 inner row")
                errors[where] = nmae.mean(axis=1)
            else:
                if nmae.shape != (len(leads),) or not np.isnan(errors[where + (index["r"][row.resource],)]):
                    sys.exit(f"{block}: malformed or duplicate {cell} inner row")
                errors[where + (index["r"][row.resource],)] = nmae.mean()
        if np.isnan(errors).any() or not np.isfinite(errors).all() or (errors <= 0).any():
            sys.exit(f"{block}/{cell}: inner-validation errors missing at the selected context")
        val[cell] = errors
    return Frame("tier1", block, "LSTM", entities, val, outer), index


def tier1_guard(frames_and_indexes):
    import pandas as pd

    spec = CONFIG["tier1"]["published_cells"]
    if digest(ROOT / spec["path"]) != spec["sha256"]:
        sys.exit("Published tier-1 matched cells differ from their recorded SHA-256")
    published = pd.read_csv(ROOT / spec["path"], dtype={"entity": str})
    worst = 0.0
    for frame, index in frames_and_indexes:
        for comparison, candidate, reference in (("S2_vs_S1", "S2", "S1"), ("M1_vs_S2", "M1", "S2")):
            rows = published[(published.block == frame.block) & (published.comparison == comparison)]
            if len(rows) != np.prod(frame.shape) // 3:
                sys.exit(f"{frame.block}: published cell count differs")
            for row in rows.itertuples(index=False):
                where = (index["e"][row.entity], index["f"][row.fold], slice(None), index["r"][row.resource],
                         index["h"][row.lead])
                for cell, value in ((candidate, row.candidate_mae), (reference, row.reference_mae)):
                    mine = frame.outer[cell][where].mean()
                    worst = max(worst, abs(mine - value) / max(abs(value), 1e-12))
    if worst > spec["relative_tolerance"]:
        sys.exit(f"Tier-1 seed means differ from the published cells (relative {worst:.3g})")
    return worst


# -- tier 2 -------------------------------------------------------------------------------------

def tier2_frames():
    from fgcs_strengthening_v04.plan_execution import fit_identities
    from fgcs_strengthening_v04.src.analysis import collect
    from fgcs_strengthening_v04.src.analysis.grid import BACKBONES, BLOCKS, COHORT, FOLDS, SEEDS, Grid, all_cells
    from fgcs_strengthening_v04.src.analysis.historical import HistoricalReader
    from fgcs_strengthening_v04a1.analyse_intervention import read_only_v04_journal

    lineage = CONFIG["lineage"]
    journal = read_only_v04_journal()
    if journal.seal.digest != lineage["tier2_execution_seal"]:
        sys.exit("The tier-2 seal differs from the A3 lineage")
    collect.require_evaluation_closed(journal)
    identities = tuple(fit_identities())
    by_digest = {identity.digest: identity for identity in identities}
    finals = [i for i in identities if i.phase == "final" and i.arm in ("core", "modern", "pairwise", "leave_one_out")]
    grid = Grid(collect.mae_rows(journal, finals), cells=tuple(all_cells()))

    def empty(block):
        return np.full((len(COHORT[block]), len(FOLDS), len(SEEDS), len(RESOURCES)), np.nan)

    val, params, splits = {}, {}, {}
    for identity in finals:
        backbone, cell = collect.label(identity)
        evidence, _ = journal.completed_evidence(identity)
        inner_identity = by_digest[evidence["inner_identity_sha256"]]
        if inner_identity.phase != "inner":
            sys.exit("A final fit links to a non-inner identity")
        inner, _ = journal.completed_evidence(inner_identity)
        epoch = evidence["selection"]["final_epoch"]
        (row,) = [e for e in inner["epochs"] if e["epoch"] == epoch]
        key = backbone, cell, identity.block
        where = (COHORT[identity.block].index(identity.entity), FOLDS.index(identity.fold),
                 SEEDS.index(identity.seed))
        for task in identity.tasks:
            r = RESOURCES.index(task)
            val.setdefault(key, empty(identity.block))[where + (r,)] = row["validation_task_mse"][task]
            params.setdefault(key, empty(identity.block))[where + (r,)] = evidence["parameter_count"]
        split = (inner["split_hashes"]["inner_validation"], inner["scaler_sha256"], inner["context"])
        if splits.setdefault((identity.block, identity.entity, identity.fold), split) != split:
            sys.exit("Inner fits of one partition differ in validation split, scaler or context")

    persistence = HistoricalReader().persistence()  # [E, R, F, H]
    frames = []
    for block in BLOCKS:
        val_p = persistence_validation(block, splits)
        outer_p = np.transpose(persistence[block], (0, 2, 1, 3))
        for backbone in BACKBONES:
            cells = [c for b, c in all_cells() if b == backbone]
            outer, v, p = {}, {}, {}
            for cell in cells:
                outer[cell] = np.transpose(grid.values[backbone, cell, block], (0, 2, 4, 1, 3))  # [E, F, S, R, H]
                v[cell], p[cell] = val[backbone, cell, block], params[backbone, cell, block]
                covered = ~np.isnan(v[cell][0, 0, 0])
                if not (np.isfinite(v[cell][..., covered]).all() and np.isfinite(outer[cell][..., covered, :]).all()):
                    sys.exit(f"{backbone}/{cell}/{block}: missing validation or outer errors")
            frames.append(Frame("tier2", block, backbone, COHORT[block], v, outer, p, val_p, outer_p))
    reader_hashes = HistoricalReader().input_hashes()
    return frames, reader_hashes


def persistence_validation(block, splits):
    """Scaled MSE of the last own-channel value on each partition's inner-validation windows [E, F, R]."""
    from fgcs_strengthening_v04.src.analysis.grid import COHORT, FOLDS
    from fgcs_strengthening_v04.src.data_adapters import adapter_for

    adapter = adapter_for(block)
    values = np.full((len(COHORT[block]), len(FOLDS), len(RESOURCES)), np.nan)
    for e, entity in enumerate(COHORT[block]):
        for f, fold in enumerate(FOLDS):
            partition = adapter.prepare(entity, fold, "inner")
            expected = splits[block, entity, fold]
            if (partition.split_hashes["inner_validation"], partition.scaler_sha256, partition.context) != expected:
                sys.exit(f"{block}/{entity}/{fold}: persistence windows differ from the inner fits' split")
            windows = partition.validation()
            inputs = windows.inputs.astype(np.float32).astype(np.float64)
            targets = windows.targets.astype(np.float32).astype(np.float64)  # [n, R, H]
            last = inputs[:, -1, :]  # [n, R]
            values[e, f] = ((targets - last[:, :, None]) ** 2).mean(axis=(0, 2))
    return values


def tier2_guard(frames, draws):
    path = ROOT / "fgcs_strengthening_v04/runtime/analysis/analysis_v04.json"
    if digest(path) != CONFIG["lineage"]["tier2_analysis_sha256"]:
        sys.exit("analysis_v04.json differs from its frozen digest")
    published = {(r["backbone"], r["contrast"], r["block"], r["resource"]): r["median_ratio"]
                 for r in json.loads(path.read_text())["results"]["P4"]["contrasts"]}
    checked = 0
    for frame in frames:
        for candidate, reference in (("S2", "S1"), ("M1", "M0"), ("M0", "S1"), ("M1", "S2")):
            if not (frame.has(candidate) and frame.has(reference)):
                continue
            for r, resource in enumerate(RESOURCES):
                mine = gate.matched_descriptives(gate.seed_mean(frame.outer[candidate], r),
                                                 gate.seed_mean(frame.outer[reference], r))["median_ratio"]
                if mine != published[frame.backbone, f"{candidate}:{reference}", frame.block, resource]:
                    sys.exit(f"Tier-2 median ratio not reproduced: {frame.backbone} {candidate}:{reference} "
                             f"{frame.block} {resource}")
                checked += 1
    return checked


# -- analysis -----------------------------------------------------------------------------------

def frame_policies(frame):
    """(name, assignment) for every policy of the frame, in a fixed order."""
    policies = [(cell, gate.fixed(frame, cell)) for cell in ("S1", "S2", "M0", "M1") if frame.has(cell)]
    if frame.has("S1"):
        policies.append(("G-ctx", gate.g_ctx(frame)))
    lattice = frame.tier == "tier2" and frame.backbone == "LSTM"
    for tolerance in TOLERANCES:
        policies.append((f"G-share@{tag(tolerance)}", gate.g_share(frame, tolerance)))
        policies.append((f"G-full@{tag(tolerance)}", gate.g_full(frame, tolerance)))
        if lattice:
            policies.append((f"G-group@{tag(tolerance)}", gate.g_group(frame, tolerance)))
    if frame.tier == "tier2":
        bases = [("S2", gate.fixed(frame, "S2")), (f"G-share@{tag(PRIMARY)}", gate.g_share(frame, PRIMARY))]
        if lattice:
            bases.append((f"G-group@{tag(PRIMARY)}", gate.g_group(frame, PRIMARY)))
        policies += [(f"{name}+fallback", gate.with_fallback(frame, assignment)) for name, assignment in bases]
    policies.append(("oracle-share", gate.oracle_share(frame)))
    if lattice:
        policies.append(("oracle-group", gate.oracle_group(frame)))
        for p, partition in enumerate(gate.partitions()):
            choice = np.full(frame.shape[:3], p)
            policies.append((f"partition:{gate.partition_label(partition)}", gate.partition_assignment(frame, choice)))
    return policies


def analyse(frames, draws_for):
    rows, summaries, detections = [], [], []
    for frame in frames:
        draws = draws_for(frame)
        for name, assignment in frame_policies(frame):
            r, s = gate.accuracy_rows(frame, name, assignment, draws)
            rows += r
            summaries.append(s)
        detection = gate.detection(frame, draws)
        detection["verdict"] = gate.detection_verdict(detection)
        detections.append(detection)
    return rows, summaries, detections


def verdicts(rows, summaries, detections):
    def models(tier, policy, backbone=None):
        chosen = [s for s in summaries if s["tier"] == tier and s["policy"] == policy
                  and (backbone is None or s["backbone"] == backbone)]
        units = sum(s["units"] for s in chosen)
        return sum(s["mean_models"] * s["units"] for s in chosen) / units

    def select(tier, backbone=None):
        return [row for row in rows if row["tier"] == tier and (backbone is None or row["backbone"] == backbone)]

    primary = f"G-share@{tag(PRIMARY)}"
    out = {"H-A3a": {}, "H-A3b": {}, "H-A3c": None, "fallback": None}
    for tier, expected in (("tier1", 22), ("tier2", 13)):
        tier_rows = select(tier)
        reference = gate.cost_cells(tier_rows, "M1")
        if reference != expected:
            sys.exit(f"{tier}: M1:S2 cost cells {reference} differ from the published {expected}")
        retained = gate.savings_retained(models(tier, primary), models(tier, "S2"), models(tier, "M1"))
        cost = gate.cost_cells(tier_rows, primary)
        out["H-A3a"][tier] = {"policy": primary, "cells": sum(r["policy"] == primary for r in tier_rows),
                              "savings_retained": retained, "cost_cells": cost, "reference_cost_cells": reference,
                              "mean_models": models(tier, primary),
                              "verdict": gate.h_a3a_verdict(retained, cost, reference)}
        per_tolerance = {}
        for tolerance in TOLERANCES:
            name = f"G-share@{tag(tolerance)}"
            per_tolerance[tag(tolerance)] = {
                "savings_retained": gate.savings_retained(models(tier, name), models(tier, "S2"), models(tier, "M1")),
                "cost_cells": gate.cost_cells(tier_rows, name)}
        out["H-A3a"][tier]["by_tolerance"] = per_tolerance
    out["H-A3b"] = {"frames": [{k: d[k] for k in ("tier", "block", "backbone", "rho", "interval", "verdict")}
                               for d in detections],
                    "counts": {v: sum(d["verdict"] == v for d in detections)
                               for v in ("detects", "weak", "does not detect")}}
    lstm = select("tier2", "LSTM")
    group = f"G-group@{tag(PRIMARY)}"
    g_models, s_models = models("tier2", group, "LSTM"), models("tier2", primary, "LSTM")
    g_cost, s_cost = gate.cost_cells(lstm, group), gate.cost_cells(lstm, primary)
    out["H-A3c"] = {"group_mean_models": g_models, "share_mean_models": s_models, "group_cost_cells": g_cost,
                    "share_cost_cells": s_cost, "cells": sum(r["policy"] == group for r in lstm),
                    "verdict": gate.h_a3c_verdict(g_models, s_models, g_cost, s_cost)}
    fallback = [r for r in select("tier2") if r["policy"] == "S2+fallback" and r["resource"] in ("CPU", "THROUGHPUT")]
    positive = sum(r["persistence_skill"] is not None and r["persistence_skill"] > 0 for r in fallback)
    baseline = [r for r in select("tier2") if r["policy"] == "S2" and r["resource"] in ("CPU", "THROUGHPUT")]
    out["fallback"] = {"cells": len(fallback), "positive_skill": positive,
                       "positive_skill_without_fallback": sum(r["persistence_skill"] > 0 for r in baseline),
                       "verdict": gate.fallback_verdict(positive)}
    return out


def dry_plan():
    return {"format": FORMAT, "fits": 0, "tier1_blocks": list(TIER1_BLOCKS),
            "tier2": {"backbones": CONFIG["tier2"]["backbones"], "blocks": ["fastStorage", "Rnd"]},
            "tolerances": list(TOLERANCES), "primary_tolerance": PRIMARY, "partitions": len(gate.partitions()),
            "decision": CONFIG["decision"]}


def run(output):
    output = Path(output)
    if output.exists():
        sys.exit(f"Refusing to overwrite {output}")
    loaded = [tier1_frame(block, CONFIG["tier1"]["blocks"][block]) for block in TIER1_BLOCKS]
    tier1_worst = tier1_guard(loaded)
    tier1 = [frame for frame, _ in loaded]
    tier1_draws = BlockDraws({frame.block: len(frame.entities) for frame in tier1})
    tier2, reader_hashes = tier2_frames()
    from fgcs_strengthening_v04.src.analysis.bootstrap import Draws
    tier2_draws = Draws()
    checked = tier2_guard(tier2, tier2_draws)
    rows, summaries, detections = analyse(tier1 + tier2,
                                          lambda f: tier1_draws if f.tier == "tier1" else tier2_draws)
    document = {"format": FORMAT, "amendment": CONFIG["amendment"], "lineage": CONFIG["lineage"],
                "config_sha256": digest(CONFIG_PATH),
                "guards": {"tier1_max_relative_difference": tier1_worst, "tier2_contrasts_reproduced": checked},
                "historical_inputs": reader_hashes,
                "bootstrap": {"seed": SEED, "replicates": REPLICATES,
                              "tier1_entity_order": "lexicographic string order of entity identifiers"},
                "verdicts": verdicts(rows, summaries, detections),
                "summaries": summaries, "detection": detections, "rows": rows}
    encoded = json.dumps(document, indent=1, allow_nan=False) + "\n"
    output.write_text(encoded)
    Path(f"{output}.sha256").write_text(f"{sha256(encoded.encode()).hexdigest()}  {output.name}\n")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", metavar="OUTPUT", help="read the frozen inputs and write OUTPUT (JSON)")
    args = parser.parse_args(argv)
    if args.run:
        print(json.dumps(run(args.run)["verdicts"], indent=1))
    else:
        json.dump(dry_plan(), sys.stdout, indent=1)
        print()


if __name__ == "__main__":
    main()
