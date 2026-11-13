# Stage 4A launcher runbook

The launcher, `fgcs_strengthening_v03/launch_stage4a.py`, is an operator tool. It is **not** a sealed source: it drives the registered orchestrator under execution seal `c0161b55…cc93` and changes no registered code. Every session records the launcher's SHA-256, preflight and recovery reports under `runtime/launcher/`.

## Before the first run

1. **Registration.** Run the anonymous check:

   ```bash
   $PY -B -m fgcs_strengthening_v03.launch_stage4a verify-registration
   ```

   It must print `REGISTRATION VERIFIED`. That requires:
   - OSF `kuwra` is public, not pending, withdrawn or embargoed, and has a DOI;
   - the title, description and 24 responses hash to the approved map (`f457dd92…`);
   - all 7 attachment SHA-256 values match;
   - the 13 Zenodo files match by name, size and MD5.

   Its report goes to `registration/OSF_VERIFICATION.json`. Only then set `EXECUTION_UNLOCKED = YES` in `REGISTRATION_EVIDENCE_TEMPLATE.md`; this is a human decision. Until then, every command that creates or opens the journal refuses.

2. **Disk.** The full run is projected at about 40–62 GB; the canary needs under 0.1 GB. The inner and final phases refuse to start below **90 GB** free or without a fresh verified backup. Every phase start requires at least **15 GB** free, and the running monitor stops gracefully below that.
   - Never delete or move a sealed input. Preflight re-hashes all of them.
   - Never move or symlink `runtime/`: the journal refuses a symlinked runtime.

3. **Power and sleep.**
   - Plug in AC power; every phase start refuses on battery.
   - Keep the **lid open**, or use clamshell mode with AC and an external display. Closing the lid sleeps the Mac whatever the software does.
   - While running, the launcher holds a `caffeinate -i -m -s` assertion against idle sleep. It changes no system setting.
   - On battery for more than 2 minutes, the monitor stops gracefully: this Mac's battery profile sleeps after 1 minute idle.

4. **Host.** Keep the frozen host as it is: no Low Power Mode, no OS or library updates.
   - Consider turning off automatic macOS update installs for the run. That is a system setting, so it needs your decision.
   - Close heavy applications. Before the systems phase, also close the Claude app and browsers: that phase refuses unless the thermal state is nominal (0), the 1-minute load is at most 1.5 and the Mac is on AC.

5. **Survive a closed terminal.** Run the launcher inside `screen`, which is preinstalled:

   ```bash
   screen -S fgcs
   cd /Users/fgtek002/TimeTrack
   export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
   PY=old_fgcs_rejected/.venv_legacy/bin/python
   ```

   Detach with `Ctrl-A d` and reattach with `screen -r fgcs`. Without `screen`, closing the terminal sends a hang-up, which the launcher also turns into a graceful stop.

6. **Preflight.** It is read-only and takes about 20 s:

   ```bash
   $PY -B -m fgcs_strengthening_v03.launch_stage4a preflight
   ```

   It must report:
   - tag commit `39f82840…`;
   - package `cb577d29…707e`;
   - seal `c0161b55…cc93`;
   - host intra-op 1, inter-op 1, the three thread variables at 1, device `cpu`;
   - AC power, free GB and thermal state.

## Stage 4A: certify, canary, stop

```bash
$PY -B -m fgcs_strengthening_v03.launch_stage4a stage4a
```

1. It repeats every gate: unlock flag, threads, tag, package, seal, host, AC, disk and the recovery check.
2. It creates the runtime journal with the registered seal.
3. It runs the three modern structural certificates with one worker.
4. It runs the 96 canary inner fits with exactly **four** single-threaded worker processes.
5. It **stops** at the canary gate and never continues by itself.

After reviewing the canary's technical evidence (outcomes, failures, timings and the health log; no outer-test quantity exists):

```bash
$PY -B -m fgcs_strengthening_v03.launch_stage4a approve-canary --approver "Abdelhak Kadouma" --note "Technical checks reviewed; no outer-test quantity consulted."
```

Later phases, one at a time, in order:

```bash
$PY -B -m fgcs_strengthening_v03.launch_stage4a run --phase inner
```

Then `final` and `diagnostics`. Fit closure, `systems` and `evaluation` follow the registered C6 order, and the orchestrator refuses anything out of order.

## While it runs

- **Logs.** Each worker writes to `runtime/launcher/logs/<time>-<phase>-r<round>-w<i>.{out,err}`, never to a pipe, so a chatty worker cannot block. The live worker PIDs are in `runtime/launcher/workers/`.
- **Health.** Every 10 minutes, `runtime/launcher/health/<date>.jsonl` gains one line with:
  - free disk and disk use per hour;
  - hours until the disk guard trips;
  - the outcome count;
  - load average, thermal state, AC power, live workers and the stop flag.

  Files rotate daily.
- **Guards.** Every minute the controller checks free disk (minimum 15 GB) and power (2-minute battery grace). Either one triggers a graceful stop, recorded as the guard's stop reason.
- **Thermal.** The fanless M3 may throttle under sustained load. That slows the run but doesn't change results; training-cost seconds are reported under the registered four-worker load (C4). Watch `thermal_state` in the health log.

## Pausing, resuming, recovery

| Action | Command |
|---|---|
| Planned pause | `$PY -B -m fgcs_strengthening_v03.launch_stage4a stop --reason "planned pause"`, or a single Ctrl-C in the launcher's terminal |
| Status | `$PY -B -m fgcs_strengthening_v03.launch_stage4a status --phase canary` (unit states, gates, stop flag, slots held, worker PIDs, free disk) |
| Recovery check | `$PY -B -m fgcs_strengthening_v03.launch_stage4a recover-check` (read-only) |
| Resume | `$PY -B -m fgcs_strengthening_v03.launch_stage4a resume`, then rerun the same phase command |

- **What a stop does.** Each worker finishes its current unit and takes no new work, so no retry is used. Ctrl-C, closing the terminal and SIGTERM all become this graceful stop, and a second signal does nothing more. Workers are never killed.
- **After a crash, reboot or power loss,** run `recover-check` first. It reports:
  - interrupted attempts (each will use one of its two retries);
  - quarantined identities and leftover temporary files;
  - halted modern families (`stop.json`, `active.json` or a failed structure certificate);
  - slot locks still held, and live or stale worker records.

  Slot and lease locks are released by the kernel when a process dies, so they can't go stale. `resume` refuses while workers are still running. It also refuses while a modern family is halted, until the author has reviewed it and passes `--acknowledge-modern-halt`. Phase runs refuse while a recovery check reports `REVIEW_REQUIRED`.
- **Never** kill worker processes, run `kill -9`, or call `Journal.quarantine` or `Orchestrator.reopen` by hand. Code repairs go only through a chained seal amendment (C3).

## Backups

The backup tool is `fgcs_strengthening_v03/backup_runtime.py`, an unsealed operator tool. Its destination is always explicit: create a folder on the external drive once, for example `/Volumes/<drive>/fgcs_runtime_backups`. Run it hourly in a second `screen` window:

```bash
$PY -B -m fgcs_strengthening_v03.backup_runtime backup --dest /Volumes/<drive>/fgcs_runtime_backups --every 3600
$PY -B -m fgcs_strengthening_v03.backup_runtime status --dest /Volumes/<drive>/fgcs_runtime_backups
$PY -B -m fgcs_strengthening_v03.backup_runtime verify --dest /Volumes/<drive>/fgcs_runtime_backups   # weekly: full re-hash
```

**How a backup works:**
1. **Copy.** rsync (macOS `openrsync`) copies `runtime/` into `snapshots/<UTC>.partial/` at background CPU and I/O priority (`nice` plus `taskpolicy -b`), reading the source only. Unchanged files are hard-linked from the latest verified snapshot; `tmp*` and `launcher/workers/` are excluded.
2. **Manifest and check.** Every file gets a SHA-256 in `MANIFEST.json`. New files are checked against the runtime, and a mismatch fails the backup.
3. **Publish atomically.** The manifest is written via a temporary file, fsync and rename; then the snapshot is renamed from `.partial`; then `latest.json` is replaced.
4. **Retention.** Only verified snapshots count, and the latest two are kept.

**Refusals and detection:**

| Problem | What happens |
|---|---|
| Destination missing | Refused (`DRIVE_MISSING`) |
| Destination on the internal disk | Refused |
| Destination inside the runtime | Refused |
| Not enough space | Refused |
| A second backup running at the same time | Refused |
| Partial backup | Stays `.partial`, is never published, and is cleaned on the next run; `status` reports `PARTIAL` |
| Corruption | `verify` reports corrupted, missing or unexpected files |
| Stale backup | `status` and the launcher's health log report `STALE` after 2 hours |

A failure never touches the runtime or the workers. It's recorded in `fgcs_strengthening_v03/backup_status.json` (git-ignored, outside the runtime), and the hourly loop simply tries again.

**Restore only into a new, empty path, never into the live journal.** After a disaster:
1. Stop.
2. Move the damaged `runtime/` aside.
3. Restore:

   ```bash
   $PY -B -m fgcs_strengthening_v03.backup_runtime restore --dest /Volumes/<drive>/fgcs_runtime_backups --into /path/new_runtime
   ```

   The command verifies the snapshot and the restored files.
4. Move `new_runtime` into place as `fgcs_strengthening_v03/runtime`.
5. Run `recover-check` before resuming.

## What the launcher checks

| Gate | Where |
|---|---|
| `EXECUTION_UNLOCKED = YES` (exactly one line) | every journal command |
| OSF public, unchanged and with a DOI; Zenodo files unchanged | `verify-registration` (before you unlock) |
| Thread variables exported as 1 before Python | controller and every worker |
| Tag resolves to the registered commit; registration files unchanged against the tag | preflight |
| `build_registration --verify` equals package `cb577d29…707e` | preflight |
| Live execution seal equals `c0161b55…cc93` | preflight and every worker |
| Live host equals `host_manifest.json`; torch intra/inter-op 1; CPU | preflight (fresh process) and every worker |
| AC power; at least 15 GB free; recovery check OK | every phase start |
| At least 90 GB free and a fresh (≤2 h) verified backup | inner and final phase start |
| Free disk at least 15 GB; battery for no more than 2 minutes | every minute while running |
| Thermal state nominal; 1-minute load at most 1.5; AC | systems phase start |
| Exactly four fit workers (slot locks); certify and systems use one | orchestrator and launcher |

## Tests

`fgcs_strengthening_v03/tests/test_launcher.py` has 21 tests on generated data, scratch journals and recorded API responses:
- **Gates:** unlock flag, threads, power, disk and systems conditions, refusal while locked (no runtime created), registered tag, `runtime/` git-ignored.
- **Monitor:** disk and battery guards, health snapshots and growth, the caffeinate assertion.
- **Registration check:** a matching public registration passes; pending, no DOI, changed response or title, wrong attachment hash, withdrawn or a changed Zenodo file all fail.
- **Four-process canary:** run through the controller, each unit fitted exactly once.
- **Stops:** an active stop request runs nothing; the disk guard stops workers gracefully; SIGINT, SIGHUP and SIGTERM all become graceful stops.
- **Robustness:** chatty workers (2 MB of stderr each) cannot block the controller.
- **Recovery:** the report catches interrupted attempts, stale PIDs, held slots and modern halt markers.
- **Threads:** worker processes are single-threaded.
