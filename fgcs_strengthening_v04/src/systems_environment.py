"""Host manifest, runtime guard and explicit RSS unit handling."""

from dataclasses import asdict, dataclass
import ctypes
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import socket
import subprocess

from .identity import canonical_json
from .provenance import ProvenanceError

ENV_THREADS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")


@dataclass(frozen=True, slots=True)
class Hardware:
    hostname: str
    cpu_model: str
    physical_cores: int
    logical_cores: int
    ram_bytes: int
    os: str
    kernel: str
    power_mode: str

    def __post_init__(self):
        if (not all(isinstance(s, str) and s.strip() for s in
                    (self.hostname, self.cpu_model, self.os, self.kernel, self.power_mode))
                or any(type(n) is not int or n < 1 for n in (self.physical_cores, self.logical_cores, self.ram_bytes))
                or self.physical_cores > self.logical_cores):
            raise ValueError("Incomplete benchmark hardware manifest")


@dataclass(frozen=True, slots=True)
class Software:
    python: str
    numpy: str
    pytorch: str
    lightgbm: str
    scikit_learn: str
    blas_backend: str

    def __post_init__(self):
        if not all(isinstance(s, str) and s.strip() for s in asdict(self).values()):
            raise ValueError("Incomplete benchmark software manifest")


@dataclass(frozen=True, slots=True)
class Conditions:
    device: str
    workers: int
    torch_intraop_threads: int
    torch_interop_threads: int
    OMP_NUM_THREADS: str
    MKL_NUM_THREADS: str
    OPENBLAS_NUM_THREADS: str
    lightgbm_jobs: int

    def require_registered(self):
        if self != REGISTERED or any(type(value) is bool for value in asdict(self).values()):
            raise ProvenanceError("Benchmark requires CPU and the registered single-worker/single-thread conditions")


REGISTERED = Conditions("cpu", 1, 1, 1, "1", "1", "1", 1)


@dataclass(frozen=True, slots=True)
class MachineManifest:
    hardware: Hardware
    software: Software
    conditions: Conditions

    def __post_init__(self):
        if not isinstance(self.hardware, Hardware) or not isinstance(self.software, Software) or not isinstance(self.conditions, Conditions):
            raise ValueError("Expected a complete machine manifest")

    @classmethod
    def from_payload(cls, record):
        return cls(Hardware(**record["hardware"]), Software(**record["software"]), Conditions(**record["conditions"]))

    @classmethod
    def from_file(cls, path):
        return cls.from_payload(json.loads(Path(path).read_bytes()))

    def payload(self):
        return asdict(self)

    @property
    def hardware_sha256(self):
        return sha256(canonical_json(asdict(self.hardware))).hexdigest()

    @property
    def software_sha256(self):
        return sha256(canonical_json({"software": asdict(self.software),
                                      "conditions": asdict(self.conditions)})).hexdigest()


def _command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


def _sysctl(key):
    return _command("/usr/sbin/sysctl", "-n", key)


def _power(system):
    try:
        if system == "Darwin":
            lines = _command("/usr/bin/pmset", "-g").splitlines()
            return " | ".join(line.strip() for line in lines
                              if line.strip().startswith(("lowpowermode", "powermode", "highpowermode"))) or "unavailable"
        paths = ("/sys/firmware/acpi/platform_profile", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        return " | ".join(Path(path).read_text().strip() for path in paths if Path(path).is_file()) or "unavailable"
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _hardware():
    system = platform.system()
    if system == "Darwin":
        cpu = _sysctl("machdep.cpu.brand_string")
        physical, logical, ram = (int(_sysctl(key)) for key in ("hw.physicalcpu", "hw.logicalcpu", "hw.memsize"))
    elif system == "Linux":
        cpuinfo = Path("/proc/cpuinfo").read_text()
        fields = [dict(line.split(":", 1) for line in block.splitlines() if ":" in line)
                  for block in cpuinfo.strip().split("\n\n")]
        fields = [{key.strip(): value.strip() for key, value in row.items()} for row in fields]
        cpu = next((row.get("model name", row.get("Hardware")) for row in fields
                    if row.get("model name") or row.get("Hardware")), "")
        logical = os.cpu_count()
        cores = set()
        for p in range(logical):
            base = Path(f"/sys/devices/system/cpu/cpu{p}/topology")
            cores.add(((base / "physical_package_id").read_text(), (base / "core_id").read_text()))
        physical = len(cores)
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    else:
        raise ProvenanceError(f"Unsupported benchmark platform {system}")
    return Hardware(socket.gethostname(), cpu, physical, logical, ram, system, platform.version(), _power(system))


def observe_environment():
    """Observe the live host without silently changing thread or device settings."""
    import lightgbm
    import numpy
    import sklearn
    import torch
    from threadpoolctl import threadpool_info

    backend = {
        "numpy": numpy.show_config(mode="dicts"),
        "torch": torch.__config__.show(),
        "thread_pools": sorted(
            [{key: value for key, value in pool.items() if key != "filepath"} for pool in threadpool_info()],
            key=lambda pool: (pool.get("prefix", ""), pool.get("internal_api", ""))),
    }
    software = Software(platform.python_version(), numpy.__version__, torch.__version__, lightgbm.__version__,
                        sklearn.__version__, canonical_json(backend).decode())
    conditions = Conditions(torch.get_default_device().type, 1, torch.get_num_threads(),
                            torch.get_num_interop_threads(), *(os.environ.get(key, "") for key in ENV_THREADS), 1)
    return MachineManifest(_hardware(), software, conditions)


def require_environment(expected):
    if not isinstance(expected, MachineManifest):
        raise ProvenanceError("An explicit machine manifest is required")
    expected.conditions.require_registered()
    try:
        observed = observe_environment()
    except (OSError, subprocess.SubprocessError, ImportError, ValueError) as error:
        raise ProvenanceError("Unable to verify the live benchmark environment") from error
    observed.conditions.require_registered()
    if expected != observed:
        raise ProvenanceError("Live hardware/software does not match the declared benchmark manifest")


def peak_rss_bytes(value, system):
    if system == "Darwin":
        return int(value), "Darwin ru_maxrss bytes"
    if system == "Linux":
        return int(value) * 1024, "Linux ru_maxrss KiB converted to bytes"
    raise ProvenanceError(f"Unsupported RSS platform {system}")


def current_rss_bytes(system):
    if system == "Linux":
        pages = int(Path("/proc/self/statm").read_text().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE")
    if system == "Darwin":
        # Darwin's PROC_PIDTASKINFO starts with uint64 virtual and resident sizes.
        # The remaining four uint64 counters and twelve int32 fields complete the ABI.
        class TaskInfo(ctypes.Structure):
            _fields_ = [("virtual_size", ctypes.c_uint64), ("resident_size", ctypes.c_uint64),
                        ("counters", ctypes.c_uint64 * 4), ("details", ctypes.c_int32 * 12)]

        info = TaskInfo()
        task_info = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True).proc_pidinfo
        task_info.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int)
        task_info.restype = ctypes.c_int
        if task_info(os.getpid(), 4, 0, ctypes.byref(info), ctypes.sizeof(info)) != ctypes.sizeof(info):
            raise ProvenanceError("Unable to read Darwin process resident size")
        return info.resident_size
    raise ProvenanceError(f"Unsupported RSS platform {system}")
