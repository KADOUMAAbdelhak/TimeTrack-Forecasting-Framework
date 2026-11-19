"""v0.4 analyses (protocol P4 and P5). Pure functions over typed rows; nothing reads data on import.

grid       native-MAE rows, the explicit-coordinate grid and the P4 missing-fit rule
bootstrap  the per-block VM-cluster draws (seed 20261007, 10,000 replicates) and Spearman
primary    P4: gains, consistency classes, intervals, interaction, descriptives, baseline table
mechanism  P5: D-1 lagged correlation, D-2 Ridge gain, D-3 association, D-4, D-6 affinity, D-7
historical v1 persistence and Ridge AR/ARX rows bound to the frozen outer-test support
collect    journal readers that turn closed v0.4 or A1 outcomes into analysis rows

Amendments A1 and A2 are analysed by analyse_intervention.py and analyse_residual.py (package root),
sealed with these sources.
"""

from pathlib import Path as _Path

_HOME = _Path(__file__).resolve().parents[2]
# Sealed with the execution runtime (orchestrator.execution_sources), so the analysis is fixed before any fit.
SOURCES = tuple((_HOME / name).relative_to(_HOME.parent).as_posix() for name in (
    "analyse_study.py", "analyse_intervention.py", "analyse_residual.py", "configs/historical_results_v03.json",
    *(f"src/analysis/{module}.py" for module in (
        "__init__", "grid", "bootstrap", "primary", "mechanism", "historical", "collect"))))
