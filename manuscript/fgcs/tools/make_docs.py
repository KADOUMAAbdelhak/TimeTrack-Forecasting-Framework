"""Write the FGCS submission documents (highlights, biographies, cover letter) as .txt/.docx/.tex."""
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(sys.argv[1])

TITLE = ("Contextual Input versus Representation Sharing in Multi-Metric Runtime Forecasting: "
         "Selective Gains and a Recurring Sharing Cost")

# Amendment-A3 numbers come from the generated macros (manuscript/fgcs/tools/a3_numbers.py), never by hand.
A3 = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}",
                     (Path(__file__).resolve().parents[1] / "latex_source/a3_numbers.tex").read_text()))
GROUP_COST = f"{100 * (float(A3['AiiiGroupMaxRatio']) - 1):.1f}"

HIGHLIGHTS = [
    "A frozen 2×2 design varies cross-resource input and model sharing one at a time.",
    "Context helps selectively; sharing costs accuracy in 54 of 56 typical cells.",
    f"Inner validation shows the sharing cost, so a 1% validation gate rarely shares.",
    f"Validation-chosen LSTM task groups keep {A3['AiiiGroupRetained']}% of the model cut at ≤{GROUP_COST}% typical cost.",
    "LSTM gradients are near orthogonal; loss balancing narrows the cost only slightly.",
]

BIOS = [
    ("Abdelhak Kadouma",
     "Abdelhak Kadouma is a Ph.D. student and software engineer based in Finland. He holds an engineering degree "
     "in computer science and conducts research at the University of Vaasa in collaboration with Fingletek. His "
     "research interests include cloud-native architectures, microservices, application lifecycle management, "
     "knowledge representation and AI-driven automation."),
    ("Amit K. Shukla",
     "Amit K. Shukla is an Associate Professor at the University of Vaasa and is also affiliated with the "
     "Department of Computer Science and Engineering, South Asian University, New Delhi, India. He received his "
     "M.Sc. and Ph.D. in computer science from South Asian University and has prior experience in software "
     "engineering. His research interests include computational intelligence, fuzzy systems, explainable AI, "
     "anomaly detection, transfer learning, machine learning and informetrics."),
    ("Mohammed Elmusrati",
     "Mohammed Elmusrati is a Professor at the University of Vaasa, where he leads research in cyber-physical and "
     "autonomous systems. He holds B.Sc. and M.Sc. degrees in telecommunication engineering and Licentiate and "
     "Doctor of Science degrees in control engineering. His research interests span control, communications, "
     "autonomous systems and related intelligent technologies."),
]

COVER = [
    ("p", "Dear Editors-in-Chief,"),
    ("p", f"We submit the manuscript “{TITLE}” for consideration as a Full Length Article in Future "
          "Generation Computer Systems."),
    ("p", "Engineers who forecast runtime telemetry for cloud resource management must decide two things: whether a "
          "target's forecaster should receive other resources' telemetry, and whether several resource targets "
          "should share one model. Prior comparisons usually change both at once. The manuscript separates them with a "
          "2×2 design (independent or shared models, own-resource or all-resource input) and evaluates CPU, "
          "throughput, memory and disk-write forecasting on the Bitbrains fastStorage and Rnd traces and three "
          "dependent Materna temporal blocks, with TimeTrack as development data. A second, separately frozen part "
          "repeats the design for LSTM, DLinear, PatchTST-style and iTransformer-style backbones and adds "
          "descriptive mechanism diagnostics. A dedicated validation-strategy section maps each threat (leakage, "
          "sample mismatch, selection freedom, capacity, model family, machine sampling, seed variation, scale "
          "dominance and implementation error) to the mechanism that addresses it, and a supplementary table maps "
          "every main claim to its evidence and its limits."),
    ("p", "The main findings are that contextual input gives small, selective and model-dependent benefits, whereas "
          "representation sharing carries a recurring accuracy cost: for a typical machine the shared model was less "
          "accurate in 54 of 56 comparisons across six data blocks and four backbones. We then ask whether this cost "
          "can be managed with data that engineers already have. The inner-validation errors computed during "
          f"ordinary model selection already show it: the shared model was worse on validation in {A3['AiiiValWorseMin']}–"
          f"{A3['AiiiValWorseMax']}% of machine–fold–seed units, and validation and test ratios were rank-correlated "
          f"in {A3['AiiiDetects']} of {A3['AiiiFrames']} settings. A gate that shares only within 1% of the independent "
          f"models' validation error therefore consolidated just {A3['AiiiRetainedOne']}–{A3['AiiiRetainedTwo']}% of "
          "units, whereas letting validation choose which resources share a model kept "
          f"{A3['AiiiGroupRetained']}% of the LSTM's model reduction at a typical-cell cost of at most {GROUP_COST}%. "
          "In the shared LSTM, task gradients were close to orthogonal but strongly unequal in magnitude, and a "
          "loss-balancing intervention narrowed the cost only slightly. Prior comparisons of channel-independent and "
          "channel-dependent forecasting change input scope and sharing together; the design separates them. We "
          "believe the work fits FGCS's scope on distributed dynamic resource management, monitoring tools and cloud "
          "infrastructures, because it gives practitioners a tested way to decide input selection and model "
          "consolidation for multi-resource forecasting."),
    ("p", "The six-block LSTM experiment, the four-backbone experiment and the two amendments (loss balancing, and "
          "validation-gated consolidation on the existing fits) were each frozen before execution, and later "
          "sensitivity controls are labelled post hoc throughout. The code is public at "
          "https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework at tagged commits, including "
          "fgcs-v04-a3-validation-gate-r2, and the derived analysis outputs are deposited on Zenodo "
          "(doi:10.5281/zenodo.24339239, doi:10.5281/zenodo.24353235 and doi:10.5281/zenodo.24458960); third-party "
          "traces remain available from their original archives. Generative AI use is disclosed in the manuscript "
          "as required by Elsevier's policy."),
    ("p", "The manuscript states two limitations openly: on the 20 Bitbrains virtual machines no model beats "
          "persistence for CPU or throughput, even with a validation-selected persistence fallback, and the modern "
          "backbones use fixed, untuned settings. To address the first, we have prepared a follow-up analysis in "
          "which every model forecasts the change from the last observed value, so that each model contains "
          "persistence as a special case. Its protocol, code and decision rule were fixed under the public Git tag "
          "fgcs-v04-a2-residual before any of its fits, and we can report its results during review."),
    ("p", "This manuscript is not under consideration by any other journal."),
    ("p", "All authors have approved the manuscript and agree with its submission. The authors declare no competing "
          "interests, and the research received no specific funding."),
    ("p", "Yours sincerely,"),
    ("p", "Abdelhak Kadouma (corresponding author), on behalf of all authors"),
    ("p", "University of Vaasa, Vaasa, Finland — abdelhak.kadouma@uwasa.fi"),
]


def docx(path, paragraphs):
    """Minimal valid .docx: paragraphs are (style, text) with style 'h' (bold) or 'p'."""
    body = []
    for style, text in paragraphs:
        run = (f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>' if style == "h"
               else f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
        body.append(f"<w:p>{run}</w:p>")
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                + "".join(body) + '<w:sectPr/></w:body></w:document>')
    files = {
        "[Content_Types].xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'),
        "_rels/.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="word/document.xml"/></Relationships>'),
        "word/document.xml": document,
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)


for h in HIGHLIGHTS:
    assert len(h) <= 85, (len(h), h)
assert 3 <= len(HIGHLIGHTS) <= 5
(OUT / "Highlights.txt").write_text("\n".join(f"- {h}" for h in HIGHLIGHTS) + "\n")
docx(OUT / "Highlights.docx", [("h", "Highlights")] + [("p", "• " + h) for h in HIGHLIGHTS])

bio_pars = [("h", "Author biographies"), ("p", TITLE)]
for name, text in BIOS:
    assert len(text.split()) <= 100, name
    bio_pars += [("h", name), ("p", text)]
docx(OUT / "Author_Biographies.docx", bio_pars)

docx(OUT / "Cover_Letter.docx", COVER)
tex = [r"\documentclass[11pt,a4paper]{article}", r"\usepackage[margin=25mm]{geometry}",
       r"\usepackage{newtxtext}", r"\usepackage{url}", r"\setlength{\emergencystretch}{3em}",
       r"\setlength{\parskip}{6pt}\setlength{\parindent}{0pt}",
       r"\begin{document}"]
for _, text in COVER:
    t = (text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
         .replace("“", "``").replace("”", "''").replace("×", r"$\times$").replace("—", "---"))
    t = re.sub(r"(https?://[^\s,;]+)", r"\\url{\1}", t)
    if t.startswith("[AUTHOR TO CONFIRM"):
        t = r"\textbf{" + t + "}"
    tex.append(t + "\n")
tex.append(r"\end{document}")
(OUT / "Cover_Letter.tex").write_text("\n".join(tex) + "\n")
print("highlight lengths:", [len(h) for h in HIGHLIGHTS], "bio words:", [len(b[1].split()) for b in BIOS])
