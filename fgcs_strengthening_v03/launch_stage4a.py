"""Stage 4A launcher for the registered FGCS v0.3 execution (operator tool, not a sealed source).

    python -m fgcs_strengthening_v03.launch_stage4a preflight
    python -m fgcs_strengthening_v03.launch_stage4a stage4a          # certify, then the 96-fit canary, then STOP
    python -m fgcs_strengthening_v03.launch_stage4a status [--phase canary]
    python -m fgcs_strengthening_v03.launch_stage4a stop --reason "..."      # graceful pause between units
    python -m fgcs_strengthening_v03.launch_stage4a resume
    python -m fgcs_strengthening_v03.launch_stage4a approve-canary --approver NAME --note "..."
    python -m fgcs_strengthening_v03.launch_stage4a run --phase inner        # later phases, after approval

Nothing scientific runs, and no runtime journal is created, unless REGISTRATION_EVIDENCE_TEMPLATE.md
records EXECUTION_UNLOCKED = YES and every preflight check passes:
- tag fgcs-v03-registration-package-r3 resolves to the registered commit;
- the registration package verifies and has the registered digest;
- the live execution seal equals the registered seal;
- a fresh single-threaded worker process matches the frozen host manifest.

Workers are separate processes in their own session, so a terminal Ctrl-C reaches only this controller.
The controller turns the first Ctrl-C into Orchestrator.request_stop: each worker finishes its current
unit and takes no new work, so no retry is used. Workers are never killed.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

from .src.identity import HOME, ROOT

TAG = "fgcs-v03-registration-package-r3"
REGISTERED_COMMIT = "39f828409cc2ee86bc3c52ee4276975488b273f4"
REGISTERED_PACKAGE = "cb577d295e18469214e141f153f00ae587dac8be284ad7cdab0c740ab3d5707e"
REGISTERED_SEAL = "c0161b55c99929093b53742771fadf63cfcd036add1ad3caa43051cae06dcc93"
THREAD_ENV = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
REGISTRATION = HOME / "registration"
EVIDENCE = REGISTRATION / "REGISTRATION_EVIDENCE_TEMPLATE.md"
HOST_MANIFEST = REGISTRATION / "host_manifest.json"
PACKAGE = REGISTRATION / "PACKAGE.json"
FIT_WORKERS = 4  # C4; Orchestrator enforces the same count with slot locks
SINGLE_WORKER_PHASES = ("certify", "systems")
EXIT_COMPLETE, EXIT_STOPPED, EXIT_INCOMPLETE = 0, 3, 4
MAX_ROUNDS = 10


class LaunchRefused(RuntimeError):
    """A gate failed; nothing was started."""


# -- gates ----------------------------------------------------------------------------------------
def execution_unlocked(path=EVIDENCE):
    """True only when the evidence file holds exactly one line `EXECUTION_UNLOCKED = YES`."""
    lines = [line.strip() for line in Path(path).read_text().splitlines()
             if line.strip().startswith("EXECUTION_UNLOCKED")]
    if len(lines) != 1 or not re.fullmatch(r"EXECUTION_UNLOCKED = (YES|NO)", lines[0]):
        raise LaunchRefused(f"Expected exactly one EXECUTION_UNLOCKED = YES|NO line in {path}")
    return lines[0].endswith("YES")


def require_thread_env(env=None):
    env = os.environ if env is None else env
    wrong = {key: env.get(key) for key, value in THREAD_ENV.items() if env.get(key) != value}
    if wrong:
        raise LaunchRefused(f"Thread variables must be exported as 1 before Python starts: {wrong}")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def check_repository():
    """The registered tag and commit exist; the registration files are unchanged against the tag."""
    tagged = _git("rev-parse", f"{TAG}^{{commit}}").stdout.strip()
    if tagged != REGISTERED_COMMIT:
        raise LaunchRefused(f"{TAG} resolves to {tagged or 'nothing'}, not {REGISTERED_COMMIT}")
    files = ["fgcs_strengthening_v03/registration/" + name for name in
             ("PACKAGE.json", "execution_seal.json", "schedule.json", "analysis_catalogue.json",
              "systems_population.json", "host_manifest.json")]
    if _git("diff", "--quiet", TAG, "--", *files).returncode != 0:
        raise LaunchRefused("Registration package files differ from the registered tag")
    return {"tag_commit": tagged, "head": _git("rev-parse", "HEAD").stdout.strip()}


def check_package():
    from .build_registration import verify

    digest, problems = verify()
    if problems or digest != REGISTERED_PACKAGE:
        raise LaunchRefused(f"Registration package does not verify: {digest} {problems}")
    return digest


def check_seal():
    from .src.orchestrator import execution_fingerprints

    digest = execution_fingerprints().digest
    recorded = json.loads((REGISTRATION / "execution_seal.json").read_text())["digest"]
    if digest != REGISTERED_SEAL or recorded != REGISTERED_SEAL:
        raise LaunchRefused(f"Live execution seal {digest} differs from the registered {REGISTERED_SEAL}")
    return digest


def host_probe():
    """Run in a fresh worker-configured process: single-threaded CPU and the frozen host."""
    from .src.orchestrator import configure_worker_process, require_fit_threads
    from .src.systems_environment import MachineManifest, require_environment

    configure_worker_process()
    threads = require_fit_threads()
    require_environment(MachineManifest.from_file(HOST_MANIFEST))
    return threads


def check_host():
    result = subprocess.run([sys.executable, "-B", "-m", "fgcs_strengthening_v03.launch_stage4a", "host-probe"],
                            cwd=ROOT, env=worker_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise LaunchRefused("Live host differs from the frozen host manifest or is not single-threaded: "
                            + (result.stderr.strip().splitlines() or ["no output"])[-1])
    return json.loads(result.stdout.strip().splitlines()[-1])


def preflight():
    """Every gate except the unlock flag. Raises LaunchRefused at the first failure."""
    report = {"repository": check_repository(), "package_sha256": check_package(), "seal": check_seal(),
              "host": check_host()}
    report["execution_unlocked"] = execution_unlocked()
    return report


def require_execution_allowed():
    if not execution_unlocked():
        raise LaunchRefused("EXECUTION_UNLOCKED = NO: scientific execution stays locked until the registration "
                            "evidence is verified (REGISTRATION_EVIDENCE_TEMPLATE.md)")
    require_thread_env()
    return preflight()


def worker_env():
    env = {**os.environ, **THREAD_ENV, "PYTHONDONTWRITEBYTECODE": "1"}
    return env


# -- workers --------------------------------------------------------------------------------------
def phase_complete(orchestrator, phase):
    return all(orchestrator.terminal(unit) for unit in orchestrator.schedule.phase(phase))


def run_worker(orchestrator, phase):
    """One worker process: repeat orchestrator passes until the phase is terminal, stopped or idle."""
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


def production_orchestrator(phase=None, *, worker=False):
    """The registered journal, schedule and executors. Creates the runtime journal: gates must pass first."""
    from .src.orchestrator import (TRAINING_WORKERS, Orchestrator, ProductionExecutors, Schedule,
                                   configure_worker_process, execution_fingerprints, registered_schedule,
                                   require_fit_threads)
    from .src.provenance import Journal
    from .src.systems_environment import MachineManifest, require_environment

    if worker:
        configure_worker_process()
        require_thread_env()
        require_fit_threads()
        require_environment(MachineManifest.from_file(HOST_MANIFEST))
    seal = execution_fingerprints()
    if seal.digest != REGISTERED_SEAL:
        raise LaunchRefused("Live execution seal differs from the registered seal")
    if TRAINING_WORKERS != FIT_WORKERS:
        raise LaunchRefused("Registered training worker count changed")
    journal = Journal(seal)
    manifest = MachineManifest.from_file(HOST_MANIFEST) if phase == "systems" else None
    holder = {}
    executors = ProductionExecutors(journal, systems_manifest=manifest,
                                    scheduler_elapsed=lambda: holder["orchestrator"].scheduler_elapsed())
    holder["orchestrator"] = Orchestrator(journal, Schedule(registered_schedule()), executors,
                                          registration=PACKAGE, workers=TRAINING_WORKERS)
    return holder["orchestrator"]


def worker_main(phase):
    if not execution_unlocked():
        raise LaunchRefused("EXECUTION_UNLOCKED = NO")
    code, summary = run_worker(production_orchestrator(phase, worker=True), phase)
    print(json.dumps(summary), flush=True)
    return code


# -- controller -----------------------------------------------------------------------------------
def worker_count(phase):
    return 1 if phase in SINGLE_WORKER_PHASES else FIT_WORKERS


def launch(phase, *, worker_command, request_stop, env=None, workers=None, max_rounds=MAX_ROUNDS, log=print):
    """Start the phase's workers, convert the first Ctrl-C/SIGTERM into a graceful stop, never kill workers.

    Rounds repeat while workers make progress and the phase is unfinished (for example, units that were
    leased by another worker during a pass). Returns the final state and every worker summary.
    """
    env = worker_env() if env is None else env
    workers = worker_count(phase) if workers is None else workers
    stopping = {"requested": False}

    def on_signal(signum, frame):
        if not stopping["requested"]:
            stopping["requested"] = True
            log(f"Signal {signum}: requesting a graceful stop; workers finish their current unit")
            request_stop("operator interrupt received by the Stage 4A launcher")

    previous = {sig: signal.signal(sig, on_signal) for sig in (signal.SIGINT, signal.SIGTERM)}
    summaries = []
    try:
        for round_index in range(1, max_rounds + 1):
            processes = [subprocess.Popen([*worker_command, phase], cwd=ROOT, env=env, start_new_session=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                         for _ in range(workers)]
            results = []
            for process in processes:
                out, err = process.communicate()
                lines = out.strip().splitlines()
                summary = json.loads(lines[-1]) if lines and lines[-1].startswith("{") else {}
                results.append({"returncode": process.returncode, **summary,
                                "stderr_tail": err.strip().splitlines()[-3:] if process.returncode not in
                                (EXIT_COMPLETE, EXIT_STOPPED, EXIT_INCOMPLETE) else []})
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


def _record(name, payload):
    """Launcher provenance next to the journal (only after the journal exists)."""
    path = HOME / "runtime" / "launcher" / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"launcher_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "argv": sys.argv,
               "utc": datetime.now(timezone.utc).isoformat(), **payload}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


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
    return out


def run_phase(phase, report):
    orchestrator = production_orchestrator(phase)
    if orchestrator.stop_requested():
        raise LaunchRefused("A stop request is active; run `resume` first")
    _record(f"run-{phase}", {"phase": phase, "preflight": report})
    command = [sys.executable, "-B", "-m", "fgcs_strengthening_v03.launch_stage4a", "worker"]
    state, summaries = launch(phase, worker_command=command,
                              request_stop=lambda reason: orchestrator.request_stop(reason=reason))
    _record(f"result-{phase}", {"phase": phase, "state": state, "rounds": summaries})
    print(json.dumps({"phase": phase, "state": state, "status": status(orchestrator, [phase])}, indent=2))
    return state, orchestrator


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("stage4a")
    run = sub.add_parser("run")
    run.add_argument("--phase", required=True, choices=("certify", "canary", "inner", "final", "diagnostics",
                                                       "systems", "evaluation"))
    sts = sub.add_parser("status")
    sts.add_argument("--phase", action="append")
    stop = sub.add_parser("stop")
    stop.add_argument("--reason", required=True)
    sub.add_parser("resume")
    approve = sub.add_parser("approve-canary")
    approve.add_argument("--approver", required=True)
    approve.add_argument("--note", required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("phase")
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
        if args.command in ("status", "stop", "resume", "approve-canary"):
            # Control commands open an existing journal only; they never create one.
            if not execution_unlocked():
                raise LaunchRefused("EXECUTION_UNLOCKED = NO")
            if not (HOME / "runtime" / "fingerprints.json").exists():
                raise LaunchRefused("No runtime journal exists yet; nothing to control")
            require_thread_env()
        else:
            # Scientific runs create the runtime journal: every gate must pass first.
            report = require_execution_allowed()
        if args.command == "stage4a":
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
            orchestrator.request_stop(reason=args.reason)
            print("Stop requested: workers finish their current unit and take no new work.")
        elif args.command == "resume":
            orchestrator.clear_stop()
            print("Stop request cleared.")
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
