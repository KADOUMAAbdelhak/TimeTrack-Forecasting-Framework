# Stage 3K — Registration package and §11 audit

Basis: tag `fgcs-v03-execution-candidate` (commit `fd45c2d5`), the author decisions of 2026-11-12 (C1–C9 approved, N = 4), and v0.3 §11. No scientific fit, evaluation or analysis ran. No runtime journal exists, and nothing was registered externally.

## Registration package

The package is in `registration/`. It is built and re-verified by `python -m fgcs_strengthening_v03.build_registration --build | --verify`; verification recomputes every generated file from the repository and compares bytes.

**Package digest: `f6bd4ba54b1ea476f33c5e2e8ae1a068fe692cf28b4b915a95e78721648a7d82`** (recomputed and verified).

| File | Content |
|---|---|
| `execution_seal.json` | `execution_fingerprints()`: 36 inputs, 60 sources, digest **`6ff4cfc0b155868e19dd39e85150129afebf448e71730a444b5afe3d7c8aa152`** |
| `schedule.json` | Schedule digest `ad6c1693…7dfee2`, 283,635 units by phase; the budget from `validate_schedule()`; 206,000 unique identities (list SHA-256 `c84610a8…7681d`); the 96 canary and 30 pilot identities |
| `analysis_catalogue.json` | All 832 registered analysis rows, 156 inferential; 1,085,800 required cells; 81,650 evaluation identities (list hash); the 15 historical tables |
| `systems_population.json` | C2: 182 partitions, 1,380 deployments |
| `host_manifest.json` | Frozen execution host (below) |
| `PACKAGE.json` | SHA-256 of every file above and of the referenced files; host summary without hostname; author decisions; status |

Referenced by hash:

- the v0.3 protocol (`7b8f80be…`);
- `protocol_v03.json` (`59cda69a…`);
- `historical_results_v03.json` (`32d9dd3d…`);
- the approved clarifications;
- the Stage 3J scope;
- the feasibility estimate.

**Frozen host.** Apple M3, 8 cores (4 performance + 4 efficiency), 24 GiB, Darwin 25.6.0, low-power mode off. Python 3.13.2, NumPy 2.5.1, PyTorch 2.13.0, LightGBM 4.7.0, scikit-learn 1.9.0. Conditions are CPU, 1 worker per process, every thread setting = 1, verified live in a fresh process.

- Hardware hash `4438e9a9…`; software hash `cd5369a4…`.
- Load average at freeze: 1.71 / 1.98 / 2.45.
- `host_manifest.json` contains the machine's hostname. For a public registration, upload the manifest's hash and the hostname-free summary in `PACKAGE.json` rather than the file itself.

## §11 audit

**Identity checks:**

- 206,000 unique identities with no duplicates.
- Every schedule dependency resolves to an earlier phase.
- The 30 modern pilots are exact members of the reduced modern study. The 96 canary units are exact registered inner identities.
- The orchestrator's 81,650 evaluation identities are **exactly the set** the analysis catalogue reads.
- The 4,375 diagnostic identities the analysis reads are scheduled.
- All 1,380 systems deployments are registered final identities.

**Mathematical checks:**

- `validate_schedule()` reproduces every v0.3 total.
- The analysis dry run gives 24 primary Holm tests; PCGrad, GradNorm and checkpoint families of 8; 12 gradient-association tests; 8 BH families of 12 (156 inferential); 676 descriptive rows.
- 17 key figures appear verbatim in the registered text, among them 91,000; 9,100; 12,600; 8,400; 2,100; 25,200; 3,000; 30; 174,500; 126,000; 149,300; 275,300; 1,747,200; 4,200 requests; 24 primary tests; 10,000 replicates; and seed 20261110.
- The statistics, bootstrap, multiplicity and estimand unit tests pass.

**No-leakage checks:**

- Outer-test windows are reachable at exactly two code sites, `OuterEvaluator._score` and `LightGBMRunner.evaluate`.
- Systems benchmarks read outer-test inputs only, with no targets. The historical reader reads origin IDs only.
- Epoch and configuration selection read inner validation outcomes only.
- **Finding, fixed in this stage.** The orchestrator enforced C6, but `OuterEvaluator.evaluate`, `LightGBMRunner.evaluate` and `TransferRunner.evaluate` were public and could be called directly before fit closure. Both evaluators now refuse unless the journal holds the fit-closure record covering every fit phase. A new test checks all three entry points and confirms that nothing is materialised. Clarification C9 now records this, and refers to the package for the seal digest instead of a stale hard-coded value.

**Preservation checks:**

- Outside `.git`, the 449,584-entry inventory is byte-identical to the pre-Stage-3I baseline (`589f058f…`, both sides). The only `.git` changes are the objects, refs and logs from the authorized commit and tag.
- The 15 historical tables are unchanged since the frozen tag.
- The pre-existing manuscript edits were not touched.
- No runtime directory or bytecode remains.

**Regression:** 168 tests pass in 91 s, 1 more than Stage 3J. Static, whitespace and unused-import scans are clean. LSTM trajectories remain byte-identical to the pre-3I reconstruction under the same seal.

**Independence.** These checks were re-derived by the implementing agent: from the protocol text, from separate enumerations, and from static call-site analysis. §11 asks for independent checks, so a reviewer who did not write the implementation should repeat them before external registration. `build_registration --verify` and the commands in this report make that repeatable.

## State after Stage 3K

- The working tree differs from `fgcs-v03-execution-candidate`: the C6 gate (2 sources, 5 tests), C9 wording, `build_registration.py` and `registration/`. The registration needs a commit and tag that contain the package.
- Before external registration:
  - The author confirms approval of v0.3 itself (§11 treats author approval and registration as separate acts).
  - An independent reviewer repeats the audit.
  - The author registers the package digest and seal digest externally.
- Stage 4A (the first execution):
  1. Verify that the live host equals `host_manifest.json`.
  2. Create the runtime journal with `execution_fingerprints()`, whose digest must equal `6ff4cfc0…`.
  3. Run `certify` and `canary` with 4 workers, then stop at the canary gate.

## Protocol deviations

None.

**Wall-clock:** start `2026-11-12T17:35:56+02:00` (first repository check), end `2026-11-12T17:46:02+02:00`, elapsed **10 min 6 s**.

STAGE03K_PASS
