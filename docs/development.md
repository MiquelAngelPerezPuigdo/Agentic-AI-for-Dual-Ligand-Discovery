# Development and reproduction

The optional local menu is started with `uv run python scripts/hte-guide.py`; the chemist-facing procedure is [here](HTE-START-HERE.md).

## Architecture

| Files | Responsibility |
|---|---|
| `hte/inventory.py`, `io.py` | Ligand IDs, checked input files and hashes |
| `hte/embeddings.py` | Frozen T5 vectors and optional regeneration |
| `hte/scoring.py`, `design.py`, `initialization.py` | Cached repeated scoring, initial consensus/Sobol selection and R2 selection |
| `hte/analytics.py`, `ingestion.py`, `analytical_stocks.py` | Calibration, peak-table normalization, QC and analytical recipes |
| `hte/preparation.py`, `planning.py`, `protocols.py` | Stock preparation/refills, volume/deck planning and standalone OT-2 Python |
| `hte/workflow.py`, `cli.py`, `scripts/hte-lc-results.py` | Local commands, complete-batch feedback and resumable staff workflow |
| `hte/transfer.py`, `scripts/hte-return-package.py` | Input snapshots and private hashed return package |
| `hte/rehearsal.py`, `demo.py`, `analytical_practice.py`, `scripts/mock-hplc-trials.py` | Offline feedback, calibration and analytical fault rehearsals |
| `hte_inputs/` | Campaign configuration, ligand/SI evidence, frozen vectors and labware |
| `campaigns/hackathon2026/` | Official first batch and selection provenance |

Generated protocols, CSVs and practice runs belong in ignored `output/`; measured configuration and experimental records belong in ignored `local_data/`. [Operator commands](start-here.md), [stock recipes](stocks-and-calibration.md) and [LC workflow](htel-lc-import.md) are the operational references.

## Install and test

```bash
uv sync --locked --python 3.12 --extra sources --extra test --extra robot --extra docs
uv run python -m pytest -q
uv run hte rehearse-loop --output output/practice
```

An activated Python 3.12 virtual environment can instead use `python -m pip install -e '.[sources,test,robot,docs]'`; omit `uv run` and invoke the CLI as `python -m hte.cli`. Tests and routine operation use included vectors, requiring no model download, GPU or API key. Install the optional `embeddings` extra only to rebuild vectors. CI uses the committed `uv.lock`; [validation evidence](../software_validation.json) records tested versions and scope.

## Reproduce the real first batch without spending

```bash
uv run hte design \
  --ranking campaigns/hackathon2026/scoring/ranking.csv \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output output/reproduced-initial.csv
uv run hte export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/round1-preview
```

The first CSV must match the official **24-consensus +24-Sobol** design byte for byte. The production selector reproduces [David's original implementation](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery/blob/c2682f3db09eb496b92d11fb6725e9870157e301/notebook/batch_suggestions.ipynb) from cached scores/vectors. Companion files record selection sources, coverage and PCA/Sobol settings. The export produces guarded standalone Python, preparation/deck tables and LC maps. Regenerate these after configuration or selection changes; use the [live workflow](start-here.md) only after local release checks.

Embedding reuse checks encoded reaction conditions. Changes require rebuilding vectors and reviewing Claude scores. Time, atmosphere and precursor identity are outside the embedding template and also require score review. Keep original paid records unchanged and record each adopted design's provenance/hashes.

`uv run hte preview-prompts --output output/prompt-preview` exports exact requests without a call. `score` starts a deliberately new paid campaign; normal setup reuses R1. Retry an interrupted staff helper with the **same command and output directory** so accepted scores, uncertain-request blocks and costs survive. Inspect uncertain API attempts before recovery; changed inputs require a new directory.

## Campaign figures and analytical practice

```bash
uv sync --locked --python 3.12 --extra sources --extra robot --extra reports
uv run python scripts/initialization-report.py --output output/initialization-review
uv run python scripts/draw-deck-setup.py
uv run python scripts/mock-hplc-trials.py --output output/mock-hplc
```

The initialization HTML contains pair identities, a ligand network, use counts and cached-score weight previews. It checks the official design before drawing it; alternatives do not change the campaign. Review before using `--publish-docs` to update the compact [overview](initialization-review.md) and SVG. The deck script updates SVG/PNG from current source positions and stock budgets; inspect labels/routes after changes.

Mock LC reports show accepted, rejected and undetected-bias cases using synthetic peak tables. `uv run hte practice-analytics --output output/analytics-practice` exercises calibration/import/QC alone. [Known-mixture preparation and actual pilot replay](htel-lc-import.md). These tests do not validate physical separation or extraction.

## Return the campaign to Miquel

The staff helper preserves effective settings, inventory, SI evidence, versions, calibration, original LC exports/maps and dosing tables. Iterations retain normalized peaks, yields/QC, exact Claude requests/responses, repeated scores/rankings, usage/cache/cost records, selections and generated protocols. Failed attempts remain available; use fresh folders for corrected imports and inspect uncertain API attempts before retrying.

Staff must also copy records held on separate instruments:

- `local_data/robot_logs/`: OT-2 JSON logs for every stage.
- `local_data/instrument_raw/`: original LC/MS data (including `.raw` directories), method/gradient, sequences, calibration/pilot and rejected/replacement injections.
- `local_data/run-notes.txt`: run IDs, times, interventions, deviations and rejection reasons.

Once writers have stopped:

```bash
uv run python scripts/hte-return-package.py
```

Send **`transfer/hte-results.zip` privately**. It includes the source snapshot and dependency lock, all `local_data/` and all `output/`, including practice. To omit obsolete/practice outputs, pass the real nonoverlapping run folders with `--runs folder1 folder2 ...`; retain every preparation, dosing, workup, decision and final-analysis folder. Choose `--output transfer/hte-results-v2.zip` for later packages; existing archives are never overwritten.

`TRANSFER_MANIFEST.json` records hashes, source revision, versions and supplied instrument-file categories. Presence does not establish completeness: inspect originals and QC. Credentials and symlinks are excluded; a Claude token in an ordinary file blocks packaging without printing it. Files changing during packaging also stop it. The command works without Git or paid calls.

For replay, extract the archive and place `local_data/` and `output/` alongside `source/` contents. Use new output folders. Saved yields/rankings/prompts can be inspected offline. **A Git push alone is not an experimental-data handoff.**

## Maintenance

Keep bench instructions in the [editable handbook sources](updating-the-handbook.md) and algorithm details in [ml-strategy.md](ml-strategy.md). Update configuration and prose together, run relevant checks, rebuild/inspect PDFs and refresh `software_validation.json`. Tests generate temporary fixtures; CI runs acceptance tests and PDF builds independently. Historical exploratory notebooks, hypothetical retention simulations and earlier versions remain available through Git history.
