"""Frozen host manifest for the v0.4 run (operator tool, not a sealed source).

    python -m fgcs_strengthening_v04.host capture --out PATH   # in a worker-configured process
    python -m fgcs_strengthening_v04.host check --manifest PATH

r3 checked the host through its systems-benchmark module, which v0.4 drops (P8). This module keeps
only the part the launcher needs: the live hardware, library versions and single-thread CPU
conditions must equal the manifest frozen with the registration package. Observing never changes
a thread or device setting.
"""

import argparse
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

THREAD_VARIABLES = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")


class HostMismatch(RuntimeError):
    """The live host differs from the frozen manifest."""


def _sysctl(key):
    return subprocess.check_output(["/usr/sbin/sysctl", "-n", key], text=True, stderr=subprocess.DEVNULL).strip()


def _power_mode():
    try:
        lines = subprocess.check_output(["/usr/bin/pmset", "-g"], text=True, stderr=subprocess.DEVNULL).splitlines()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return " | ".join(line.strip() for line in lines
                      if line.strip().startswith(("lowpowermode", "powermode", "highpowermode"))) or "unavailable"


def observe():
    """The live host: hardware, software and the CPU thread conditions of this process."""
    import numpy
    import pandas
    import torch

    if platform.system() != "Darwin":
        raise HostMismatch(f"Unsupported host platform {platform.system()}")
    blas = next((line.split("BLAS_INFO=", 1)[1].split(",", 1)[0] for line in torch.__config__.show().splitlines()
                 if "BLAS_INFO=" in line), "unknown")
    return {
        "hardware": {"hostname": socket.gethostname(), "cpu_model": _sysctl("machdep.cpu.brand_string"),
                     "physical_cores": int(_sysctl("hw.physicalcpu")), "logical_cores": int(_sysctl("hw.logicalcpu")),
                     "ram_bytes": int(_sysctl("hw.memsize")), "os": platform.system(), "kernel": platform.version(),
                     "power_mode": _power_mode()},
        "software": {"python": platform.python_version(), "numpy": numpy.__version__, "pandas": pandas.__version__,
                     "pytorch": torch.__version__, "torch_blas": blas},
        "conditions": {"device": torch.get_default_device().type, "torch_intraop_threads": torch.get_num_threads(),
                       "torch_interop_threads": torch.get_num_interop_threads(),
                       **{key: os.environ.get(key) for key in THREAD_VARIABLES}},
    }


EXPECTED_CONDITIONS = {"device": "cpu", "torch_intraop_threads": 1, "torch_interop_threads": 1,
                       **dict.fromkeys(THREAD_VARIABLES, "1")}


def differences(frozen, live):
    """Every field whose live value differs from the frozen one, as 'section.field: frozen -> live'."""
    found = []
    for section in ("hardware", "software", "conditions"):
        expected, observed = frozen.get(section, {}), live.get(section, {})
        for key in sorted(set(expected) | set(observed)):
            if expected.get(key) != observed.get(key):
                found.append(f"{section}.{key}: {expected.get(key)!r} -> {observed.get(key)!r}")
    return found


def require_host(manifest, live=None):
    """Raise HostMismatch unless the live host equals the frozen manifest and runs single-threaded on CPU."""
    frozen = json.loads(Path(manifest).read_text())
    if frozen.get("conditions") != EXPECTED_CONDITIONS:
        raise HostMismatch("The frozen manifest does not record the registered single-thread CPU conditions")
    live = observe() if live is None else live
    found = differences(frozen, live)
    if found:
        raise HostMismatch("Live host differs from the frozen manifest: " + "; ".join(found))
    return live


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capture").add_argument("--out", required=True)
    sub.add_parser("check").add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    from .src.orchestrator import configure_worker_process

    configure_worker_process()
    if args.command == "capture":
        live = observe()
        if live["conditions"] != EXPECTED_CONDITIONS:
            print(f"REFUSED: capture in a single-threaded worker environment: {live['conditions']}", file=sys.stderr)
            return 2
        out = Path(args.out)
        if out.exists():
            print(f"REFUSED: {out} exists", file=sys.stderr)
            return 2
        out.write_text(json.dumps(live, indent=2, sort_keys=True) + "\n")
        print(f"Wrote {out}")
        return 0
    try:
        print(json.dumps(require_host(args.manifest), indent=2))
    except HostMismatch as error:
        print(f"MISMATCH: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
