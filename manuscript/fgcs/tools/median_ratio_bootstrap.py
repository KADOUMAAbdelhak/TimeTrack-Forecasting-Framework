"""Post-hoc VM-cluster bootstrap intervals for the tier-2 matched-cell median MAE ratios (read only).

    old_fgcs_rejected/.venv_legacy/bin/python manuscript/fgcs/tools/median_ratio_bootstrap.py OUT.json

Reads the closed tier-2 (v0.4) journal through the read-only reader, with every write refused, and rebuilds
the native-MAE grid with the frozen tier-2 analysis code. It then resamples the ten VMs of each block, using
the frozen tier-2 draw matrices (seed 20261007, 10,000 replicates), and recomputes the median over matched,
seed-averaged entity x fold x horizon cells of the candidate/reference MAE ratio. The point estimates must
equal the frozen analysis output (analysis_v04.json) exactly, or the script refuses.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from fgcs_strengthening_v04a1.analyse_intervention import read_only_v04_journal  # noqa: E402
from fgcs_strengthening_v04.plan_execution import fit_identities  # noqa: E402
from fgcs_strengthening_v04.src.analysis import collect  # noqa: E402
from fgcs_strengthening_v04.src.analysis.bootstrap import Draws, percentile_interval  # noqa: E402
from fgcs_strengthening_v04.src.analysis.grid import BACKBONES, BLOCKS, COHORT, DEFINED, Grid, seed_average  # noqa: E402
from fgcs_strengthening_v04.src.analysis.primary import CONTRASTS, defined  # noqa: E402
from fgcs_strengthening_v04.src.identity import RESOURCES  # noqa: E402

ANALYSIS = ROOT / "fgcs_strengthening_v04/runtime/analysis/analysis_v04.json"
ANALYSIS_SHA = "308841865ec87b04e10ecb64f20bc13ce2e671511a1574056028f7b5710dd17a"


def median_interval(draws, block, candidate, reference):
    """Point median ratio and its VM-cluster bootstrap interval over seed-averaged [entity, fold, horizon] arrays."""
    present = np.isfinite(candidate) & np.isfinite(reference) & (reference > 0)
    ratios = np.where(present, candidate / np.where(present, reference, 1.0), np.nan).reshape(len(candidate), -1)
    point = float(np.nanmedian(ratios))
    indices = draws.indices(block)  # [replicates, entities]
    replicates = np.nanmedian(ratios[indices].reshape(len(indices), -1), axis=1)
    interval, undefined = percentile_interval(replicates)
    return point, interval, undefined


def main():
    out = Path(sys.argv[1])
    if out.exists():
        sys.exit(f"Refusing to overwrite {out}")
    if sha256(ANALYSIS.read_bytes()).hexdigest() != ANALYSIS_SHA:
        sys.exit("analysis_v04.json differs from its frozen digest")
    frozen = {(r["backbone"], r["contrast"], r["block"], r["resource"]): r
              for r in json.loads(ANALYSIS.read_text())["results"]["P4"]["contrasts"]}
    journal = read_only_v04_journal()
    collect.require_evaluation_closed(journal)
    identities = [i for i in fit_identities() if i.phase == "final" and i.arm in ("core", "modern")]
    grid = Grid(collect.mae_rows(journal, identities), cells=[(b, c) for b in BACKBONES for c in DEFINED[b]])
    draws = Draws()
    rows = []
    for block in BLOCKS:
        for backbone in BACKBONES:
            mask = grid.mask(backbone, block)
            arrays = {cell: grid.masked(backbone, cell, block, mask) for cell in DEFINED[backbone]}
            for candidate, reference, _ in CONTRASTS:
                if not defined(backbone, candidate, reference):
                    continue
                for r, resource in enumerate(RESOURCES):
                    c, b = seed_average(arrays[candidate][:, r]), seed_average(arrays[reference][:, r])
                    point, interval, undefined = median_interval(draws, block, c, b)
                    expected = frozen[backbone, f"{candidate}:{reference}", block, resource]["median_ratio"]
                    if point != expected:
                        sys.exit(f"Point median differs from the frozen output: {backbone} {candidate}:{reference} "
                                 f"{block} {resource} {point!r} != {expected!r}")
                    rows.append({"backbone": backbone, "contrast": f"{candidate}:{reference}", "block": block,
                                 "resource": resource, "median_ratio": point, "interval": interval,
                                 "undefined_replicates": undefined,
                                 "win_rate": frozen[backbone, f"{candidate}:{reference}", block, resource]["win_rate"]})
    document = {"format": "fgcs-tier2-median-ratio-bootstrap/1",
                "post_hoc": "computed after all results were known; descriptive, no p-values",
                "source_analysis_sha256": ANALYSIS_SHA, "v04_execution_seal": journal.seal.digest,
                "bootstrap": {"seed": 20261007, "replicates": len(draws.indices(BLOCKS[0])),
                              "unit": "VM (ten per block), reusing the frozen tier-2 draw matrices",
                              "interval": "percentile 95%"},
                "cohort": {block: list(COHORT[block]) for block in BLOCKS}, "rows": rows}
    encoded = json.dumps(document, indent=1, allow_nan=False) + "\n"
    out.write_text(encoded)
    print(out, sha256(encoded.encode()).hexdigest(), len(rows), "rows")


if __name__ == "__main__":
    main()
