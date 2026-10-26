# Stage 19E inspected evidence and coding boundary

Inspected 23 October 2026. No bibliography entry was added or changed.

## Sources

U, D and M denote the current full-text U/D/M ledgers in
`manuscript/jss/literature/closest_papers_fulltext_clearance.md`, sections 6–9.
The dated supplied-PDF clearance supersedes the historical access-blocked
sections in that file and `novelty_audit.md`. It includes original PDF identities,
hashes, page-specific methods/results and the completed reported-arm inventory.
The three original Downloads paths are no longer available; this stage uses
the preserved full-text inspection evidence, not a claim to have reopened
those originals. Relevant sources and all table cells are mapped in
`table_cell_evidence.json` by `verify_revision.py`.

- U: Ullah 2023, DOI 10.1016/j.comnet.2023.109653. Context/targets U3;
  model organisation U4–U5; comparison/transfer limits U5/U8/U9; costs U9.
- D: Di Menna 2026, DOI 10.1016/j.jss.2026.112937. Organisation D3–D4/D7;
  reported comparisons D9; efficiency-related scope D10.
- M: Tripathi 2025, DOI 10.1016/j.future.2024.107692. Target/architecture
  M3–M4; contextual single-target precedent and fit-inventory qualification M5;
  comparison/transfer scope M9–M12; inference measurements M11.
- N: Nikentari and Wei 2022, DOI 10.1109/ICAC55051.2022.9911071.
  Fresh inspection of the six-page paper embedded at PDF pp. 118–123 in the
  [author thesis](https://etheses.whiterose.ac.uk/id/eprint/36236/1/Multitask%20Learning%20Using%20Nonlinear%20Model%20for%20Forecasting%20Task.pdf):
  N1 = paper pp. 1–2, Introduction/contribution 3; N2 = paper p. 3, §III,
  Eq. (3) and shared-layer description; N3 = paper p. 5, §IV/Fig. 2.
  These corroborate the prior `novelty_audit.md` NARMAX inspection. N does not
  establish a separately fitted all-input target bridge. Transfer discussion
  is the paper's reported analysis, not our endorsement of a causal diagnosis.
- T: MTLinear, [official AISTATS record](https://proceedings.mlr.press/v258/nochumsohn25a.html)
  and [author full text](https://arxiv.org/html/2502.03571v2).
  Fresh inspection: T1 = §2, Eq. (4); T2 = §§4.1–4.4; T3 = §5.2,
  grouping criteria/Fig. 4 and Table 6; T4 = §5.3/Appendix C.4.
  The own-history temporal-weight mapping is distinct from channel mixing;
  grouping endpoints are not an all-input independent-target control.
- B: Bi 2019, DOI 10.1109/LRA.2019.2899224. Freshly inspected
  [author-institution abstract](https://digitalcommons.njit.edu/fac_pubs/7495/)
  and the existing Stage 6 abstract/method-excerpt audit. The DOI full text
  was inaccessible; the author-site PDF route also did not yield accessible
  full text. B1 = institutional abstract: workload decomposition, stochastic
  configuration networks and training-speed comparison. Detailed input,
  sharing and comparator cells remain **not established**, not NO.
- O: this manuscript, unchanged Sections 3–4, Figures 1–2 and Results §§5.2/5.6;
  its unchanged Stage 18C1 synthesis authenticates the completed controls.

## Coding decisions

The six dimensions are contextual input/target organisation, independent
all-input target models, cross-target shared parameters, explicit
single-task/shared comparison, adverse-transfer analysis, and
efficiency/consolidation evidence. All seven rows have six trace entries.

NO is limited to a feature excluded by an inspected reported design. It is
not inferred from a title, an abstract's silence or missing access. PARTIAL
records specified overlap or incomplete matching; not established records
an unresolved cell. Pretrained reuse is not joint learning across the evaluated
target series. Multiple horizons are not multiple resource targets. Shared
temporal weights need not mix channels. Efficiency PARTIAL acknowledges real
but limited timing, cost or network-reduction evidence; YES is not a claim
that every study measures the same operational quantity. Likewise, transfer
analysis codes cover different reported analyses, not causal equivalence.

The prior NO/PARTIAL values for U/D/M are supported by the complete reported
design inventories. N's all-input independent-fit inventory and B's detailed
method/comparator cells are intentionally not resolved by speculation.
No exhaustive literature search, priority claim, architectural novelty claim,
new experiment or scientific statistic is asserted.
