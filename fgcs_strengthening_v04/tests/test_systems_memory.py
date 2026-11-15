import os
import platform
import unittest

from fgcs_strengthening_v04.src.systems import run_isolated
from fgcs_strengthening_v04.src.systems_environment import ENV_THREADS, peak_rss_bytes
from fgcs_strengthening_v04.src.provenance import ProvenanceError


def touch_memory(mib):
    buffer = bytearray(mib * 1024 * 1024)
    for index in range(0, len(buffer), 4096):
        buffer[index] = 1
    return {"pid": os.getpid(), "threads": [os.environ[name] for name in ENV_THREADS]}


class SystemsMemoryTests(unittest.TestCase):
    def test_platform_units(self):
        self.assertEqual(peak_rss_bytes(10, "Darwin"), (10, "Darwin ru_maxrss bytes"))
        self.assertEqual(peak_rss_bytes(10, "Linux"), (10240, "Linux ru_maxrss KiB converted to bytes"))
        with self.assertRaises(ProvenanceError):
            peak_rss_bytes(10, "Unknown")

    def test_real_fresh_process_and_peak(self):
        module = "fgcs_strengthening_v04.tests.test_systems_memory"
        first = run_isolated(module, "touch_memory", {"mib": 16})
        second = run_isolated(module, "touch_memory", {"mib": 32})
        self.assertEqual(len({os.getpid(), first["worker_pid"], second["worker_pid"]}), 3)
        for result in (first, second):
            self.assertEqual(result["result"], {"pid": result["worker_pid"], "threads": ["1"] * 3})
            self.assertTrue(result["platform_interpretation"].startswith(platform.system()))
            self.assertGreater(result["baseline_rss_bytes"], 0)
            self.assertGreater(result["peak_increment_bytes"], 0)
            self.assertEqual(result["peak_rss_bytes"] - result["baseline_rss_bytes"], result["peak_increment_bytes"])


import subprocess as _subprocess
from dataclasses import replace as _replace

from fgcs_strengthening_v04.src.systems_environment import (
    MachineManifest, REGISTERED, current_rss_bytes, observe_environment,
)


def fail_workload():
    raise RuntimeError("synthetic workload failure")


def lstm_workload(batch):
    import torch
    from fgcs_strengthening_v04.src.identity import RESOURCES
    from fgcs_strengthening_v04.src.models.lstm import LSTM

    torch.manual_seed(0)
    model = LSTM(formulation="M1", block="fastStorage", tasks=RESOURCES, hidden_size=64).eval()
    values = torch.zeros((batch, 18, 4))
    with torch.inference_mode():
        for _ in range(120):
            output = model(values)
    return {"shape": list(output.shape), "threads": [torch.get_num_threads(), torch.get_num_interop_threads()]}


class SystemsMemoryGuardTests(unittest.TestCase):
    def test_allocation_size_is_visible_in_peak_increment(self):
        result = run_isolated("fgcs_strengthening_v04.tests.test_systems_memory", "touch_memory", {"mib": 64})
        self.assertGreaterEqual(result["peak_increment_bytes"], 48 * 1024 * 1024)
        self.assertGreater(current_rss_bytes(platform.system()), 0)

    def test_manifest_guarded_worker_and_failures_are_fail_closed(self):
        live = observe_environment()
        expected = MachineManifest(live.hardware, live.software, REGISTERED)
        module = "fgcs_strengthening_v04.tests.test_systems_memory"
        result = run_isolated(module, "lstm_workload", {"batch": 128}, manifest=expected)
        self.assertEqual(result["result"], {"shape": [128, 4, 5], "threads": [1, 1]})
        self.assertGreater(result["peak_increment_bytes"], 0)
        other = _replace(expected, hardware=_replace(expected.hardware, hostname="replacement-host"))
        for manifest, function in ((other, "touch_memory"), (None, "fail_workload")):
            with self.subTest(function=function), self.assertRaises(_subprocess.CalledProcessError) as caught:
                run_isolated(module, function, {"mib": 1} if function == "touch_memory" else {}, manifest=manifest)
            self.assertIn(b"ProvenanceError" if manifest else b"synthetic workload failure", caught.exception.stderr)
