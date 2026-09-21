# Clean Environment Reproduction Report

Date: 2026-08-04  
Config: `configs/final_fgcs.yaml`  
HEAD at report time: see git (pre-freeze machinery commits)

## Procedure

1. Create a temporary virtualenv (see `scripts/reproduce_clean_env.sh`).
2. `pip install -r requirements.txt`
3. `python scripts/tt_cli.py test`
4. `python scripts/validate_final_config.py --config configs/final_fgcs.yaml`
5. `python scripts/reproduce.py --tier smoke --config configs/final_fgcs.yaml`

## Results (project `.venv` dry run — authoritative for this checkpoint)

| Check | Result |
|-------|--------|
| Tests | **72 passed** |
| Config validator (pre-freeze) | **OK** (PENDING freeze markers noted) |
| Config validator `--require-frozen` | **Rejects PENDING** (expected) |
| Dataset fingerprint | `bf06dc0e7fe6ff5e` (matches config) |
| Smoke tier | **OK** (~30s): memory_um × {persistence, ridge} × h1 × fold0 |
| Coherence after recon | Verified for non-independent methods |
| Table + figure | `results/final/tables/main_comparison.*`, `figures/coherence_before_after.pdf` |
| Smoke claim eligibility | **false** while freeze markers are PENDING |

## Clean temp-venv

`scripts/reproduce_clean_env.sh` performs the same sequence in a disposable venv and deletes it afterward. Run when network/time permits:

```bash
bash scripts/reproduce_clean_env.sh
```

Torch + LightGBM install from a cold venv is the dominant cost.

## Final tier

`python scripts/reproduce.py --tier final` **refuses** until `freeze_commit` / `freeze_tag` are real (`--require-frozen`).

## Notes

- Smoke artifacts under `results/final/` are machinery validation only (`evaluation_role: smoke_validation`).
- Do not mix smoke rows into FGCS claim tables after freeze; re-run `--tier final` into a clean final tree or overwrite with frozen metadata.
