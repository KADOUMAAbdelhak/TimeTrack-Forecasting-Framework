"""Compose requested evidence report, without changing any input or manuscript."""
from pathlib import Path
import json,csv
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
a=json.loads((OUT/'analysis.json').read_text());p=json.loads((OUT/'preservation.json').read_text())
assert a['classification']=='BROAD_DEGRADATION' and p['status']=='PASS'
def records(name):
    with (OUT/name).open(newline='') as s:return list(csv.DictReader(s))
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(str,r))+' |' for r in rows]])
def num(v,n=6):return f'{float(v):.{n}f}'
def link(name):return f'[{name}]({OUT/name})'
m=a['timetrack_memory'];cap=a['capacity_exact']
sections=['''# STAGE 19G1 — Final evidence surfacing report

**Status: STAGE_19G1_PASS.** Existing-artifact evidence only. No training,
model inference, manuscript edit, frozen/post-hoc result edit or new experiment.
All new attribution summaries are **POST-HOC DIAGNOSTICS**, not replacements
for frozen MacroMAE gains or prospective consistency classifications.

Repository: `/Users/fgtek002/TimeTrack`; branch `paper/jss-review-revision`;
HEAD `f6936cd111d911e40ec2725a18fdfc53768d9ccf`.

## 1. Estimands and traceability

Materna repeats the Stage 18A1 estimand: for each VM, average the existing
seed-mean MAEs equally across five outer folds and five forecast leads.
TimeTrack uses the analogous original M1:S2 matched errors, with three seed
MAEs averaged first and eight leads weighted equally. Machine/fold summaries
average those lead errors; machine summaries average five folds and fold
summaries seven machines. No pooling of predictions, native errors across
resources, or blocks is introduced.

For any stated aggregation unit, excess is M1 MAE minus S2 MAE. Net excess is
the sum of these unit-level differences; positive excess is the sum of their
positive parts. Contributor percentages divide the stated unit's excess by
that same aggregation level's net or positive total. Taking positive parts
after aggregation is not interchangeable with taking them at a finer level.
The tables explicitly identify the level. These diagnostics neither reweight
the frozen endpoint nor remove an adverse machine/VM.

The 24-cell table projects Stage 18C1's **seed-mean entity×fold×lead** robust
table verbatim, not its separate seed-matched panel. Win fractions are merely
expressed as percentages. The 48-row seed table copies the existing gains,
range and population SD (`ddof=0`) without recalculating or rounding them.
Stable/FLIP uses the existing strict-positive-and-negative-seed definition,
not an effect-size cutoff. All source decimal strings survive CSV round-trip
checks. Overlapping folds/leads, three fixed seeds and dependent Materna
blocks are not IID replicates.

Inputs: Stage 18A1 diagnostic report; Stage 18C1 synthesis, matched errors,
robust and seed tables; original frozen metrics, contexts, registries,
completion/scaler/support records, saved predictions and checkpoints; completed
H129 results. `input_sha256_inventory.json` records every directly read source.
`surface_evidence.py` and `verify_materna_saved.py` implement only descriptive
arithmetic and static artifact checks. No model is instantiated or called.

## 2. Materna T1/T3 disk attribution — re-verified
''']
rows=[]
for block,s in a['materna'].items():
    rows.append([block,s['worse'],s['better'],s['ties'],num(s['median_ratio']),
        s['largest']['units'][0]['vm_id'],num(s['largest']['share_positive_percent'],2)+'%',
        ', '.join(v['vm_id'] for v in s['top3']['units']),num(s['top3']['share_positive_percent'],2)+'%'])
sections.append(table(['Block','M1 worse VMs','M1 better VMs','Ties','Median VM M1/S2','Largest VM','Largest / positive excess','Top-3 VMs','Top-3 / positive excess'],rows))
sections.append('''
All **70 per-VM S2/M1 MAEs, ratios and excesses** reproduce Stage 18A1
Appendix E to every displayed six-decimal digit. The original 28/7 and 32/3
counts, VM266/VM272 concentration and 82.10/91.72% and 86.97/92.93% contributor
shares agree. See Appendix A below for every VM, including leading-zero IDs.
No different estimand or leave-one-VM-out endpoint is substituted.

**Fitting diagnosis remains NO_TRAINING_FAILURE_VISIBLE for both traces.**
Freshly inspected all 2,100 relevant original S2-disk/M1 final checkpoints and
prediction files across T1/T3: registry/completion hashes match, weights and
saved disk targets/predictions are finite, parameter counts are correct,
paired target/support signatures agree, saved log1p inverse/expm1/projection
maps reproduce exactly, and saved prediction MAEs reproduce stored metrics.
One final test evaluation is recorded per valid fit; none was newly executed.
All selected final scaler vectors match the frozen training-partition manifest
exactly (259 distinct selected partitions in T1 and 252 in T3). Existing
technical validations remain PASS with zero recorded violations. Their scope
is technical conformance, not proof of ideal predictive quality.

Stage 18A1's raw-archive reconstruction of all **3,150 inner/final scaler
partitions** is reused with unchanged source/artifact hashes; that entire raw
reconstruction was not rerun in this stage. Its conclusion about positive,
non-singular scales and the large dominant-VM disk IQRs remains applicable.
The fresh final-scaler checks above are against that frozen partition manifest,
not falsely described as a new 3,150-partition raw reconstruction.

VM266's M1 selected epochs remain 26–50; VM272's 40–50. M1 logs contain finite
joint losses. VM266 is context-matched at L18 in all five folds. VM272 is
matched in folds 1 and 4 and mismatched in 2,3,5; its largest fold excess is
the matched fold 1. The preserved T1 failed attempt is S1 CPU/VM74/fold1/seed0
(`KeyError: support_hash`), not an M1 disk fitting failure; it has not been
erased or reused. T3 has no saved failure record. S1/S2 detailed epoch-loss
histories and gradient/clipping diagnostics remain incomplete. Finite artifacts
do not establish optimisation optimality or identify a transfer mechanism.

Interpretation is unchanged: adverse direction is widespread, but the large
absolute-error magnitude is concentrated. The per-VM medians above differ
legitimately from the Stage 18C1 **entity×fold×lead** disk medians
1.024565/1.034743; they aggregate at different levels.

## 3. TimeTrack memory attribution — original M1:S2

**Descriptive classification: BROAD_DEGRADATION, with nonuniform magnitude.**
This is not an added frozen consistency rule or a numerical concentration
threshold. All seven machine averages worsen, as do 31/35 machine/fold pairs
and 239/280 seed-mean machine/fold/lead cells. One machine contributes a large
share of magnitude, but the direction is not an isolated-outlier failure.
''')
sections.append(table(['Aggregation level','M1 worse','M1 better','Ties','Median M1/S2 ratio'],[
    [label,m[k]['worse'],m[k]['better'],m[k]['ties'],num(m[k]['median_ratio'],9)]
    for k,label in [('machine','Machine (7)'),('fold','Fold (5)'),('machine_fold','Machine/fold (35)'),('entity_fold_lead','Machine/fold/lead (280)')]]))
attrib=records('timetrack_memory_attribution.csv')
sections.append('\nPer-machine and per-fold native-memory MAEs below retain original units; no unit conversion is applied.\n')
sections.append(table(['Scope / identity','S2 MAE','M1 MAE','M1/S2','Excess MAE'],[
    [r['scope']+' / '+(r['machine'] if r['scope']=='machine' else r['fold']),num(r['S2_MAE']),num(r['M1_MAE']),num(r['M1_S2_ratio']),num(r['excess_MAE'])]
    for r in attrib if r['scope']!='machine_fold']))
sections.append('\n'+link('timetrack_memory_attribution.csv')+' contains all **47 rows**: 35 machine/fold pairs, 7 machine averages and 5 fold averages, including context-match status for each pair.\n')
sections.append(table(['Level','Positive excess sum','Net excess sum','Largest unit','Largest / positive','Largest / net','Top-3 units','Top-3 / positive','Top-3 / net'],[
    [label,num(m[k]['positive_excess_sum']),num(m[k]['net_excess_sum']),
     '; '.join('/'.join(str(x) for x in v.values()) for v in m[k]['largest']['units']),
     num(m[k]['largest']['share_positive_percent'],4)+'%',num(m[k]['largest']['share_net_percent'],4)+'%',
     '; '.join('/'.join(str(x) for x in v.values()) for v in m[k]['top3']['units']),
     num(m[k]['top3']['share_positive_percent'],4)+'%',num(m[k]['top3']['share_net_percent'],4)+'%']
    for k,label in [('machine','Machine'),('machine_fold','Machine/fold')]]))
sections.append('''
At machine/fold level, the largest excess is machine01/fold2:
S2=446438210.31378144, M1=926941614.6238251, ratio=2.0763043870557567,
excess=480503404.31004363. Next are machine01/fold3 and machine03/fold5.
The largest three supply 51.0590% of positive and 55.1696% of net excess.
Machine01 alone supplies 50.6329% of positive/net **per-machine** excess;
machine01, machine03 and machine02 supply 80.4181% together. These statements
describe different levels and must not be conflated.

The top three machine/fold contexts (S2/M1) are 128/64, 32/64 and 64/32:
all mismatched. There are 17 mismatches across 35 pairs. However, the next
two largest pairs, machine01/fold4 and machine03/fold3, both match at 128/128
and still have substantial positive excess. Mismatch is not demonstrated as a
cause or a necessary condition. Common-context S2 is a separate already
completed sensitivity control, not a reason to replace these frozen errors.

**Fresh static checks:** all **210** original S2-memory/M1 final checkpoints
and prediction files checked; finite weights/targets/native/scaled predictions;
correct 51,720/53,280 parameter counts; file hashes agree with registries and
completions; exact matched target/support IDs; correct target timestamps and
float32 canonical native targets; saved prediction MAEs agree with all
**1,680** original memory metric rows. Memory is identity-transformed, not
log-transformed: float64 affine inverse maps reproduce saved native predictions
exactly, with no log-resource projection applied to memory. All **52 distinct
selected final memory scaler partitions** were independently reconstructed by
quantiles of the original legal outer-training history/target row union and
match stored centres/IQRs exactly. Target-time purging and test-origin hashes
pass. The canonical panel SHA matches the frozen anchor. No model forward
pass, new checkpoint, selection or test evaluation occurred.

Existing full TimeTrack validation remains PASS with zero structural
violations/failures. These checks demonstrate no current implementation defect;
they do not measure gradient conflict, make optimisation ideal, or uniquely
attribute the loss to representation sharing. The diagnosis is broader than
the concentrated Ridge-throughput outlier and must not inherit that outlier's
classification.

## 4. Exact Table A TimeTrack memory check
''')
sections.append(table(['Quantity','Exact authoritative value'],[
    ['Original S2 MacroMAE',cap['S2_MacroMAE']],['Original H64 M1 MacroMAE',cap['M1_H64_MacroMAE']],
    ['H129 M1 MacroMAE',cap['M1_H129_MacroMAE']],['Original H64 M1:S2 gain %',cap['original_H64_vs_S2_gain_percent']],
    ['H129 M1:S2 gain %',cap['H129_vs_S2_gain_percent']],['Existing H129:H64 gain %',cap['H129_vs_H64_gain_percent']]]))
sections.append('''
**Both gains legitimately round to −18.48% at two decimals. They are not
identical results.** H129 has slightly higher MAE. The original H64 value
cross-checks to the frozen comparison row; the H129 value is copied from
`m1_capacity_matched/posthoc_results.csv`. The manuscript post-hoc Table A's
original/common/H129 memory values are correctly distinguished. No figure,
table source or result was changed.

## 5. Reviewer-facing robust and seed tables
''')
sections.append('- '+link('m1_s2_robustness_24.csv')+': **24 unique block/resource rows**, original M1:S2 gain, median candidate/reference MAE ratio, win percent and ties. All ratios exceed 1, win percentages are below 50, ties=0.\n\n- '+link('seed_sensitivity_48.csv')+': **48 unique rows**, 24 S2:S1 and 24 M1:S2. Seed0/1/2 gains, range in percentage points, population SD in percentage points and stable/FLIP. S2 has 15 stable/9 FLIP summaries; M1 has 20 stable/4 FLIP summaries. No interval, significance test, new seed or effect-size cutoff added.\n')
sections.append('''
Exact CSV values, not the report's display rounding, should populate later
manuscript/supplement tables. Gain is positive when the candidate has lower
MacroMAE. Ratios greater than one favour the reference. Win percentages count
strictly lower candidate MAE; exact ties remain separate. The seed table
preserves SD `ddof=0` and must not be relabelled standard error or confidence.
The three-seed summary does not independently validate a temporal regime.

## 6. RQ4 wording audit — recommendations only

The stored seven classification changes and five raw sign reversals across
12 resource/comparison pairs were verified against the frozen temporal table.
The frozen rule/outcome remains unchanged. Several relevant small point signs
vary across seeds (e.g. S2 throughput in T1/T2/T3, T1 S2 memory, and T1 M1 CPU).
This supports bounded wording, not declaring the prespecified criterion invalid.
Not all seven class changes are near-zero sign changes: M1:S1 throughput
changes class while its points remain negative. No seed-specific RQ4 rerun was
performed; the supplied seed table covers S2:S1 and M1:S2, not M1:S1.

The current surrounding paragraph already calls the outcome frozen and rejects
causal mechanisms/post-hoc regimes. The isolated word “confirmed” can still be
read as stronger seed-stable/inferential confirmation than demonstrated. This
is the essential minimal wording change, not a numerical correction:
''')
for i,w in enumerate(a['rq4_wording_audit'],1):
    sections.append(f'\n### {i}. Manuscript lines {w["line_start"]}–{w["line_end"]}\n\n{w["scope"]}\n\nCurrent exact source:\n\n```latex\n{w["current_exact"]}\n```\n\nRecommended:\n\n```latex\n{w["recommended"]}\n```\n')
sections.append('''
If one further short qualifier is useful, follow the retained rule/counts with:
“This rule-based result concerns the frozen classifications and trace decisions;
it does not establish seed-stable temporal regimes.” Keep seven/12, five sign
changes, trace decisions and their frozen definitions intact. The two optional
edits above qualify point-estimate language rather than alleging false counts.
No manuscript change has been made.

## 7. Verification and bounded disposition

- All requested outputs exist and their fields round-trip exactly. Robust and
  seed tables are projections, not recomputed alternative estimands.
- Materna per-VM attribution reproduces Stage 18A1. Fresh saved-artifact checks
  cover 2,100 S2-disk/M1 final fits; TimeTrack checks cover 210 S2-memory/M1 fits.
  **Training=0; model inference=0.** Loading weights-only tensors and checking
  saved prediction arithmetic is not model execution.
- Full protected-tree audit: **395,786 files unchanged**, including manuscript,
  frozen outputs, completed post-hoc controls and predecessors, plus all
  **25 Stage 18C1 output hashes**. Earlier authorised manuscript revisions are
  matched to their existing hashes, not overwritten. Branch/HEAD/scientific
  refs unchanged; no staged changes; `git diff --check` passes. Directly read
  inputs are additionally rehashed at final handoff.
- The spreadsheet workflow informed flat records, explicit units/denominators,
  exact decimal preservation and CSV round-trip checks. The writing guidance
  informed a status-led, bounded interpretation. No extra workbook, submission
  package or manuscript revision was created.

**Implementation defect demonstrated: NO. Further experiment required: NO.**
No evidence supports outcome-driven refitting/reselection of the adverse cells.
Residual limitations are the original fixed cohort/design, only three seeds,
dependent temporal blocks, finite artifacts that cannot prove optimiser
optimality, and absence of complete gradient/clipping diagnostics. Context and
capacity controls remain separate, incomplete causal controls. This audit
does not resolve the metadata/declaration/package blocks found in Stage 19F2A.

Manuscript modifications=0; frozen/post-hoc/scientific modifications=0;
commit=no; push=no.

## Appendix A. All Materna T1/T3 disk per-VM errors

Existing Stage 18A1 estimand, reproduced at its six-decimal display precision.
Native MAE/excess units KB/s; ratios dimensionless; VM identifiers are text.
''')
sections.append(table(['Block','VM','S2 MAE','M1 MAE','M1/S2','Excess MAE'],[
    [r['block'],r['vm'],num(r['S2_MAE']),num(r['M1_MAE']),num(r['ratio']),num(r['excess'])] for r in a['materna_per_vm']]))
sections.append('\nSTAGE_19G1_PASS\n')
(OUT/'STAGE19G1_EVIDENCE_SURFACING_REPORT.md').write_text('\n'.join(sections))
print('REPORT_WRITTEN')
