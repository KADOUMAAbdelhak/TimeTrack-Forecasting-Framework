"""Figure 5: the tier-2 LSTM accuracy-consolidation trade-off of amendment A3, from the hash-checked A3 output.

    old_fgcs_rejected/.venv_legacy/bin/python manuscript/fgcs/tools/a3_figure.py OUT.pdf

Plots, for the tier-2 LSTM, mean models per machine x fold x seed unit against the largest matched-cell median MAE
ratio versus S2 over the 8 resource x block cells. The points are exactly the values reported in main-text Table 5
(S2, M1, G-share 1%, G-group 1% and 2%, the oracle) and Supplementary Table S24 (the 15 fixed groupings). It
computes no new statistic and prints every plotted value.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
A3 = ROOT / "fgcs_strengthening_v04a3/runtime/analysis_a3.json"
A3_SHA = "33e11a858ea338b3c3ff25bec2f59527a3a2100a386658443def77956501cee0"
BLUE, GREY, INK, MUTED = "#2166ac", "#8c8c8c", "#222222", "#555555"
plt.rcParams.update({"font.family": "serif", "font.size": 7, "axes.titlesize": 8, "pdf.fonttype": 42,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})


def main():
    out = Path(sys.argv[1])
    data = A3.read_bytes()
    if sha256(data).hexdigest() != A3_SHA:
        sys.exit("analysis_a3.json differs from its frozen digest")
    d = json.loads(data)

    def point(policy):
        rows = [r for r in d["rows"] if r["tier"] == "tier2" and r["backbone"] == "LSTM" and r["policy"] == policy]
        sums = [s for s in d["summaries"] if s["tier"] == "tier2" and s["backbone"] == "LSTM" and s["policy"] == policy]
        assert len(rows) == 8 and len(sums) == 2
        models = sum(s["mean_models"] * s["units"] for s in sums) / sum(s["units"] for s in sums)
        return models, max(r["median_ratio_vs_S2"] for r in rows)

    fixed = sorted({r["policy"] for r in d["rows"] if r["policy"].startswith("partition:")})
    fixed_points = [point(p) for p in fixed]
    policies = {"S2": point("S2"), "M1": point("M1"), "G-share@1%": point("G-share@1%"),
                "G-group@1%": point("G-group@1%"), "G-group@2%": point("G-group@2%"),
                "oracle-group": point("oracle-group")}

    fig, ax = plt.subplots(figsize=(3.45, 2.35), constrained_layout=True)
    ax.axhline(1.01, color=GREY, lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(0.85, 1.0105, "1% margin", ha="left", va="bottom", fontsize=6, color=MUTED)
    ax.axhline(1.0, color=GREY, lw=0.5, zorder=1)
    xs, ys = np.array(fixed_points).T
    ax.scatter(xs, ys, s=22, color=GREY, edgecolor="white", linewidth=0.6, zorder=2,
               label="Fixed grouping, every unit (15)")
    ax.scatter(*policies["S2"], s=34, marker="s", color=INK, zorder=4)
    ax.scatter(*policies["M1"], s=34, marker="s", color=INK, zorder=4)
    ax.scatter(*zip(policies["G-group@1%"], policies["G-group@2%"]), s=46, marker="D", color=BLUE,
               edgecolor="white", linewidth=0.6, zorder=5, label="Validation-chosen grouping")
    ax.scatter(*policies["G-share@1%"], s=40, marker="^", color=BLUE, edgecolor="white", linewidth=0.6, zorder=5,
               label="Validation gate, share all or none")
    ax.scatter(*policies["oracle-group"], s=40, marker="o", facecolor="none", edgecolor=INK, linewidth=0.9,
               zorder=5, label="Oracle grouping (uses test)")

    def label(key, text, dx, dy, ha="left"):
        x, y = policies[key]
        ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va="center",
                    fontsize=6.2, color=INK)

    label("M1", "M1: one shared model", 6, 0)
    label("S2", "S2: four\nindependent", -6, 9, ha="right")
    label("G-group@1%", r"$\tau$ = 1%", -7, -7, ha="right")
    label("G-group@2%", r"$\tau$ = 2%", -6, 3, ha="right")

    ax.set_xlim(0.8, 4.2)
    ax.set_xticks([1, 2, 3, 4])
    ax.set_ylim(0.994, 1.068)
    ax.set_xlabel("Models per machine, fold and seed (mean)")
    ax.set_ylabel("Largest median MAE ratio vs S2\n(over 8 resource-block cells)")
    ax.grid(axis="y", color="#e6e6e6", lw=0.5, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="upper right", fontsize=5.8, frameon=False, handletextpad=0.3, borderaxespad=0.2)
    fig.savefig(out, metadata={"Title": "Figure 5", "Creator": None, "Producer": None})

    for name, (x, y) in policies.items():
        print(f"{name:14s} models {x:.2f} max ratio {y:.4f}")
    for name, (x, y) in zip(fixed, fixed_points):
        print(f"{name[len('partition:'):]:45s} models {x:.2f} max ratio {y:.4f}")


if __name__ == "__main__":
    main()
