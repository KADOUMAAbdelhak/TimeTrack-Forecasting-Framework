"""Assemble the condensed FGCS main text and the extended supplement from the full source.

Main: template with %%KEEP a-b%% (verbatim original lines) and [[SUPP:label]] placeholders.
Supplement: the existing flat supplement plus S-A..S-D built from verbatim original line ranges.
References from moved text to labels are resolved with the main/supplement .aux files.
"""
import re
import sys
from pathlib import Path

CUT = Path(__file__).resolve().parent
FULL = (CUT.parent / "full_manuscript.tex").read_text().split("\n")
FULL_SUPP = (CUT.parent / "full_supplement.tex").read_text()
mode = sys.argv[1]            # "main" or "supp"


def lines(a, b):
    return "\n".join(FULL[a - 1:b])


def expand(template):
    return re.sub(r"%%KEEP (\d+)-(\d+)%%", lambda m: lines(int(m.group(1)), int(m.group(2))), template)


def aux_labels(path):
    out = {}
    if Path(path).exists():
        for m in re.finditer(r"\\newlabel\{([^}]*)\}\{\{([^}]*)\}", Path(path).read_text()):
            out[m.group(1)] = m.group(2)
    return out


# Supplement sections built from verbatim original line ranges (title, [(a, b), ...]).
MOVED = [
    ("S-A Extended related work (moved from the main text)", [(188, 412)]),
    ("S-B0 Full formulation text (moved from the main text)", [(470, 623), (650, 657)]),
    ("S-B1 Data, preprocessing and leakage control (moved from the main text)", [(733, 793), (846, 942), (1115, 1150)]),
    ("S-B2 Model architecture, training and selection (moved from the main text)", [(947, 1010)]),
    ("S-B3 Evaluation metrics and consistency classes (moved from the main text)", [(1015, 1113)]),
    ("S-B4 Post-hoc sensitivity procedures (moved from the main text)", [(1155, 1201)]),
    ("S-B5 Tier-2 backbone specifications (moved from the main text)", [(1231, 1273)]),
    ("S-B6 Tier-2 diagnostic definitions (moved from the main text)", [(1312, 1355), (1765, 1774)]),
    ("S-B7 Tier-2 diagnostic statistics (moved from the main text)", [(1829, 1871)]),
    ("S-C1 Tier-1 contextual-input results by block (moved from the main text)", [(1475, 1524)]),
    ("S-C2 Tier-1 sharing results by block and tail attribution (moved from the main text)", [(1549, 1619)]),
    ("S-C4 Joint system, heterogeneity, synthesis, persistence and efficiency (moved from the main text)",
     [(1737, 1760), (1877, 1916), (1921, 1949), (1957, 1959), (1964, 1978), (2005, 2023), (2079, 2120)]),
    ("S-D Full-length discussion and threats to validity (moved from the main text)", [(2122, 2381)]),
    ("S-E Protocol provenance and question mapping (moved from the main text)", [(723, 728), (1275, 1284)]),
]
# Labels whose sections now live only in the supplement: map to the supplement section name.
SUPP_SECTION_OF = {
    "sec:rw-runtime": "S-A", "sec:rw-information-sharing": "S-A", "sec:rw-multitask": "S-A", "sec:rw-gap": "S-A",
    "sec:resource-horizons": "S-B0", "sec:timetrack-data": "S-B1", "sec:bitbrains-data": "S-B1",
    "sec:materna-data": "S-B1", "sec:horizons-contexts": "S-B1",
}


if mode == "main":
    text = expand((CUT / "main_template.tex").read_text())
    supp = aux_labels(sys.argv[2]) if len(sys.argv) > 2 else {}
    text = re.sub(r"\[\[SUPP:([^\]]+)\]\]", lambda m: supp.get(m.group(1), "S??"), text)
    Path(sys.argv[3] if len(sys.argv) > 3 else CUT / "manuscript.tex").write_text(text)
    sys.exit()

# ---- supplement --------------------------------------------------------------------------------
main_aux = aux_labels(sys.argv[2])
moved_blocks = []
for title, ranges in MOVED:
    body = "\n\n".join(lines(a, b) for a, b in ranges)
    moved_blocks.append((title, body))
supp_defined = set(re.findall(r"\\label\{([^}]+)\}", FULL_SUPP + "".join(b for _, b in moved_blocks)))
SECTION_LABELS = {l for l in supp_defined if l.startswith("sec:")}


def resolve(body):
    # Section labels inside moved text would number unnumbered sections: drop them.
    body = re.sub(r"\\label\{sec:[^}]+\}", "", body)
    body = re.sub(r"\\(sub)?(sub)?section\{", lambda m: "\\" + (m.group(1) or "") + (m.group(2) or "") + "section*{", body)

    def rep(m):
        prefix, label = m.group(1) or "", m.group(2)
        if label in supp_defined and label not in SECTION_LABELS:
            return m.group(0)                       # table/equation defined in the supplement
        if label in SUPP_SECTION_OF:
            return f"Supplementary Section~{SUPP_SECTION_OF[label]}"
        if label in main_aux:
            word = prefix.rstrip("~").strip()
            return (f"main-text {word}~{main_aux[label]}" if word else main_aux[label])
        raise SystemExit(f"unresolved reference in moved text: {label}")

    return re.sub(r"((?:Section|Sections|Table|Figure|Equation)~)?\\ref\{([^}]+)\}", rep, body)


def fit_tables(body):
    # Formatting only: moved two-column tables are typeset in footnotesize to fit the single-column page.
    return body.replace("\\begin{table*}[t]", "\\begin{table*}[t]\\let\\small\\footnotesize")


parts = [f"\\clearpage\n\\section*{{{title}}}\n{fit_tables(resolve(body))}\n" for title, body in moved_blocks]
intro = ("\\clearpage\n\\section*{Material moved from the main text}\n"
         "To meet the journal's length limit, the following passages, tables and definitions were moved "
         "verbatim from the main text. Only cross-references were rewritten (``main-text Section~$n$'') and "
         "section headings made unnumbered; no number or claim was changed.\n")
supp = FULL_SUPP
assert supp.count("\\end{document}") == 1
supp = supp.replace("\\usepackage{seqsplit}", "\\usepackage{seqsplit}\n\\usepackage{amsmath,amssymb,array}\n"
                    "\\usepackage[numbers,sort&compress]{natbib}\n\\setlength{\\emergencystretch}{3em}", 1)
supp = supp.replace("\\end{document}", intro + "\n".join(parts)
                    + "\n\\bibliographystyle{elsarticle-num-names}\n\\bibliography{references}\n\\end{document}")
Path(sys.argv[3]).write_text(supp)
