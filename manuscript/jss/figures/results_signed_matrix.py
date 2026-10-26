#!/usr/bin/env python3
"""Render the frozen primary gains without recomputing scientific results.

From the repository root:
    old_fgcs_rejected/.venv_legacy/bin/python \
        manuscript/jss/figures/results_signed_matrix.py

Requires matplotlib (validated with 3.11.1). The bundled Python can also run
--audit-only without matplotlib. The script validates both frozen manifests
and the existing manuscript table before drawing, then prints all 72 labels.
Only the neighbouring results_signed_matrix.pdf is generated. No manuscript,
table, reference, frozen result, supplementary statistic or raster is written.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import math
import os
from pathlib import Path
import re
import tempfile


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
OUTPUT = SCRIPT.with_suffix(".pdf")
SCIENTIFIC_CHECKPOINT = "fee20c316040c57b69ba12a193530c955b539771"
TABLE = "manuscript/jss/tables/primary_gains.tex"
PHASE4C = (
    "independent_validation/05_bitbrains_factorial/"
    "PHASE4C_V2_SCIENTIFIC_ANALYSIS_FREEZE_MANIFEST.md"
)
PHASE4D = (
    "independent_validation/06_materna_replication/"
    "PHASE4D_MATERNA_FINAL_SCIENTIFIC_FREEZE_MANIFEST.md"
)
SOURCE_SHA256 = {
    TABLE: "98febf2c21b58cc787cdb367de00d9977943312ce8a1eafd713ab693d753f04e",
    PHASE4C: "a674c36f8f3f8a01d32e13b3d4dc7591e5b85259ee1444384bb6750db331d6f4",
    PHASE4D: "99b789fa273a57def0d0ed9531dad0f3f471a9ebe0ee5c1f97d2b047c162b941",
}

RESOURCES = ("CPU", "Throughput", "Memory", "Disk write")
BLOCKS = ("TimeTrack", "fastStorage", "Rnd", "Materna T1", "Materna T2", "Materna T3")
COLUMN_LABELS = ("TimeTrack", "fastStorage", "Rnd", "T1", "T2", "T3")
COMPARISONS = ("S2 vs S1", "M1 vs S2", "M1 vs S1")
PANEL_TITLES = (
    "(a) Contextual input: S2 versus S1",
    "(b) Shared representation: M1 versus S2",
    "(c) Full joint system: M1 versus S1",
)

# Explicit source-reported decimal strings, not inferred unrounded estimates.
# Rows: CPU, Throughput, Memory, Disk write. Columns: BLOCKS above.
# Phase 4C manifest: Bitbrains lines 56--61; TimeTrack lines 127--129.
# Final Phase 4D manifest: Materna lines 33--41.
SOURCE_VALUES = (
    (
        ("-3.3130", "-3.198519", "+1.412867", "-4.317958", "+4.207624", "-2.787548"),
        ("-0.2428", "+0.012731", "-7.214491", "+0.986935", "+0.294315", "+0.044766"),
        ("+0.8594", "+2.449985", "+1.673083", "-0.019692", "+3.948171", "+3.089002"),
        ("-0.4923", "+2.689207", "+0.160400", "-6.699662", "-1.120181", "+1.907168"),
    ),
    (
        ("+0.4696", "+0.045047", "-16.509941", "+0.882699", "-2.564363", "-8.099015"),
        ("-0.8401", "-27.094152", "-14.318987", "-7.308355", "-8.692761", "-7.914278"),
        ("-18.4769", "-4.867061", "-8.915737", "-13.218360", "-9.266823", "-8.702593"),
        ("-0.7956", "-4.072129", "-5.551233", "-27.457746", "-7.888503", "-71.295095"),
    ),
    (
        ("-2.8279", "-3.152031", "-14.863811", "-3.397145", "+1.751160", "-11.112327"),
        ("-1.0849", "-27.077972", "-22.566520", "-6.249291", "-8.372862", "-7.865970"),
        ("-17.4587", "-2.297834", "-7.093487", "-13.240655", "-4.952782", "-5.344768"),
        ("-1.2918", "-1.273414", "-5.381929", "-35.996983", "-9.097050", "-68.028209"),
    ),
)

PROPOSED_CAPTION = (
    "Primary overall MacroMAE percentage gains for (a) S2 versus S1, "
    "(b) M1 versus S2 and (c) M1 versus S1 across the evaluated evidence blocks. "
    "Positive values indicate lower MacroMAE for the candidate formulation; "
    "negative values indicate higher MacroMAE. Continuous signed colour uses a "
    "symmetric asinh mapping as a nonlinear visual aid only, without clipping "
    "values; printed raw percentages at the reported precision are authoritative. "
    "Legend ticks are raw percentage units, not transformed scores. "
    "Values are point estimates, not significance classifications. "
    "Materna T1, T2 and T3 are dependent temporal blocks. Comparisons are bounded to "
    "the evaluated implementation and eligible populations."
)

# Presentation constants only; no endpoint, threshold or scientific aggregation.
# Explicit signs remain readable in greyscale; text contrast follows luminance.
COLOUR_LIMIT = 75.0
WIDTH_MM = 174.0
HEIGHT_MM = 108.0


class ResultValueConflict(RuntimeError):
    """A supplied frozen number or its source identity does not reconcile."""


class FigureLegibilityConflict(RuntimeError):
    """Artwork geometry fails a non-scientific legibility check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ResultValueConflict("RESULT_VALUE_CONFLICT_FOUND: " + message)


def require_layout(condition: bool, message: str) -> None:
    if not condition:
        raise FigureLegibilityConflict("FIGURE_LEGIBILITY_CONFLICT: " + message)


def display(value: Decimal) -> str:
    """Formatting only: retain sign and use the table's two-decimal precision."""
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN), "+.2f")


def values_by_key() -> dict[tuple[str, str, str], Decimal]:
    require(len(SOURCE_VALUES) == 3, "expected three panels")
    values = {}
    for comparison, panel in zip(COMPARISONS, SOURCE_VALUES):
        require(len(panel) == 4, "expected four resource rows")
        for resource, row in zip(RESOURCES, panel):
            require(len(row) == 6, "expected six evidence blocks")
            for block, raw in zip(BLOCKS, row):
                value = Decimal(raw)
                require(value.is_finite(), "missing/non-finite value")
                values[comparison, block, resource] = value
    require(len(values) == 72, "expected 72 numeric cells")
    return values


def read_frozen_rows(text: str) -> dict[tuple[str, str, str], Decimal]:
    """Read existing reported rows; no metrics or aggregates are calculated."""
    rows = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[1] in COMPARISONS:
            block, comparison = cells[:2]
            if block in ("T1", "T2", "T3"):
                block = "Materna " + block
            if block not in BLOCKS:
                continue
            numbers = cells[2:]
        elif len(cells) == 5 and cells[0].startswith("TimeTrack "):
            block = "TimeTrack"
            comparison = cells[0].removeprefix("TimeTrack ")
            if comparison not in COMPARISONS:
                continue
            numbers = cells[1:]
        else:
            continue
        for resource, raw in zip(RESOURCES, numbers):
            key = comparison, block, resource
            require(key not in rows, "duplicate frozen row " + str(key))
            rows[key] = Decimal(raw.removesuffix("%"))
    return rows


def markdown_section(text: str, heading: str) -> str:
    """Select only the requested point-estimate section, not other analyses."""
    matches = list(re.finditer(r"(?m)^## " + re.escape(heading) + r"\s*$", text))
    require(len(matches) == 1, "missing/duplicate primary section " + heading)
    remainder = text[matches[0].end():]
    next_heading = re.search(r"(?m)^## ", remainder)
    return remainder[:next_heading.start()] if next_heading else remainder


def read_table(text: str) -> dict[tuple[str, str, str], Decimal]:
    rows = {}
    comparison = None
    for line in text.splitlines():
        match = re.search(r"Panel ([ABC]):", line)
        if match:
            comparison = COMPARISONS["ABC".index(match.group(1))]
        if not re.match(
            r"\s*(TimeTrack|Bitbrains fastStorage|Bitbrains Rnd|Materna T[123])\s*&", line
        ):
            continue
        cells = line.split("&")
        block = cells[0].strip().removeprefix("Bitbrains ")
        require(comparison is not None and len(cells) == 5, "invalid table row")
        for resource, cell in zip(RESOURCES, cells[1:]):
            match = re.search(r"\$\s*([+-]?\s*\d+\.\d+)\s*\$", cell)
            require(match is not None, "invalid table number")
            key = comparison, block, resource
            require(key not in rows, "duplicate table row " + str(key))
            rows[key] = Decimal(match.group(1).replace(" ", ""))
    return rows


def validate_sources() -> dict[tuple[str, str, str], Decimal]:
    values = values_by_key()
    texts = {}
    for relative, expected_hash in SOURCE_SHA256.items():
        raw = (ROOT / relative).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected_hash, "source identity " + relative)
        texts[relative] = raw.decode("utf-8")
    primary_4c = markdown_section(texts[PHASE4C], "Primary MacroMAE gains")
    primary_4c += markdown_section(texts[PHASE4C], "TimeTrack comparison")
    primary_4d = markdown_section(texts[PHASE4D], "Frozen Materna primary gains")
    frozen = read_frozen_rows(primary_4c)
    for key, value in read_frozen_rows(primary_4d).items():
        require(key not in frozen, "duplicate cross-manifest value")
        frozen[key] = value
    table = read_table(texts[TABLE])
    require(set(frozen) == set(values) == set(table), "source/key coverage is not 72/72/72")
    for key, value in values.items():
        require(value == frozen[key], "frozen value mismatch " + str(key))
        require(display(value) == display(table[key]), "table display mismatch " + str(key))
    return values


def print_audit(values: dict[tuple[str, str, str], Decimal]) -> None:
    print("SOURCE VALIDATION PASS: 72 supplied values / 72 frozen values / 72 table cells")
    print("Panel,Resource," + ",".join(BLOCKS))
    for panel, comparison in zip("ABC", COMPARISONS):
        for resource in RESOURCES:
            labels = [display(values[comparison, block, resource]) for block in BLOCKS]
            print(",".join([panel, resource] + labels))


def render(values: dict[tuple[str, str, str], Decimal]) -> None:
    # Font caches are temporary; no dependency or user configuration is modified.
    with tempfile.TemporaryDirectory(prefix="stage15c1-mpl-") as cache:
        os.environ.setdefault("MPLCONFIGDIR", cache)
        os.environ.setdefault("XDG_CACHE_HOME", cache)
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        from matplotlib.patches import Rectangle

        with matplotlib.rc_context({
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "pdf.use14corefonts": False,
            "axes.unicode_minus": False,
        }):
            fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), dpi=180)
            ax = fig.add_axes((0, 0, 1, 1))
            ax.set(xlim=(0, WIDTH_MM), ylim=(0, HEIGHT_MM))
            ax.set_axis_off()
            cell_width, cell_height, grid_left = 24.0, 4.8, 28.0
            cmap = LinearSegmentedColormap.from_list(
                "signed_gain", ("#9b4410", "#fffdfb", "#14547a"), N=1024)
            def position(raw):
                return 0.5 + math.asinh(raw) / (2 * math.asinh(COLOUR_LIMIT))
            def colour(raw):
                require_layout(abs(raw) <= COLOUR_LIMIT, "colour scale would clip a value")
                return cmap(position(raw))
            numeric_artists = []
            for comparison, title, panel_top in zip(COMPARISONS, PANEL_TITLES, (104, 73, 42)):
                ax.text(2, panel_top, title, fontsize=9.5, fontweight="bold", va="center")
                ax.text(136, panel_top, "Materna temporal blocks", fontsize=8.5,
                        ha="center", va="center")
                ax.plot([100.5, 171.5], [panel_top - 2.1] * 2, color="0.35", lw=0.55)
                for x in (100.5, 171.5):
                    ax.plot([x, x], [panel_top - 2.1, panel_top - 2.7], color="0.35", lw=0.55)
                for column, label in enumerate(COLUMN_LABELS):
                    ax.text(grid_left + (column + 0.5) * cell_width, panel_top - 5.3,
                            label, fontsize=9, ha="center", va="center")
                for row, resource in enumerate(RESOURCES):
                    y = panel_top - 10.0 - row * cell_height
                    ax.text(2, y, resource, fontsize=9.2, va="center")
                    for column, block in enumerate(BLOCKS):
                        value = values[comparison, block, resource]
                        x = grid_left + column * cell_width
                        bottom = y - cell_height / 2
                        fill = colour(float(value))
                        ax.add_patch(Rectangle((x, bottom), cell_width, cell_height,
                                               facecolor=fill, edgecolor="white", lw=0.65,
                                               rasterized=False))
                        luminance = sum(c * w for c, w in zip(fill[:3], (0.2126, 0.7152, 0.0722)))
                        artist = ax.text(x + cell_width / 2, y, display(value), fontsize=9.5,
                                         ha="center", va="center",
                                         color="white" if luminance < 0.48 else "black")
                        numeric_artists.append((artist, x, bottom))
                # Boundary denotes group membership, never pooling or independence.
                grid_top = panel_top - 10.0 + cell_height / 2
                grid_bottom = grid_top - 4 * cell_height
                ax.plot([100, 100], [grid_bottom, grid_top], color="0.45", lw=0.65)

            ax.text(2, 6, "Gain (%)", fontsize=8.5, va="center")
            ax.text(103, 10.6, "Nonlinear asinh colour aid; exact values printed above",
                    fontsize=8, ha="center", va="center")
            left, width, steps = 36.0, 134.0, 512
            for i in range(steps):
                ax.add_patch(Rectangle((left + width*i/steps, 5), width/steps + 0.002,
                                       2.6, facecolor=cmap((i+0.5)/steps), edgecolor="none"))
            for raw in (-75, -20, -5, -1, 0, 1, 5, 20, 75):
                x = left + width * position(raw)
                ax.plot((x, x), (4.4, 5), color="0.3", lw=0.5)
                ax.text(x, 2.1, f"{raw:+d}" if raw else "0", fontsize=7.5,
                        ha="center", va="center")

            # Geometry checks are implementation checks, not scientific analyses.
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            for text in ax.texts:
                box = text.get_window_extent(renderer)
                require_layout(box.x0 >= 0 and box.y0 >= 0 and box.x1 <= fig.bbox.width
                               and box.y1 <= fig.bbox.height, "text outside artwork bounds")
            require_layout(len(numeric_artists) == 72, "expected 72 rendered numeric labels")
            for text, x, bottom in numeric_artists:
                box = text.get_window_extent(renderer)
                lo = ax.transData.transform((x + 0.4, bottom + 0.4))
                hi = ax.transData.transform((x + cell_width - 0.4, bottom + cell_height - 0.4))
                require_layout(box.x0 >= lo[0] and box.y0 >= lo[1]
                               and box.x1 <= hi[0] and box.y1 <= hi[1], "numeric label clips its cell")
            fig.savefig(OUTPUT, format="pdf", facecolor="white", metadata={
                "Title": "Primary overall MacroMAE gains: signed matrix",
                "Creator": "Matplotlib",
                "CreationDate": None,
                "ModDate": None,
            })
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true", help="validate and print; do not draw")
    parser.add_argument("--print-caption", action="store_true", help="also print the proposed caption")
    args = parser.parse_args()
    try:
        values = validate_sources()
        print_audit(values)
        if not args.audit_only:
            render(values)
            print("VECTOR PDF:", OUTPUT)
            print(f"ARTWORK SIZE: {WIDTH_MM:.0f} x {HEIGHT_MM:.0f} mm")
        if args.print_caption:
            print("PROPOSED CAPTION:", PROPOSED_CAPTION)
    except (ResultValueConflict, FigureLegibilityConflict) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
