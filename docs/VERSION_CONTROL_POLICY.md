# Version Control Policy

## Official repository

- **URL:** https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework.git
- **Primary branch:** `main`
- **Local path:** `/Users/fgtek002/TimeTrack`

This remote is the authoritative codebase for TimeTrack forecasting development.

## Commit and push workflow

For each coherent implementation unit:

1. `git status`
2. Implement one logical unit
3. Run relevant tests (`python scripts/tt_cli.py test` or targeted pytest)
4. Inspect `git diff` / `git diff --stat`
5. Stage only intended paths (`git add <paths>`)
6. Inspect `git diff --cached`
7. Commit with a descriptive message
8. `git push origin main`

Do not accumulate unrelated features in one commit. Push after each checkpoint.

## Ignored-data policy

**Never commit:**

- Raw TimeTrack CSVs (project-root or `data/raw/`)
- Virtual environments (`.venv/`, `venv/`)
- Caches (`__pycache__/`, `.pytest_cache/`, etc.)
- Processed intermediates (`data/interim/`, `data/processed/`, parquet/HDF5)
- Model checkpoints (`results/**/models/`, `*.pt`, `*.joblib`, …)
- Raw prediction matrices (`results/**/predictions/`)
- Optuna / tuning databases (`results/**/tuning/*.db`)
- Logs and secrets

**May commit (lightweight):**

- Aggregated metric CSVs and Markdown/LaTeX tables
- Configs, manifests, protocol docs
- Compact statistical summaries
- Essential figures within GitHub size limits
- Pilot raw-run **JSON metadata** (small per-run summaries), not prediction dumps

GitHub rejects files > 100 MB. The ~316 MB CPU-core CSV must never be tracked.

**Git LFS:** not used by default. Introduce only with a written justification in this file.

## Generated-artifact policy

| Artifact | Git | Archive outside Git |
|----------|-----|---------------------|
| Leaderboards / summary CSVs | Yes (when compact) | Optional |
| Pilot/final run JSON metadata | Yes if small | Optional |
| Predictions / model weights | No | Yes |
| Optuna SQLite DBs | No | Yes |
| Large figures | Prefer external or compressed essentials | Yes |

Dataset identity is preserved via **fingerprints** in manifests (`dataset_fingerprint`), not by redistributing raw files.

## Safety rules

- **No force-push** to `main` (`--force` / `--force-with-lease`)
- No history rewrite of pushed commits for cosmetics
- No `reset --hard`, `clean -fd`, or blanket restore unless explicitly authorized
- Never commit credentials, tokens, or machine-specific secret env files

## Freeze-tag procedure

Before final FGCS experiments:

1. Clean working tree
2. Full test suite green
3. Commit + push freeze implementation
4. Annotated tag, e.g. `experiment-freeze-v1`
5. `git push origin experiment-freeze-v1`

Do not tag ordinary development commits as experiment freezes.

Every final result manifest must record: repository URL, branch, commit hash, freeze tag, dataset fingerprint, configuration hash, dependency-lock hash.

## Associating experiments with commits

Run JSON / manifests must include (when available):

- `git_commit` (full hash)
- `git_branch`
- `repository_url`
- `dataset_fingerprint`
- `config_hash`
- `experiment_stage` / `eligible_for_final_claims`

## Restoring datasets locally

1. Obtain TimeTrack CSV files from the authorized dataset source (not this Git repo).
2. Place them either at the project root **or** under `data/raw/` with the expected filenames.
3. Verify with `python scripts/tt_cli.py audit` and compare `dataset_fingerprint` to recorded manifests.

## Archiving heavy artifacts outside Git

Store predictions, checkpoints, and tuning DBs on local or institutional storage keyed by freeze tag + commit hash, e.g.:

```text
archives/TimeTrack-Forecasting-Framework/<tag-or-commit>/results/{pilot,development,final}/...
```

Record the archive location in the corresponding stage `MANIFEST.json` without embedding secrets.

## Unresolved administration

- **LICENSE:** not selected; do not invent a license file until the owner chooses one.
