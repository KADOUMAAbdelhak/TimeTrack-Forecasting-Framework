#!/usr/bin/env python3
"""Build a flat Editorial Manager LaTeX package (no subdirectories)."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

FGCS = Path(__file__).resolve().parents[1]
OUT = FGCS / "dist" / "editorial_manager"
STAGE = OUT / "_flat_stage"
ZIP_PATH = OUT / "timetrack_fgcs_em_flat.zip"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rewrite_tex(text: str) -> str:
    text = re.sub(
        r"\\includegraphics(\[[^\]]*\])?\{figs/([^}]+)\}",
        r"\\includegraphics\1{\2}",
        text,
    )
    text = re.sub(r"\\input\{tables/([^}]+)\}", r"\\input{\1}", text)
    text = re.sub(
        r"\\begin\{highlights\}.*?\\end\{highlights\}\s*", "", text, flags=re.S
    )
    return text


def main() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    OUT.mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True)

    ms = rewrite_tex((FGCS / "manuscript.tex").read_text(encoding="utf-8"))
    (STAGE / "manuscript.tex").write_text(ms, encoding="utf-8")

    for name in [
        "references.bib",
        "cas-dc.cls",
        "cas-common.sty",
        "cas-model2-names.bst",
        "highlights.txt",
    ]:
        src = FGCS / name
        if src.exists():
            shutil.copy2(src, STAGE / Path(name).name)

    # Flatten CAS social icons (class expects thumbnails/…; EM ZIP forbids subdirs)
    thumb_dir = FGCS / "thumbnails"
    sty_path = STAGE / "cas-common.sty"
    sty = sty_path.read_text(encoding="utf-8")
    for thumb in thumb_dir.glob("cas-*.jpeg"):
        shutil.copy2(thumb, STAGE / thumb.name)
        sty = sty.replace(f"thumbnails/{thumb.name}", thumb.name)
    sty_path.write_text(sty, encoding="utf-8")

    # figures referenced after rewrite (basename only)
    for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", ms):
        src = FGCS / "figs" / fig
        if not src.exists():
            src = FGCS / fig
        if not src.exists():
            raise SystemExit(f"missing figure for flat package: {fig}")
        dest = STAGE / Path(fig).name
        if dest.exists() and dest.resolve() != src.resolve():
            raise SystemExit(f"figure name collision: {dest.name}")
        shutil.copy2(src, dest)

    for inc in re.findall(r"\\input\{([^}]+)\}", ms):
        stem = Path(inc).name
        candidates = [
            FGCS / "tables" / f"{stem}.tex",
            FGCS / "tables" / stem,
            FGCS / f"{stem}.tex",
            FGCS / stem,
        ]
        src = next((c for c in candidates if c.exists()), None)
        if src is None:
            raise SystemExit(f"missing table input: {inc}")
        dest = STAGE / (stem if stem.endswith(".tex") else f"{stem}.tex")
        shutil.copy2(src, dest)

    # compile staging sources
    subprocess.run(
        [
            "bash",
            "-lc",
            "tectonic -X compile --keep-logs --keep-intermediates manuscript.tex",
        ],
        cwd=STAGE,
        check=True,
    )
    pdf = STAGE / "manuscript.pdf"
    if not pdf.exists():
        raise SystemExit("flat stage manuscript.pdf missing")

    shutil.copy2(pdf, OUT / "manuscript.pdf")
    shutil.copy2(FGCS / "highlights.txt", OUT / "highlights.txt")

    supp_script = FGCS / "scripts" / "build_supplementary.sh"
    supp_pdf = FGCS / "supplementary" / "supplementary_material.pdf"
    if not supp_pdf.exists():
        subprocess.run(["bash", str(supp_script)], check=True)
    shutil.copy2(supp_pdf, OUT / "supplementary_material.pdf")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    include_ext = {
        ".tex",
        ".bib",
        ".bbl",
        ".bst",
        ".cls",
        ".sty",
        ".pdf",
        ".txt",
        ".jpeg",
        ".jpg",
        ".png",
    }
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(STAGE.iterdir()):
            if not p.is_file():
                continue
            if p.suffix.lower() not in include_ext:
                continue
            if p.name == "manuscript.pdf":
                continue  # PDF uploaded separately
            zf.write(p, arcname=p.name)

    files = zipfile.ZipFile(ZIP_PATH).namelist()
    if any("/" in f or "\\" in f for f in files):
        raise SystemExit("flat ZIP contains subdirectories")

    inventory_lines = []
    sums = []
    for p in sorted(OUT.iterdir()):
        if p.is_file():
            digest = sha256(p)
            inventory_lines.append(f"{p.name}\t{p.stat().st_size}\t{digest}")
            sums.append(f"{digest}  {p.name}")
    (OUT / "inventory.txt").write_text("\n".join(inventory_lines) + "\n", encoding="utf-8")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    from pypdf import PdfReader

    pages = len(PdfReader(str(OUT / "manuscript.pdf")).pages)
    print("==== EM FLAT PACKAGE ====")
    print(f"zip={ZIP_PATH}")
    print(f"sha256={sha256(ZIP_PATH)}")
    print(f"bytes={ZIP_PATH.stat().st_size}")
    print(f"file_count={len(files)}")
    print(f"manuscript_pages={pages}")
    print("files=" + ",".join(files))
    print("PACKAGE OK")


if __name__ == "__main__":
    main()
