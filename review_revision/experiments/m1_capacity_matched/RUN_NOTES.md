# Stage 18B2 execution handoff

POST-HOC SENSITIVITY CONTROL. Not a replacement for any frozen result.

## Scope

M1 hidden size 64 to 129 only. The original M1 inner training, context selection
and seed-specific epoch selection are rerun. There are 8,190 inner and 2,730
final fresh fits, 910 context selections and 55,860 final metric rows across
TimeTrack, fastStorage, Rnd and Materna T1–T3. No H64 choices/fits are reused.

Parameter counts: 206,420 externally versus aggregate S2 206,100; 207,980 for
TimeTrack versus aggregate S2 206,880. All other scientific settings remain
frozen. Three authorised comparisons use H129 against original S2, original
M1-H64 and completed Stage18B1R common-S2. The latter's contexts are aligned
to H64, not necessarily H129's newly selected contexts.

## Execution and safety

Adapter: `run_capacity_control.py`; configuration: `control_config.json`;
tests: `test_capacity_control.py`; analysis: `analyse_capacity_control.py`.
All writes are restricted to this directory. Frozen driver main/writer functions
and Stage18B1R writers are never invoked. Frozen training/selection functions
are imported; the M1 model factory alone is replaced by an H129 factory, with
fail-closed finite-loss/gradient checks that do not change finite calculations.

The initial test suite passed 48 non-training checks in isolated TimeTrack,
Bitbrains and Materna processes. `validation/tests.json` holds results. The
preflight must pass before execution. `provenance/experiment.json` seals the
source/config/plan hashes. Do not patch sealed code during execution.

The protected baseline includes all three original scientific trees, the
manuscript, Stage18B1R and its predecessor snapshot. Original frozen scientific
bytes are checked against Stage18B1R's pre-control baseline before this new
baseline is accepted. Final audit hashes every protected file and checks refs.

Use the legacy environment with bytecode writes disabled:

```
PYTHONDONTWRITEBYTECODE=1 old_fgcs_rejected/.venv_legacy/bin/python -B review_revision/experiments/m1_capacity_matched/run_capacity_control.py run --workers 4
```

Before any launch, inspect process IDs and the runtime lock; never launch a
duplicate. Inspect `STOP.json`, `failures/`, `attempts/`, `completions/` and
`execution.log`. An attempt without an exact valid completion requires explicit
recovery authorisation; do not silently retry it. Current failures require stop
and notification. Completed exact H129 units are skipped with hash/identity
validation. Inner and final completions have separate namespaces. All planned
identities and exact final coverage are independently audited per block.

The runner performs all six blocks, independent audits, full preservation and
then analysis. `completion_summary.json` marks numerical completion pending a
human report audit; the generated report is explicitly a draft, not a PASS.
The final report must answer the central capacity question, all priority cases,
all-six resource outcomes, unexpected results and limitations. Refresh the
output SHA256 inventory after any report-only edits. Do not pool blocks or add
tests/statistics/experiments. Do not edit the manuscript, commit or push.

Automatic follow-up is authorised. Heartbeat:
`continue-stage-18b2-m1-capacity-matched-control`.
Stay quiet while healthy; notify only meaningful completion/failure/user action;
pause after terminal completion or blocking failure.
