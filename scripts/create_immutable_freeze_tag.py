"""Create an annotated freeze tag immutably (never force-updates)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create an annotated freeze tag. Fails if the tag already exists."
    )
    ap.add_argument("--tag", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument(
        "--push",
        action="store_true",
        help="Push the new tag to origin without force",
    )
    args = ap.parse_args()
    from timetrack.freeze_immutability import create_annotated_tag_immutable, peeled_commit, tag_object
    import subprocess

    peel = create_annotated_tag_immutable(args.tag, args.message)
    obj = tag_object(args.tag)
    print(f"created tag={args.tag} object={obj} peel={peel}")
    if args.push:
        subprocess.check_call(["git", "push", "origin", args.tag], cwd=str(ROOT))
        remote = subprocess.check_output(
            ["git", "ls-remote", "--tags", "origin", args.tag, f"{args.tag}^{{}}"],
            cwd=str(ROOT),
            text=True,
        ).strip()
        print(remote)
        if peel not in remote:
            raise SystemExit("remote peel verification failed")
    print(
        "Tags are immutable. Corrections require a new versioned freeze tag. "
        "Never use git tag -f or git push --force for freeze tags."
    )


if __name__ == "__main__":
    main()
