#!/usr/bin/env python3
"""Validate FGCS manuscript workspace before packaging."""
from __future__ import annotations

import re
import sys
from pathlib import Path

FGCS = Path(__file__).resolve().parents[1]
FORBIDDEN = ["TODO", "TBD", "FIXME", "INSERT", "citation needed"]
# Allow XX only outside hex-ish contexts; keep simple phrase bans for visible text
FORBIDDEN_PHRASES = ["TODO", "TBD", "FIXME", "INSERT HERE", "citation needed", "Materna"]
ALLOWLIST_UNCITED = set()  # none by default
MAX_FILE_MB = 25


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    ms = FGCS / "manuscript.tex"
    bib = FGCS / "references.bib"
    if not ms.exists():
        fail("manuscript.tex missing")
    if not bib.exists():
        fail("references.bib missing")

    text = ms.read_text(encoding="utf-8")
    # strip comments for visible checks
    visible = "\n".join(
        ln for ln in text.splitlines() if not ln.strip().startswith("%")
    )
    if re.search(r"\bTODO\b", visible) or re.search(r"\bTBD\b", visible) or re.search(r"\bFIXME\b", visible):
        fail("forbidden placeholder in visible manuscript text")
    if "INSERT HERE" in visible.upper() or "citation needed" in visible.lower():
        fail("forbidden placeholder phrase in visible manuscript text")
    if re.search(r"\bMaterna\b", visible):
        fail("Materna-specific result text in manuscript")

    # abstract word count
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
    if not m:
        fail("abstract missing")
    abs_words = len(re.sub(r"\s+", " ", m.group(1)).split())
    if abs_words > 250:
        fail(f"abstract word count {abs_words} > 250")

    # highlights
    hl = FGCS / "highlights.txt"
    if not hl.exists():
        fail("highlights.txt missing")
    bullets = [ln.strip() for ln in hl.read_text().splitlines() if ln.strip()]
    if not (3 <= len(bullets) <= 5):
        fail(f"highlight count {len(bullets)} not in 3..5")
    for b in bullets:
        if len(b) > 85:
            fail(f"highlight too long ({len(b)}): {b}")

    # inputs / figures
    for inc in re.findall(r"\\input\{([^}]+)\}", text):
        p = FGCS / inc
        if not p.exists() and not (FGCS / f"{inc}.tex").exists():
            fail(f"missing \\input {inc}")
    for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        p = FGCS / fig
        if not p.exists():
            fail(f"missing figure {fig}")

    # citations
    cites = set()
    for block in re.findall(r"\\cite[tp]?\{([^}]+)\}", text):
        for k in block.split(","):
            cites.add(k.strip())
    keys = set(re.findall(r"@\w+\{([^,]+),", bib.read_text(encoding="utf-8")))
    if len(keys) != len(set(keys)):
        fail("duplicate bib keys")
    # duplicate DOI
    dois = re.findall(r"doi\s*=\s*\{([^}]+)\}", bib.read_text(), flags=re.I)
    doi_norm = [d.strip().lower() for d in dois]
    if len(doi_norm) != len(set(doi_norm)):
        fail(f"duplicate DOI values: {sorted({d for d in doi_norm if doi_norm.count(d)>1})}")
    missing = cites - keys
    if missing:
        fail(f"undefined citations: {sorted(missing)}")
    uncited = keys - cites - ALLOWLIST_UNCITED
    # allow a few intentionally retained? require all cited
    if uncited:
        print(f"WARN: uncited bibliography entries: {sorted(uncited)}")
        # soft-fail for packaging gate? user asked no uncited unless allowlisted
        fail(f"uncited bibliography entries: {sorted(uncited)}")
    if len(cites) < 20:
        fail(f"cited references {len(cites)} < 20")

    # symlinks / large files / npz
    for p in FGCS.rglob("*"):
        if p.is_symlink():
            fail(f"symlink not allowed: {p}")
        if p.is_file():
            if p.suffix.lower() in {".npz", ".pt", ".ckpt", ".h5"}:
                fail(f"forbidden artifact: {p}")
            if p.stat().st_size > MAX_FILE_MB * 1024 * 1024:
                fail(f"file too large ({p.stat().st_size}): {p}")
            if "/Users/" in p.read_text(encoding="utf-8", errors="ignore") and p.suffix in {
                ".tex",
                ".bib",
                ".md",
                ".sh",
                ".py",
            }:
                # Overleaf package docs may mention absolute local path in BUILD.md; README should be relative
                if p.name not in {"BUILD.md", "CLEANUP_REPORT.md", "validate_manuscript.py", "prepare_manuscript_assets.py", "package_overleaf.sh", "verify_overleaf_package.sh", "build_manuscript.sh"}:
                    if "manuscript.tex" == p.name or p.suffix == ".tex":
                        fail(f"absolute path in {p}")

    # page count if PDF exists
    pdf = FGCS / "manuscript.pdf"
    if pdf.exists():
        pages = None
        try:
            import subprocess

            out = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
            m = re.search(r"Pages:\s+(\d+)", out)
            if m:
                pages = int(m.group(1))
        except Exception:
            try:
                from pypdf import PdfReader

                pages = len(PdfReader(str(pdf)).pages)
            except Exception as exc:  # noqa: BLE001
                print(f"WARN: could not read page count: {exc}")
        if pages is not None:
            print(f"page_count={pages}")
            if pages > 15:
                fail(f"page count {pages} > 15")

    print(
        f"validate_manuscript: OK abstract_words={abs_words} cites={len(cites)} highlights={len(bullets)}"
    )


if __name__ == "__main__":
    main()
