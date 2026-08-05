#!/usr/bin/env python3
"""Validate FGCS manuscript workspace before packaging."""
from __future__ import annotations

import re
import sys
from pathlib import Path

FGCS = Path(__file__).resolve().parents[1]
FORBIDDEN_PHRASES = ["TODO", "TBD", "FIXME", "INSERT HERE", "citation needed", "Materna"]
ALLOWLIST_UNCITED: set[str] = set()
MAX_FILE_MB = 25
INTERNAL_PAGE_LIMIT = 15

# Horizon wording: allow clarifying “not lead time” and “horizontal”
HORIZON_BAD = re.compile(
    r"(?i)\b("
    r"long[- ]horizon|short[- ]horizon|"
    r"performance across forecast horizons|"
    r"\d+-step-ahead result|"
    r"increasing forecast lead|"
    r"samples ahead|minutes ahead"
    r")\b"
)
# Bare “horizon(s)” as forecast lead (not “horizontal”, not “not … lead time” context)
BARE_HORIZON = re.compile(r"(?i)(?<!not )(?<!not evaluated )\bhorizons?\b")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def strip_comments(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("%"))


def main() -> None:
    ms = FGCS / "manuscript.tex"
    bib = FGCS / "references.bib"
    if not ms.exists():
        fail("manuscript.tex missing")
    if not bib.exists():
        fail("references.bib missing")

    text = ms.read_text(encoding="utf-8")
    visible = strip_comments(text)

    for phrase in FORBIDDEN_PHRASES:
        if phrase == "Materna":
            if re.search(r"\bMaterna\b", visible):
                fail("Materna-specific result text in manuscript")
        elif phrase in ("TODO", "TBD", "FIXME"):
            if re.search(rf"\b{phrase}\b", visible):
                fail(f"forbidden placeholder {phrase} in visible manuscript text")
        elif phrase.lower() in visible.lower():
            fail(f"forbidden placeholder phrase in visible manuscript text: {phrase}")

    if "\\begin{highlights}" in text or "\\begin{highlights}" in visible:
        fail("highlights environment must not appear in manuscript.tex (use highlights.txt)")

    # abstract
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
    if not m:
        fail("abstract missing")
    abs_words = len(re.sub(r"\s+", " ", re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", m.group(1))).split())
    if abs_words > 250:
        fail(f"abstract word count {abs_words} > 250")

    # keywords 6–10
    km = re.search(r"\\begin\{keywords\}(.*?)\\end\{keywords\}", text, re.S)
    if not km:
        fail("keywords missing")
    kws = [k.strip() for k in re.split(r"\\sep", km.group(1)) if k.strip()]
    if not (6 <= len(kws) <= 10):
        fail(f"keyword count {len(kws)} not in 6..10")

    # highlights file
    hl = FGCS / "highlights.txt"
    if not hl.exists():
        fail("highlights.txt missing")
    bullets = [ln.strip() for ln in hl.read_text().splitlines() if ln.strip()]
    if not (3 <= len(bullets) <= 5):
        fail(f"highlight count {len(bullets)} not in 3..5")
    for b in bullets:
        if len(b) > 85:
            fail(f"highlight too long ({len(b)}): {b}")

    # forecast semantics
    if HORIZON_BAD.search(visible):
        fail(f"forbidden horizon/lead wording: {HORIZON_BAD.search(visible).group(0)}")
    for match in BARE_HORIZON.finditer(visible):
        start = max(0, match.start() - 40)
        ctx = visible[start : match.end() + 40]
        if re.search(r"(?i)horizontal", ctx):
            continue
        if re.search(r"(?i)(not|rather than).{0,40}lead", ctx) or re.search(
            r"(?i)lead time", ctx
        ):
            # clarifying negation nearby
            continue
        # allow “output-width” discussions that mention historical horizon only in comments already stripped
        fail(f"ambiguous bare 'horizon' in manuscript near: {ctx!r}")

    # inputs / figures
    for inc in re.findall(r"\\input\{([^}]+)\}", text):
        p = FGCS / inc
        if not p.exists() and not (FGCS / f"{inc}.tex").exists():
            fail(f"missing \\input {inc}")
    for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        p = FGCS / fig
        if not p.exists():
            fail(f"missing figure {fig}")

    # citations / bib integrity
    cites: set[str] = set()
    for block in re.findall(r"\\cite[tp]?\{([^}]+)\}", text):
        for k in block.split(","):
            cites.add(k.strip())
    bib_text = bib.read_text(encoding="utf-8")
    keys = re.findall(r"@\w+\{([^,]+),", bib_text)
    if len(keys) != len(set(keys)):
        fail("duplicate bib keys")
    keyset = set(keys)
    dois = re.findall(r"doi\s*=\s*\{([^}]+)\}", bib_text, flags=re.I)
    doi_norm = [d.strip().lower() for d in dois]
    if len(doi_norm) != len(set(doi_norm)):
        fail(
            f"duplicate DOI values: {sorted({d for d in doi_norm if doi_norm.count(d) > 1})}"
        )
    missing = cites - keyset
    if missing:
        fail(f"undefined citations: {sorted(missing)}")
    uncited = keyset - cites - ALLOWLIST_UNCITED
    if uncited:
        fail(f"uncited bibliography entries: {sorted(uncited)}")
    if len(cites) < 20:
        fail(f"cited references {len(cites)} < 20")

    # labels unique
    labels = re.findall(r"\\label\{([^}]+)\}", text)
    if len(labels) != len(set(labels)):
        fail(f"duplicate labels: {sorted({x for x in labels if labels.count(x) > 1})}")

    # declarations presence / author-action awareness
    for heading in [
        "Data Availability",
        "Code and Artifact Availability",
        "CRediT Author Statement",
        "Declaration of Competing Interest",
    ]:
        if heading not in text:
            fail(f"missing declaration heading: {heading}")

    # packaging hygiene
    for p in FGCS.rglob("*"):
        if p.is_symlink():
            fail(f"symlink not allowed: {p}")
        if not p.is_file():
            continue
        if p.suffix.lower() in {".npz", ".pt", ".ckpt", ".h5", ".npz"}:
            fail(f"forbidden artifact: {p}")
        if p.stat().st_size > MAX_FILE_MB * 1024 * 1024:
            fail(f"file too large ({p.stat().st_size}): {p}")
        if p.suffix in {".tex", ".bib"} and "/Users/" in p.read_text(
            encoding="utf-8", errors="ignore"
        ):
            fail(f"absolute local path in {p}")

    # page count
    pdf = FGCS / "manuscript.pdf"
    pages = None
    if pdf.exists():
        try:
            from pypdf import PdfReader

            pages = len(PdfReader(str(pdf)).pages)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: could not read page count: {exc}")
        if pages is not None:
            print(f"page_count={pages}")
            if pages > INTERNAL_PAGE_LIMIT:
                fail(f"page count {pages} > {INTERNAL_PAGE_LIMIT}")
            # highlights must not be first page title
            try:
                from pypdf import PdfReader

                t0 = PdfReader(str(pdf)).pages[0].extract_text() or ""
                if t0.lstrip().startswith("Highlights"):
                    fail("manuscript.pdf still begins with Highlights page")
            except Exception:
                pass

    print(
        f"validate_manuscript: OK abstract_words={abs_words} keywords={len(kws)} "
        f"cites={len(cites)} highlights={len(bullets)} pages={pages}"
    )


if __name__ == "__main__":
    main()
