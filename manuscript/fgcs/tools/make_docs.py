"""Write the FGCS submission documents (highlights, biographies, cover letter) as .txt/.docx/.tex."""
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(sys.argv[1])

TITLE = ("Contextual Input versus Representation Sharing in Multi-Metric Runtime Forecasting: "
         "Selective Gains and a Recurring Sharing Cost")

HIGHLIGHTS = [
    "A 2x2 design varies cross-resource input and model sharing one at a time.",
    "Context helps selectively; no context effect holds for every backbone.",
    "Shared models are less accurate in typical cells in 30 of 32 comparisons.",
    "Balancing unequal LSTM task gradients narrows but does not remove that cost.",
    "On 20 Bitbrains VMs, no backbone beats persistence for CPU or throughput.",
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
          "should share one model. These decisions are usually made together. The manuscript separates them with a "
          "2×2 design (independent or shared models, own-resource or all-resource input) and evaluates CPU, "
          "throughput, memory and disk-write forecasting on TimeTrack development data, the Bitbrains fastStorage "
          "and Rnd traces and three dependent Materna temporal blocks. A separately frozen extension repeats the "
          "design for LSTM, DLinear, PatchTST-style and iTransformer-style backbones and adds descriptive mechanism "
          "diagnostics."),
    ("p", "The main findings are that contextual input gives small, selective and model-dependent benefits, whereas "
          "representation sharing carries a small but recurring accuracy cost: in typical cells the shared model was less "
          "accurate in 30 of 32 backbone, resource and environment cells, while larger aggregate penalties came from a few "
          "high-scale machines. We position the design against channel-independent versus channel-dependent forecasting, "
          "which changes input scope and sharing together. In the shared LSTM, task gradients were close to "
          "orthogonal without excess conflict but strongly unequal in magnitude. A separately frozen loss-balancing "
          "amendment then made the shared LSTM slightly more accurate in every resource and environment cell, but "
          "it did not remove the sharing cost. We believe the work fits FGCS's scope on distributed dynamic "
          "resource management, monitoring tools and cloud infrastructures, because it gives practitioners "
          "evidence-based guidance on input selection and model consolidation for multi-resource forecasting."),
    ("p", "The original experiment, the extension and its loss-balancing amendment were each frozen before execution, and later sensitivity "
          "controls are labelled post hoc throughout. The code is public at a tagged commit, and the derived "
          "analysis outputs, including those of the loss-balancing amendment, are deposited on Zenodo "
          "(doi:10.5281/zenodo.24339239 and doi:10.5281/zenodo.24353235); third-party traces remain "
          "available from their original archives. Generative AI use is disclosed in the manuscript as required by "
          "Elsevier's policy."),
    ("p", "[AUTHOR TO CONFIRM BEFORE UPLOAD: This manuscript is not under consideration by any other journal. "
          "State here any previous submission of this work to FGCS or to another journal (including the Journal "
          "of Systems and Software) and its outcome, or delete this paragraph if there is none.]"),
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
       r"\usepackage{newtxtext}", r"\setlength{\parskip}{6pt}\setlength{\parindent}{0pt}", r"\begin{document}"]
for _, text in COVER:
    t = (text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
         .replace("“", "``").replace("”", "''").replace("×", r"$\times$").replace("—", "---"))
    if t.startswith("[AUTHOR TO CONFIRM"):
        t = r"\textbf{" + t + "}"
    tex.append(t + "\n")
tex.append(r"\end{document}")
(OUT / "Cover_Letter.tex").write_text("\n".join(tex) + "\n")
print("highlight lengths:", [len(h) for h in HIGHLIGHTS], "bio words:", [len(b[1].split()) for b in BIOS])
