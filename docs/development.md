# Development and reproduction

## Architecture

| File / folder | Responsibility |
|---|---|
| `hte/inventory.py`, `io.py` | Immutable ligand IDs, availability, checked CSV/JSON and hashes |
| `hte/embeddings.py` | Frozen T5 embedding generation/loading; model downloads are optional |
| `hte/scoring.py`, `design.py` | Small cached Claude requests, strict scores, repeated aggregation and pair selection |
| `hte/analytics.py`, `ingestion.py` | HTEL peak-table normalization, calibration/QC and complete-batch joins |
| `hte/analytical_stocks.py` | Small independent analytical masters, with a practical minimum weighing and explicit containers |
| `hte/analytical_practice.py`, `scripts/mock-hplc-trials.py` | Calibration/pilot replay and visual mock-LC fault challenges |
| `scripts/simulate-lc-separation.py` | Uncalibrated column/gradient scenarios; separate from campaign quantification |
| `hte/planning.py`, `protocols.py` | Stoichiometry, reserves, deck loads, timing and standalone local OT-2 Python |
| `hte/workflow.py` | Complete LC event → measured-feedback scoring → next batch, with replay guards |
| `hte/transfer.py`, `scripts/hte-return-package.py` | Exact input snapshots and a private, hashed archive for knowledge transfer |
| `hte/rehearsal.py`, `demo.py` | Offline rehearsal / synthetic test fixtures generated on demand |
| `hte/cli.py`, `scripts/hte-lc-results.py` | CLI and staff-facing LC entry point |
| `hte_inputs/` | Canonical configuration, inventory, evidence, frozen vectors and actual labware |
| `campaigns/hackathon2026/` | Real initial selection and the compact evidence needed to reproduce it |

Generated protocols, stock/deck CSVs and synthetic runs belong in ignored `output/`. The repository keeps one campaign configuration; local measured settings go in ignored `local_data/`. Old generated runs and unused GP/MOCCA integrations were removed; Git history preserves previous versions. The supplied integrated LC export is processed directly, and the current project needs neither a trained GoLLuM optimizer nor raw-DAD integration.

## Install and test

Use Python 3.12 in a virtual environment:

```bash
python -m pip install -e '.[sources,test,docs]'
python -m pytest -q
python -m hte.cli rehearse-loop --output output/practice
```

Equivalent uv setup: `uv sync --python 3.12 --extra sources --extra test --extra docs`, then prefix commands with `uv run`. Routine operation/tests use the included embedding matrix and require no PyTorch/model download. Install `.[embeddings]` only to deliberately rebuild vectors. Tested dependency versions are recorded in `software_validation.json`.

## Reproduce the real first batch without spending

```bash
python -m hte.cli design \
  --ranking campaigns/hackathon2026/scoring/ranking.csv \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output output/reproduced-initial.csv
```

The design CSV should match `campaigns/hackathon2026/round1_design.csv` byte for byte. Companion files show coverage and selection steps. To inspect/simulate matching robot files and preparation tables:

```bash
python -m hte.cli export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/round1-preview
```

This writes self-contained guarded Python, stock preparation/deck loads, LC mappings and predose instructions. `pd_material_budget.json` reconciles the single 90 mg bulk across both rounds; zero-mass Pd CSV rows are aliquots. `catalyst_mixing_timing.json` reports additional pumping/waits from source remixing; include it within measured dosing times. Live release uses the [local operator workflow](start-here.md); never edit generated Python to bypass its guard.

`preview-prompts --output output/prompt-preview` exports exact requests with no API call. `score` is for a deliberately new paid campaign; normal setup reuses the prepared first batch. Keep corrected imports in fresh output folders and inspect uncertain request records before retrying.

## Review initialization maps and statistics

```bash
python -m pip install -e '.[reports]'
python scripts/initialization-report.py --output output/initialization-review
```

Open `output/initialization-review/initialization-review.html` for hoverable pair identities, a ligand network, use counts and a dropdown comparing cached-score weight previews. The folder includes SVG/PNG, JSON statistics and comparison/count CSVs. No API key or model download is required. The script validates the frozen design against the current selector before drawing it; alternative selections remain previews and do not change campaign files.

The compact [published overview](initialization-review.md) stores only Markdown and SVG. Deliberately refresh those two files with `--publish-docs` after reviewing a newly generated report. Full interactive outputs remain in ignored `output/`.

## Return the campaign to Miquel

The staff LC helper snapshots effective configuration, inventory, SI evidence (for selection), installed versions and calibration before processing. Ingestion preserves exact source exports, injection maps and dosing tables under `ingestion/sources/`; normalization does not discard the archived all-channel export. Iterations also retain effective settings, normalized source tables, yields/QC, exact Claude requests and responses, repeated scores/rankings, usage/cost/cache records, selection and dosing CSVs, and any released protocols. Failed attempts remain available; use fresh folders for corrected imports, and review uncertain API attempts before retrying.

Staff must copy files that live on separate instruments:

- `local_data/robot_logs/`: actual OT-2 JSON run logs for both rounds/stages.
- `local_data/instrument_raw/`: original raw LC/MS data (including `.raw` directories), method/gradient and sequence exports, calibration/pilot files, and rejected/replacement injections.
- `local_data/run-notes.txt`: actual stock masses/assays and volumes, run IDs, real times, manual interventions, deviations and reasons for rejected injections.

Keep any additional files under `local_data/` too. Once all writers have stopped, run from the repository root:

```bash
python scripts/hte-return-package.py
```

Send **`transfer/hte-results.zip` privately**. The default includes the source snapshot, all `local_data/` and all `output/`, including practice runs. It works without Git and requires no paid call. To omit practice or large obsolete outputs, supply the real, nonoverlapping run folders with `--runs folder1 folder2 ...`; never omit a campaign's dosing, workup, decision or final-analysis folder. Choose `--output transfer/hte-results-v2.zip` for a later archive; an existing archive is never overwritten.

`TRANSFER_MANIFEST.json` lists file sizes/SHA-256 hashes, source revision when available, installed versions, exclusions and whether external-log/raw/notes files were supplied. Presence is not a completeness or scientific-validity check: review the original instrument files and final QC. Named key/environment/credential files and symlinks are excluded; a Claude token pasted into an ordinary file blocks packaging without printing it. Do not store unrelated secrets in run/data directories. Packaging refuses files that change while read; stop writers and retry with a fresh filename.

For replay, extract the archive and copy `local_data/` and `output/` alongside the contents of `source/`. Use new output folders. Saved yields/rankings/prompts can be inspected offline, without repeating paid scoring. **Git ignores experimental outputs and local settings; a repository push alone is not a data handoff.**

Practice remains `python -m hte.cli rehearse-loop --output output/practice` (mocked feedback, no paid calls), or `practice-analytics --output output/pilot` for calibration/import/QC alone. [Real pilot replay](htel-lc-import.md).

## Maintaining the project

Explore assumed column/gradient scenarios with `python scripts/simulate-lc-separation.py --output output/lc-separation` after installing `.[reports]`. The standalone report includes explicit retention/peak/response assumptions, three gradients, overlap stresses and numerical checks. It does not fit a retention predictor or alter the analytical method. [Scope and assumptions](htel-lc-import.md#assumed-column-and-gradient-scenarios).

Keep practical instructions in the staff/runbook sources and expert algorithm details in [ml-strategy.md](ml-strategy.md). Change configuration plus corresponding prose together, run the relevant checks, rebuild/visually inspect [the PDFs](updating-the-handbook.md), and refresh `software_validation.json`. Preserve frozen paid scores and source provenance; a new selection should be a new campaign record. Tests generate their own fixtures in temporary directories. GitHub CI runs the active acceptance suite and PDF builds independently. No network access or Claude key is required by tests.
