# Stage 6 literature and novelty audit

Audit date: 16 October 2026. Internal manuscript-development record only.
Scientific checkpoint: `fee20c316040c57b69ba12a193530c955b539771`.
Manuscript title: *Disentangling Information Sharing in Multi-Metric Runtime Forecasting for Cloud Software Systems*.

## Decision and outstanding evidence

**Current Stage 6B verdict, 16 October 2026: STAGE_6_PASS for the bounded three-paper full-text gate.** User-supplied PDFs were verified and read completely: Ullah 22 pages, Di Menna 17, MMRP 23. No complete reported S1/S2/M1 decomposition with both bridges was found. **MMRP contains related univariate/multivariate single-target comparisons**; the contribution is not first contextual forecasting or first S1–S2 comparison. The complete page/section/table evidence, genuine reporting uncertainties and qualified decisions are in [closest_papers_fulltext_clearance.md](closest_papers_fulltext_clearance.md). The current matrix and Claims C–G below supersede the earlier abstract-only uncertainties. No drafting stage is authorised or begun by this clearance.

### Historical access decision — superseded by user PDFs

The following three paragraphs preserve the earlier limitation, not the current verdict.

**STAGE_6_BLOCKED** for final novelty clearance. The bibliography can be used as a verified candidate library, but the absence of an equivalent S1/S2/M1 experiment has **not** been established. No directly equivalent cloud-resource decomposition was identified in the accessible methods inspected. That is a bounded search finding, not a priority claim.

The unresolved methods are especially consequential in Ullah et al. (2023), Di Menna et al. (2026), and Tripathi et al. (2025). Publisher abstracts/highlights, institutional records, Crossref metadata, and available author material were checked. Full methods were not obtained for these three papers: publisher requests returned access errors, the JSS browser page presented a CAPTCHA, and the publisher FULL API required an API key. Lancaster explicitly reports no deposited Ullah full text. No CAPTCHA was completed, credentials requested, purchase made, or paywall bypassed.

To clear this gate, inspect legitimate full texts of these three papers, resolve the UNCLEAR cells below, and re-evaluate Claims C--G. Do not convert an inaccessible method into a NO. Author copies, institutional access, or publisher downloads supplied by the user would resolve this evidence gap. The audit otherwise proceeds through all unaffected requirements, including bibliography validation.

## Search strategy and coverage

This is a targeted, structured literature audit, not a systematic review or an exhaustive claim about all publications. Search date is the date above. Prioritised 2018--2026 and followed selected references backwards to older foundations. Searched exact mandatory titles/DOIs first, then combinations of cloud resource/workload/runtime telemetry, CPU/memory/disk/network, multivariate/multi-output/multi-resource, LSTM/BiLSTM/Transformer, shared parameters, negative transfer, and task grouping. Followed relevant references and surfaced related/citing papers from publisher pages; no bibliometric completeness is claimed.

Primary sources: Elsevier/ScienceDirect and DOI records; Springer Nature full text; IEEE; ACM/author-deposited copies; PMLR; NeurIPS proceedings; OpenReview; MIT Press/HDSR; arXiv for version/status checks. Crossref and DBLP verify metadata, not experimental claims. University repositories and author project sites provide legitimate copies and implementation information. Search snippets served for discovery; unverified aggregators and AI-generated summaries were not used as scientific authority. ResearchGate was not used as final bibliographic authority.

The decision ledger contains **33 shortlisted papers: 26 accepted into references.bib and 7 not selected**. Search-engine hits that were plainly unrelated were not counted as inspected papers. Acceptance means bibliographic verification and a specific positioning purpose; it does not imply all methods were accessible, independently reproduced, or endorsed.

## Operational comparison with our study

Our reference point is manuscript Sections 3--6 and the frozen Phase 4D manifest. S1 receives the target resource history and retains a separate model for that resource. S2 receives all four resource histories but retains separate target models. M1 receives the same four channels and uses a shared LSTM encoder with resource heads. Each predicts its horizon vector. The intended evidence roles are development on TimeTrack, separate external evaluation in Bitbrains fastStorage and Rnd, and dependent temporal replication in Materna T1--T3. Resource, horizon, support, partition, and preprocessing controls matter to the comparison.

Two positioning cautions follow from our own design, without changing the frozen science:

- The three formulations form three matched contrasts, not a complete two-by-two factorial with an estimated interaction. The own-resource-input/shared-parameter cell is not evaluated. Avoid claiming that every combination of input and parameter sharing was tested.
- S2 and M1 also differ in aggregate parameter/model count and joint optimisation. Their contrast estimates the implemented representation-sharing design change. It cannot identify gradient conflict, capacity limitation, or a universal causal effect of sharing. A degradation relative to S2 supports an operational negative-transfer description, with this scope stated.

## Closest-paper audits

The first three entries below are **historical abstract-level summaries**. Their access limitations and control uncertainties are superseded by the dated full-text matrix and U/D/M evidence ledger. Other papers' earlier inspections are unchanged; no new broad search was undertaken.

### Ullah, Bilal and Yoon (Computer Networks, 2023)

Authority: [publisher](https://doi.org/10.1016/j.comnet.2023.109653), [Lancaster record](https://eprints.lancs.ac.uk/id/eprint/205130/), [author institution record](https://pure.jbnu.ac.kr/en/publications/intelligent-time-series-forecasting-framework-for-non-linear-dyna/). Citation key: `Ullah2023CloudBiLSTM`.

| Requested item | Verified evidence or unresolved issue |
|---|---|
| Resources | Publisher lists ten outputs: CPU provisioned, CPU utilisation in MHz and percent, memory provisioned/utilised, disk read/write throughput, network transmit/receive throughput, and CPU cores. |
| Inputs | Multiple resource state variables are explicit; the exact history tensor and whether every listed channel is always supplied are UNCLEAR. |
| Outputs/model | Multi-output multivariate BiLSTM is explicit. One multi-output network is supported; exact shared encoder/head topology is UNCLEAR. |
| Separate resource models | UNCLEAR; comparisons with LSTM/stacked/autoencoder architectures do not establish this. |
| S1--S2 / S2--M1 controls | Both UNCLEAR without methods. No inference of their absence from the abstract. |
| Input/representation disentanglement | UNCLEAR. |
| Horizons, context | Historical-window and train/test-size sensitivity are explicit; exact values and prediction strategy are UNCLEAR. |
| Train/test and selection | Exact chronology, scaler-fit scope, validation selection, and leakage safeguards UNCLEAR. No allegation of leakage. |
| Bitbrains | Both fastStorage and Rnd used; exact VMs, dates, aggregation, separate reporting, and eligibility rules UNCLEAR. |
| Persistence, negative transfer, model/parameter accounting | UNCLEAR. |
| Replication | Two traces supported; external-provider and dependent-block replication protocol UNCLEAR. |
| Authors' contribution | An intelligent multivariate framework and multi-input/multi-output BiLSTM, with comparisons and sensitivity experiments. |

**Direct comparison:** Multi-resource inputs, joint resource outputs, BiLSTM, and both Bitbrains environments precede our work. Our proposed distinction is the separate all-input S2 arm and the same-contrast replication policy. Whether Ullah already includes an equivalent intermediate arm remains a required full-text check. Different recurrent cell direction, channel count, or dataset reuse alone does not establish a contribution.

### Di Menna, Traini and Cortellessa (JSS, 2026)

Authority: [publisher](https://doi.org/10.1016/j.jss.2026.112937), [author publication list](https://lucatraini.me/), [DBLP](https://dblp.org/rec/journals/jss/MennaTC26.html). Citation key: `DiMenna2026RuntimeForecasting`.

The verified problem is forecasting software runtime metrics: 110 real metrics over roughly one year; eight methods in three statistical, three neural, and two foundation-model categories. The publisher reports strong zero-shot foundation-model performance with metric-dependent exceptions and unavailable private data. The exact metric catalogue/source, eight model names, horizons, baseline definitions, chronology, and multivariate/independent forecasting organisation remain UNCLEAR. Cross-resource and representation-sharing experiments, MTL, and negative-transfer analyses also remain UNCLEAR; they must not be assigned NO from an abstract.

**Question difference:** Their verified objective compares forecasting model families and transfer from pretraining. Ours compares information-sharing arrangements within a conventional model family and resource tasks. This difference is supportable at the problem level; detailed non-overlap needs the journal methods.

**ICPE predecessor:** [Author-deposited ICPE 2024 paper](https://recharge-project.github.io/pdfs/Time-Series-Forecasting-of-Runtime-Software-Metrics-An-Empirical-Study.pdf), DOI 10.1145/3629526.3645049, pp. 48--59, is the same authors' earlier empirical line: 25 daily series, eight applications plus an OS crash series, crash/hang/wait metrics, SARIMA and three RNNs, seasonal naive/seasonal monthly-mean baselines, and offsets through 14 days. Its conclusion explicitly leaves multivariate forecasting for future work. Treat the journal as the preferred expanded study, not an independent replication. The exact journal extension and cohort overlap require full-text confirmation; do not transfer the conference's precise settings to the journal.

### Tripathi, Priyadarshni, Misra and Singh: MMRP (FGCS, 2025)

Authority: [publisher](https://doi.org/10.1016/j.future.2024.107692), [author repository](https://github.com/tri-shi/MMRP), [DBLP](https://dblp.org/rec/journals/fgcs/TripathiPMS25.html). Citation key: `Tripathi2025MMRP`.

The published abstract/highlights establish Transformer/CNN/BiLSTM integration, Alibaba and Google traces, and univariate/multivariate forecasting. Indexed introductory text states multiple prediction steps. This is relevant architecture and evaluation overlap. Exact joint targets, separate-target controls, an S2-equivalent arm, negative-transfer testing, persistence, parameter counts, timing comparisons, eligibility, and repeated temporal-block design are UNCLEAR. Public repository material advertises datasets/environment setup and says model code is available on request; it is not sufficient to certify implementation reproducibility. Multiple datasets do not automatically constitute a prospective external replication.

**Direct comparison:** Do not claim a first multivariate/univariate resource comparison, hybrid model, or evaluation across providers. A controlled distinction between input scope and representation sharing is the candidate difference, pending full text. Performance-improvement headlines do not establish that every resource benefits from joint prediction.

### Nikentari and Wei: NARMAX-LSTM (ICAC, 2022)

Authority: [IEEE](https://doi.org/10.1109/ICAC55051.2022.9911071) and [author thesis appendix](https://etheses.whiterose.ac.uk/id/eprint/36236/1/Multitask%20Learning%20Using%20Nonlinear%20Model%20for%20Forecasting%20Task.pdf), PDF pp. 118--123 (paper pp. 1--6). Citation key: `Nikentari2022NARMAXLSTM`.

Tasks are tide levels at Wick, Workington, Ullapool, and New Haven; four additional stations test new tasks. Shared LSTM layers and task-specific outputs are explicit. Joint losses and single-task baselines are compared; negative transfer is explicitly defined and avoidance is claimed. The data have about 29,000 observations at 15-minute cadence; horizons are 15, 30, and 45 minutes with a separate model per horizon. Input/output/noise lags are tuned. The paper does not provide our intermediate all-input, separate-resource formulation or three-source cloud replication. Network reduction is discussed, but it is not our parameter-count/accuracy boundary. This constrains any claim to introduce MTL forecasting, shared LSTM forecasting, multi-horizon MTL, or investigation of negative transfer in forecasting. It is the closest mandatory LSTM forecasting comparison, while MTLinear below is closer to channel/task analysis.

### Rossi et al. (Cluster Computing, 2025)

Authority: [full publisher text, Sections 3.1--3.6 and 4](https://link.springer.com/article/10.1007/s10586-024-04933-2). Citation key: `Rossi2025CloudUncertainty`.

Univariate and joint processing-unit/memory predictions use deterministic/probabilistic LSTM and hybrid Bayesian models. One/two distribution outputs sit after common network layers. Google and Alibaba datasets, training across single/multiple domains, fine-tuning/zero-shot transfer scenarios, and runtime costs are examined. Their univariate--bivariate comparison changes input/target organisation together; no separate all-input single-target S2 arm is identified in the inspected methodology. The paper discusses cases where univariate prediction is easier and the uncertain payoff of multivariate/multiple-dataset cost. This materially overlaps the general accuracy/cost boundary and external-generalisation framing. Our candidate difference is four-resource matched contrasts retained through development, external confirmation, and dependent temporal replication. Do not claim that cross-provider evaluation or a cloud accuracy/cost comparison is absent from prior work.

### Zhang et al.: SWT-CLSTM (2025)

Authority: [full publisher text, experimental multivariate extension and Fig. 8--9](https://link.springer.com/article/10.1007/s44443-025-00316-8). Citation key: `Zhang2025SWTCLSTM`.

This work includes Google/Alibaba forecasting, a CPU/memory joint-task feasibility analysis, and direct application to an external Azure subset. It therefore defeats any unqualified claim that close cloud papers never evaluate joint resources or an external unknown workload. The multivariate extension is limited relative to a fixed four-resource S1/S2/M1 experiment; no matched intermediate S2 control or repeated same-source three-block replication is specified in the inspected experiments. The joint-task extension and a future-work proposal for fuller CPU/memory/network collaboration should not be conflated. Treat transfer/robustness explanations as the authors' interpretations, not proof of mechanisms in our results.

### Nochumsohn, Zisling and Azencot: MTLinear (AISTATS, 2025)

Authority: [PMLR proceedings](https://proceedings.mlr.press/v258/nochumsohn25a.html), [full author text Sections 3--5 and Appendix C](https://arxiv.org/html/2502.03571v2). Citation key: `Nochumsohn2025MTLinear`.

This peer-reviewed study treats variates/groups as tasks, measures gradient conflicts, groups correlated variates, balances errors, and assigns linear weights to groups. It compares several standard forecasting datasets, includes ablations and efficiency analysis, and discusses separate weights per variate. This is a substantial conceptual constraint: forecasting channels as tasks, selective sharing, conflicts, and efficiency are established subjects. Channel-independent processing can still share weights, as PatchTST illustrates; it is not equivalent to our independently trained S1. MTLinear does not supply the same four-resource cloud S1/S2/M1 replication protocol. It is a key Related Work/Discussion source; our study does not measure its gradient mechanisms or test its mitigation method.

### Huang et al.: cloud-native shared representation (arXiv 2512.21102)

Authority: [arXiv provenance/version record](https://arxiv.org/abs/2512.21102), [five-page full text](https://arxiv.org/pdf/2512.21102), and [DBLP informal-publication record](https://dblp.org/rec/journals/corr/abs-2512-21102.html).

**PREPRINT_ONLY.** Six names match the archive: Zixiao Huang, Jixiao Yang, Sijia Li, Chi Zhang, Jinyu Chen, Chengda Xu. Listed affiliations are Washington, Westcliff, Michigan, Northeastern, Virginia, and Washington respectively; these are self-reported and not independently authenticated. No peer-reviewed successor was verified.

The paper specifies shared encoding, task-specific decoding, joint loss, and Alibaba 2018; it reports horizons 1--8 and baseline error summaries. Precise subset/targets, chronological splits, scaler-fit scope, training settings, code, and seeds are insufficiently specified for an independent reproduction. No S1/S2/M1 ablation, persistence, resource-wise negative-transfer boundary, or prospective external/temporal replication is documented in its five pages. The shared-representation title/topic overlaps, but its architecture-performance aim differs. Do not infer fraud or invalidity from incomplete reporting. **Do not add to references.bib at this stage:** acknowledge the overlap in this audit; reconsider citation if a reproducible implementation or stronger published version appears.

## Further constraints and contextual sources

- [Ilbert et al., NeurIPS 2024 Time Series in the Age of Large Models workshop](https://helios2.mi.parisdescartes.fr/~themisp/publications/tsalm24-forecasting.pdf) explicitly model each channel as a task with shared and task-specific linear components. Their random-matrix analysis connects transfer to data covariance and noise, followed by synthetic and real forecasting tests. This is another direct conceptual precedent for distinguishing shared from task-specific learning. It does not establish an equivalent cloud-resource three-arm replication. The verified document identifies a workshop, not the NeurIPS main proceedings; no final journal version or independent peer-review-status confirmation was established. Retain it in the audit rather than the compact bibliography, alongside the stronger, directly relevant AISTATS MTLinear source. This selection is not evidence that the workshop contribution is unimportant or invalid.
- [Tran et al. 2018](https://doi.org/10.1016/j.procs.2018.07.298) already combine correlated cloud metrics and LSTM forecasting. It constrains priority for multivariate resource inputs.
- [Xu et al. 2022, esDNN](https://cam.tju.edu.cn/homepage/wuhuaming/PDF/TOIT.pdf), Sections 3--5, use non-CPU resource covariates and evaluate CPU forecasts on Alibaba/Google. Multiple inputs must not be misreported as multiple jointly predicted resource outputs. It does not present the complete matched three-arm experiment in the inspected methods.
- [Bi et al. 2019](https://doi.org/10.1109/LRA.2019.2899224) already place multi-task learning in the cloud-workload title, using smoothing, wavelet components, and stochastic configuration networks for succeeding-slot forecasts. The workload/component task definition is different from our resource heads. Do not claim first cloud MTL.
- [OMCR](https://doi.org/10.1109/TKDE.2025.3619097) establishes recent online multivariate cloud forecasting. The verified abstract supports that scope; full protocol cells remain UNCLEAR. Use the final 2026 issue, not the 2025 online date as the issue year.
- [Caruana](https://doi.org/10.1023/A:1007379606734), [Standley et al.](https://proceedings.mlr.press/v119/standley20a.html), [Fifty et al.](https://proceedings.neurips.cc/paper/2021/hash/e77910ebb93b511588557806310f78f1-Abstract.html), [Sener and Koltun](https://proceedings.neurips.cc/paper/2018/hash/432aca3a1e345e339f35a30c8f65edce-Abstract.html), and [Yu et al., PCGrad](https://papers.neurips.cc/paper/2020/hash/3fe78a8acf5fda99de95303940a2420c-Abstract.html) ground sharing, task relatedness, negative interactions, grouping, and optimisation. These are conceptual precedents, not direct cloud replications or measured causes in our study.
- [Yu et al. 2025 review](https://hdsr.mitpress.mit.edu/pub/7fcc3jhv/release/2) provides a recent formal MTL framework. Select it instead of multiplying general surveys.
- [PatchTST](https://arxiv.org/abs/2211.14730) explicitly shares weights across independently processed channels; [iTransformer](https://arxiv.org/abs/2310.06625) captures inter-variate dependencies. Input mixing and parameter sharing are distinct in generic forecasting already. [DLinear](https://doi.org/10.1609/aaai.v37i9.26317) motivates careful baselines, not a universal rejection of Transformers.
- [DeepAR](https://doi.org/10.1016/j.ijforecast.2019.07.001) and [Montero-Manso and Hyndman](https://doi.org/10.1016/j.ijforecast.2021.03.004) establish sharing across series/global forecasting and parameter-efficiency precedents. Our per-VM cross-resource design is a different sharing axis; it does not refute global-model theory.
- [Bauer et al.](https://doi.org/10.1109/JPROC.2020.2983857) connects forecasting to self-aware systems; [Syu et al.](https://doi.org/10.1016/j.jss.2017.09.011) already compare dynamic software-service forecasting accuracy and cost. [Cerqueira et al.](https://doi.org/10.1007/s10994-020-05910-7) supports attention to temporal performance estimation; it does not validate our exact split automatically.

### MTL foundations: what each source can and cannot explain

| Source | Audited contribution | Use and limit for our manuscript |
|---|---|---|
| Caruana 1997 | Learning related tasks together through shared inductive bias/representations | Establishes hard-sharing motivation; does not predict which cloud resources will benefit. |
| Standley et al. 2020 | Empirically searches task combinations under computational constraints | Supports evaluating relatedness and accuracy/compute choices; its vision tasks do not validate our resource grouping. |
| Fifty et al. 2021 | Chooses groups using estimated effects of one task's gradient on other task losses | Direct precedent for adverse all-task training and selective grouping; we did not measure its transfer scores or test its algorithm. |
| Sener and Koltun 2018 | Treats conflicting task objectives as multi-objective optimisation with a Pareto-oriented algorithm | Shows why a simple weighted loss is not a universal solution; does not demonstrate gradient conflict in our trained models. |
| Yu et al. 2020, PCGrad | Modifies conflicting gradients during joint training | A possible mitigation reference, not a mechanism we observed or an experiment we ran. |
| Yu et al. 2025 HDSR review | Covers sharing/representation choices, feature interference, and negative transfer with mitigation strategies | Supplies current terminology and a synthesis; it is not another empirical cloud replication. |

These interpretations use the primary sources linked above. Do not cite a survey as if it directly measured our forecasting behaviour. Hard sharing means common learned parameters; soft sharing retains task-specific parameters with coupling. Neither is synonymous with simply adding other resources as input covariates.

## Stage 6B focused control matrix

### STAGE 6B FULL-TEXT CLEARANCE — USER-SUPPLIED PDFS

Date: **16 October 2026**. All three complete supplied PDFs, including embedded appendices, were inspected using native extraction and visual checks. Every resolved target-paper cell is mapped to exact PDF pages/sections/tables in the [full-text evidence map](closest_papers_fulltext_clearance.md#9-final-21-row-comparison-matrix). NO means not present in the complete **reported experimental design**, not impossible in unpublished code. PARTIAL records related but non-equivalent evidence; UNCLEAR now means genuinely unspecified, not inaccessible.

D's S1 is a per-runtime-metric organisational analogue. Its PARTIAL sharing is pretrained weight reuse, not runtime-resource MTL; PARTIAL persistence is seasonal naive, not last-value persistence; PARTIAL temporal replication is overlapping rolling evaluation, not retained dependent-block replication. M's S2/first bridge is PARTIAL because target-K contextual forecasting is clear but exact all-channel/disjoint-fit inventory and matched settings are not. U's M1 is PARTIAL because joint common-encoder output is explicit but our per-resource head topology is not.

| Feature | Ullah | Di Menna | MMRP | Our study |
|---|---|---|---|---|
| Own-resource-only input | NO | YES | YES | YES |
| All-resource input | YES | NO | PARTIAL | YES |
| Target-specific independently trained model | NO | YES | PARTIAL | YES |
| Joint multi-resource output | YES | NO | NO | YES |
| Shared predictive representation | YES | PARTIAL | NO | YES |
| S1-equivalent arm | NO | YES | YES | YES |
| S2-equivalent arm | NO | NO | PARTIAL | YES |
| M1-equivalent arm | PARTIAL | NO | NO | YES |
| Explicit S1-vs-S2-equivalent comparison | NO | NO | PARTIAL | YES |
| Explicit S2-vs-M1-equivalent comparison | NO | NO | NO | YES |
| Input scope isolated | NO | NO | PARTIAL | PARTIAL |
| Representation sharing isolated | NO | NO | NO | PARTIAL |
| Multi-horizon | YES | YES | YES | YES |
| Persistence baseline | NO | PARTIAL | NO | YES |
| Resource-wise evaluation | YES | PARTIAL | YES | YES |
| Multiple environments | YES | PARTIAL | YES | YES |
| Dependent temporal replication | NO | PARTIAL | NO | YES |
| Negative-transfer analysis | NO | NO | NO | YES |
| Parameter/model efficiency analysis | PARTIAL | PARTIAL | PARTIAL | YES |
| Explicit population restriction | PARTIAL | YES | PARTIAL | YES |
| Leakage-controlled temporal selection | UNCLEAR | PARTIAL | PARTIAL | YES |

**Evidence:** the final report's 21-row evidence map connects every target-paper field to U1–U9, D1–D10 and M1–M12, each specifying PDF page, section, table/figure, evidence and interpretation. U pp. 5–7/12/19 show multivariate input–output models and single-variable future work; D pp. 5–7/15 show per-series models and multivariate future work; M pp. 3–7/11–13/19–21 show a specific single-target covariate formulation, univariate/multivariate comparisons and component—not resource-sharing—ablations. U's remaining UNCLEAR is split/scaler/selection reporting (pp. 5, 10–13), not S1/S2 existence. No consequential complete-decomposition/second-bridge cell remains UNCLEAR.

### Evidence for every resolved matrix field

Primary local source: `manuscript/jss/manuscript.tex`, read without modification; source-line anchors below refer to the Stage 6B unchanged file, SHA-256 `fb1636c78476b9e9e136d3e1acacacb1fcca2a4664c859d9261e9b82baf8c75b`. Source section/equation labels are more stable than compiled PDF pagination; no PDF page is invented. These references establish the study design/reporting, not fresh independent validation or new numerical analysis.

| Resolved fields in Our study | Section / source location | Inspected evidence and qualification |
|---|---|---|
| Own-resource input; independent target model; S1 arm | Section 3.3, lines 175–206; Eqs. `eq:s1-input`, `eq:s1-forecast` | One target history; separately learned parameters per resource; horizon-vector output. |
| All-resource input; independent target model; S2 arm | Section 3.4, lines 208–240; Eq. `eq:s2-forecast` | All four histories enter each independently optimised target model; no shared encoder or cross-target loss. |
| Joint multi-resource output; shared representation; M1 arm | Section 3.5, lines 242–303; Eqs. `eq:m1-forecast`, `eq:m1-loss` | One encoder, resource heads, joint resource-by-horizon output and combined resource loss. |
| Both explicit contrasts | Section 3.6, lines 305–361; Section 4.8, lines 659–670 | S2/S1 and M1/S2 are separately defined and evaluated on matched resource/horizon/support units. |
| Input scope isolated: PARTIAL | Sections 3.4, 4.6–4.7, lines 208–240, 565–617 | S1/S2 retain separate target models and the backbone family, but input width changes parameter count and context/epoch settings are selected separately. This is an implemented input-scope policy contrast, not an everything-else-numerically-identical intervention. |
| Representation sharing isolated: PARTIAL | Sections 3.5–3.6, 4.6–4.7, lines 242–361, 565–617 | S2/M1 retain all-channel availability, but sharing also changes aggregate capacity, model count, joint optimisation and target-specific versus common context selection. No pure causal isolation of shared parameters or gradient mechanism. |
| Multi-horizon | Sections 3.2, 4.5, lines 136–173, 548–563 | Each head predicts all prescribed offsets jointly; horizon sets are fixed by dataset. |
| Persistence baseline; resource-wise evaluation | Section 4.8, lines 619–682; Eq. `eq:persistence-skill` | Last observed target is a separate baseline; errors are evaluated by resource/horizon; native errors are not averaged across resources. |
| Multiple environments; dependent temporal replication | Sections 4.2 and 4.9, lines 395–465, 684–711; Table `tab:dataset-summary` | TimeTrack development; separately evaluated Bitbrains environments; Materna consecutive dependent blocks, not independent datasets. |
| Negative-transfer analysis | Section 5.2, lines 812–856 | M1/S2 degradation and resource-specific exceptions are reported. YES means operational adverse transfer relative to independent all-input models, not a measured gradient-conflict cause. |
| Parameter/model efficiency analysis | Sections 4.6 and 5.6, lines 585–591, 992–1026; Table in `tables/efficiency_summary.tex` | Aggregate parameter/model inventories and Materna fit-time accounting are distinguished from forecasting accuracy; no universal latency or energy claim. |
| Explicit population restriction | Sections 4.2 and 4.10, lines 424–465, 713–735 | Structural and positive training-scale eligibility; deterministic cohorts; excluded populations are outside the inference scope. |
| Leakage-controlled temporal selection | Sections 4.3–4.4 and 4.7, lines 467–546, 593–617 | Training-only scaling, chronological expanding folds, target-time purge, inner context/epoch selection and fresh outer refits without test callbacks. |

The two PARTIAL entries qualify the existing Claim D wording; they do not change the frozen experiment. The informative S2 bridge remains real. The design separates operational contrasts, not every consequence of the model changes. No new scientific result or manuscript correction is introduced here.

## Earlier Stage 6 topic-overlap matrix (historical)

The three target rows below preserve earlier abstract-level topic screening only. Their positive labels and UNCLEAR cells are **historical**, not current full-text decisions. Use the updated focused matrix above exclusively for Stage 6B controls, baselines and protocol. Other papers' earlier full-text audits are unchanged.

YES requires explicit supporting evidence. NO means the inspected methods do not include that feature, within the stated operational definition. PARTIAL denotes related but non-equivalent evidence. UNCLEAR denotes inaccessible or insufficiently specified evidence. In particular, a multivariate prediction claim does not prove separate all-input target models. Temporal replication here means repeated, separately evaluated blocks with retained contrasts, not merely chronological train/test splitting. Population restrictions means explicit sample/applicability detail, not equivalence to our eligibility rule.

| Reference | Software/runtime/cloud domain | Multiple resource inputs | Multiple resource targets | Separate target-specific models | Shared multi-task representation | Explicit local-vs-context comparison | Explicit context-vs-shared comparison | Multi-horizon | Persistence baseline | Multiple environments/datasets | Temporal replication | Negative-transfer analysis | Model/parameter efficiency | Population/applicability restrictions | Key difference from our work |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ullah 2023 | YES | YES | YES | UNCLEAR | PARTIAL | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | YES | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | Closest Bitbrains/resource overlap; precise control unresolved |
| Di Menna JSS 2026 | YES | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | PARTIAL | Model-family/zero-shot question verified; detailed protocol unresolved |
| MMRP 2025 | YES | YES | UNCLEAR | UNCLEAR | UNCLEAR | PARTIAL | UNCLEAR | YES | UNCLEAR | YES | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | Hybrid model/univariate--multivariate comparison; exact sharing control unresolved |
| NARMAX-LSTM 2022 | NO | NO | NO | YES | YES | NO | NO | YES | NO | PARTIAL | NO | YES | PARTIAL | PARTIAL | Tide stations are tasks; separate model per horizon |
| MTLinear 2025 | NO | NO | NO | YES | YES | NO | NO | YES | UNCLEAR | YES | NO | YES | YES | PARTIAL | Generic channel grouping and measured gradient analysis |
| Huang 2025 preprint | YES | YES | PARTIAL | UNCLEAR | YES | NO | NO | YES | NO | NO | NO | NO | NO | PARTIAL | Proposed adaptive model, incomplete reproducibility |
| Rossi 2025 | YES | YES | YES | YES | YES | PARTIAL | NO | UNCLEAR | UNCLEAR | YES | NO | PARTIAL | PARTIAL | YES | Univariate/bivariate + transfer; no fixed-input S2 bridge identified |
| SWT-CLSTM 2025 | YES | YES | YES | PARTIAL | PARTIAL | PARTIAL | NO | UNCLEAR | UNCLEAR | YES | NO | UNCLEAR | UNCLEAR | YES | CPU/memory feasibility and external Azure test, rather than full controlled replication |
| esDNN 2022 | YES | YES | NO | NO | NO | PARTIAL | NO | YES | UNCLEAR | YES | NO | NO | PARTIAL | YES | Multivariate inputs, primarily CPU target; distinct preprocessing/GRU comparison |
| OMCR 2026 | YES | YES | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | Online adaptation rather than verified matched sharing ablation |

For the two non-cloud forecasting rows, NO in resource columns means no cloud-resource variables, not no multivariate data. NARMAX and MTLinear do jointly forecast non-resource tasks. A multi-horizon YES may mean several horizons evaluated separately; it does not certify a joint horizon head.

## Candidate claim verdicts

| Claim | Verdict | Defensible scope |
|---|---|---|
| A: contribution is not a new architecture | SUPPORTED | Conventional LSTM and heads; contribution rests on experiment and evidence. |
| B: prior cloud work has demonstrated multivariate/joint improvements | SUPPORTED | Ullah/MMRP report improvements; Rossi and SWT provide further comparisons. Not universal superiority. |
| C: prior work often combines input and output/sharing changes | PARTIALLY_SUPPORTED; materially narrowed | U compares joint multivariate architectures; D stays per-series; **M already compares univariate/contextual single-target designs**. The blanket closest-three conflation claim is not supported. The bounded missing element is the complete decomposition, particularly S2–M1, not all S1–S2 comparisons. |
| D: S1/S2/M1 is a controlled decomposition | SUPPORTED for implemented contrasts; no complete equivalent identified in the three full-text reported designs | U lacks S2; D lacks S2/M1; M has no reported joint-resource M1/second bridge. Acknowledge partial arms/first-bridge precedents. Unequal capacity, optimisation and selected settings keep strict isolation PARTIAL. No first, full-factorial or pure-causal claim. |
| E: replicated empirical negative-transfer boundary | SUPPORTED as scoped evidence, not phenomenon priority | None reports adverse controlled S2–M1 resource transfer and replication. M contains worse contextual cells (Tables 3–6, D.11), not an intervention introducing cross-target sharing. Generic negative transfer and mechanisms pre-exist; our causes are unmeasured. |
| F: retained external + dependent-temporal contrast sequence | SUPPORTED as a bounded design distinction, not rarity/priority | U has two Bitbrains environments; M two providers; D many applications/rolling origins. None retains both bridges across the specified development/external/dependent-block sequence. No first multi-dataset/temporal evaluation claim. |
| G: consolidation with adverse shared accuracy | SUPPORTED as implementation-specific evidence | U discusses training qualitatively; D gives model sizes/local fits; M measures inference/throughput. None reports independent-target→joint-resource consolidation with adverse controlled S2–M1 accuracy. Generic forecasting efficiency is not new. |

## PROHIBITED OR UNSUPPORTED NOVELTY CLAIMS

- First multivariate cloud forecaster, first LSTM/BiLSTM resource predictor, first multi-output resource predictor, or first use of Bitbrains for multivariate forecasting.
- First joint resource model, first MTL forecasting model, first cloud MTL application, first treatment of channels as tasks, first recognition of negative transfer, or first selective task-sharing argument.
- First cross-provider/cloud-dataset evaluation, first external unknown-workload test, or first forecasting accuracy--cost comparison.
- Prior work never separates information availability and parameter sharing; all multivariate models share representations; channel independence means independently fitted parameters.
- A complete two-by-two factorial, a causal identification of gradient conflict, or capacity-/parameter-matched S2/M1 comparison when those properties are not present.
- Joint forecasting is universally harmful; MTL is ineffective for cloud telemetry; cross-resource information is useless; shared representations always cause degradation.
- Statistical independence of Materna blocks, unrestricted applicability outside eligible VMs, pooled cross-study inferential claims, or superiority to untested modern architectures.
- Claiming MMRP lacks univariate/contextual single-target comparisons or necessarily forecasts resources jointly; confusing attention heads with resource heads or foundation pretraining with runtime-target MTL.
- Treating unspecified preprocessing, split, feature or model-fit details as proven absent, certified leakage-free, or evidence of misconduct; silently resolving PDF population/count/feature discrepancies.

## Defensible contribution claims for later drafting

These are internal claim specifications, not Introduction prose. The three supplied full texts have been cleared for the bounded reported-control comparison; exclusive priority across all literature is not established.

1. We evaluate explicit matched S1/S2/M1 operational contrasts, including the independent-versus-shared all-input comparison, acknowledging existing univariate/contextual comparisons and unequal capacity/selection constraints.
2. We evaluate the resource-dependent value of cross-resource context through development, external confirmation, and dependent temporal replication, retaining the populations and source roles defined prospectively.
3. We provide replicated empirical evidence of adverse representation-sharing and complete-system outcomes for the evaluated conventional shared-LSTM design, distinguished from the contextual-input contrast.
4. We quantify the co-occurrence of substantial model/parameter consolidation and adverse accuracy, and state the eligibility, architecture, and temporal-dependence limits of that evidence.

## Recommended future Related Work structure

Recommend consolidating the current five subsections into four; do not modify the skeleton during this audit.

1. **Runtime and cloud-resource forecasting:** software-engineering problem (Di Menna, Bauer, Syu), followed by multivariate cloud designs (Ullah, esDNN, MMRP, Rossi, SWT, OMCR). Synthesise what is predicted and compared, rather than one paragraph per paper.
2. **Information scope and sharing in forecasting:** separate cross-channel covariates, joint outputs, shared weights with channel-independent inputs, and global learning across series (PatchTST, iTransformer, DeepAR, Montero-Manso, MTLinear).
3. **Multi-task learning, task relatedness, and adverse transfer:** Caruana, HDSR, Standley, Fifty, Sener, PCGrad; then NARMAX and MTLinear forecasting examples. Keep mechanisms separate from measured outcomes.
4. **Evaluation gap and study scope:** the specific intermediate S2 control, retained replication contrasts, efficiency accounting, and eligibility boundary. State the gap conditionally until full texts are cleared. Avoid a generic forecasting survey or another algorithm leaderboard.

## Introduction paragraph-purpose blueprint

P1: software runtime telemetry, forecasting decisions, and the software-engineering problem; anchor Di Menna/Bauer/Syu.

P2: opportunities already explored through multivariate and multi-output resource prediction; anchor Ullah/MMRP/Rossi and acknowledge established capabilities.

P3: distinguish input information, target organisation, and parameter sharing; connect to channel-independent/shared-weight and MTL literature.

P4: identify the specific evaluation question that remains after the full-text gate: additional resource histories versus shared predictive representation, under matched support.

P5: state the conventional model, the three formulations, dataset roles, and conservative external/temporal population scope.

P6: enumerate the four scoped empirical contribution claims above and the high-level boundary findings. No architecture priority or universal claim.

## Discussion-literature map

| OUR OBSERVATION | LITERATURE-SUPPORTED INTERPRETATION | SPECULATIVE MECHANISM: not measured here |
|---|---|---|
| S2 contextual effects vary by resource/environment/block | Cloud univariate/bivariate work and generic channel-dependence research make conditional benefits plausible (Rossi; MTLinear; PatchTST/iTransformer) | Particular resource coupling, irrelevant channels, or signal-to-noise explanation |
| M1 versus S2 often degrades | Sharing can have task-dependent benefits/costs (Caruana; Standley; Fifty; NARMAX) | Gradient conflict, capacity shortage, or task competition as the demonstrated cause |
| No universally favourable resource sharing pattern | Task relatedness should be evaluated rather than assumed (Standley; Fifty; HDSR; MTLinear) | A correlation-derived grouping would repair our model |
| M1 consolidates models and parameters | Accuracy/efficiency is an established MTL/global-model design consideration (Standley; Montero-Manso; Rossi; Syu) | Equal latency, energy savings, deployment savings, or performance on different hardware |
| External and temporal directions/classifications vary | Provider transfer and temporal performance estimation deserve explicit evaluation (Rossi; SWT; Cerqueira) | A named workload regime, non-stationarity, or a specific distribution shift caused our results |

Future mechanism discussion may present hypotheses with citations, but must identify them as untested. The current study does not test PCGrad, grouping, adaptive sharing, larger encoders, or modern foundation models.

## Novelty risk assessment

Stage 6B full-text verdict: **STAGE_6_PASS**, with **MODERATE_RISK** overall. No complete equivalent was found in the three reported experimental designs. M's contextual first bridge and U's joint resource architecture materially limit priority claims. The risk judgement is qualitative, not a probability or an authorisation to draft.

**Overall: MODERATE_RISK.** Architecture, multivariate forecasting and generic sharing are established; the defensible contribution is the complete explicit operational comparison and retained empirical boundaries. Genuine reporting gaps are recorded, not converted into missing arms or accusations. NOVELTY_CONFLICT_FOUND is not warranted for these complete reported designs.

| Dimension | Risk of claiming novelty | Assessment |
|---|---|---|
| Runtime forecasting itself | HIGH_RISK | Established software-engineering/cloud literature. |
| Multivariate forecasting itself | HIGH_RISK | Established before this work, including Bitbrains. |
| MTL/shared representation itself | HIGH_RISK | Foundations, forecasting methods, and cloud examples pre-exist. |
| Controlled experimental design in this domain | MODERATE_RISK | Complete trio/second bridge not found in the three full texts, but M already provides related first-bridge comparisons; no conceptual first claim. |
| Replicated empirical boundaries | MODERATE_RISK | Specific source/contrast/eligibility protocol is the candidate contribution; generic negative transfer and external testing are established. |

## Audit completion boundary

Original Stage 6 bibliography work is recorded in reference_verification.md. During resumed Stage 6B **only the three authorised literature audit records** were edited; references.bib remained unchanged at 36 entries. Manuscript sections, title, figures, tables, scientific values and frozen artifacts were not edited. No experiments, recomputation, commit, push or next-stage manuscript prose. The three supplied PDFs were inspected completely, removing the access blocker. The bounded gate passes without an exclusive priority or mechanism claim.
