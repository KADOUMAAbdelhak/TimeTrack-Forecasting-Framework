"""Amendment A2 analysis (A2 protocol, sections 4 and 5): dry plan by default; --run after both journals close.

Invoke from the repository root:
    python -m fgcs_strengthening_v04a2.analyse_residual               # table sizes only; reads no data
    python -m fgcs_strengthening_v04a2.analyse_residual --run OUTPUT  # A2 and v0.4 evaluation gates closed

Inputs:
- the closed A2 journal (the tier-2 2x2 of four backbones under the change parameterisation);
- read only, the closed v0.4 journal (the same cells under the level parameterisation);
- v1 persistence on the frozen outer-test support.

Everything is descriptive: no p-values.
"""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from .analyse_intervention import _metadata, read_only_v04_journal
from .src.identity import RESOURCES, read_config
from .src.analysis.bootstrap import REPLICATES, SEED, Draws
from .src.analysis.grid import BACKBONES, BLOCKS, DEFINED, Grid, MAERow, gain, macro, seed_average
from .src.analysis.primary import CONTRASTS, baseline_rows, contrast_rows, defined, matched_descriptives

FORMAT = "fgcs-v04-a2-analysis/1"
_CONFIG = read_config()
RULE = _CONFIG["residual"]["decision"]
CELLS = tuple((backbone, cell) for backbone in BACKBONES for cell in DEFINED[backbone])


# -- pure analysis ------------------------------------------------------------------------------

def parameterisation_rows(change, level):
    """Per backbone x cell x resource x block: the A2 (change) cell against the same tier-2 (level) cell."""
    rows = []
    for block in BLOCKS:
        for backbone in BACKBONES:
            mask = change.mask(backbone, block) | level.mask(backbone, block)
            for cell in DEFINED[backbone]:
                a = change.masked(backbone, cell, block, mask)
                b = level.masked(backbone, cell, block, mask)
                for r, resource in enumerate(RESOURCES):
                    abar, bbar = seed_average(a[:, r]), seed_average(b[:, r])
                    rows.append({"block": block, "backbone": backbone, "cell": cell, "resource": resource,
                                 "macro_mae": {"change": macro(abar), "level": macro(bbar)},
                                 "gain_percent": gain(macro(abar), macro(bbar)),
                                 **matched_descriptives(abar, bbar)})
    return rows


def _skill(entry):
    return entry["persistence_skill"]


def decide(contrasts, baseline):
    """The frozen A2 decision rule (section 5)."""
    precondition = RULE["precondition"]
    s2 = [{"block": row["block"], "resource": row["resource"], "backbone": backbone, "skill": _skill(entry)}
          for row in baseline if row["cell"] == precondition["cell"] and row["resource"] in precondition["resources"]
          for backbone, entry in row["backbones"].items()]
    if len(s2) != precondition["of"]:
        raise RuntimeError(f"Precondition covers {len(s2)} cells, expected {precondition['of']}")
    positive = sum(item["skill"] is not None and item["skill"] > 0 for item in s2)

    primary = [row for row in contrasts if row["contrast"] == "M1:S2"]
    if len(primary) != RULE["of"]:
        raise RuntimeError(f"M1:S2 covers {len(primary)} cells, expected {RULE['of']}")
    above = sum(row["median_ratio"] is not None and row["median_ratio"] > 1 for row in primary)
    verdict = ("holds" if above >= RULE["holds_at_least"]
               else "does not hold" if above <= RULE["does_not_hold_at_most"] else "mixed")

    restricted = [row for row in primary
                  if all((row["persistence_skill"][cell]["skill"] or 0) > 0 for cell in ("M1", "S2"))]
    restricted_above = sum(row["median_ratio"] is not None and row["median_ratio"] > 1 for row in restricted)
    if len(restricted) < RULE["restricted"]["min_cells"]:
        restricted_verdict = "too few cells"
    elif restricted_above >= RULE["restricted"]["fraction_above_one"] * len(restricted):
        restricted_verdict = "holds among persistence-beating models"
    else:
        restricted_verdict = "does not hold among persistence-beating models"

    secondary = {}
    for candidate, reference, _ in CONTRASTS:
        rows = [row for row in contrasts if row["contrast"] == f"{candidate}:{reference}"]
        secondary[f"{candidate}:{reference}"] = {
            "cells": len(rows), "median_ratio_above_one": sum(r["median_ratio"] is not None and r["median_ratio"] > 1
                                                             for r in rows)}
    return {
        "precondition": {"met": positive >= precondition["positive_skill_at_least"], "positive": positive,
                         "of": len(s2), "threshold": precondition["positive_skill_at_least"], "cells": s2},
        "sharing": {"verdict": verdict, "median_ratio_above_one": above, "of": len(primary),
                    "holds_at_least": RULE["holds_at_least"], "does_not_hold_at_most": RULE["does_not_hold_at_most"]},
        "restricted": {"verdict": restricted_verdict, "cells": len(restricted), "median_ratio_above_one": restricted_above,
                       "min_cells": RULE["restricted"]["min_cells"],
                       "fraction_above_one": RULE["restricted"]["fraction_above_one"],
                       "members": [{"backbone": r["backbone"], "block": r["block"], "resource": r["resource"]}
                                   for r in restricted]},
        "contrast_counts": secondary,
    }


def analyse(*, change_rows, level_rows, persistence, draws=None):
    """All A2 tables from collected inputs (pure; used by --run and the synthetic tests)."""
    draws = draws or Draws()
    change = Grid(change_rows, cells=CELLS)
    level = Grid(level_rows, cells=CELLS)
    contrasts = contrast_rows(change, draws, persistence)
    baseline = baseline_rows(change, persistence)
    return {"contrasts": contrasts, "baseline_accuracy": baseline,
            "parameterisation_effect": parameterisation_rows(change, level),
            "decision": decide(contrasts, baseline), "missing_units": change.missing_units()}


def dry_plan():
    contrasts = sum(defined(b, c, r) for b in BACKBONES for c, r, _ in CONTRASTS) * len(RESOURCES) * len(BLOCKS)
    return {"contrast_rows": contrasts, "baseline_rows": 4 * len(RESOURCES) * len(BLOCKS),
            "parameterisation_rows": len(CELLS) * len(RESOURCES) * len(BLOCKS),
            "decision": {"precondition": RULE["precondition"], "primary": "M1:S2 median ratio above 1",
                         "holds_at_least": RULE["holds_at_least"], "does_not_hold_at_most": RULE["does_not_hold_at_most"],
                         "of": RULE["of"], "restricted": RULE["restricted"]},
            "bootstrap": {"seed": SEED, "replicates": REPLICATES, "draw_matrices": list(BLOCKS)}}


# -- journal readers ----------------------------------------------------------------------------

def v04_level_identities():
    """The tier-2 core and modern final identities (v0.4 namespace), read only."""
    from fgcs_strengthening_v04.plan_execution import fit_identities

    return [identity for identity in fit_identities()
            if identity.phase == "final" and identity.arm in ("core", "modern")]


def collect(a2_journal, v04_journal):
    from fgcs_strengthening_v04.src.analysis import collect as v04_collect
    from fgcs_strengthening_v04.src.evaluation import OuterEvaluator as V04Evaluator
    from .plan_execution import fit_identities
    from .src.analysis import collect as a2_collect
    from .src.evaluation import OuterEvaluator as A2Evaluator

    a2_collect.require_evaluation_closed(a2_journal)
    v04_collect.require_evaluation_closed(v04_journal)
    a2_finals = [identity for identity in fit_identities() if identity.phase == "final"]
    v04_finals = v04_level_identities()
    change_rows = list(a2_collect.mae_rows(a2_journal, a2_finals))
    level_rows = [MAERow(**asdict(row)) for row in v04_collect.mae_rows(v04_journal, v04_finals)]
    a2_support = _metadata(A2Evaluator(a2_journal), a2_finals)
    v04_support = _metadata(V04Evaluator(v04_journal), v04_finals)
    differing = sorted(key for key in a2_support.keys() & v04_support.keys() if a2_support[key] != v04_support[key])
    if differing:
        raise RuntimeError(f"A2 and v0.4 evaluations differ in context, support, scaler or test IDs: {differing[:5]}")
    return change_rows, level_rows


def run(output):
    from .src.analysis.historical import HistoricalReader
    from .src.orchestrator import execution_fingerprints
    from .src.provenance import Journal

    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    seal = execution_fingerprints()
    a2_journal = Journal(seal)
    v04_journal = read_only_v04_journal()
    change_rows, level_rows = collect(a2_journal, v04_journal)
    reader = HistoricalReader()
    results = analyse(change_rows=change_rows, level_rows=level_rows, persistence=reader.persistence())
    gates = {name: sha256(journal._path("orchestrator", "gates", "evaluation.json").read_bytes()).hexdigest()
             for name, journal in (("A2", a2_journal), ("v0.4", v04_journal))}
    document = {"format": FORMAT, "amendment": _CONFIG["amendment"], "lineage": _CONFIG["lineage"],
                "tier": "tier 2 amendment A2; descriptive, no p-values", "fingerprint_sha256": seal.digest,
                "evaluation_gate_sha256": gates, "historical_inputs": reader.input_hashes(), "results": results}
    encoded = json.dumps(document, indent=1, allow_nan=False) + "\n"
    output.write_text(encoded)
    Path(f"{output}.sha256").write_text(f"{sha256(encoded.encode()).hexdigest()}  {output.name}\n")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", metavar="OUTPUT", help="analyse both closed journals and write OUTPUT (JSON)")
    args = parser.parse_args(argv)
    if args.run:
        decision = run(args.run)["results"]["decision"]
        print(json.dumps({"precondition_met": decision["precondition"]["met"],
                          "sharing": decision["sharing"]["verdict"], "restricted": decision["restricted"]["verdict"]}))
    else:
        json.dump(dry_plan(), sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
