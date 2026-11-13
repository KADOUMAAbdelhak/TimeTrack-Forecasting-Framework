# Stage 4A launcher runbook

The launcher, `fgcs_strengthening_v03/launch_stage4a.py`, is an operator tool. It is **not** a sealed source: it drives the registered orchestrator under execution seal `c0161b55…cc93` and changes no registered code. Every session it starts records its own SHA-256 under `runtime/launcher/`.

## Before the first run

1. **Registration.** The OSF registration (`kuwra`) is public and verified, and `REGISTRATION_EVIDENCE_TEMPLATE.md` reads `EXECUTION_UNLOCKED = YES`. Until then, every command that creates or opens the journal refuses, and nothing scientific runs.
2. **Host conditions.** The machine is the frozen host, on mains power, with low-power mode off. Nothing heavy is running alongside, and the Mac is kept awake, for example with `caffeinate -dimsu` in a separate terminal.
3. **Shell environment.** Use a terminal where the thread variables are exported **before** Python starts:

   ```bash
   cd /Users/fgtek002/TimeTrack
   export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
   PY=old_fgcs_rejected/.venv_legacy/bin/python
   ```

4. **Preflight.** It is read-only and takes about 20 s:

   ```bash
   $PY -B -m fgcs_strengthening_v03.launch_stage4a preflight
   ```

   It must report:
   - tag commit `39f82840…`;
   - package `cb577d29…707e`;
   - seal `c0161b55…cc93`;
   - host intra-op 1, inter-op 1, the three thread variables at 1, device `cpu`.

   Any failure prints `REFUSED`, and nothing starts.

## Stage 4A: certify, canary, stop

```bash
$PY -B -m fgcs_strengthening_v03.launch_stage4a stage4a
```

- **Gates first.** It repeats every gate, then creates the runtime journal with the registered seal.
- **Certify.** It runs the three modern structural certificates with one worker.
- **Canary.** It runs the 96 canary inner fits with exactly **four** single-threaded worker processes.
- **Stop.** It then **stops** at the canary gate and prints the gate record. It never continues to the inner phase by itself.

After reviewing the canary's technical evidence (journal outcomes, failures and timings; no outer-test quantity exists), record the approval:

```bash
$PY -B -m fgcs_strengthening_v03.launch_stage4a approve-canary --approver "Abdelhak Kadouma" --note "Technical checks reviewed; no outer-test quantity consulted."
```

Later phases, one at a time, in order:

```bash
$PY -B -m fgcs_strengthening_v03.launch_stage4a run --phase inner
```

Then `final` and `diagnostics`. Fit closure, `systems` and `evaluation` follow the registered C6 order, and the orchestrator refuses anything out of order.

## Pausing, resuming, status

| Action | Command |
|---|---|
| Planned pause | `$PY -B -m fgcs_strengthening_v03.launch_stage4a stop --reason "planned pause"` (or a single Ctrl-C in the launcher's terminal) |
| Resume | `$PY -B -m fgcs_strengthening_v03.launch_stage4a resume`, then rerun the same phase command |
| Status | `$PY -B -m fgcs_strengthening_v03.launch_stage4a status --phase canary` |

- **What a pause does.** Each worker finishes its current unit and takes no new work, so no retry is used.
- **Ctrl-C.** The workers run in their own process session, so a terminal Ctrl-C reaches only the launcher, which turns it into this graceful stop. A second Ctrl-C does nothing more; the launcher waits for the workers.
- **Never** kill worker processes, run `kill -9` or close the terminal mid-fit. A killed fit uses one of its two retries, and a killed modern-family fit halts that family pending author review.
- **No manual repairs.** Never call `Journal.quarantine` or `Orchestrator.reopen` by hand. Retries and repairs go only through the orchestrator, and code repairs only through a chained seal amendment (C3).

## What the launcher checks

| Gate | Where |
|---|---|
| `EXECUTION_UNLOCKED = YES` (exactly one line) | every journal command |
| Thread variables exported as 1 before Python | controller and every worker |
| Tag resolves to the registered commit; registration files unchanged against the tag | preflight |
| `build_registration --verify` equals package `cb577d29…707e` | preflight |
| Live execution seal equals `c0161b55…cc93` | preflight and every worker |
| Live host equals `host_manifest.json`; torch intra/inter-op 1; CPU | preflight (fresh process) and every worker |
| Exactly four fit workers (slot locks); certify and systems use one | orchestrator and launcher |

## Tests

`fgcs_strengthening_v03/tests/test_launcher.py` runs on generated data in scratch journals:
- **Gates:** the unlock flag, the thread variables, refusal while locked (no runtime created), and the registered tag.
- **Four-process canary:** the real launcher controller drives four worker processes, and each unit is fitted exactly once with no retries.
- **Stop handling:** an active stop request runs nothing, and an interrupt becomes a graceful stop without killing workers.
- **Threads:** worker processes are single-threaded.
