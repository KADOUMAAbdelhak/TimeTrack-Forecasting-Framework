"""Format existing CSV decimal strings only; emit a LaTeX source patch."""
from pathlib import Path
import csv
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'review_revision/stage19g1_evidence'
def rows(name):
    with (INPUT / name).open(newline='') as stream:
        return list(csv.DictReader(stream))

robust = rows('m1_s2_robustness_24.csv')
seeds = rows('seed_sensitivity_48.csv')
assert len(robust) == 24 and len(seeds) == 48
names = dict(CPU='CPU', THROUGHPUT='Throughput', MEMORY='Memory', DISK_WRITE='Disk write')
def identity(row):
    return row['block'] + ' / ' + names[row['resource']]
def number(value):
    display = format(Decimal(value), '.6f')
    return r'\evidencevalue{' + value + '}{' + display + '}'

source = r'''\documentclass[a4paper,11pt]{article}
\usepackage[margin=20mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{stix}
\usepackage{booktabs,longtable}
\usepackage[hidelinks]{hyperref}
% The first argument preserves the source decimal; the second is display rounding.
\newcommand{\evidencevalue}[2]{#2}
\renewcommand{\thetable}{S\arabic{table}}
\setlength{\LTcapwidth}{\textwidth}
\setlength{\tabcolsep}{4pt}
\begin{document}
\begin{center}
{\Large Supplementary evidence}\par\medskip
Evaluating Contextual Input and Shared Representation in Multi-Metric
Runtime Forecasting for Cloud Software Systems
\end{center}

These post-hoc diagnostic tables accompany the original frozen experiment;
they do not replace its primary estimates or prespecified classifications.
All numeric inputs retain the existing result-file decimal strings in the
LaTeX source; values are rounded to at most six decimal places for display.
Positive gain means lower candidate MacroMAE. No additional fits, seeds,
intervals or significance tests are introduced.

\section*{Original sharing comparison: matched-cell robustness}
In Table~\ref{tab:supp-m1-robustness}, the candidate is M1 and reference S2.
A matched cell is entity $\times$ outer fold $\times$ forecast lead, with
MAE first averaged over the three existing seeds. The median uses these
cell-level MAE ratios, whereas the frozen gain uses MacroMAEs. M1 win
percentage counts strictly lower cell MAE; exact ties are counted separately.
All 24 median ratios exceed one and all M1 win percentages are below 50\%.
Dependent temporal blocks, overlapping folds/leads and existing seeds are
not IID replicates. These diagnostics describe direction and typical-cell
magnitude, not an inferential test or a new effect-size threshold.

\small
\begin{longtable}{@{}lrrrr@{}}
\caption{Post-hoc matched-cell robustness of the original frozen M1:S2 comparison.}
\label{tab:supp-m1-robustness}\\
\toprule
Block / resource & \shortstack{Frozen gain\\(\%)} & \shortstack{Median\\M1/S2 MAE} & \shortstack{M1 win\\(\%)} & Ties \\
\midrule
\endfirsthead
\multicolumn{5}{l}{Table~\thetable\ (continued)}\\
\toprule
Block / resource & \shortstack{Frozen gain\\(\%)} & \shortstack{Median\\M1/S2 MAE} & \shortstack{M1 win\\(\%)} & Ties \\
\midrule
\endhead
\midrule\multicolumn{5}{r}{Continued on next page}\\
\endfoot
\bottomrule
\endlastfoot
'''
for index, row in enumerate(robust):
    if index and index % 4 == 0:
        source += '\\addlinespace\n'
    values = [identity(row)] + [number(row[key]) for key in
        ['frozen_MacroMAE_gain_percent', 'median_candidate_reference_MAE_ratio',
         'candidate_win_percent']] + [row['ties']]
    source += ' & '.join(values) + r' \\' + '\n'
source += r'''\end{longtable}
\normalsize
\clearpage
\section*{Existing-seed sensitivity}
Table~\ref{tab:supp-seed-sensitivity} retains the existing seed-specific
MacroMAE gains and their stored range and population standard deviation
(SD, divisor three), expressed in percentage points (pp). Neither range nor
SD is a confidence interval or standard error. FLIP denotes both strictly
positive and strictly negative seed gains; stable denotes no such sign flip,
not demonstrated reproducibility under arbitrary retraining. There are 9/24
FLIP summaries for S2:S1 and 4/24 for M1:S2. No meaningfulness threshold is
imposed on small effects. Materna T1--T3 are dependent temporal blocks.

\small
\begin{longtable}{@{}lrrrrrl@{}}
\caption{Post-hoc sensitivity across the three existing neural seeds.
Panel A: S2:S1; Panel B: M1:S2.}
\label{tab:supp-seed-sensitivity}\\
\toprule
Block / resource & \shortstack{Seed 0\\gain (\%)} & \shortstack{Seed 1\\gain (\%)} & \shortstack{Seed 2\\gain (\%)} & \shortstack{Range\\(pp)} & \shortstack{SD\\(pp)} & Status \\
\midrule
\endfirsthead
\multicolumn{7}{l}{Table~\thetable\ (continued)}\\
\toprule
Block / resource & \shortstack{Seed 0\\gain (\%)} & \shortstack{Seed 1\\gain (\%)} & \shortstack{Seed 2\\gain (\%)} & \shortstack{Range\\(pp)} & \shortstack{SD\\(pp)} & Status \\
\midrule
\endhead
\midrule\multicolumn{7}{r}{Continued on next page}\\
\endfoot
\bottomrule
\endlastfoot
'''
for comparison, panel in [('S2_vs_S1', 'A: S2:S1'), ('M1_vs_S2', 'B: M1:S2')]:
    if comparison == 'M1_vs_S2':
        source += '\\pagebreak[4]\n'
    source += r'\multicolumn{7}{l}{\textbf{Panel ' + panel + r'}}\\*' + '\n'
    selected = [row for row in seeds if row['comparison'] == comparison]
    assert len(selected) == 24
    for index, row in enumerate(selected):
        if index and index % 4 == 0:
            source += '\\addlinespace\n'
        values = [identity(row)] + [number(row[key]) for key in
            ['seed0_gain_percent', 'seed1_gain_percent', 'seed2_gain_percent',
             'range_percentage_points', 'population_SD_percentage_points']] + [row['status']]
        source += ' & '.join(values) + r' \\' + '\n'
source += '\\end{longtable}\n\\normalsize\n\\end{document}\n'
print('*** Begin Patch')
target = ROOT / 'manuscript/jss/supplementary/final_evidence_supplement.tex'
if target.exists():
    print('*** Update File: ' + str(target))
    print('@@')
    print('\n'.join('-' + line for line in target.read_text().splitlines()))
else:
    print('*** Add File: ' + str(target))
print('\n'.join('+' + line for line in source.splitlines()))
print('*** End Patch')
