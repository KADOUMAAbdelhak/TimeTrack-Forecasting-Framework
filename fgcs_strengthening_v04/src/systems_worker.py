"""Fresh-process RSS worker. Workloads are imported after the memory baseline."""

from contextlib import redirect_stdout
import importlib
import json
import os
import platform
import resource
import sys

from .systems_environment import MachineManifest, current_rss_bytes, peak_rss_bytes, require_environment


def main():
    spec = json.load(sys.stdin)
    system = platform.system()
    with redirect_stdout(sys.stderr):
        if spec["manifest"] is not None:
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            require_environment(MachineManifest.from_payload(spec["manifest"]))
        baseline = current_rss_bytes(system)
        module = importlib.import_module(spec["module"])
        function = getattr(module, spec["function"])
        result = function(**spec["arguments"])
        peak, interpretation = peak_rss_bytes(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, system)
    if peak < baseline:
        raise RuntimeError("Peak RSS is lower than the observed baseline")
    json.dump({"baseline_rss_bytes": baseline, "peak_rss_bytes": peak, "peak_increment_bytes": peak - baseline,
               "platform_interpretation": interpretation, "worker_pid": os.getpid(), "result": result},
              sys.stdout, allow_nan=False)


if __name__ == "__main__":
    main()
