# A2 launcher runbook (v0.4 amendment A2)

**A2 differences from the v0.4 run.** This package runs only amendment A2
(`review_revision/fgcs_strengthening/residual_amendment_A2.md`). Its own runtime is
`fgcs_strengthening_v04a2/runtime/`, and it is frozen by the annotated tag `fgcs-v04-a2-residual`.

- **Schedule:** the tier-2 2×2 of all four backbones under the change parameterisation: 3 certificates,
  70 canary, 10,430 inner, 10,500 final and 10,500 evaluation units.
- **Diagnostics:** none; the diagnostics phase is empty.
- **Canary:** the first cohort VM per block, fold 1, seed 0, inner fits of every cell of every backbone (70 fits).
- **v0.4 and A1:** the packages and their closed runtimes are only read, by `analyse_residual.py`, after both
  evaluation gates close.

The v0.4 text below applies otherwise, with these substitutions:
- tag `fgcs-v04-min-final-r2` → `fgcs-v04-a2-residual`;
- 90-fit canary → 70-fit canary;
- the analysis entry point `analyse_study` → `analyse_residual`.


The launcher, `fgcs_strengthening_v04a2/launch.py`, is an operator tool. It is **not** a sealed source: it drives the frozen orchestrator under the v0.4 execution seal and changes no registered code. Every session records the launcher's SHA-256, preflight and recovery reports under `runtime/launcher/`.

It is ported from the r3 Stage 4A launcher with the protocol P9 changes:
- exactly **six** single-threaded fit workers;
- no systems phase;
- the host is checked against `registration/host_manifest.json` by `host.py`, instead of r3's systems module.

**Freezing (protocol P9, deviation D1).** v0.4-min is frozen by Git, not by an external registration. The final state is the annotated tag `fgcs-v04-min-final-r2`. It carries exactly the package and seal of `fgcs-v04-min-final` (whose name the package's recorded decisions still cite) and differs only in this unsealed launcher: the mandatory backup gate, which no protocol section requires, was removed. `fgcs-v04-min-final` stays published and is never used to run. The launcher reads the tagged commit, package digest (`registration/PACKAGE.json`) and execution seal (`registration/execution_seal.json`) from the tag itself, and refuses if any tracked file under `fgcs_strengthening_v04a2/` or the protocol differs from the tag. The only exception is `registration/REGISTRATION_EVIDENCE_TEMPLATE.md`, which holds the unlock flag. OSF `kuwra` (v0.3) is kept as superseded historical evidence; nothing in v0.4 reads it. The predecessor tag `fgcs-v04-registration-package` is kept and never used to run.

**Status: locked** until you set `EXECUTION_UNLOCKED = YES` in `registration/REGISTRATION_EVIDENCE_TEMPLATE.md`. The r3 package and its launcher stay locked permanently.

## Before the first run

1. **Authorise.** Run the read-only preflight (step 6), record its output in `REGISTRATION_EVIDENCE_TEMPLATE.md` with the date and your decision, and only then change the flag to `EXECUTION_UNLOCKED = YES`. This is a human decision.

2. **Disk.** P9 projects about 5–6 GB for the whole run.
   - Every phase start needs at least **15 GB** free, and the running monitor stops gracefully below that.
   - The inner and final phases also need at least **20 GB** free to start. A backup is not required (see Backups).
   - Never delete or move a sealed input; preflight re-hashes them. Never move or symlink `runtime/`.

3. **Power and sleep.**
   - Plug in AC power; every phase start refuses on battery.
   - Keep the lid open, or use clamshell mode with AC and an external display.
   - While running, the launcher holds a `caffeinate -i -m -s` assertion against idle sleep. It changes no system setting.
   - On battery for more than 2 minutes, the monitor stops gracefully.

4. **Host.** Keep the frozen host as it is: no Low Power Mode, no OS or library updates during the run. The host manifest records the hostname, CPU, cores, memory, OS kernel and power mode; Python, NumPy, pandas, PyTorch and its BLAS; and the single-thread CPU conditions. Any difference refuses.

5. **Survive a closed terminal.** Run the launcher inside `screen`:

   ```bash
   screen -S fgcs
   cd /Users/fgtek002/TimeTrack
   export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
   PY=old_fgcs_rejected/.venv_legacy/bin/python
   ```

   Detach with `Ctrl-A d` and reattach with `screen -r fgcs`.

6. **Preflight** (read-only):

   ```bash
   $PY -B -m fgcs_strengthening_v04a2.launch preflight
   ```

   It reports the frozen tag (object and commit), package digest and seal; the host check (intra-op 1, inter-op 1, the three thread variables at 1, device `cpu`); AC power, free disk and thermal state.

## Start: certify, canary, stop

```bash
$PY -B -m fgcs_strengthening_v04a2.launch start
```

1. It repeats every gate: unlock flag, threads, tag and tracked files, package, seal, host, AC, disk and the recovery check.
2. It creates the runtime journal with the frozen seal; every launcher record names the tag object and commit.
3. It runs the three modern structural certificates with one worker (re-run in A2 for the anchored outputs).
4. It runs the **90** canary inner fits (P9 step 2; **70** in A2) with exactly **six** single-threaded worker processes.
5. It **stops** at the canary gate and never continues by itself.

After reviewing the canary's technical evidence (no outer-test quantity exists):

```bash
$PY -B -m fgcs_strengthening_v04a2.launch approve-canary --approver "NAME" --note "Technical checks reviewed; no outer-test quantity consulted."
```

Then, one phase at a time and in order: `inner`, `final`, `diagnostics`, then `evaluation`:

```bash
$PY -B -m fgcs_strengthening_v04a2.launch run --phase inner
```

`run --phase X` refuses until every earlier phase is terminal (complete, failed or abandoned), in the controller and again in each worker (P9 run order). The orchestrator also closes the fit phases before evaluation. The analysis (`analyse_study.py --run`) needs the closed evaluation gate.

## While it runs

- **Logs.** Each worker writes to `runtime/launcher/logs/<time>-<phase>-r<round>-w<i>.{out,err}`, never to a pipe. Live worker PIDs are in `runtime/launcher/workers/`.
- **Health.** Every 10 minutes, `runtime/launcher/health/<date>.jsonl` gains one line: free disk and use per hour, hours until the disk guard, the outcome count, load, thermal state, AC power, live workers, the stop flag and backup freshness.
- **Guards.** Every minute the controller checks free disk (minimum 15 GB) and power (2-minute battery grace). Either one triggers a graceful stop.
- **Thermal.** The fanless M3 reached thermal state "fair" (1) in the sustained six-worker benchmark. Throttling slows the run but doesn't change results.

## Pausing, resuming, recovery

| Action | Command |
|---|---|
| Planned pause | `$PY -B -m fgcs_strengthening_v04a2.launch stop --reason "planned pause"`, or one Ctrl-C in the launcher's terminal |
| Status | `$PY -B -m fgcs_strengthening_v04a2.launch status --phase canary` |
| Recovery check | `$PY -B -m fgcs_strengthening_v04a2.launch recover-check` (read-only) |
| Resume | `$PY -B -m fgcs_strengthening_v04a2.launch resume`, then rerun the same phase command |

- A stop lets each worker finish its current unit; no retry is used. Ctrl-C, closing the terminal and SIGTERM all become this graceful stop. Workers are never killed.
- After a crash, reboot or power loss, run `recover-check` first. `resume` refuses while workers are still running, and while a modern family is halted until the author passes `--acknowledge-modern-halt` after review.
- **Never** kill workers, run `kill -9`, or call `Journal.quarantine` or `Orchestrator.reopen` by hand. Code repairs go only through a chained seal amendment.

## Backups

Backups are **optional** and never block a phase: the frozen protocol does not require them. They are still recommended for a multi-day run. `fgcs_strengthening_v04a2/backup_runtime.py` is ported unchanged from r3 (verified, hard-linked rsync snapshots on an external drive; the latest two kept), and the health log and `status` report their freshness. To use it, run it hourly in a second `screen` window:

```bash
$PY -B -m fgcs_strengthening_v04a2.backup_runtime backup --dest /Volumes/<drive>/fgcs_v04_runtime_backups --every 3600
$PY -B -m fgcs_strengthening_v04a2.backup_runtime status --dest /Volumes/<drive>/fgcs_v04_runtime_backups
$PY -B -m fgcs_strengthening_v04a2.backup_runtime verify --dest /Volumes/<drive>/fgcs_v04_runtime_backups
```

Failures never touch the runtime; they are recorded in `fgcs_strengthening_v04a2/backup_status.json` (git-ignored). Restore only into a new, empty path, then move it into place and run `recover-check`.

## What the launcher checks

| Gate | Where |
|---|---|
| `EXECUTION_UNLOCKED = YES` (exactly one line; a missing file refuses) | every journal command |
| Thread variables exported as 1 before Python | controller and every worker |
| `fgcs-v04-min-final-r2` is an annotated tag; no tracked v0.4 file or the protocol differs from it (unlock flag excepted) | preflight and every worker |
| The package rebuilt from the repository equals the tagged digest | preflight |
| Live execution seal equals the tagged seal | preflight and every worker |
| Live host equals `host_manifest.json`; torch intra/inter-op 1; CPU | preflight (fresh process) and every worker |
| AC power; at least 15 GB free; recovery check OK | every phase start |
| Every earlier phase terminal (P9 run order) | every phase start and every worker |
| At least 20 GB free | inner and final phase start |
| Free disk at least 15 GB; battery for no more than 2 minutes | every minute while running |
| Exactly six fit workers (slot locks); certify uses one | orchestrator and launcher |

## Tests

`tests/test_launcher.py` and `tests/test_backup_runtime.py` use generated data and scratch journals only:
- **Gates:** unlock flag, missing authorisation file, tag-based freezing (tagged values, tracked-file drift, no external registration gate), P9 phase order, threads, power and disk; refusal while locked, with no runtime created; six workers and no systems phase; `runtime/` git-ignored.
- **Host:** the live host matches its own capture; a changed kernel, library version or thread count is reported.
- **Six-process canary:** run through the controller, each unit fitted exactly once.
- **Stops, robustness and recovery:** as in r3.
