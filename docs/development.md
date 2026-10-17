# Development and reproduction

## Architecture

| File / folder | Responsibility |
|---|---|
| `hte/inventory.py`, `io.py` | Immutable ligand IDs, availability, checked CSV/JSON and hashes |
| `hte/embeddings.py` | Frozen T5 embedding generation/loading; model downloads are optional |
| `hte/scoring.py`, `design.py` | Small cached Claude requests, strict scores, repeated aggregation and pair selection |
| `hte/analytics.py`, `ingestion.py` | Chromeleon normalization, calibration/QC and complete-batch joins |
| `hte/planning.py`, `protocols.py` | Stoichiometry, reserves, deck loads, timing and standalone local OT-2 Python |
| `hte/workflow.py` | Complete LC event → measured-feedback scoring → next batch, with replay guards |
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

This writes self-contained guarded Python, stock preparation/deck loads, LC mappings and predose instructions. Live release uses the [local operator workflow](start-here.md); never edit generated Python to bypass its guard.

`preview-prompts --output output/prompt-preview` exports exact requests with no API call. `score` is for a deliberately new paid campaign; normal setup reuses the prepared first batch. Keep corrected imports in fresh output folders and inspect uncertain request records before retrying.

## Maintaining the project

Keep practical instructions in the staff/runbook sources and expert algorithm details in [ml-strategy.md](ml-strategy.md). Change configuration plus corresponding prose together, run the relevant checks, rebuild/visually inspect [the PDFs](updating-the-handbook.md), and refresh `software_validation.json`. Preserve frozen paid scores and source provenance; a new selection should be a new campaign record. Tests generate their own fixtures in temporary directories. GitHub CI runs the active acceptance suite and PDF builds independently. No network access or Claude key is required by tests.
