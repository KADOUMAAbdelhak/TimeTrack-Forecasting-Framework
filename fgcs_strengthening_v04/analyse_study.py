"""v0.4 analysis (protocol P4 and P5): dry plan by default; --run after evaluation closure.

Invoke from the repository root:
    python -m fgcs_strengthening_v04.analyse_study               # table sizes only; reads no data
    python -m fgcs_strengthening_v04.analyse_study --run OUTPUT  # after the evaluation gate closes
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from .src.identity import RESOURCES, canonical_json
from .src.analysis.bootstrap import REPLICATES, SEED, Draws
from .src.analysis.grid import BACKBONES, BLOCKS, CELLS, DEFINED, Grid
from .src.analysis.mechanism import d1_rows, d2_dependence, d3_rows, d4_rows, d6_rows, d7_rows
from .src.analysis.primary import (CONTRASTS, baseline_rows, contrast_rows, cross_backbone_rows, defined,
                                   interaction_rows, parameter_counts)

FORMAT = "fgcs-v04-analysis/1"


def dry_plan():
    """Row counts of every table, from the design alone."""
    resources, blocks = len(RESOURCES), len(BLOCKS)
    contrasts = sum(defined(b, c, r) for b in BACKBONES for c, r, _ in CONTRASTS) * resources * blocks
    full = sum(DEFINED[b] == CELLS for b in BACKBONES)
    from .src.analysis.grid import COHORT, FOLDS
    entities = sum(len(COHORT[b]) for b in BLOCKS)
    return {
        "P4": {"contrast_rows": contrasts, "interaction_rows": full * resources * blocks,
               "cross_backbone_rows": len(CONTRASTS) * resources * blocks,
               "baseline_rows": len(CELLS) * resources * blocks,
               "parameter_count_rows": sum(len(DEFINED[b]) for b in BACKBONES) * 3},
        "P5": {"D-1_entity_fold_rows": entities * len(FOLDS), "D-2_entity_values": entities * resources,
               "D-3_associations": 2 * 2 * resources * blocks, "D-4_entity_rows": 2 * entities,
               "D-6_entries": 2 * resources * (resources - 1) * blocks, "D-7_rows": resources * blocks},
        "bootstrap": {"seed": SEED, "replicates": REPLICATES, "draw_matrices": list(BLOCKS)},
    }


def analyse(*, rows, persistence, ridge, d1, d4, d7, draws=None):
    """All P4 and P5 tables from already-collected inputs (pure; used by --run and synthetic tests)."""
    draws = draws or Draws()
    grid = Grid(rows)
    contrasts = contrast_rows(grid, draws, persistence)
    d1_table, d1_dependence = d1_rows(d1)
    dependence = {"D-1": d1_dependence, "D-2": d2_dependence(ridge)}
    return {
        "P4": {"contrasts": contrasts, "interaction": interaction_rows(grid, draws, contrasts),
               "cross_backbone": cross_backbone_rows(contrasts), "baseline_accuracy": baseline_rows(grid, persistence),
               "parameter_counts": parameter_counts(), "missing_units": grid.missing_units()},
        "P5": {"D-1": d1_table,
               "D-2": {block: {RESOURCES[r]: dict(zip(_cohort(block), _list(values[:, r])))
                               for r in range(len(RESOURCES))} for block, values in dependence["D-2"].items()},
               "D-3": d3_rows(draws, dependence, contrasts), "D-4": d4_rows(d4), "D-6": d6_rows(grid),
               "D-7": d7_rows(d7)},
    }


def _cohort(block):
    from .src.analysis.grid import COHORT
    return COHORT[block]


def _list(values):
    return [None if value != value else float(value) for value in values]


def run(output):
    from .src.analysis.collect import d1_summaries, d4_slots, d7_fits, mae_rows, require_evaluation_closed
    from .src.analysis.historical import HistoricalReader
    from .src.provenance import Journal

    from .src.orchestrator import execution_fingerprints

    seal = execution_fingerprints()
    journal = Journal(seal)
    gate = require_evaluation_closed(journal)
    reader = HistoricalReader()
    results = analyse(rows=mae_rows(journal), persistence=reader.persistence(), ridge=reader.ridge(),
                      d1=d1_summaries(), d4=d4_slots(journal), d7=d7_fits(journal))
    document = {"format": FORMAT, "tier": "tier 2 extension; descriptive, no p-values",
                "fingerprint_sha256": seal.digest, "evaluation_gate_sha256": sha256(canonical_json(gate)).hexdigest(),
                "historical_inputs": reader.input_hashes(), "results": results}
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    output.write_text(json.dumps(document, indent=1, allow_nan=False) + "\n")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", metavar="OUTPUT", help="analyse the closed journal and write OUTPUT (JSON)")
    args = parser.parse_args(argv)
    if args.run:
        run(args.run)
        print(f"Wrote {args.run}")
    else:
        json.dump(dry_plan(), sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
