"""Figures 2 and 3 as typical-cell statistics: matched-cell median MAE ratio (colour, printed) and win rate.

    old_fgcs_rejected/.venv_legacy/bin/python manuscript/fgcs/tools/typical_cell_figures.py OUT_DIR

Reads only hash-checked frozen outputs; refuses on any digest mismatch. Prints every plotted value.

- Tier 1 (Figure 2): seed-averaged entity x fold x lead MAEs, matched per comparison
  (matched_seed_mean_errors.csv). S2:S1 and M1:S2 reproduce the published medians and win rates.
  M1:S1 uses the same cells (S2 is identical in both files).
- Tier 2 (Figure 3): the contrast rows of the frozen tier-2 analysis output (analysis_v04.json).
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
TIER1 = ROOT / "review_revision/stage18c1_evidence/matched_seed_mean_errors.csv"
TIER1_INVENTORY = ROOT / "review_revision/stage18c1_evidence/output_sha256_inventory.json"
TIER1_ROBUST = ROOT / "review_revision/stage18c1_evidence/robust_seed_mean_cells.csv"
TIER2 = ROOT / "fgcs_strengthening_v04/runtime/analysis/analysis_v04.json"
TIER2_SHA = "308841865ec87b04e10ecb64f20bc13ce2e671511a1574056028f7b5710dd17a"

RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
LABEL = {"CPU": "CPU", "THROUGHPUT": "Throughput", "MEMORY": "Memory", "DISK_WRITE": "Disk write"}
T1_BLOCKS = ("TimeTrack", "fastStorage", "Rnd", "Materna-T1", "Materna-T2", "Materna-T3")
T1_COLUMNS = ("TimeTrack", "fastStorage", "Rnd", "Materna T1", "Materna T2", "Materna T3")
BACKBONES = ("LSTM", "DLinear", "PatchTST", "iTransformer")
BACKBONE_LABEL = {"LSTM": "LSTM", "DLinear": "DLinear", "PatchTST": "PatchTST-style",
                  "iTransformer": "iTransformer-style"}
SATURATION = 0.10  # colour saturates at |ln ratio| = 0.10; printed values are authoritative
NORM = TwoSlopeNorm(vmin=-SATURATION, vcenter=0.0, vmax=SATURATION)
CMAP = plt.get_cmap("RdBu_r")
plt.rcParams.update({"font.family": "serif", "font.size": 7, "axes.titlesize": 8, "pdf.fonttype": 42})


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def tier1():
    inventory = json.loads(TIER1_INVENTORY.read_text())
    recorded = json.dumps(inventory)
    for path in (TIER1, TIER1_ROBUST):
        if digest(path) not in recorded:
            sys.exit(f"{path.name} differs from its recorded SHA-256")
    cells = pd.read_csv(TIER1)
    keys = ["block", "resource", "entity", "fold", "lead"]
    context = cells[cells.comparison == "S2_vs_S1"].set_index(keys)
    sharing = cells[cells.comparison == "M1_vs_S2"].set_index(keys)
    joined = context.join(sharing, lsuffix="_c", rsuffix="_s", how="inner")
    if len(joined) != len(context) or not np.array_equal(joined.candidate_mae_c.values, joined.reference_mae_s.values):
        sys.exit("S2 differs between the context and sharing cell files")
    robust = pd.read_csv(TIER1_ROBUST)
    values = {}
    for comparison, (cand, ref) in {"S2:S1": ("candidate_mae_c", "reference_mae_c"),
                                     "M1:S2": ("candidate_mae_s", "reference_mae_s"),
                                     "M1:S1": ("candidate_mae_s", "reference_mae_c")}.items():
        for (block, resource), g in joined.groupby(level=["block", "resource"]):
            ratio = float(np.median(g[cand] / g[ref]))
            win = float((g[cand] < g[ref]).mean())
            values[comparison, block, resource] = (ratio, win)
            if comparison != "M1:S1":
                row = robust[(robust.block == block) & (robust.resource == resource)
                             & (robust.comparison == comparison.replace(":", "_vs_"))].iloc[0]
                if abs(row.median_MAE_ratio - ratio) > 1e-12 or abs(row.candidate_win_rate - win) > 1e-12:
                    sys.exit(f"Published tier-1 value not reproduced: {comparison} {block} {resource}")
    return values


def tier2():
    if digest(TIER2) != TIER2_SHA:
        sys.exit("analysis_v04.json differs from its frozen digest")
    rows = json.loads(TIER2.read_text())["results"]["P4"]["contrasts"]
    return {(r["contrast"], r["backbone"], r["block"], r["resource"]): (r["median_ratio"], r["win_rate"]) for r in rows}


def cell(ax, x, y, ratio, win):
    if ratio is None:
        ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1, facecolor="white", hatch="////", edgecolor="0.75", lw=0))
        return
    shade = math.log(ratio)
    face = CMAP(NORM(max(-SATURATION, min(SATURATION, shade))))
    ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1, facecolor=face, edgecolor="white", lw=0.8))
    dark = abs(shade) > 0.6 * SATURATION
    # Print as many decimals as needed (up to six) for the printed value to show its side of 1.
    digits = 3
    while ratio != 1 and round(ratio, digits) == 1 and digits < 6:
        digits += 1
    text = f"{ratio:.{digits}f}"
    ax.text(x, y - 0.12, text, ha="center", va="center", fontsize={3: 6.6, 4: 6.0}.get(digits, 5.4),
            color="white" if dark else "black")
    ax.text(x, y + 0.24, f"{100 * win:.0f}%", ha="center", va="center", fontsize=5.4,
            color="white" if dark else "0.25")


def frame(ax, columns, rows, title):
    ax.set_xlim(-.5, len(columns) - .5)
    ax.set_ylim(len(rows) - .5, -.5)
    ax.set_xticks(range(len(columns)), columns)
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_title(title, loc="left")


def colourbar(fig, axes):
    mappable = plt.cm.ScalarMappable(norm=NORM, cmap=CMAP)
    bar = fig.colorbar(mappable, ax=axes, orientation="horizontal", fraction=0.04, pad=0.09, aspect=60)
    ticks = [-0.10, -0.05, 0, 0.05, 0.10]
    bar.set_ticks(ticks, labels=[f"{math.exp(t):.2f}" for t in ticks])
    bar.set_label("Matched-cell median MAE ratio, candidate / reference (log scale; colour saturates beyond 0.90 and 1.11)")


def figure2(values, out):
    fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.25), constrained_layout=True)
    titles = {"S2:S1": "(a) Contextual input: S2 vs S1", "M1:S2": "(b) Sharing: M1 vs S2",
              "M1:S1": "(c) Joint change: M1 vs S1"}
    for ax, comparison in zip(axes, titles):
        frame(ax, ["Time-\nTrack", "fast-\nStorage", "Rnd", "T1", "T2", "T3"],
              [LABEL[r] for r in RESOURCES], titles[comparison])
        ax.tick_params(axis="x", labelsize=6.2)
        for x, block in enumerate(T1_BLOCKS):
            for y, resource in enumerate(RESOURCES):
                cell(ax, x, y, *values[comparison, block, resource])
        if comparison != "S2:S1":
            ax.set_yticklabels([])
    colourbar(fig, axes)
    fig.savefig(out, metadata={"Title": "Figure 2", "Creator": None, "Producer": None})


def figure3(values, out):
    contrasts = (("S2:S1", "(a) Context, independent: S2 vs S1"), ("M1:M0", "(b) Context, shared: M1 vs M0"),
                 ("M0:S1", "(c) Sharing, own input: M0 vs S1"), ("M1:S2", "(d) Sharing, all input: M1 vs S2"))
    short = {"CPU": "CPU", "THROUGHPUT": "Thr.", "MEMORY": "Mem.", "DISK_WRITE": "Disk"}
    columns = [short[r] for _ in ("fastStorage", "Rnd") for r in RESOURCES]
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 4.1), constrained_layout=True)
    for ax, (contrast, title) in zip(axes.flat, contrasts):
        frame(ax, columns, [BACKBONE_LABEL[b] for b in BACKBONES], title)
        ax.tick_params(axis="x", labelsize=6.2)
        for x, block in ((1.5, "fastStorage"), (5.5, "Rnd")):
            ax.text(x, 4.05, block, ha="center", va="top", fontsize=6.6, style="italic")
        for y, backbone in enumerate(BACKBONES):
            for x, (block, resource) in enumerate((b, r) for b in ("fastStorage", "Rnd") for r in RESOURCES):
                ratio, win = values.get((contrast, backbone, block, resource), (None, None))
                cell(ax, x, y, ratio, win)
        ax.axvline(3.5, color="0.35", lw=0.8)
    colourbar(fig, axes)
    fig.savefig(out, metadata={"Title": "Figure 3", "Creator": None, "Producer": None})


def main():
    out = Path(sys.argv[1])
    t1, t2 = tier1(), tier2()
    figure2(t1, out / "Figure_2.pdf")
    figure3(t2, out / "Figure_3.pdf")
    for key, (ratio, win) in sorted(t1.items()):
        print("T1", *key, f"{ratio:.4f}", f"{win:.3f}")
    for key, (ratio, win) in sorted(t2.items()):
        print("T2", *key, f"{ratio:.4f}", f"{win:.3f}")


if __name__ == "__main__":
    main()
