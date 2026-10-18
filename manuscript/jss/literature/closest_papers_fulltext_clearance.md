# STAGE 6B FINAL FULL-TEXT NOVELTY CLEARANCE REPORT

## STAGE 6B FULL-TEXT CLEARANCE — USER-SUPPLIED PDFS

Completed 16 October 2026. **STAGE_6_PASS for this bounded three-paper methods/novelty gate.** This supersedes the access-blocked report preserved below. All three supplied PDFs match their intended articles and were read in full, including references, embedded appendices and figure-only pages. No equivalent complete S1/S2/M1 experiment with both bridges was found in the reported methods/experiments. This is not an exhaustive priority search, a claim of implementation reproducibility, or permission to begin drafting. There is material partial overlap: **MMRP already compares univariate and multivariate single-target forecasting.** No architecture, multivariate-input or S1–S2 priority claim survives this audit.

### 1–5. Source identity, integrity and reading method

Page references below are **one-based PDF pages**, which coincide with the printed article page numbers. User-supplied originals were opened read-only in `/Users/fgtek002/Downloads/`; no copy was modified. Titles, authors, venue/year and DOI were checked against the actual first page, not merely the filename.

| Paper / file | Bytes | Pages | Verified first-page identity | SHA-256 |
|---|---:|---:|---|---|
| U — `1-s2.0-S1389128623000981-main.pdf` | 7,458,902 | 22 | Farman Ullah; Muhammad Bilal; Su-Kyung Yoon. *Intelligent time-series forecasting framework for non-linear dynamic workload and resource prediction in cloud*. Computer Networks 225 (2023), 109653. DOI 10.1016/j.comnet.2023.109653. | f65b142e662c59e2819fd6b31b097ebe26b6cac0a9f2a30877cc3a7d0b419ae0 |
| D — `1-s2.0-S0164121226001706-main.pdf` | 3,321,102 | 17 | Federico Di Menna; Luca Traini; Vittorio Cortellessa. *Forecasting software runtime metrics: A comparative study of classical statistical, neural network, and foundation models*. JSS 240 (2026), 112937. DOI 10.1016/j.jss.2026.112937. | 946280db3eaccbc6b0aefcdd9c31a18fdbcfcaacc81963d4ae188060df6462b3 |
| M — `1-s2.0-S0167739X24006563-main.pdf` | 6,200,268 | 23 | Shivani Tripathi; Priyadarshni; Rajiv Misra; T. N. Singh. *Multilayer multivariate forecasting network for precise resource utilization prediction in edge data centers*. FGCS 166 (2025), 107692. DOI 10.1016/j.future.2024.107692. | e81b099db492b7d8fce8710111abcd6ef53bd8169f9d464f47f409d034efdbba |

`pdftotext` was unavailable; the bundled Python runtime's **pypdf native text extraction** was used instead, page by page. All PDFs have usable text layers. **OCR = not used.** The PDF skill also guided Poppler rendering and visual inspection: U Fig. 3 (p. 7), convergence figures (pp. 8–9) and resource curves (pp. 16–19); D Figs. 2–4 (p. 6) and metric-class results (p. 12); M architecture (p. 5), univariate/multivariate tables (p. 11), scalability (pp. 15–16), ablation tables (p. 19) and Appendix C curves (pp. 20–21). This checked distinctions that captions/text extraction alone could obscure. Temporary page images are under `/private/tmp/stage6b-fulltext.NowuNf/`, not manuscript/scientific outputs. No new online retrieval, experiment, scientific recomputation or bibliography expansion was needed.

Coverage: U pp. 1–4 Introduction/Background, pp. 4–7 and 10 methods, pp. 8–20 experiments/results/conclusion, pp. 20–22 declarations/references/biographies; no embedded appendix. D pp. 1–3 Introduction/Background, pp. 3–8 Design, pp. 8–14 Results, pp. 14–15 Threats/Conclusion, pp. 16–17 declarations/references; no embedded appendix. M pp. 1–4 Introduction/Related Work/Problem, pp. 4–10 Methods/Setup, pp. 10–17 Results/Discussion/Conclusion, pp. 17–21 **Appendices A–D**, pp. 22–23 references/biographies.

### Operational coding rules

The matrix refers to the **reported experiment**, not every capability of an algorithm or an inaccessible implementation. YES = directly described; NO = not an arm/analysis in the inspected complete experimental design; PARTIAL = an explicit related but non-equivalent design; UNCLEAR = the PDF genuinely does not specify enough. NO does not allege that an unreported implementation is impossible.

An own-metric independently trained runtime forecaster is an S1 organisational analogue even if its target is not a CPU/memory channel. “All-resource input” means the study's selected multichannel input set, not every measured feature in a source. Shared representation means **cross-target** sharing, not BiLSTM forward/backward branches, attention query/key/value heads, an encoder/decoder within one target model, or joint prediction of horizons. Foundation pretraining/reused weights are distinguished explicitly from joint runtime-target learning. M1-equivalent PARTIAL permits common-encoder joint outputs without our explicit per-resource heads. S2-equivalent PARTIAL acknowledges a multivariate single-target bridge whose exact all-channel mapping or disjoint-fit inventory is not fully specified.

### 6. Ullah 2023 — full-text evidence ledger

All entries in this subsection refer to Paper U. No result was recomputed.

| ID | PDF page; section; table/figure | Evidence inspected (paraphrase) | Interpretation for our study |
|---|---|---|---|
| U1 | pp. 4–6; §3.1; Tables 2–3 | fastStorage: one month, 1,250 VMs; Rnd: three months, **500 VMs in Table 2**, while p. 4 prose says **50**. Combined preprocessed matrices have 9,100×10 and 10,154×10 records. Exact selected dates/VM IDs and combination operator are not supplied. Raw cadence is printed as 300 ms and preprocessing averages 1,000 samples into five minutes. | Record the internal 50/500 discrepancy and cadence exactly as printed; do not silently replace them with our dataset facts. Their aggregate trace-level series are not our fixed eligible per-VM cohorts. Exact original sampling correctness is not independently established here. |
| U2 | pp. 4–6; §3.1; Eq. (1), Tables 2–3 | NaNs are deleted, five-minute feature means formed, VM data combined per trace, and each feature min–max scaled to [0,1]. No dynamic/IQR eligibility rule, selected VM list, training-only scaler scope or exact calendar range is specified. | Population restriction is PARTIAL (explicit processing, incomplete retained population). Training-only scaling/chronology protection is genuinely UNCLEAR, not a proven leakage defect. |
| U3 | pp. 5–6; §3.1; Table 3, Eqs. (2)–(3), Boxes I–II | The ten channels are CPU cores; CPU provision MHz; CPU utilisation MHz; CPU utilisation percent; memory provision MB; memory utilisation MB; disk read and write throughput; network transmit and receive throughput. **The same ten variables are both inputs and predicted outputs.** X contains all ten channels at each of s historical positions; Y contains all ten at future positions 1…n. | Simultaneous ten-channel histories and joint ten-resource/attribute output are YES. Historical window structure is common across channels. No extra calendar/ID input is introduced in the reported equations. |
| U4 | pp. 5–7, 10; §3.2; Fig. 3, Eqs. (4)–(18), Algorithm 1 | Forward/backward LSTM processing combines into a common hidden representation; one dense output mapping with L2 regularisation serves the multivariate forecast. Algorithm specifies 128 cell units. No individually parameterised resource-head branches are drawn or specified. | Cross-resource shared predictive representation is YES; **M1-like/PARTIAL**, not the same explicit task-head topology. The documented model is one joint forecaster per trace/configuration, not ten independently fitted resource models; total run/checkpoint count is not supplied. |
| U5 | pp. 7, 10–12, 15, 20; §§3.3, 4.1–4.4; Tables 4–7, 14–15 | Six algorithms are assessed: LSTM, stacked BiLSTM, stacked LSTM–BiLSTM, stacked BiLSTM–LSTM, LSTM autoencoder and proposed multivariate BiLSTM. §4.1 explicitly says the models are trained with multivariate inputs **and** outputs; common §3.1 construction applies. Exact layer widths/topologies of every baseline are not provided. | These are algorithm/architecture comparisons within multivariate input–output forecasting, **not S1 or S2 controls**. LSTM does not mean independently fitted single-resource models. Autoencoder is later omitted from the detailed five-model comparison because its errors are high. |
| U6 | pp. 10–15; Algorithm 1, §§4.2–4.3; Tables 4–13 | History candidates s={3,6,9}; future lengths n={1,2,3}, explicitly 5/10/15 minutes. Eq. (3) defines a direct multi-output future sequence, rather than an explicit recursive feedback scheme. Results favour s=3 fastStorage and s=6 Rnd; n=1 for main comparisons. Batch sizes 32/64/128, epochs 100/300/500; Adam, tanh and 128 units; main runs use batch 32 and 500 epochs. | Multi-horizon YES; not our longer horizon range or our context-selection protocol. Epoch/window/batch sensitivity is not a sharing ablation. |
| U7 | pp. 8–13; Algorithm 1, §§4.1–4.2; Figs. 4–5, Tables 4–7 | 90–10 and 80–20 splits are studied; training/validation curves reported. Algorithm mentions train/test/validation, but does not uniquely specify validation allocation, chronological versus shuffled splitting, horizon purge or a held-out tuning protocol. Stop criterion is iteration/convergence/stagnation, without an early-stopping patience rule. Seeds are not reported. | Do not certify strict leakage-controlled temporal selection; the paper is insufficiently specific on those details. Do not infer a random split or accuse leakage. |
| U8 | pp. 7, 10–20; §§3.3, 4, 5; Tables 8–15, Figs. 6–7 | MAE/RMSE/MAPE and curves are resource-wise and trace-wise. fastStorage/Rnd have separately presented results and history-window preferences. No persistence/naive comparator appears in the complete baseline/result inventory. | Resource-wise evaluation and multiple environments YES. These are two environments from Bitbrains, not multiple providers. No repeated dependent temporal-block replication with retained sharing contrasts. |
| U9 | pp. 12–20; §§4.2–5 | Batch-dependent training speed is discussed qualitatively; no parameter inventory, model-consolidation experiment, training-time table or shared-versus-independent accuracy/cost analysis is provided. Error variation at spikes and across resources is discussed. Conclusion leaves a single-variable model to future work. | Generic computational discussion PARTIAL; parameter/model consolidation trade-off absent. No operational negative-transfer analysis from introducing sharing: **no S2 baseline**. No S1/S2/M1 trio, either bridge, input-only control or sharing-only control appears in the complete experiment. |

Baseline I/O finding: all five comparison families plus the proposed BiLSTM use the paper's ten-input/ten-output protocol (U3/U5). Per-resource independent models and own-resource-only variants are not evaluated. Detailed baseline layer layouts remain unreported, but this does not obscure the expressly multivariate input–output experimental organisation.

### 7. Di Menna JSS 2026 — full-text evidence ledger

All entries in this subsection refer to Paper D.

| ID | PDF page; section; table/figure | Evidence inspected (paraphrase) | Interpretation for our study |
|---|---|---|---|
| D1 | pp. 2–4; Introduction, §3.1; Table 1 | One anonymised worldwide corporate IT infrastructure; 29 anonymous applications, including browser, communications and word-processing types, over heterogeneous devices. 110 reported analysed series, each 400 daily aggregated observations (~one year). Exact company/application names and calendar dates are withheld/not enumerated. | Rich application/metric diversity, but not an external multi-provider design or simultaneous four-resource VM forecasting. |
| D2 | p. 4; §3.1; Table 1 | Classes: crash rate, hang-time %, wait-time %, active-time %, launch-time %, open-time %, save-time %. Table totals 21/26/25/26/7/2/3=110; discarded counts 8/3/4/3/2/1/0=21. Prose excludes 11 missing and 10 constant series, yet calls the final dataset 110 and uses 110 throughout evaluation. Company provides z-standardised data using series mean/SD. | Report the authors' operational 110, not an invented final 89; the exact pre-/post-filter count bookkeeping is not fully reconciled by the prose/table. Explicit eligibility/applicability restriction YES. Training-only standardisation is not established by the PDF. |
| D3 | pp. 5–7; §§3.2–3.3.4; Figs. 2–4 | Eight methods: SARIMA, ETS, Prophet, FC-RNN, LSTM, GRU, TimesFM 200M, Chronos-Bolt Base 205M. Experiments independently address each scalar time series. Statistical models instantiate one model per metric; RNNs train one model per metric; foundation models prompt one scalar history without fine-tuning. | Conventional models provide an S1 organisational analogue. **No multichannel input, joint runtime-metric output, S2 or M1 experiment.** Pretraining across other series/domains is not joint learning of these runtime-resource targets. |
| D4 | pp. 5–7; §§3.2, 3.3.2–3.3.4 | Statistical methods: scalar input history to scalar-series 14-day forecast. RNNs: 14×1 look-back to 14 future values of that same metric; 14-unit recurrent layer, 14-unit bidirectional recurrent second layer, dense 14-output tanh layer. FMs: scalar-series historical array to 14 values using fixed pretrained weights. | A 14-value output is **multi-horizon, not multi-resource**. Reusing a pretrained network is PARTIAL generic sharing only; it does not supply M1 or an MTL/control contrast on the 110 metrics. No runtime-task joint loss/resource-head experiment or MTL/negative-transfer study is reported. |
| D5 | pp. 6–7; §3.3; Figs. 2–4 | Initial 90%=360 observations, remaining 40 for testing; rolling 28-observation windows split into 14 recent-context and 14 future positions. Paper reports 13 overlapping windows, 1,430 segments and 20,020 point forecasts per method. All methods use common test segments. | Horizon offsets 0…13 correspond to **leads 1…14 days**, not offsets interpreted as leads 0…13. Rolling evaluation is PARTIAL temporal evaluation, not prospective separately assessed Materna-like blocks. p. 6's 374…387 inclusive index statement is not fully consistent with its 13-window count; no silent repair or recomputation. |
| D6 | pp. 6–7; §§3.3.2–3.3.3 | SARIMA p,q,P,Q searched 0…3; differencing by ADF and lowest AIC, weekly seasonality 7; re-fit to data preceding each target. ETS trend via STL; Prophet no explicit parameter search. RNNs reserve last 10% of training for validation; Adam .001, plateau LR reduction, max 500 epochs, best validation loss, patience 50. Offline RNN training reported; online alternative only in linked package. | Chronological fitting/validation is explicit, but no training-only scaler and no explicit purge of overlapping selection windows. Leakage-control row PARTIAL, not the same strict nested/purged protocol and not a diagnosis that results are invalid. |
| D7 | pp. 7–8; §§3.3.4–3.4 | Foundation models receive all observations preceding the forecast, use default settings/horizon 14, TimesFM batch/core 32; Chronos mean forecasts. Underlying torch/numpy seed 42 and repeatability spot checks specified for FMs. Standardised MAE is primary; average ranks and paired tests assess methods. | Foundation results are zero-shot cross-domain generalisation, not resource-sharing transfer. The text does not give a corresponding multi-seed RNN replication protocol. |
| D8 | pp. 8–9, 13–14; §§4.1, 4.4; Table 2, Fig. 13 | Seasonal naive repeats the previous week's values; seasonal monthly mean averages corresponding weekdays over preceding month. Multi-step evaluation traverses all 14 lead positions and also highlights 1/7/14 days. No separate last-value-at-origin persistence comparator is evaluated. | Persistence row PARTIAL: explicit seasonal naive/reference baselines exist, but not our flat last-value baseline. No false NO for naive forecasting generally. |
| D9 | pp. 9–15; §§4.2–4.4, Threats, Conclusion; Figs. 5–14, Tables 3–5 | Per-series/model rankings and class-specific errors/metric-dependent exceptions are analysed. Single-infrastructure/generalisation, daily aggregation, fixed RNN settings and limited series length are explicit threats. Conclusion puts exogenous variables and multivariate forecasting in future work. | Resource/metric-wise reporting PARTIAL (different runtime aspects). Exceptions to foundation-model rankings are not a controlled shared-versus-independent negative-transfer test. No two sharing bridges or repeated external/temporal sharing-contrast replication. |
| D10 | pp. 5–7, 15; §§3.2–3.3, Threats/Conclusion | 200M/205M foundation sizes, per-series fitted instances, and qualitative costs of offline/online adaptation are stated. There is no empirical compute-time/parameter-consolidation-versus-accuracy experiment, deployment consolidation measurement or shared-target model-count trade-off. | Efficiency reporting PARTIAL, not our Claim G. Reusable pretrained weights must be acknowledged without inventing a resource-MTL comparison. Data is private (p. 16); no code execution was attempted here. |

Per-model organisation:

| Model | Inputs / targets | Fitting / shared weights | Classification justified by PDF |
|---|---|---|---|
| SARIMA | One metric history → 14 future values of it | Independently fitted per metric/rolling origin | Local/univariate |
| ETS | Same scalar-series organisation | Independently fitted per metric/rolling origin | Local/univariate |
| Prophet | Same scalar-series organisation | Independently fitted per metric/rolling origin | Local/univariate |
| FC-RNN | 14×1 → 14×1 | Independently trained per metric | Local/univariate |
| LSTM | 14×1 → 14×1 | Independently trained per metric | Local/univariate |
| GRU | 14×1 → 14×1 | Independently trained per metric | Local/univariate |
| TimesFM | One scalar history → 14 future values | Reused 200M pretrained weights, zero-shot, no target fine-tuning | Foundation/shared pretraining; not joint runtime-target MTL |
| Chronos-Bolt Base | One scalar history → 14 future values | Reused 205M pretrained weights, zero-shot, no target fine-tuning | Foundation/shared pretraining; not joint runtime-target MTL |

### 8. MMRP 2025 — full-text evidence ledger

All entries in this subsection refer to Paper M. This is the important correction to the prior abstract-only uncertainty: its mathematical forecast target is a **specific single series K**, not a jointly predicted resource vector.

| ID | PDF page; section; table/figure | Evidence inspected (paraphrase) | Interpretation for our study |
|---|---|---|---|
| M1 | pp. 8–9; §§5.1–5.2 | Alibaba PAI GPU July/August 2020: >6,500 GPUs/~1,800 machines, described raw 5-second records. Google 2011: 29 days in May, ~12,500 machines/>25M tasks. Sources are processed/aggregated separately into five-minute series. | Multiple providers YES; source population descriptions are not exact retained machine/sample cohorts. No selected VM IDs, final sample counts or prospective dynamic-scale cohort restriction is given. |
| M2 | pp. 8–9; §5.2; Figs. 4–5 | Alibaba selected table columns: job_id, task_index, machine_id, mean/max CPU, mean/max memory, mean/max disk I/O. Google adds mean/max network traffic. IDs/irrelevant columns are later removed; missing rows are dropped or interpolated, five-minute resampling/interpolation, moving-average decomposition, min–max scaling. Network may be derived from read/write fields. | Explicit processing/population restriction PARTIAL. Actual retained predictive channel list and derived-field lineage are not fully specified; **do not list IDs as proven network inputs** or invent which 20 input features remain. |
| M3 | pp. 3–4; §3, §4.1.1 | X is T×n multi-resource data, but F maps a historical window to **m future observations of target series X_K** and minimises error against x_(T+i,K). Univariate means one variable; multivariate means multiple feature channels. | This is a single-target contextual forecasting formulation, not evidence of joint CPU+memory prediction. The output index is horizon, not a resource-head index. |
| M4 | pp. 4–7; §§4.1–4.2; Figs. 2–3, Algorithm 1 | Covariate series enters CNN→multi-head attention→normalisation→BiLSTM encoder; encoded target series enters decoder CNN/self-attention, cross-attention to encoder, BiLSTM/add-norm, then dense target forecast. No parallel resource/task heads or combined multi-resource target loss is defined. | Multi-head attention means attention heads, **not resource heads**. Common internal feature extraction within a target predictor is not cross-target sharing. **No M1 arm in the reported architecture/experiment.** Decoder input timing/masking at inference is not fully specified; do not assume future targets were used or certify their exclusion. |
| M5 | pp. 9–14; §§5.2–6.4; Tables 3–10, Figs. 6–10; pp. 15–16 Figs. 11–14 | Both univariate and multivariate predictions are reported separately for CPU and memory in both providers; scalability figures explicitly label CPU Model and Memory Model. §3/Algorithm use a target series, not a joint resource vector. | **S1-like YES; S2-like PARTIAL.** Multivariate input→single target is directly supported; the exact all-channel mapping and disjoint parameter/model-fit inventory are not enumerated. Target-specific model organisation PARTIAL, not a fabricated exact model count or proven simultaneous multi-target system. This is meaningful S1–S2-related prior overlap, not a wholly confounded jump to M1. |
| M6 | pp. 9–13; §§5.2–5.3, Tables 2–10 | Look-back/encoder/decoder steps 20 (tested 10…30); Table 2 also declares 20 features, without reconciling that count with the earlier retained columns/univariate inputs. Main comparison captions specify future leads **1/10/20 five-minute steps = 5/50/100 minutes**. Algorithm is encoder–decoder multi-step, but exact direct-versus-autoregressive generation/masking is not fully defined. | Multi-horizon YES. Do not confuse input length, declared feature count and forecast lead. Appendix C's “100-step prediction” curves are not sufficient to invent a fourth horizon or rollout algorithm. |
| M7 | pp. 9–10; §§5.2–5.3; Table 2 | First 80% training, last 20% testing; validation mentioned for grid/random hyperparameter selection without a numeric validation split or allocation procedure. Min–max fit scope and preprocessing boundaries not specified. Hidden 64, four attention heads, two transformer layers, kernel 1, dropout .001, Adam .0001, MSE, batch 32 and 70 nominal epochs. | Chronological holdout exists, but leakage-controlled selection PARTIAL; no training-only scaling, purge or leakage-free decoder inference certification. Exact validation design remains genuinely unspecified. |
| M8 | pp. 9–11, 19; §5.3, §6.1, Appendix D | Main epoch sensitivity uses 10/25/50/100; table says 70; ablation uses 30. Batch sensitivity 32/64/128 and time-step settings are reported. No random seeds/repeated-seed protocol or specific early-stopping rule is given. | These are different reported experimental settings, not a single internally reconstructable frozen selection protocol. Do not silently use 70 for every result or turn its tuning into our prospective selection rule. |
| M9 | pp. 10–14, 17–18; §6.3, Appendix B; Tables 7–10 | Comparator families: ARIMA, SARIMA, LR, GRU, LSTM, BiGRU, BiLSTM, CNN–LSTM, ARIMA–ANN, MAG-D, attention-BiLSTM, LSTM encoder–decoder and hierarchical LSTM. Result tables have univariate/multivariate columns for each, but Appendix B describes generic families, not exact per-baseline channels/fit tensors. | Do not infer cross-resource MTL from any baseline name, or invent how ARIMA's labelled multivariate column was implemented. **Exact baseline input/parameter protocols remain unspecified**; reported tables do not introduce an all-input independent-versus-joint resource arm. No persistence/naive baseline in the complete inventory. |
| M10 | p. 11; §6.1, Tables 3–6; p. 19 Appendix D, Tables D.11–D.14 | Some multivariate results exceed univariate error: e.g. Alibaba memory, 100 epochs, lead 1 RMSE .00109 vs .00090 (Table 3); complete MMRP Alibaba-memory ablation, lead 1 RMSE .00262 vs .00192 (D.11). Other target/provider settings favour multivariate. | **Do not claim prior work shows uniformly beneficial contextual information.** These are reported table observations, not a new aggregation. They are not evidence that introducing cross-target shared parameters causes negative transfer: no S2–M1 contrast exists. Authors focus on model superiority/component ablations, not a replicated adverse shared-vs-independent boundary. |
| M11 | pp. 14–17; §§6.5–6.6; Figs. 11–14 | Inference seconds/sample and samples/second versus batch size for CPU and memory/provider models; qualitative training/deployment complexity and limited-resource constraints. No parameter inventory, independent-target→joint-model consolidation, quantified training-time comparison or adverse-accuracy/consolidation test. | Efficiency analysis PARTIAL and established prior overlap. Our Claim G must be about **co-occurring model/parameter consolidation and adverse shared accuracy**, not first cloud forecasting efficiency analysis. |
| M12 | pp. 17–21; Appendices A–D; Tables D.11–D.14, Figs. C.15–C.16 | A defines metrics; B lists baselines; C gives predicted/actual CPU/memory curves; D removes attention, decoder, CNN or replaces BiLSTM with feed-forward layers, retaining univariate/multivariate tables. | Component ablation is not target-sharing ablation. No missing appendix supplies a joint resource-head model or the S2–M1 bridge. Both providers reuse the comparison families, but there are no separately evaluated consecutive dependent blocks or prospectively retained directional rules. |

**MMRP control verdict:** the PDF supports a single-target univariate/contextual comparison; it does **not** support saying that this comparison necessarily changes target organisation to joint output. Input-only isolation is PARTIAL because exact feature assignment, independent-fit inventory and matched settings/support are incompletely specified. M1 and the second bridge are **NO within the complete reported experiment**, not UNCLEAR from failed access. “No M1 reported” is not a guarantee about unpublished code. This distinction removes the consequential complete-decomposition uncertainty without pretending every reproducibility detail is specified.

### 9. Final 21-row comparison matrix

| Feature | Ullah 2023 | Di Menna 2026 | MMRP 2025 | Our study |
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

All target-paper resolved cells map to the inspected evidence below. Read qualifications in the ledger, not just binary labels. In particular, D sharing is pretrained weight reuse, D persistence is seasonal naive, D temporal replication is overlapping rolling evaluation, U M1 is common-encoder joint output without explicit resource heads, and M S2 is a partially specified contextual single-target organisation. No consequential complete three-arm/second-bridge cell remains UNCLEAR. U's remaining UNCLEAR concerns chronology/scaler/selection reporting, **not** a hidden S1/S2 experiment.

| Matrix feature | U evidence | D evidence | M evidence |
|---|---|---|---|
| Own-resource input | U3/U5/U9, pp. 5–7, 12, 19 | D3/D4, pp. 5–7 | M3/M5, pp. 3–4, 9–16 |
| All-resource input | U3, pp. 5–6, Boxes I–II | D3/D4/D9, pp. 5–7, 15 | M2–M6, pp. 3–9, Tables 3–10 |
| Independent target models | U4/U5, pp. 7, 11–12 | D3/D4, pp. 6–7 | M3/M5, pp. 3–4, Figs. 11–14 pp. 15–16 |
| Joint resource outputs | U3/U4, pp. 5–7 | D3/D4/D9, pp. 5–7, 15 | M3/M4/M12, pp. 3–7, 17–21 |
| Shared representation | U4, pp. 5–7, Fig. 3 | D3/D4/D7, pp. 5–7 | M3/M4/M12, pp. 3–7, 17–21 |
| S1 arm | U3/U5/U9, pp. 5–7, 12, 19 | D3/D4, pp. 6–7 | M3/M5, pp. 3–4, Tables 3–10 |
| S2 arm | U3/U5/U9, pp. 5–7, 12, 19 | D3/D4/D9, pp. 5–7, 15 | M3/M5/M6, pp. 3–4, 9–16 |
| M1 arm | U3/U4, pp. 5–7 | D3/D4/D9, pp. 5–7, 15 | M3/M4/M12, pp. 3–7, 17–21 |
| S1–S2 comparison | U5/U9, pp. 11–20 | D3/D4/D9, pp. 5–15 | M3/M5/M6, Tables 3–10 pp. 11–13 |
| S2–M1 comparison | U5/U9, pp. 11–20 | D3/D4/D9, pp. 5–15 | M3/M4/M9/M12, pp. 3–7, 10–21 |
| Input isolation | U5/U9, pp. 11–20 | D3/D4, pp. 5–7 | M3/M5–M9, pp. 3–4, 9–13 |
| Sharing isolation | U5/U9, pp. 11–20 | D3/D4/D9, pp. 5–15 | M3/M4/M12, pp. 3–7, 19–21 |
| Multi-horizon | U3/U6, pp. 6, 10, 14–15 | D4/D5/D8, pp. 6–7, 13–14 | M6, Tables 7–10 pp. 12–13 |
| Persistence | U5/U8, pp. 7, 10–20 | D8, pp. 8–9, §4.1 | M9/M12, pp. 10–14, 17–21 |
| Resource-wise evaluation | U8, Tables 8–15 pp. 12–20 | D1/D9, Table 1 p. 4, §4.3 pp. 11–13 | M5/M10, Tables 3–10 pp. 11–13 |
| Multiple environments | U1/U8, pp. 4–6, 12–20 | D1/D9, pp. 3–4, 15 | M1/M5, pp. 8, 11–16 |
| Dependent temporal replication | U7/U8, pp. 8–20 | D5/D9, pp. 6–7, 15 | M7/M12, pp. 9, 17–21 |
| Negative-transfer analysis | U5/U8/U9, pp. 11–20 | D3/D9, pp. 5–7, 9–15 | M3/M10/M12, pp. 3–4, 11, 19–21 |
| Efficiency | U9, §4.2 pp. 12–13 | D10, §§3.2–3.3 pp. 5–7 | M11, §6.5–6.6 pp. 14–17 |
| Population restriction | U1/U2, §3.1 pp. 4–6 | D1/D2/D9, §3.1 p. 4, §5 p. 15 | M1/M2, §§5.1–5.2 pp. 8–9 |
| Leakage-controlled selection | U2/U7, pp. 5, 10–13 (unspecified) | D2/D5/D6, pp. 4, 6–7 | M4/M7/M8, pp. 7, 9–11 |

Our-study cells retain the primary manuscript section/equation/line evidence table in `novelty_audit.md`. The two PARTIAL isolation labels remain essential: S1/S2 change input width/parameter count and separately selected settings; S2/M1 change aggregate model/capacity/optimisation and target-specific versus common selected context. These are matched operational contrasts, not a pure causal parameter-sharing intervention or complete 2×2 factorial.

### 10–14. Arm and bridge overlap findings

- **S1:** absent from U's reported experiment; explicit per-metric local fit analogue in D; univariate target forecasting in M.
- **S2:** absent from U/D; **related and materially overlapping in M**, whose specific target K is predicted from multivariate covariates. Exact selected channels/disjoint fit inventory remain only partially documented.
- **M1:** U has a joint shared BiLSTM/common dense-output analogue, not our explicit resource-head construction; D and M do not report joint runtime/resource-target arms.
- **S1–S2 bridge:** M supplies related univariate/multivariate same-target comparisons. It must be cited as such, with reporting/matching qualifications; our study does not introduce contextual resource forecasting or its comparison with univariate forecasting.
- **S2–M1 bridge:** none of these complete reported experiments evaluates the independent all-input target model against a jointly resource-shared output model under the same all-channel availability. Combining U's architecture with M's comparison across papers is not an existing controlled within-study three-arm experiment.

### 15–20. Claims C–G and direct conflict

| Claim | Final verdict | Full-text-supported scope |
|---|---|---|
| C — close work combines sharing decisions | **PARTIALLY_SUPPORTED; materially narrowed** | U evaluates shared multivariate input–output architectures without either local/contextual bridge; D stays per-series; M **already makes a univariate/multivariate single-target comparison**. Thus neither “all three conflate input and target/sharing changes” nor the suggested blanket closest-studies sentence is defensible. The bounded gap is the **complete operational decomposition, especially the second bridge**, not absence of S1–S2 comparisons. Evidence U3–U9, D3–D9, M3–M12. |
| D — implemented S1/S2/M1 contrasts | **SUPPORTED as the reported design; no complete equivalent identified in these three** | Partial arms/first-bridge precedents must be acknowledged. No exact priority/first claim; our two isolation rows remain PARTIAL. U has no S2, D has no S2/M1, M has no reported M1 or second bridge. |
| E — replicated adverse sharing | **SUPPORTED as scoped empirical evidence, not a new phenomenon/mechanism** | None reports controlled resource-wise adverse S2–M1 transfer and replication of that contrast. U reports resource errors among joint models; D examines model-family exceptions; M has context-related worse cells but no introduced cross-target-sharing intervention. Generic negative transfer remains established by the wider audit. |
| F — retained external/dependent temporal contrasts | **SUPPORTED as a bounded design distinction** | U separately assesses two Bitbrains environments; M repeats univariate/multivariate/model comparisons across two providers; D has multiple applications and overlapping rolling origins. None retains **both sharing bridges** across development, external environments and separately evaluated dependent temporal blocks with our prospective rules. No “first multi-dataset/temporal evaluation” claim. |
| G — consolidation with adverse accuracy | **SUPPORTED as an implementation-specific evidence contribution** | U has qualitative batch/training discussion, D model sizes/local fit organisation, M inference-throughput/complexity analysis. None reports the independent-target→joint-resource model/parameter consolidation together with adverse controlled S2–M1 accuracy. No universal efficiency, equal-capacity, or inference-energy claim. |

**Direct novelty-conflict finding:** **no complete operational equivalent found in the three full-text reported designs; NOVELTY_CONFLICT_FOUND is not triggered.** Partial novelty overlap is substantial, especially M's first bridge and U's joint resource model. Our decomposition is not a new mathematical/MTL idea; its defensible contribution is explicit operational controls and retained boundary evidence. The result does not prove literature-wide novelty or rule out unreported implementations.

### 21. One manuscript-safe internal research-gap statement

Prior work has established multivariate cloud forecasting, joint resource prediction and shared models, as well as univariate/multivariate single-target comparisons. In the closest studies examined, Ullah et al. compare multivariate joint-output architectures, Di Menna et al. compare independently forecast runtime series and zero-shot foundation models, and MMRP compares univariate and multivariate single-target forecasting without a reported joint-resource sharing arm. These designs do not provide the complete within-study contrast between own-resource forecasting, independent target models with cross-resource inputs, and a jointly shared resource representation. The S2 bridge lets our study assess the value of additional resource histories separately from the implemented move to shared predictive representation, retaining these operational contrasts across development, external environments and dependent temporal replication, with explicit capacity, selection and population qualifications.

This is an internal bounded gap specification, not inserted manuscript prose. No architecture novelty, first claim or universal prior-work absence is implied.

### 22. Exactly four internal contribution specifications

1. Explicit matched S1/S2/M1 operational contrasts, including a shared-versus-independent all-input comparison, while acknowledging existing univariate/contextual comparisons and non-equal capacity/selection constraints.
2. Resource-, environment- and time-dependent assessment of contextual-input value across the specified development, external and dependent-temporal evidence roles and eligible populations.
3. Replicated adverse shared-representation evidence for the evaluated conventional shared-LSTM implementation relative to independent all-input targets, without asserting a measured interference mechanism or universal MTL failure.
4. Joint reporting of model/parameter consolidation, observed fitting workload and adverse accuracy/applicability boundaries for that implementation, without extrapolating to unmeasured latency, energy, hardware or excluded populations.

### 23. Updated prohibited claims

- First multivariate, recurrent, multi-output, shared/MTL or contextual resource forecaster; first univariate/multivariate comparison; first use of Bitbrains or multi-provider evaluation; first negative transfer or forecasting efficiency analysis.
- MMRP necessarily forecasts CPU/memory jointly, necessarily changes target sharing in its univariate/multivariate comparison, or lacks an S1–S2-related control. Its attention heads are not resource heads.
- Di Menna jointly forecasts the 110 metrics, trains a resource-task MTL model, lacks naive baselines, or its zero-shot pretrained weights are equivalent to our M1 learning intervention.
- Ullah's LSTM baseline is a separately fitted single-resource S1/S2; its joint model is identical to our explicit head topology; its Rnd population/cadence inconsistencies can be silently corrected.
- No prior study separates information and parameter sharing; no equivalent exists anywhere; the trio is proven first; inaccessible/unreported details are proven absent.
- Parameter-equal causal isolation, a complete 2×2 factorial, diagnosed gradient conflict/capacity shortage, independent Materna blocks, unrestricted population applicability, universal harmful sharing or universal deployment savings.

### 24. Novelty-risk assessment

| Dimension | Risk of claiming novelty | Reason |
|---|---|---|
| Runtime forecasting | HIGH_RISK | Directly established, including D's empirical model comparison. |
| Multivariate forecasting | HIGH_RISK | U and M explicitly establish it; M contains first-bridge-related comparisons. |
| Shared/MTL forecasting | HIGH_RISK | U's common joint representation and the wider audited MTL literature pre-exist. |
| Controlled contrast design | MODERATE_RISK | No complete equivalent in these three, but partial arms/bridge overlap and our control qualifications preclude broad conceptual priority. |
| Replicated boundary evidence | MODERATE_RISK | No equivalent retained sequence found here; accurately describing our evidence is defensible, but no exhaustive rarity/priority claim is justified. |
| Accuracy–efficiency boundary | MODERATE_RISK | Efficiency is established; specific co-occurrence of consolidation and adverse controlled accuracy is the scoped evidence addition. |

**Overall: MODERATE_RISK.** The full-text access gate is cleared and no complete conflict is found; the case rests on rigorous operational/replicated evidence, not architecture, generic sharing or an invented absence of contextual forecasting.

### 25–32. Files, preservation and final status

25. `novelty_audit.md`: dated user-PDF clearance, updated 21-row matrix/evidence links, narrowed C, updated D–G/risk/prohibitions. Historical access limitation retained, explicitly superseded.
26. This file: current full-text report, identity/hash record, complete-method ledgers, per-model organisation, matrix/evidence map and final decisions; earlier access-blocked report retained below.
27. `reference_verification.md`: only an access-status/page-count addendum and current-state pointer; verified bibliographic ledger retained.
28. `references.bib`: **0 changes**, **36 entries**; supplied first pages expose no genuine bibliographic error requiring a correction.
29. `manuscript.tex` substantive changes = **0**; Sections 3–6, title and citation insertions unchanged; no Introduction/Related Work/Discussion/Abstract drafted into the manuscript.
30. Frozen scientific artifacts modified = **0**; experiments/scientific recomputation = **0**.
31. Commit = **no**.
32. Push = **no**.

Protected SHA-256 values remain: manuscript `fb1636c78476b9e9e136d3e1acacacb1fcca2a4664c859d9261e9b82baf8c75b`; bibliography `cbceabcca409cac51dad9b21db2caedb7c20a52c61d64df26bedb0cbd7011b70`; Stage 6A reuse audit `85dd99c96d52c79164fb51f8724f21ebdfba04dec0cb5ba61f202506efad48c4`. HEAD remains `fee20c316040c57b69ba12a193530c955b539771`. Only the three authorised literature audit files were edited; temporary render files are not manuscript/scientific artifacts. The final validation rechecks these invariants.

**Current verdict: STAGE_6_PASS. STOP. No drafting stage begun.**

---

# Historical Stage 6B bounded-access report — superseded, retained for transparency

Everything below records the earlier failed-access state, not the current verdict. The user-supplied full-text audit above removes that access blocker while preserving genuine reporting uncertainties.

# STAGE 6B CLOSEST-PAPER FULL-TEXT NOVELTY CLEARANCE REPORT

Date: 16 October 2026. Internal evidence/decision record only. Locked title: *Disentangling Information Sharing in Multi-Metric Runtime Forecasting for Cloud Software Systems*. No manuscript prose is drafted here.

## 1. Status

**FULL_TEXT_REQUIRED_FROM_USER. Stage 6 remains blocked.** The bounded legitimate refresh did not obtain any of the three complete methods. No consequential S1/S2/M1 arm can be cleared from abstracts. A direct equivalent is neither established nor excluded; this is not STAGE_6_PASS and not a demonstrated NOVELTY_CONFLICT_FOUND.

## 2. Ullah full-text access status

**FULL_TEXT_REQUIRED_FROM_USER** — Farman Ullah, Muhammad Bilal, Su-Kyung Yoon (2023), *Intelligent time-series forecasting framework for non-linear dynamic workload and resource prediction in cloud*, Computer Networks 225, 109653; [DOI 10.1016/j.comnet.2023.109653](https://doi.org/10.1016/j.comnet.2023.109653).

Publisher article/PDF requests returned 403. Institutional records exposed no copy; Lancaster explicitly records full text unavailable. Public publisher XML contained metadata only, and FULL view required an API key. This is an access finding, not an absence-of-method finding.

## 3. Di Menna full-text access status

**FULL_TEXT_REQUIRED_FROM_USER** — Federico Di Menna, Luca Traini, Vittorio Cortellessa (2026), *Forecasting software runtime metrics: A comparative study of classical statistical, neural network, and foundation models*, Journal of Systems and Software 240, 112937; [DOI 10.1016/j.jss.2026.112937](https://doi.org/10.1016/j.jss.2026.112937).

Fresh priority OA check completed. Publisher metadata explicitly confirms CC BY 4.0 open access. Nevertheless publisher article/PDF requests failed, Chrome showed a human-verification challenge, and the public FULL API required a key. The author publication entry linked the DOI only. OpenAlex discovered [L'Aquila's institutional record](https://ricerca.univaq.it/handle/11697/284000), which also returned a challenge/403. Neither challenge was solved. OA status does not establish that methods were actually inspected. The ICPE predecessor and other Traini PDFs were not substituted.

## 4. MMRP full-text access status

**FULL_TEXT_REQUIRED_FROM_USER** — Shivani Tripathi, Priyadarshni, Rajiv Misra, T. N. Singh (2025), *Multilayer multivariate forecasting network for precise resource utilization prediction in edge data centers*, Future Generation Computer Systems 166, 107692; [DOI 10.1016/j.future.2024.107692](https://doi.org/10.1016/j.future.2024.107692).

Publisher article/PDF requests returned 403; public XML was metadata only, FULL view required a key. The official GitHub tree did not supply an article or complete implementation; README says code is available on request. No message, purchase, authentication or circumvention was attempted.

## 5. Exact sources inspected

The [fresh reference-verification ledger](reference_verification.md#stage-6b-fresh-three-paper-access-verification) records all article PIIs, exact endpoint patterns, response codes, metadata byte counts, institutional URLs, the author site, official GitHub and discovery records. It distinguishes primary content from discovery metadata. The three full publisher PDF URLs were tested directly. No target PDF was downloaded; there are consequently no invented PDF page/section citations or claims of PDF visual inspection.

## 6. Ullah resolved method cells

**0 newly resolved; 21/21 focused fields UNCLEAR.** Required full-text checks:

- Exact resource/input variables and joint tensor/window construction; simultaneous all-resource histories; exact jointly predicted variables; shared layers and head topology.
- Every baseline's input set, target set and separately fitted versus shared parameter organisation. Identify actual S1, S2 and M1 equivalents and both contrasts; do not infer a missing bridge from architecture names.
- fastStorage/Rnd populations, VM/sample selection and whether environments are reported separately; chronology, validation, scaler-fitting scope, horizon strategy, history-window candidates and persistence.
- Resource-wise degradation/negative transfer, temporal replication and parameter/model-count analysis.

Why it matters: C requires knowing which dimensions changed; D requires the actual three arms; E requires a comparable shared-versus-independent target baseline and resource-wise adverse outcomes; F requires retained controls and dependent-block design; G requires joint accuracy/consolidation accounting. Bitbrains overlap makes missing S2/control evidence consequential. Abstract-level multi-input/multi-output claims establish topic overlap only.

## 7. Di Menna resolved method cells

**0 newly resolved; 21/21 focused fields UNCLEAR.** Required full-text checks:

- Introduction and research questions; exact data collection/metric catalogue; whether 110 metrics are independent series, simultaneous inputs or joint targets.
- Each forecasting model's input/output organisation, shared representations, cross-metric training and MTL discussion/evaluation. Distinguish pretrained shared weights from a matched cross-resource M1 arm.
- Local/context/shared arms and equivalent comparisons; exact horizons, naive/persistence definitions, chronological splits, validation, selection and scaling.
- Resource-wise adverse transfer, temporal/source roles, parameter/compute/model-count comparisons and limitations.

Why it matters: the model-family framing alone cannot rule out S1/S2/M1 controls (C/D). Metric-wise exceptions are not automatically an operational negative-transfer experiment (E). A long observation period is not necessarily retained dependent temporal replication (F); model-family cost reporting is not automatically the same consolidation/accuracy contrast (G). Only the journal full methods can resolve this; the earlier conference protocol cannot be transferred.

## 8. MMRP resolved method cells

**0 newly resolved; 21/21 focused fields UNCLEAR.** Required full-text checks:

- Alibaba and Google variables and exact definitions of univariate/multivariate: input channels, target channels, joint outputs and one-target-at-a-time models.
- Whether each resource has an independently trained all-input model; whether parameters are shared across targets; actual S1/S2/M1 equivalents and whether changing univariate/multivariate also changes output organisation and sharing.
- Exact horizons, context lengths, chronological split, scaling, validation/model selection, baselines, persistence and architecture ablations.
- Resource-wise degradation, temporal/source replication, population restrictions and parameter/compute reporting.

Why it matters: the existence of a univariate/multivariate comparison does not answer whether input scope alone changes (C) or an S2 bridge exists (D). Hybrid components and gains against other algorithms do not establish comparable negative-transfer analysis (E), retained temporal controls (F), or model consolidation with adverse accuracy (G).

## 9. Focused S1/S2/M1 comparison matrix

The complete 21-row, five-column [focused control matrix](novelty_audit.md#stage-6b-focused-control-matrix) is the authoritative Stage 6B matrix. Every target-paper cell is UNCLEAR. The adjoining evidence table maps every resolved Our study cell to an inspected manuscript section/equation/source line. No target-paper YES or NO is asserted.

Our study has all three arms and both explicit contrasts. Its strict input-isolation and representation-isolation rows are PARTIAL: input dimensionality/parameter counts and separately selected settings change for S1/S2; aggregate capacity/model count, optimisation and common-versus-target context choice change for S2/M1. It is a matched operational decomposition, not a complete two-by-two factorial, parameter-equal causal intervention or gradient-mechanism test. These are audit qualifications, not changes to science or manuscript text.

## 10. Claim C updated verdict

**PARTIALLY_SUPPORTED.** Earlier inspected full-text cloud examples support a bounded observation that some comparisons change input and target/sharing organisation together. The three-paper-specific statement is **not cleared**. Do not write “in the closest three studies we inspected, designs commonly combine the dimensions”: their methods were not inspected. No literature-wide absence or frequency claim follows from this targeted audit.

## 11. Claim D updated verdict

**SUPPORTED as a description of our implemented contrasts; prior-equivalence clearance UNRESOLVED.** S1/S2 compare access to additional channels with separate target models; S2/M1 compare separate versus jointly shared implementations with all-channel availability. Strict causal isolation is qualified as in item 9. Whether any target already contains an operationally equivalent three-arm experiment remains UNCLEAR. No first/priority or complete-factorial claim is allowed. No direct conflict has been demonstrated, but lack of access cannot exonerate overlap.

## 12. Claim E updated verdict

**PARTIALLY_SUPPORTED as a scoped empirical contribution.** Our contribution specification can concern replicated operational adverse sharing relative to S2 in the evaluated conventional design. Negative transfer itself, its forecasting study and selective-sharing ideas are established. Comparable target-paper degradation analyses remain unresolved. Capacity shortage, gradient conflict, task interference or data-regime causes remain hypotheses, not measured mechanisms.

## 13. Claim F updated verdict

**PARTIALLY_SUPPORTED.** Retaining the same operational contrasts across separately evaluated external environments and dependent temporal blocks is an accurate specification of our study. Its priority relative to these three papers is unresolved. Multiple datasets, a long trace, an ordinary chronological split and a prospective dependent-block replication must not be conflated; Materna blocks are not independent datasets.

## 14. Claim G updated verdict

**PARTIALLY_SUPPORTED as a scoped empirical contribution.** Our model/parameter inventories and recorded fitting cost can be considered alongside adverse accuracy for this implementation. General accuracy/efficiency trade-offs are not new, and comparable target-paper accounting remains unresolved. No universal inference-time, energy, hardware, deployment-cost or equal-capacity claim is justified.

## 15. Direct novelty conflict / closest known overlap

**No new direct three-arm conflict established; exclusion is also unproved.** Topic-level overlaps remain the earlier publisher-record findings: Ullah is the highest dataset/resource overlap because of Bitbrains and multi-resource forecasting; JSS directly overlaps runtime-metric forecasting and model comparison; MMRP overlaps multivariate resource forecasting and multiple provider datasets. Those labels are not verified control equivalents.

Already established in the prior audit: multivariate covariates, joint resource outputs, recurrent forecasting, shared/task-specific forecasting, resource-dependent transfer and accuracy/cost considerations. This study definitely does **not** introduce these general ideas, a new recurrent architecture, cloud MTL, Bitbrains forecasting or multi-provider evaluation. No claim to introduce negative transfer is permissible. Earlier full-text precedents and their limits remain in `novelty_audit.md`; Stage 6B does not recast them as newly inspected sources.

## 16. Defensible research-gap statement

**Research question, not a cleared literature-absence claim:** evaluate what additional resource histories and an implemented shared predictive representation each contribute under matched resource/horizon/temporal support, and whether the resulting accuracy/consolidation boundary persists across the specified external environments and dependent temporal blocks. Our S2 bridge makes the two operational contrasts explicit. Differentiation from equivalent controls in Ullah, Di Menna and MMRP remains pending their full methods.

This is the defensible gap specification for internal planning. Do not turn it into an asserted first, an established omission of these three papers or manuscript Introduction/Related Work prose before the gate is cleared.

## 17. Four defensible contribution specifications

These describe this study's work, not exclusive priority:

1. An explicit S1/S2/M1 comparison separating own-resource inputs, all-resource inputs with independently trained targets, and a shared multi-resource LSTM, evaluated using matched resource/horizon/support contrasts and the stated capacity/selection qualifications.
2. Resource-, environment- and time-dependent assessment of contextual-input value, retaining development/external/dependent-temporal source roles and prospectively restricted populations.
3. Replicated empirical adverse representation-sharing evidence for the evaluated conventional implementation relative to the independent all-input bridge, distinguished from the contextual-input contrast and from unmeasured causes.
4. Joint reporting of model/parameter consolidation, observed fitting workload and accuracy/applicability boundaries, without extrapolating runtime or performance to other architectures, hardware or excluded populations.

## 18. Prohibited claims updated

- Any of these three papers lacks S1, S2, M1, persistence, leakage controls, negative-transfer analysis or efficiency accounting merely because its methods were inaccessible.
- The three closest full texts were inspected, all consequential cells were cleared, or no equivalent exists.
- First multivariate/joint/cloud/MTL/recurrent resource forecaster; first Bitbrains/multi-provider test; first negative transfer or accuracy/efficiency trade-off; first S1/S2/M1 decomposition without direct priority evidence.
- All multivariate methods share cross-target parameters; channel-independent processing necessarily means independently trained target models; an abstract's “univariate/multivariate” label determines the arms.
- A pure causal effect of representation sharing, parameter equality, full two-by-two factorial, measured gradient conflict, independent Materna blocks or universal adverse sharing.
- Unrestricted-population claims, new untested architecture comparisons, universal latency/energy savings or a mechanism diagnosis from the present results.

## 19. Novelty risk

**MODERATE, provisional.** The proposed empirical design/boundary contribution is plausibly scoped; architectural and generic-phenomenon novelty are unsupported. Consequential methods uncertainty prevents downgrading this to LOW or claiming clearance. This is a qualitative editorial judgement, not a quantified probability that the candidate is original. No evidence justifies alleging direct duplication or concealing the unresolved risk.

## 20–24. Preservation and stop

20. `references.bib` additions = **0**, deletions = **0**, modifications = **0**; current entry count **36**.
21. `manuscript.tex` substantive changes = **0**; Sections 3–6 unchanged. No Introduction, Related Work or Discussion drafted.
22. Frozen scientific artifacts modified by this task = **0**; experiments/new scientific analyses = **0**.
23. Commit = **no**.
24. Push = **no**.

Only the two permitted audit records and this optional internal clearance file were edited. Protected-file hashes and endpoint observations are recorded in `reference_verification.md`. PDF inspection was prepared under the PDF skill, but no target PDF was obtained and no full-method or page-based inspection is claimed.

Required next action: supply legitimate full copies of the three DOI-identified papers, including methods, experiments, relevant tables/figures, limitations and any appendices defining the arms. No additional broad search or experiments are requested. Stop this stage here.

FULL_TEXT_REQUIRED_FROM_USER

---

End of historical access-blocked record. **Current resumed full-text verdict is the report at the top: STAGE_6_PASS.** No further manuscript stage has begun.

STAGE_6_PASS
