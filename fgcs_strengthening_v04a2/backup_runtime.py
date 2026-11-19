"""Verified, hard-linked snapshots of the FGCS v0.4 runtime journal (operator tool, not a sealed source).

    python -m fgcs_strengthening_v04a2.backup_runtime backup  --dest /Volumes/<drive>/fgcs_runtime_backups
    python -m fgcs_strengthening_v04a2.backup_runtime backup  --dest ... --every 3600     # hourly loop
    python -m fgcs_strengthening_v04a2.backup_runtime verify  --dest ... [--snapshot NAME]
    python -m fgcs_strengthening_v04a2.backup_runtime status  --dest ...
    python -m fgcs_strengthening_v04a2.backup_runtime restore --dest ... --into /new/empty/path [--snapshot NAME]

Design:
- The destination is always explicit, must already exist, and must be on a different device than the
  runtime. A missing destination means the drive is missing.
- rsync copies `runtime/` into `snapshots/<UTC>.partial/` at background CPU and I/O priority, read-only
  on the source. It hard-links unchanged files from the latest verified snapshot (`--link-dest`) and
  excludes temporary (`tmp*`) and launcher worker-PID files.
- Every file gets a SHA-256 in the manifest. Files hard-linked from the previous snapshot reuse its hash;
  new files are hashed on the destination and checked against the source.
- Publication is atomic: the manifest goes through a temporary file, fsync and rename; then the snapshot
  directory is renamed from `.partial`; then `latest.json` is replaced. Only verified snapshots count,
  and the latest two are kept.
- Failures never touch the runtime or workers. They are recorded in `fgcs_strengthening_v04a2/backup_status.json`
  (outside the runtime, git-ignored), which the launcher's health snapshot reports.
- Restore only goes into an empty, new path outside the live runtime, after verifying the manifest. The
  journal is never restored in place.
"""

import argparse
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from .src.identity import HOME

RUNTIME = HOME / "runtime"
STATUS = HOME / "backup_status.json"
SNAPSHOT_NAME = re.compile(r"^\d{8}T\d{6}Z$")
EXCLUDES = ("tmp*", "launcher/workers/")
KEEP = 2
STALE_HOURS = 2.0
MARGIN = 1.2
FIXED_MARGIN_BYTES = 1e9
RSYNC = "rsync"


class BackupRefused(RuntimeError):
    """A precondition failed; nothing was copied and nothing was changed."""


class BackupFailed(RuntimeError):
    """Copy or verification failed; the snapshot stays `.partial` and is not published."""


def _utc():
    return datetime.now(timezone.utc)


def _sha256(path):
    digest = sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path, record):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w") as stream:
        stream.write(json.dumps(record, indent=1, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _files(root):
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and not path.is_symlink():
            yield path.relative_to(root).as_posix(), path


def _excluded(relative):
    name = relative.rsplit("/", 1)[-1]
    return name.startswith("tmp") or relative.startswith("launcher/workers/")


def snapshots_dir(dest):
    return Path(dest) / "snapshots"


def verified_snapshots(dest):
    directory = snapshots_dir(dest)
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir()
                  if SNAPSHOT_NAME.match(path.name) and (path / "MANIFEST.json").is_file())


def read_latest(dest):
    path = Path(dest) / "latest.json"
    return json.loads(path.read_text()) if path.is_file() else None


def write_status(record, status_path=STATUS):
    try:
        _atomic_json(status_path, {**record, "status_written_utc": _utc().isoformat()})
    except OSError:
        pass  # status reporting must never affect the run


def require_destination(runtime, dest, *, allow_same_device=False):
    runtime, dest = Path(runtime), Path(dest)
    if not (runtime / "fingerprints.json").is_file():
        raise BackupRefused(f"No runtime journal at {runtime}")
    if not dest.is_dir():
        raise BackupRefused(f"Backup destination {dest} does not exist: is the drive mounted?")
    if not allow_same_device and os.stat(dest).st_dev == os.stat(runtime).st_dev:
        raise BackupRefused("Backup destination is on the same device as the runtime; use an external drive")
    if dest.resolve() == runtime.resolve() or runtime.resolve() in dest.resolve().parents:
        raise BackupRefused("Backup destination may not be inside the runtime")


def _tree_bytes(root):
    return sum(path.stat().st_size for _, path in _files(root))


def backup_once(runtime=RUNTIME, dest=None, *, allow_same_device=False, rsync=RSYNC, free=None,
                status_path=STATUS, now=None, keep=KEEP):
    """Make, verify and publish one snapshot. Returns the published latest record."""
    runtime, dest = Path(runtime), Path(dest)
    require_destination(runtime, dest, allow_same_device=allow_same_device)
    snapshots_dir(dest).mkdir(exist_ok=True)
    with open(dest / ".backup.lock", "a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupRefused("Another backup is already running for this destination") from None
        for stale in snapshots_dir(dest).glob("*.partial"):
            shutil.rmtree(stale)  # an earlier failed or interrupted attempt; never published
        latest = read_latest(dest)
        previous = latest["snapshot"] if latest and latest["snapshot"] in verified_snapshots(dest) else None
        previous_manifest = (json.loads((snapshots_dir(dest) / previous / "MANIFEST.json").read_text())
                             if previous else None)
        runtime_bytes = _tree_bytes(runtime)
        known = previous_manifest["total_bytes"] if previous_manifest else 0
        needed = max(runtime_bytes - known, 0) * MARGIN + FIXED_MARGIN_BYTES
        available = (free or (lambda: shutil.disk_usage(dest).free))()
        if available < needed:
            raise BackupRefused(f"Destination has {available / 1e9:.1f} GB free; about {needed / 1e9:.1f} GB needed")

        name = (now or _utc()).strftime("%Y%m%dT%H%M%SZ")
        if (snapshots_dir(dest) / name).exists():
            raise BackupRefused(f"Snapshot {name} already exists")
        partial = snapshots_dir(dest) / f"{name}.partial"
        command = ["nice", "-n", "19", "taskpolicy", "-b", rsync, "-a"]
        if previous:
            command.append(f"--link-dest={(snapshots_dir(dest) / previous).resolve()}")
        for pattern in EXCLUDES:
            command += ["--exclude", pattern]
        command += [f"{runtime}/", f"{partial}/"]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise BackupFailed(f"rsync exited {result.returncode}: {result.stderr.strip()[-500:]}")

        old = previous_manifest["files"] if previous_manifest else {}
        files, unverified, mismatched = {}, [], []
        for relative, path in _files(partial):
            if _excluded(relative):
                path.unlink()
                continue
            stat = path.stat()
            reused = None
            if relative in old and previous:
                prior = snapshots_dir(dest) / previous / relative
                if prior.exists() and os.stat(prior).st_ino == stat.st_ino:
                    reused = old[relative][1]
            digest = reused or _sha256(path)
            if reused is None:
                source = runtime / relative
                if not source.exists():
                    unverified.append(relative)  # moved during the copy (e.g. quarantine); kept as copied
                elif _sha256(source) != digest:
                    mismatched.append(relative)
            files[relative] = [stat.st_size, digest]
        if mismatched:
            raise BackupFailed(f"{len(mismatched)} copied files differ from the runtime: {mismatched[:5]}")
        manifest = {"snapshot": name, "created_utc": _utc().isoformat(), "runtime": str(runtime.resolve()),
                    "previous": previous, "file_count": len(files), "total_bytes": sum(v[0] for v in files.values()),
                    "unverified_source_gone": unverified, "files": files}
        _atomic_json(partial / "MANIFEST.json", manifest)
        manifest_sha = _sha256(partial / "MANIFEST.json")
        final = snapshots_dir(dest) / name
        os.replace(partial, final)
        record = {"snapshot": name, "manifest_sha256": manifest_sha, "utc": manifest["created_utc"],
                  "file_count": manifest["file_count"], "total_bytes": manifest["total_bytes"],
                  "previous_snapshot": previous}
        _atomic_json(dest / "latest.json", record)
        for stale in verified_snapshots(dest)[:-keep]:
            shutil.rmtree(snapshots_dir(dest) / stale)
        write_status({"result": "ok", "dest": str(dest), **record}, status_path)
        return record


def verify_snapshot(dest, name=None):
    """Re-hash a published snapshot against its manifest. Returns (ok, report)."""
    dest = Path(dest)
    latest = read_latest(dest)
    name = name or (latest or {}).get("snapshot")
    if not name or not (snapshots_dir(dest) / name / "MANIFEST.json").is_file():
        return False, {"snapshot": name, "problems": ["no published snapshot"]}
    root = snapshots_dir(dest) / name
    manifest = json.loads((root / "MANIFEST.json").read_text())
    problems = []
    if latest and latest["snapshot"] == name and _sha256(root / "MANIFEST.json") != latest["manifest_sha256"]:
        problems.append("MANIFEST.json differs from latest.json")
    present = {relative for relative, _ in _files(root) if relative != "MANIFEST.json"}
    missing = sorted(set(manifest["files"]) - present)
    extra = sorted(present - set(manifest["files"]))
    corrupt = [relative for relative, (size, digest) in manifest["files"].items()
               if relative in present and ((root / relative).stat().st_size != size or _sha256(root / relative) != digest)]
    if missing:
        problems.append(f"{len(missing)} files missing: {missing[:5]}")
    if extra:
        problems.append(f"{len(extra)} unexpected files: {extra[:5]}")
    if corrupt:
        problems.append(f"{len(corrupt)} files corrupted: {corrupt[:5]}")
    return not problems, {"snapshot": name, "file_count": len(manifest["files"]), "problems": problems}


def backup_status(dest, *, now=None, stale_hours=STALE_HOURS):
    """Drive presence, freshness and leftovers. Verdicts: OK, STALE, NO_SNAPSHOT, PARTIAL, DRIVE_MISSING."""
    dest = Path(dest)
    if not dest.is_dir():
        return {"verdict": "DRIVE_MISSING", "dest": str(dest)}
    latest = read_latest(dest)
    partial = sorted(path.name for path in snapshots_dir(dest).glob("*.partial")) if snapshots_dir(dest).is_dir() else []
    report = {"dest": str(dest), "latest": latest, "verified_snapshots": verified_snapshots(dest),
              "partial": partial, "free_gb": round(shutil.disk_usage(dest).free / 1e9, 1)}
    if not latest:
        report["verdict"] = "NO_SNAPSHOT"
        return report
    age = ((now or _utc()) - datetime.fromisoformat(latest["utc"])).total_seconds() / 3600
    report["age_hours"] = round(age, 2)
    report["verdict"] = "PARTIAL" if partial else ("STALE" if age > stale_hours else "OK")
    return report


def backup_freshness(status_path=STATUS, *, now=None, stale_hours=STALE_HOURS):
    """What the launcher reports: the last recorded backup result and its age, from the status file."""
    path = Path(status_path)
    if not path.is_file():
        return {"verdict": "NO_BACKUP_RECORDED"}
    record = json.loads(path.read_text())
    if record.get("result") != "ok":
        return {"verdict": "LAST_BACKUP_FAILED", "error": record.get("error"), "utc": record.get("utc")}
    age = ((now or _utc()) - datetime.fromisoformat(record["utc"])).total_seconds() / 3600
    return {"verdict": "STALE" if age > stale_hours else "OK", "age_hours": round(age, 2),
            "snapshot": record.get("snapshot"), "dest": record.get("dest")}


def restore(dest, into, *, name=None, live_runtime=RUNTIME, rsync=RSYNC):
    """Copy a verified snapshot into an empty new directory. Never into the live runtime."""
    into, live = Path(into), Path(live_runtime)
    if into.exists():
        raise BackupRefused(f"{into} already exists; restore only into a new, empty path")
    resolved, live_resolved = into.resolve(), live.resolve()
    if resolved == live_resolved or live_resolved in resolved.parents or resolved in live_resolved.parents:
        raise BackupRefused("Restore may not target, contain, or sit inside the live runtime")
    ok, report = verify_snapshot(dest, name)
    if not ok:
        raise BackupFailed(f"Snapshot does not verify: {report['problems']}")
    root = snapshots_dir(dest) / report["snapshot"]
    into.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([rsync, "-a", "--exclude", "MANIFEST.json", f"{root}/", f"{into}/"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise BackupFailed(f"rsync exited {result.returncode}: {result.stderr.strip()[-500:]}")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    restored = {relative: [path.stat().st_size, _sha256(path)] for relative, path in _files(into)}
    if restored != manifest["files"]:
        raise BackupFailed("Restored files differ from the snapshot manifest")
    return {"snapshot": report["snapshot"], "into": str(into), "file_count": len(restored)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "verify", "status", "restore"):
        command = sub.add_parser(name)
        command.add_argument("--dest", required=True)
        if name == "backup":
            command.add_argument("--every", type=int, default=0, help="repeat every N seconds (0 = once)")
        if name in ("verify", "restore"):
            command.add_argument("--snapshot")
        if name == "restore":
            command.add_argument("--into", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            print(json.dumps(backup_status(args.dest), indent=2))
            return 0
        if args.command == "verify":
            ok, report = verify_snapshot(args.dest, args.snapshot)
            print(json.dumps(report, indent=2))
            return 0 if ok else 1
        if args.command == "restore":
            print(json.dumps(restore(args.dest, args.into, name=args.snapshot), indent=2))
            return 0
        while True:
            try:
                record = backup_once(RUNTIME, args.dest)
                print(json.dumps({"result": "ok", **record}), flush=True)
            except (BackupRefused, BackupFailed, OSError) as error:
                write_status({"result": "failed", "error": f"{type(error).__name__}: {error}",
                              "dest": args.dest, "utc": _utc().isoformat()})
                print(json.dumps({"result": "failed", "error": str(error)}), flush=True)
                if not args.every:
                    return 1
            if not args.every:
                return 0
            time.sleep(args.every)
    except (BackupRefused, BackupFailed) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
