"""Generate a lightweight artifact manifest for a results stage directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def file_sha256(path: Path, max_bytes: int = 50_000_000) -> str | None:
    if path.stat().st_size > max_bytes:
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="development", choices=["pilot", "development", "final"])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1] / "results" / args.stage
    entries = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix in {".log", ".db"} or "logs" in p.parts:
            continue
        rel = str(p.relative_to(root))
        entries.append(
            {
                "path": rel,
                "bytes": p.stat().st_size,
                "sha256": file_sha256(p),
            }
        )
    manifest = {
        "stage": args.stage,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "n_files": len(entries),
        "files": entries,
    }
    out = args.out or (root / "artifact_manifest.json")
    out.write_text(json.dumps(manifest, indent=2))
    print("wrote", out, "files", len(entries))


if __name__ == "__main__":
    main()
