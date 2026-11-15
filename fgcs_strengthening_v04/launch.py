"""Launcher for the registered FGCS v0.4 execution (operator tool, not a sealed source).

    python -m fgcs_strengthening_v04.launch preflight
    python -m fgcs_strengthening_v04.launch verify-registration     # OSF + Zenodo, anonymous, read-only
    python -m fgcs_strengthening_v04.launch start                   # certify, 90-fit canary, then STOP
    python -m fgcs_strengthening_v04.launch status [--phase canary]
    python -m fgcs_strengthening_v04.launch stop --reason "..."      # graceful pause between units
    python -m fgcs_strengthening_v04.launch recover-check
    python -m fgcs_strengthening_v04.launch resume [--acknowledge-modern-halt]
    python -m fgcs_strengthening_v04.launch approve-canary --approver NAME --note "..."
    python -m fgcs_strengthening_v04.launch run --phase inner        # later phases, after approval

Ported from the r3 Stage 4A launcher (fgcs_strengthening_v03/launch_stage4a.py) with the v0.4 changes
of protocol P9: exactly six single-threaded fit workers, no systems phase, and a host check against the
v0.4 host manifest (host.py) instead of r3's systems module.

Nothing scientific runs, and no runtime journal is created, unless the v0.4 registration is recorded
below and REGISTRATION_EVIDENCE_TEMPLATE.md records EXECUTION_UNLOCKED = YES, and every preflight check
passes:
- the v0.4 registration tag resolves to the registered commit;
- the registration package verifies and has the registered digest;
- the live execution seal equals the registered seal;
- a fresh single-threaded worker process matches the frozen host manifest.
Until the v0.4 registration exists, REGISTERED_COMMIT, REGISTERED_PACKAGE, REGISTERED_SEAL and
OSF_REGISTRATION are None, and every gate that needs them refuses.

Each phase run also requires AC power and at least MIN_FREE_GB of free disk. Workers are separate
processes in their own session and write to log files, never to pipes. A terminal Ctrl-C or a hang-up
reaches only this controller, which turns it into Orchestrator.request_stop: each worker finishes its
current unit and takes no new work, so no retry is used. While running, the controller holds a
caffeinate assertion against idle sleep. Every minute it checks free disk and power: low disk, or
battery power for longer than the grace period, also triggers a graceful stop. Every ten minutes it
appends a health snapshot. Workers are never killed.
"""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
from hashlib import md5, sha256
import html
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .src.identity import HOME, ROOT, read_config

# Filled in by the v0.4 registration step; None keeps every scientific command locked.
TAG = "fgcs-v04-registration-package"
REGISTERED_COMMIT = None
REGISTERED_PACKAGE = None
REGISTERED_SEAL = None
OSF_REGISTRATION = None  # the new v0.4 Secondary Data Preregistration (P9); links to OSF kuwra
ZENODO_RECORD = "24189108"  # the reused v0.3 input archive (P7)

THREAD_ENV = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
MODULE = "fgcs_strengthening_v04.launch"
REGISTRATION = HOME / "registration"
EVIDENCE = REGISTRATION / "REGISTRATION_EVIDENCE_TEMPLATE.md"
HOST_MANIFEST = REGISTRATION / "host_manifest.json"
PACKAGE = REGISTRATION / "PACKAGE.json"
OSF_FIELDS = REGISTRATION / "OSF_SECONDARY_DATA_FIELDS.json"
UPLOAD_LIST = REGISTRATION / "EXTERNAL_ARCHIVE_UPLOAD_LIST.json"
OSF_VERIFICATION = REGISTRATION / "OSF_VERIFICATION.json"
REGISTRATION_FILES = ("PACKAGE.json", "execution_seal.json", "schedule.json", "host_manifest.json")
FIT_WORKERS = 6  # P9; the orchestrator enforces the same count with slot locks
SINGLE_WORKER_PHASES = ("certify",)
PHASES = ("certify", "canary", "inner", "final", "diagnostics", "evaluation")
EXIT_COMPLETE, EXIT_STOPPED, EXIT_INCOMPLETE = 0, 3, 4
MAX_ROUNDS = 10
MIN_FREE_GB = 15
FULL_RUN_MIN_FREE_GB = 20  # inner and final phases (P9 projects about 5-6 GB for the whole run)
FULL_RUN_PHASES = ("inner", "final")
BATTERY_GRACE_SECONDS = 120
MONITOR_SECONDS = 60
HEALTH_SECONDS = 600
ATTACHMENT_QUESTIONS = ("72-22", "72-26")

if read_config()["execution"]["fit_workers"] != FIT_WORKERS:
    raise RuntimeError("The launcher's worker count differs from the v0.4 configuration")


class LaunchRefused(RuntimeError):
    """A gate failed; nothing was started."""


def _utc():
    return datetime.now(timezone.utc)


def runtime_dir():
    return HOME / "runtime"


def _registered(name, value):
    if value is None:
        raise LaunchRefused(f"{name} is not recorded yet: the v0.4 registration does not exist")
    return value


# -- host probes (read-only) ----------------------------------------------------------------------
def free_bytes(path=None):
    return shutil.disk_usage(path or HOME).free


def on_ac_power():
    """True on AC, False on battery, None if unknown."""
    try:
        first = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    if "'AC Power'" in first:
        return True
    if "'Battery Power'" in first:
        return False
    return None


def thermal_state():
    """macOS NSProcessInfo thermal state: 0 nominal, 1 fair, 2 serious, 3 critical; None if unknown."""
    try:
        out = subprocess.run(["osascript", "-l", "JavaScript", "-e",
                              'ObjC.import("Foundation"); $.NSProcessInfo.processInfo.thermalState'],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return int(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def load_average():
    return list(os.getloadavg())


# -- gates ----------------------------------------------------------------------------------------
def execution_unlocked(path=EVIDENCE):
    """True only when the evidence file holds exactly one line `EXECUTION_UNLOCKED = YES`."""
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        raise LaunchRefused(f"No registration evidence file at {path}: the v0.4 registration does not exist") from None
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("EXECUTION_UNLOCKED")]
    if len(lines) != 1 or not re.fullmatch(r"EXECUTION_UNLOCKED = (YES|NO)", lines[0]):
        raise LaunchRefused(f"Expected exactly one EXECUTION_UNLOCKED = YES|NO line in {path}")
    return lines[0].endswith("YES")


def require_thread_env(env=None):
    env = os.environ if env is None else env
    wrong = {key: env.get(key) for key, value in THREAD_ENV.items() if env.get(key) != value}
    if wrong:
        raise LaunchRefused(f"Thread variables must be exported as 1 before Python starts: {wrong}")


def require_ac_power(probe=on_ac_power):
    if probe() is not True:
        raise LaunchRefused("AC power is required to start a phase (battery or unknown power source)")


def require_free_disk(minimum_gb=MIN_FREE_GB, probe=free_bytes):
    free = probe()
    if free < minimum_gb * 1e9:
        raise LaunchRefused(f"Only {free / 1e9:.1f} GB free; at least {minimum_gb} GB is required")
    return free


def require_backup_fresh(freshness=None):
    """A verified backup no older than the stale limit (backup_runtime.py writes the status file)."""
    from .backup_runtime import backup_freshness

    state = (freshness or backup_freshness)()
    if state.get("verdict") != "OK":
        raise LaunchRefused(f"A fresh verified runtime backup is required before this phase: {state}")
    return state


def require_full_run_capacity(phase, *, free=free_bytes, freshness=None):
    """Inner and final phases need >= FULL_RUN_MIN_FREE_GB free and a fresh verified backup."""
    if phase not in FULL_RUN_PHASES:
        return None
    require_free_disk(FULL_RUN_MIN_FREE_GB, free)
    return require_backup_fresh(freshness)


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def check_repository():
    """The registered tag and commit exist; the registration files are unchanged against the tag."""
    commit = _registered("REGISTERED_COMMIT", REGISTERED_COMMIT)
    tagged = _git("rev-parse", f"{TAG}^{{commit}}").stdout.strip()
    if tagged != commit:
        raise LaunchRefused(f"{TAG} resolves to {tagged or 'nothing'}, not {commit}")
    files = [f"fgcs_strengthening_v04/registration/{name}" for name in REGISTRATION_FILES]
    if _git("diff", "--quiet", TAG, "--", *files).returncode != 0:
        raise LaunchRefused("Registration package files differ from the registered tag")
    return {"tag_commit": tagged, "head": _git("rev-parse", "HEAD").stdout.strip()}


def check_package():
    package = _registered("REGISTERED_PACKAGE", REGISTERED_PACKAGE)
    try:
        from .build_registration import verify
    except ImportError:
        raise LaunchRefused("The v0.4 registration builder does not exist yet") from None
    digest, problems = verify()
    if problems or digest != package:
        raise LaunchRefused(f"Registration package does not verify: {digest} {problems}")
    return digest


def check_seal():
    from .src.orchestrator import execution_fingerprints

    registered = _registered("REGISTERED_SEAL", REGISTERED_SEAL)
    digest = execution_fingerprints().digest
    recorded = json.loads((REGISTRATION / "execution_seal.json").read_text())["digest"]
    if digest != registered or recorded != registered:
        raise LaunchRefused(f"Live execution seal {digest} differs from the registered {registered}")
    return digest


def host_probe():
    """Run in a fresh worker-configured process: single-threaded CPU and the frozen host."""
    from .host import require_host
    from .src.orchestrator import configure_worker_process, require_fit_threads

    configure_worker_process()
    threads = require_fit_threads()
    require_host(HOST_MANIFEST)
    return threads


def check_host():
    result = subprocess.run([sys.executable, "-B", "-m", MODULE, "host-probe"],
                            cwd=ROOT, env=worker_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise LaunchRefused("Live host differs from the frozen host manifest or is not single-threaded: "
                            + (result.stderr.strip().splitlines() or ["no output"])[-1])
    return json.loads(result.stdout.strip().splitlines()[-1])


def preflight():
    """Every gate except the unlock flag. Raises LaunchRefused at the first failure."""
    report = {"repository": check_repository(), "package_sha256": check_package(), "seal": check_seal(),
              "host": check_host(), "on_ac_power": on_ac_power(), "free_gb": round(free_bytes() / 1e9, 1),
              "thermal_state": thermal_state()}
    report["execution_unlocked"] = execution_unlocked()
    return report


def require_execution_allowed():
    if not execution_unlocked():
        raise LaunchRefused("EXECUTION_UNLOCKED = NO: scientific execution stays locked until the registration "
                            "evidence is verified (REGISTRATION_EVIDENCE_TEMPLATE.md)")
    require_thread_env()
    return preflight()


def worker_env():
    return {**os.environ, **THREAD_ENV, "PYTHONDONTWRITEBYTECODE": "1"}


# -- workers --------------------------------------------------------------------------------------
def phase_complete(orchestrator, phase):
    return all(orchestrator.terminal(unit) for unit in orchestrator.schedule.phase(phase))


def run_worker(orchestrator, phase):
    """One worker process: repeat orchestrator passes until the phase is terminal, stopped or idle.

    The orchestrator checks the stop request before every unit, so the controller's monitor can stop
    workers between units without any change to the sealed orchestrator.
    """
    executed = {}
    while True:
        session = orchestrator.run(phase)
        for key, value in session.executed.items():
            executed[key] = executed.get(key, 0) + value
        if session.stopped:
            return EXIT_STOPPED, {"phase": phase, "slot": session.slot, "executed": executed, "state": "stopped"}
        if phase_complete(orchestrator, phase):
            return EXIT_COMPLETE, {"phase": phase, "slot": session.slot, "executed": executed, "state": "complete"}
        if not session.executed:
            return EXIT_INCOMPLETE, {"phase": phase, "slot": session.slot, "executed": executed, "state": "idle"}


def production_orchestrator(*, worker=False):
    """The registered journal, schedule and executors. Creates the runtime journal: gates must pass first."""
    from .host import require_host
    from .src.orchestrator import (TRAINING_WORKERS, Orchestrator, ProductionExecutors, Schedule,
                                   configure_worker_process, execution_fingerprints, registered_schedule,
                                   require_fit_threads)
    from .src.provenance import Journal

    if worker:
        configure_worker_process()
        require_thread_env()
        require_fit_threads()
        require_host(HOST_MANIFEST)
    seal = execution_fingerprints()
    if seal.digest != _registered("REGISTERED_SEAL", REGISTERED_SEAL):
        raise LaunchRefused("Live execution seal differs from the registered seal")
    if TRAINING_WORKERS != FIT_WORKERS:
        raise LaunchRefused("Registered training worker count changed")
    journal = Journal(seal)
    return Orchestrator(journal, Schedule(registered_schedule()), ProductionExecutors(journal),
                        registration=PACKAGE, workers=TRAINING_WORKERS)


def worker_main(phase):
    if not execution_unlocked():
        raise LaunchRefused("EXECUTION_UNLOCKED = NO")
    code, summary = run_worker(production_orchestrator(worker=True), phase)
    print(json.dumps(summary), flush=True)
    return code


# -- controller -----------------------------------------------------------------------------------
def worker_count(phase):
    return 1 if phase in SINGLE_WORKER_PHASES else FIT_WORKERS


def safe_request_stop(orchestrator, reason):
    """Request a stop once; a request that already exists (from another source) is left as it is."""
    from .src.provenance import DuplicateIdentity

    if orchestrator.stop_requested():
        return False
    try:
        orchestrator.request_stop(reason=reason)
    except DuplicateIdentity:
        return False
    return True


@contextmanager
def keep_awake(command=("caffeinate", "-i", "-m", "-s")):
    """Hold a no-idle-sleep assertion while the controller lives (no system setting is changed)."""
    process = None
    try:
        process = subprocess.Popen([*command, "-w", str(os.getpid())], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
    except OSError:
        process = None
    try:
        yield process
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


@dataclass
class Monitor:
    """Controller-side guards and health snapshots. Probes are injectable for tests."""

    request_stop: object
    health_dir: Path | None = None
    phase: str = ""
    count_outcomes: object = None
    min_free_bytes: float = MIN_FREE_GB * 1e9
    battery_grace: float = BATTERY_GRACE_SECONDS
    free: object = free_bytes
    power: object = on_ac_power
    thermal: object = thermal_state
    load: object = load_average
    clock: object = time.monotonic
    backup: object = None
    battery_since: float | None = None
    stopped_reason: str | None = None
    last_free: tuple | None = None
    snapshots: list = field(default_factory=list)

    def check(self, live_workers=0):
        """Return a stop reason, after requesting the stop, or None."""
        if self.stopped_reason:
            return None
        free = self.free()
        reason = None
        if free < self.min_free_bytes:
            reason = f"free disk {free / 1e9:.1f} GB below {self.min_free_bytes / 1e9:.0f} GB"
        power = self.power()
        if power is False:
            self.battery_since = self.battery_since if self.battery_since is not None else self.clock()
            if self.clock() - self.battery_since >= self.battery_grace:
                reason = reason or f"on battery power for {self.battery_grace:.0f} s"
        else:
            self.battery_since = None
        if reason:
            self.stopped_reason = reason
            self.request_stop(f"launcher guard: {reason}")
        return reason

    def _backup(self):
        try:
            if self.backup is not None:
                return self.backup()
            from .backup_runtime import backup_freshness
            return backup_freshness()
        except Exception as error:  # reporting only; never affects the run
            return {"verdict": "UNKNOWN", "error": f"{type(error).__name__}: {error}"}

    def snapshot(self, live_workers=0, stop_requested=None):
        now, free = self.clock(), self.free()
        rate = None
        if self.last_free is not None and now > self.last_free[0]:
            rate = (self.last_free[1] - free) / ((now - self.last_free[0]) / 3600)  # bytes consumed per hour
        self.last_free = (now, free)
        hours_left = (free - self.min_free_bytes) / rate if rate and rate > 0 else None
        record = {"utc": _utc().isoformat(), "phase": self.phase, "free_bytes": free,
                  "disk_use_bytes_per_hour": rate, "hours_until_disk_guard": hours_left,
                  "outcomes": self.count_outcomes() if self.count_outcomes else None,
                  "load_average": self.load(), "thermal_state": self.thermal(), "on_ac_power": self.power(),
                  "live_workers": live_workers, "stop_requested": stop_requested,
                  "backup": self._backup(), "guard_stop_reason": self.stopped_reason}
        self.snapshots.append(record)
        if self.health_dir is not None:
            self.health_dir.mkdir(parents=True, exist_ok=True)
            with (self.health_dir / f"{_utc():%Y-%m-%d}.jsonl").open("a") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        return record


def _last_json_line(path):
    try:
        lines = Path(path).read_text().strip().splitlines()
    except FileNotFoundError:
        return {}
    for line in reversed(lines):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return {}
    return {}


def launch(phase, *, worker_command, request_stop, log_dir, env=None, workers=None, max_rounds=MAX_ROUNDS,
           log=print, monitor=None, pid_dir=None, poll_seconds=1.0, monitor_seconds=MONITOR_SECONDS,
           health_seconds=HEALTH_SECONDS):
    """Start the phase's workers and supervise them until they exit. Workers are never killed.

    Worker stdout/stderr go to files in log_dir (never pipes, so a chatty worker cannot block). The first
    SIGINT/SIGTERM/SIGHUP becomes a graceful stop; the monitor may also request one (low disk, battery).
    Rounds repeat while workers make progress and the phase is unfinished.
    """
    env = worker_env() if env is None else env
    workers = worker_count(phase) if workers is None else workers
    log_dir = Path(log_dir)  # explicit: never defaults into the real runtime
    log_dir.mkdir(parents=True, exist_ok=True)
    stopping = {"requested": False}

    def stop(reason):
        if not stopping["requested"]:
            stopping["requested"] = True
            log(f"Requesting a graceful stop ({reason}); workers finish their current unit")
            request_stop(reason)

    def on_signal(signum, frame):
        stop(f"operator signal {signal.Signals(signum).name} received by the v0.4 launcher")

    if monitor is not None:
        monitor.request_stop = stop  # guard stops go through the same single, logged stop request
    previous = {sig: signal.signal(sig, on_signal) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    summaries = []
    stamp = _utc().strftime("%Y%m%dT%H%M%SZ")
    try:
        for round_index in range(1, max_rounds + 1):
            processes = []
            for index in range(workers):
                base = log_dir / f"{stamp}-{phase}-r{round_index}-w{index}"
                out, err = open(f"{base}.out", "w"), open(f"{base}.err", "w")
                process = subprocess.Popen([*worker_command, phase], cwd=ROOT, env=env, start_new_session=True,
                                           stdout=out, stderr=err)
                out.close()
                err.close()
                if pid_dir is not None:
                    Path(pid_dir).mkdir(parents=True, exist_ok=True)
                    (Path(pid_dir) / f"{process.pid}.json").write_text(json.dumps(
                        {"pid": process.pid, "phase": phase, "round": round_index, "started": _utc().isoformat(),
                         "log": str(base)}))
                processes.append((process, base))
            last_monitor = last_health = time.monotonic()
            if monitor is not None:
                monitor.check(len(processes))
                monitor.snapshot(len(processes), stopping["requested"])
            while any(process.poll() is None for process, _ in processes):
                time.sleep(poll_seconds)
                now = time.monotonic()
                live = sum(process.poll() is None for process, _ in processes)
                if monitor is not None and now - last_monitor >= monitor_seconds:
                    last_monitor = now
                    monitor.check(live)
                if monitor is not None and now - last_health >= health_seconds:
                    last_health = now
                    monitor.snapshot(live, stopping["requested"])
            results = []
            for process, base in processes:
                if pid_dir is not None:
                    (Path(pid_dir) / f"{process.pid}.json").unlink(missing_ok=True)
                results.append({"returncode": process.returncode, **_last_json_line(f"{base}.out"),
                                "log": str(base)})
            summaries.append({"round": round_index, "workers": results})
            codes = {result["returncode"] for result in results}
            if codes - {EXIT_COMPLETE, EXIT_STOPPED, EXIT_INCOMPLETE}:
                return "error", summaries
            if EXIT_STOPPED in codes or stopping["requested"]:
                return "stopped", summaries
            if EXIT_COMPLETE in codes:
                return "complete", summaries
            if not any(result.get("executed") for result in results):
                return "incomplete", summaries
        return "incomplete", summaries
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if monitor is not None:
            monitor.snapshot(0, stopping["requested"])


def _record(name, payload):
    """Launcher provenance next to the journal (only after the journal exists)."""
    path = runtime_dir() / "launcher" / f"{_utc():%Y%m%dT%H%M%S%fZ}-{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"launcher_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "argv": sys.argv,
               "utc": _utc().isoformat(), **payload}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def count_outcomes(runtime=None):
    runtime = runtime or runtime_dir()
    total = 0
    for directory in (runtime / "outcomes", runtime / "evaluations" / "outcomes"):
        if directory.is_dir():
            with os.scandir(directory) as entries:
                total += sum(1 for entry in entries if entry.name.endswith(".json"))
    return total


# -- status and recovery --------------------------------------------------------------------------
def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def worker_processes(runtime=None):
    """Recorded worker PIDs and whether each is still alive (dead entries are stale)."""
    directory = (runtime or runtime_dir()) / "launcher" / "workers"
    rows = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        record = json.loads(path.read_text())
        rows.append({**record, "alive": _pid_alive(record["pid"])})
    return rows


def slots_held(runtime=None, workers=FIT_WORKERS):
    """Slot locks currently held by some process (probed without creating any lock file)."""
    held = []
    directory = (runtime or runtime_dir()) / "orchestrator" / "slots"
    for index in range(workers):
        path = directory / f"{index}.lock"
        if not path.exists():
            continue
        with path.open("rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                held.append(index)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
    return held


def recovery_report(runtime=None):
    """Read-only state after a crash, reboot or power loss. Never deletes or moves anything."""
    runtime = runtime or runtime_dir()
    interrupted = []
    for prefix in ((), ("evaluations",)):
        attempts = runtime.joinpath(*prefix, "attempts")
        outcomes = runtime.joinpath(*prefix, "outcomes")
        if attempts.is_dir():
            interrupted += [("evaluation" if prefix else "fit", path.stem) for path in attempts.glob("*.json")
                            if not (outcomes / path.name).exists()]
    modern = {}
    for family in sorted((runtime / "modern").glob("*")) if (runtime / "modern").is_dir() else []:
        markers = [name for name in ("stop.json", "active.json") if (family / name).exists()]
        structure = family / "structure.json"
        if structure.exists() and json.loads(structure.read_text()).get("status") != "complete":
            markers.append("structure.json:failed")
        if markers:
            modern[family.name] = markers
    quarantine = runtime / "quarantine"
    leftovers = [str(path.relative_to(runtime)) for path in runtime.rglob("tmp*") if path.is_file()]
    workers = worker_processes(runtime)
    report = {
        "interrupted_attempts": len(interrupted), "interrupted": interrupted[:50],
        "quarantined_identities": sum(1 for _ in quarantine.iterdir()) if quarantine.is_dir() else 0,
        "modern_family_markers": modern, "leftover_temporary_files": leftovers[:50],
        "leftover_temporary_count": len(leftovers), "slots_held": slots_held(runtime),
        "live_workers": [row["pid"] for row in workers if row["alive"]],
        "stale_worker_records": [row["pid"] for row in workers if not row["alive"]],
        "stop_requested": (runtime / "orchestrator" / "stop" / "request.json").exists(),
        "free_gb": round(free_bytes(runtime if runtime.exists() else HOME) / 1e9, 1)}
    blocking = []
    if modern:
        blocking.append("a modern family is halted or has an unresolved attempt: author review required")
    if report["slots_held"] or report["live_workers"]:
        blocking.append("workers are still running")
    report["verdict"] = "REVIEW_REQUIRED" if blocking else "OK"
    report["blocking"] = blocking
    return report


# -- registration verification (anonymous, read-only) --------------------------------------------
def _fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "registration-verifier/1.0",
                                                   "Accept": "application/vnd.api+json, application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _sha256(path):
    digest = sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _md5(path):
    digest = md5()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_responses(title, description, responses):
    payload = json.dumps({"title": title, "description": description,
                          "responses": {key: responses[key] for key in sorted(responses)}},
                         ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()


def verify_registration(fetch=_fetch_json, fields_path=OSF_FIELDS, upload_list_path=UPLOAD_LIST, root=ROOT,
                        registration=None):
    """Check the public v0.4 OSF registration and the Zenodo archive against the local frozen records.

    Uses only anonymous public API reads. Returns (passed, report); never edits the unlock flag.
    """
    registration = registration or _registered("OSF_REGISTRATION", OSF_REGISTRATION)
    fields = json.loads(Path(fields_path).read_text())
    expected = fields["registration_responses"]
    meta = fields["metadata"]
    problems, report = [], {"utc": _utc().isoformat(), "osf_registration": registration,
                            "zenodo_record": ZENODO_RECORD}

    try:
        osf = fetch(f"https://api.osf.io/v2/registrations/{registration}/?embed=identifiers")["data"]
    except urllib.error.HTTPError as error:
        problems.append(f"OSF registration is not publicly readable (HTTP {error.code}); it is not public yet")
        report.update(problems=problems, passed=False, osf_http_status=error.code)
        return False, report
    attributes = osf["attributes"]
    identifiers = osf.get("embeds", {}).get("identifiers", {}).get("data", []) or []
    doi = next((item["attributes"]["value"] for item in identifiers if item["attributes"]["category"] == "doi"), None)
    report.update(public=attributes.get("public"), pending=attributes.get("pending_registration_approval"),
                  withdrawn=attributes.get("withdrawn"), embargo=attributes.get("embargo_end_date"), osf_doi=doi,
                  date_registered=attributes.get("date_registered"))
    if attributes.get("public") is not True:
        problems.append("OSF registration is not public")
    if attributes.get("pending_registration_approval"):
        problems.append("OSF registration is still pending approval")
    if attributes.get("withdrawn"):
        problems.append("OSF registration is withdrawn")
    if attributes.get("embargo_end_date"):
        problems.append("OSF registration is embargoed")
    if not doi:
        problems.append("OSF registration has no DOI yet")
    stored = attributes.get("registration_responses") or {}
    unescaped = {key: html.unescape(stored[key]) for key in expected if isinstance(stored.get(key), str)}
    missing = sorted(set(expected) - set(unescaped))
    if missing:
        problems.append(f"OSF responses missing: {missing}")
    observed_hash = _canonical_responses(html.unescape(attributes.get("title", "")),
                                         html.unescape(attributes.get("description", "")), unescaped)
    expected_hash = _canonical_responses(meta["title"], meta["description"], expected)
    report.update(responses_sha256=observed_hash, expected_responses_sha256=expected_hash)
    if observed_hash != expected_hash:
        problems.append("OSF title, description or responses differ from the approved field map")
    attachments = {}
    for question in ATTACHMENT_QUESTIONS:
        for item in stored.get(question) or []:
            attachments[item["file_name"]] = item.get("file_hashes", {}).get("sha256")
    local = {Path(path).name: _sha256(Path(root) / path) for path in fields["attachments"]}
    report["attachments"] = {name: attachments.get(name) == digest for name, digest in local.items()}
    if set(attachments) != set(local) or not all(report["attachments"].values()):
        problems.append("OSF attachments differ from the local registration files")

    uploads = json.loads(Path(upload_list_path).read_text())["uploads"]
    zenodo = fetch(f"https://zenodo.org/api/records/{ZENODO_RECORD}/files")
    remote = {entry["key"]: (entry["size"], entry.get("checksum")) for entry in zenodo["entries"]}
    expected_files = {item["upload_filename"]: (item["size_bytes"], "md5:" + _md5(Path(root) / item["source_path"]))
                      for item in uploads}
    report["zenodo_files_match"] = remote == expected_files
    if remote != expected_files:
        problems.append("Zenodo files differ from the upload list (names, sizes or MD5)")
    report["problems"] = problems
    report["passed"] = not problems
    return not problems, report


# -- commands -------------------------------------------------------------------------------------
def status(orchestrator, phases):
    out = {}
    for phase in phases:
        counts = {}
        for unit in orchestrator.schedule.phase(phase):
            state = orchestrator.state(unit)
            counts[state] = counts.get(state, 0) + 1
        out[phase] = counts
    out["gates"] = {name: orchestrator.gate(name) is not None for name in ("canary", "fits", "evaluation")}
    out["canary_approved"] = orchestrator._path("gates", "canary.approval.json").exists()
    out["stop_requested"] = orchestrator.stop_requested()
    out["slots_held"] = slots_held()
    out["workers"] = worker_processes()
    out["free_gb"] = round(free_bytes() / 1e9, 1)
    from .backup_runtime import backup_freshness
    out["backup"] = backup_freshness()
    return out


def run_phase(phase, report):
    require_ac_power()
    require_free_disk()
    require_full_run_capacity(phase)
    orchestrator = production_orchestrator()
    if orchestrator.stop_requested():
        raise LaunchRefused("A stop request is active; run `recover-check`, then `resume` first")
    recovery = recovery_report()
    if recovery["verdict"] != "OK":
        raise LaunchRefused(f"Recovery check requires review first: {recovery['blocking']}")
    _record(f"run-{phase}", {"phase": phase, "preflight": report, "recovery": recovery})
    command = [sys.executable, "-B", "-m", MODULE, "worker"]
    monitor = Monitor(request_stop=lambda reason: safe_request_stop(orchestrator, reason),
                      health_dir=runtime_dir() / "launcher" / "health", phase=phase, count_outcomes=count_outcomes)
    with keep_awake():
        state, summaries = launch(phase, worker_command=command,
                                  request_stop=lambda reason: safe_request_stop(orchestrator, reason),
                                  log_dir=runtime_dir() / "launcher" / "logs", monitor=monitor,
                                  pid_dir=runtime_dir() / "launcher" / "workers")
    _record(f"result-{phase}", {"phase": phase, "state": state, "rounds": summaries,
                                "guard_stop_reason": monitor.stopped_reason})
    print(json.dumps({"phase": phase, "state": state, "guard_stop_reason": monitor.stopped_reason,
                      "status": status(orchestrator, [phase])}, indent=2))
    return state, orchestrator


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("verify-registration")
    sub.add_parser("start")
    run = sub.add_parser("run")
    run.add_argument("--phase", required=True, choices=PHASES)
    sts = sub.add_parser("status")
    sts.add_argument("--phase", action="append", choices=PHASES)
    stop = sub.add_parser("stop")
    stop.add_argument("--reason", required=True)
    sub.add_parser("recover-check")
    resume = sub.add_parser("resume")
    resume.add_argument("--acknowledge-modern-halt", action="store_true")
    approve = sub.add_parser("approve-canary")
    approve.add_argument("--approver", required=True)
    approve.add_argument("--note", required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("phase", choices=PHASES)
    sub.add_parser("host-probe")
    args = parser.parse_args(argv)

    try:
        if args.command == "host-probe":
            print(json.dumps(host_probe()))
            return 0
        if args.command == "worker":
            return worker_main(args.phase)
        if args.command == "preflight":
            require_thread_env()
            print(json.dumps(preflight(), indent=2))
            return 0
        if args.command == "verify-registration":
            passed, report = verify_registration()
            OSF_VERIFICATION.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            print(json.dumps(report, indent=2))
            print("REGISTRATION VERIFIED" if passed else "REGISTRATION NOT VERIFIED")
            return 0 if passed else 1
        if args.command in ("status", "stop", "resume", "approve-canary", "recover-check"):
            # Control commands open an existing journal only; they never create one.
            if not execution_unlocked():
                raise LaunchRefused("EXECUTION_UNLOCKED = NO")
            if not (runtime_dir() / "fingerprints.json").exists():
                raise LaunchRefused("No runtime journal exists yet; nothing to control")
            require_thread_env()
            if args.command == "recover-check":
                report = recovery_report()
                print(json.dumps(report, indent=2))
                return 0 if report["verdict"] == "OK" else 1
        else:
            # Scientific runs create the runtime journal: every gate must pass first.
            report = require_execution_allowed()
        if args.command == "start":
            state, orchestrator = run_phase("certify", report)
            if state != "complete":
                print(f"STOP: certify ended {state}; inspect before continuing.")
                return 1
            state, orchestrator = run_phase("canary", report)
            gate = orchestrator.gate("canary")
            print("STOP: canary gate reached." if gate else f"STOP: canary ended {state}.")
            if gate:
                print(json.dumps(gate, indent=2))
                print("Review the canary technical evidence, then: approve-canary --approver NAME --note TEXT "
                      "(the note must not cite any outer-test quantity; none exists).")
            return 0 if gate else 1
        if args.command == "run":
            state, _ = run_phase(args.phase, report)
            return 0 if state == "complete" else 1
        orchestrator = production_orchestrator()
        if args.command == "status":
            print(json.dumps(status(orchestrator, args.phase or ["certify", "canary"]), indent=2))
        elif args.command == "stop":
            safe_request_stop(orchestrator, args.reason)
            print("Stop requested: workers finish their current unit and take no new work.")
        elif args.command == "resume":
            recovery = recovery_report()
            if recovery["slots_held"] or recovery["live_workers"]:
                raise LaunchRefused("Workers are still running; wait for them to finish before resuming")
            if recovery["modern_family_markers"] and not args.acknowledge_modern_halt:
                raise LaunchRefused(f"Modern family markers need author review first: "
                                    f"{recovery['modern_family_markers']} (then --acknowledge-modern-halt)")
            orchestrator.clear_stop()
            _record("resume", {"recovery": recovery, "acknowledged_modern_halt": args.acknowledge_modern_halt})
            print(json.dumps(recovery, indent=2))
            print("Stop request cleared. Rerun the same phase command to continue.")
        elif args.command == "approve-canary":
            orchestrator.approve("canary", approver=args.approver, note=args.note)
            _record("approve-canary", {"approver": args.approver, "note": args.note})
            print("Canary gate approved.")
        return 0
    except LaunchRefused as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
