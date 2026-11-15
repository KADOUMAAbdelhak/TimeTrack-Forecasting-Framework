# v0.4 launcher runbook

The launcher, `fgcs_strengthening_v04/launch.py`, is an operator tool. It is **not** a sealed source: it drives the registered orchestrator under the v0.4 execution seal and changes no registered code. Every session records the launcher's SHA-256, preflight and recovery reports under `runtime/launcher/`.

It is ported from the r3 Stage 4A launcher with the protocol P9 changes:
- exactly **six** single-threaded fit workers;
- no systems phase;
- the host is checked against `registration/host_manifest.json` by `host.py`, instead of r3's systems module.

**Status: locked.** `launch.py` records the built package (tag `fgcs-v04-registration-package`, its commit, package digest and seal), but `OSF_REGISTRATION` is `None` until the v0.4 OSF registration exists, and `REGISTRATION_EVIDENCE_TEMPLATE.md` reads `EXECUTION_UNLOCKED = NO`. Every scientific or journal command refuses until both are filled in and the stored verification passes. The r3 package and its launcher stay locked permanently.

## Before the first run

1. **Registration.** After the v0.4 OSF registration is public, run the anonymous check:

   ```bash
   $PY -B -m fgcs_strengthening_v04.launch verify-registration
   ```

   It must print `REGISTRATION VERIFIED`. That requires:
   - the v0.4 OSF registration is public, not pending, withdrawn or embargoed, and has a DOI;
   - its title, description and responses hash to the approved field map;
   - every attachment's SHA-256 matches;
   - the Zenodo files (record `24189108`, reused from v0.3) match by name, size and MD5.

   Record the OSF ID as `OSF_REGISTRATION` in `launch.py` first. The report goes to `registration/OSF_VERIFICATION.json`; `start`, `run` and every worker refuse unless it records `passed: true` for that same ID, so the unlock flag alone never starts anything. Only then set `EXECUTION_UNLOCKED = YES` in `REGISTRATION_EVIDENCE_TEMPLATE.md`; this is a human decision.

2. **Disk.** P9 projects about 5–6 GB for the whole run.
   - Every phase start needs at least **15 GB** free, and the running monitor stops gracefully below that.
   - The inner and final phases also need at least **20 GB** free and a fresh (≤ 2 h) verified backup.
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
   $PY -B -m fgcs_strengthening_v04.launch preflight
   ```

   It reports the registered tag commit, package digest and seal; the host check (intra-op 1, inter-op 1, the three thread variables at 1, device `cpu`); AC power, free disk and thermal state.

## Start: certify, canary, stop

```bash
$PY -B -m fgcs_strengthening_v04.launch start
```

1. It repeats every gate: unlock flag, stored registration verification, threads, tag, package, seal, host, AC, disk and the recovery check.
2. It creates the runtime journal with the registered seal.
3. It runs the three modern structural certificates with one worker.
4. It runs the **90** canary inner fits (P9 step 2) with exactly **six** single-threaded worker processes.
5. It **stops** at the canary gate and never continues by itself.

After reviewing the canary's technical evidence (no outer-test quantity exists):

```bash
$PY -B -m fgcs_strengthening_v04.launch approve-canary --approver "NAME" --note "Technical checks reviewed; no outer-test quantity consulted."
```

Then, one phase at a time and in order: `inner`, `final`, `diagnostics`, then `evaluation`:

```bash
$PY -B -m fgcs_strengthening_v04.launch run --phase inner
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
| Planned pause | `$PY -B -m fgcs_strengthening_v04.launch stop --reason "planned pause"`, or one Ctrl-C in the launcher's terminal |
| Status | `$PY -B -m fgcs_strengthening_v04.launch status --phase canary` |
| Recovery check | `$PY -B -m fgcs_strengthening_v04.launch recover-check` (read-only) |
| Resume | `$PY -B -m fgcs_strengthening_v04.launch resume`, then rerun the same phase command |

- A stop lets each worker finish its current unit; no retry is used. Ctrl-C, closing the terminal and SIGTERM all become this graceful stop. Workers are never killed.
- After a crash, reboot or power loss, run `recover-check` first. `resume` refuses while workers are still running, and while a modern family is halted until the author passes `--acknowledge-modern-halt` after review.
- **Never** kill workers, run `kill -9`, or call `Journal.quarantine` or `Orchestrator.reopen` by hand. Code repairs go only through a chained seal amendment.

## Backups

`fgcs_strengthening_v04/backup_runtime.py` is ported unchanged from r3 (verified, hard-linked rsync snapshots on an external drive; the latest two kept). Run it hourly in a second `screen` window:

```bash
$PY -B -m fgcs_strengthening_v04.backup_runtime backup --dest /Volumes/<drive>/fgcs_v04_runtime_backups --every 3600
$PY -B -m fgcs_strengthening_v04.backup_runtime status --dest /Volumes/<drive>/fgcs_v04_runtime_backups
$PY -B -m fgcs_strengthening_v04.backup_runtime verify --dest /Volumes/<drive>/fgcs_v04_runtime_backups
```

Failures never touch the runtime; they are recorded in `fgcs_strengthening_v04/backup_status.json` (git-ignored). Restore only into a new, empty path, then move it into place and run `recover-check`.

## What the launcher checks

| Gate | Where |
|---|---|
| `EXECUTION_UNLOCKED = YES` (exactly one line; a missing file refuses) | every journal command |
| v0.4 OSF registration public, unchanged and with a DOI; Zenodo files unchanged | `verify-registration` (before you unlock) |
| `OSF_REGISTRATION` recorded and `OSF_VERIFICATION.json` passed for it | `start`, `run` and every worker |
| Thread variables exported as 1 before Python | controller and every worker |
| Tag resolves to the registered commit; registration files unchanged against the tag | preflight |
| The v0.4 registration builder verifies the package digest | preflight |
| Live execution seal equals the registered seal | preflight and every worker |
| Live host equals `host_manifest.json`; torch intra/inter-op 1; CPU | preflight (fresh process) and every worker |
| AC power; at least 15 GB free; recovery check OK | every phase start |
| Every earlier phase terminal (P9 run order) | every phase start and every worker |
| At least 20 GB free and a fresh verified backup | inner and final phase start |
| Free disk at least 15 GB; battery for no more than 2 minutes | every minute while running |
| Exactly six fit workers (slot locks); certify uses one | orchestrator and launcher |

## Tests

`tests/test_launcher.py` (27 tests) and `tests/test_backup_runtime.py` use generated data, scratch journals and recorded API responses only:
- **Gates:** unlock flag, missing evidence file, the stored registration verification, P9 phase order, threads, power and disk; refusal while locked or unregistered, with no runtime created; six workers and no systems phase; `runtime/` git-ignored.
- **Host:** the live host matches its own capture; a changed kernel, library version or thread count is reported.
- **Registration check:** a matching public registration passes; pending, no DOI, changed response or title, wrong attachment hash, withdrawn, embargoed or a changed Zenodo file all fail.
- **Six-process canary:** run through the controller, each unit fitted exactly once.
- **Stops, robustness and recovery:** as in r3.
