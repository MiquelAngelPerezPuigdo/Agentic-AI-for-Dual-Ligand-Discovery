# Agentic AI for Dual-Ligand Discovery

Local OT-2 experiment planning and LC-to-LLM iteration for Pd-catalyzed desulfonylative fluorination. The campaign searches 435 pairs from 30 active ligands using repeated Claude performance scoring with potential ligand cooperativity and diversity across language-model embeddings.

For HTE staff, use the **[two-page action checklist](docs/HTE-staff-checklist.pdf)**. Its [editable source](docs/hte-staff-checklist.md) contains setup, deck loads, calibration preparation and the run sequence.

Project setup and unresolved decisions are in [start here](docs/start-here.md) and the [HTE configuration checklist](docs/hte-questions.md).

The [full reference handbook](docs/HTE-operator-handbook.pdf) preserves the detailed procedures and explanations. Its [editable sources and rebuild command](docs/updating-the-handbook.md) let us refresh it as the pipeline changes.

## Campaign

- Round 1: 59 distinct ligand pairs and one tBuBrettPhos single-ligand reference.
- Round 2: 10 new pairs selected after the first LC results arrive.
- Fixed conditions: 25 µmol substrate, 250 µL toluene (provisional larger-vial scale), 0.1 M, 95 °C for four hours, 6 mol% of each ligand and 12 mol% Pd(COD)(DQ).
- Initial selection combines Claude ranking and T5 embedding diversity at 50/50, with mandatory coverage of all 30 active ligands in the 59 pair wells. After first-round yields arrive, the iterative selection uses only Claude scoring informed by those results; GoLLuM is not used for round two.
- Generated handoffs include dosing CSVs, stock preparation, exact deck loads, LC sequences and local Opentrons Python protocols.
- A local watcher validates complete LC exports, calculates yields and creates the next dosing plan. Robot operation uses the local Opentrons App.

The ten second-round substrate wells receive 25 µL of the combined 1 M SM/10 mM naphthalene stock in toluene during the first reaction and are promptly capped. Retain that solvent; no evaporation step is used in either round. Calibration measurements run during the first four-hour hold. Release first dosing with `export --live --stage dose_and_react`; release workup separately after calibration passes. [LC import and calibration](docs/htel-lc-import.md).

The [combined-stock and calibration plan](docs/stocks-and-calibration.md) uses one toluene stock with 1 M SM and 10 mM naphthalene, a separate reservoir channel for LC dilution solvent, and five nonzero analyte calibration levels at fixed IS concentration. Pre-reaction IS retention and compatibility require HTE validation.

L07 AdJohnPhos (CAS 224311-55-1) is excluded because its delivery is delayed. Original IDs and the 31-row source inventory stay unchanged; `design.excluded_ligands` controls availability.

## Install and verify

Use Python 3.12 on the operator workstation. For HTEL’s preferred uv installation, run `uv sync --python 3.12 --extra sources` and then `uv run hte check`. The existing pip/testing setup remains available:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[sources,test,analytics]'
python -m pip install -r requirements-gollum.txt
python -m pytest -q
python -m hte.cli demo --output output/rehearsal
python -m hte.cli rehearse-loop --output output/fake-first-loop
```

The optional ML dependencies support rebuilding embeddings and historical adapter validation; the campaign uses GoLLuM-inspired embeddings only for initialization. Precomputed real T5-base embeddings for all 435 pairs are included, so initial selection does not require downloading model weights. [Tested package versions](requirements-hte-tested.txt) document the local acceptance environment.

To score and select the first batch, set `ANTHROPIC_API_KEY` through a local secret mechanism, then run:

```bash
python -m hte.cli score --output output/round1-scoring
python -m hte.cli design --ranking output/round1-scoring/ranking.csv \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output output/round1-design.csv
```

For file-based setup, copy `anthropic.key.example` to `anthropic.key` in the repository root and replace its single placeholder line with your API key. This local file is ignored by Git and excluded from the handoff. Scoring and the watcher read it automatically; an existing `ANTHROPIC_API_KEY` environment variable takes precedence.

The [first-batch script](scripts/first-batch.zsh) loads the local key file and combines scoring and selection. If no key file or environment variable exists, it asks for hidden input. Optional arguments are the output folder, campaign configuration and ligand inventory; use the same campaign configuration for protocol export and LC feedback. After confirming the hardware configuration, see the runbook for protocol/stock exports, calibration, the LC watcher, pipetting settings and live operation. Keep API keys and experimental outputs outside version control.

[Anthropic prompt caching](docs/prompt-caching.md) is enabled by default in both rounds, with a one-hour lifetime and provider-reported usage/cost records in `cache_summary.json`.

The [scoring prompt guide](docs/scoring-prompt.md) lists every ligand ID, name, SMILES and available single-ligand SI yield, and defines the precise JSON outcome. Inspect the [full first-round prompt](docs/claude-scoring-prompt.txt), or regenerate it without API calls using `python -m hte.cli preview-prompts --output output/prompt-review`.

## Validation status

The local acceptance exercise passed **131 tests**, including OT-2 simulation, combined SM/IS dosing and dilution, LC calibration/QC with independent checks, MOCCA raw-DAD integration on synthetic data, the GoLLuM adapter and a complete watcher/scoring rehearsal with mocked Claude responses. [Validation record](software_validation.json), [rehearsal results](docs/rehearsal-results.md), [repository audit](docs/rehearsal-results.md#repository-audit).

`demo/` contains **synthetic chemistry results and selections**. Its protocols refuse physical execution. Three live Opus 4.8 smoke tests (four pairs, two repeats each) passed. The current v4 prompt returns scores only with extended thinking disabled; provider-reported cache reuse was verified. Combined estimated test cost was $0.4023. The full first-round selection still needs to be run; physical bench validation remains open.

Analytical sample transfers use fresh same-well tip conditioning, slower flow and a slow air gap; the runbook covers representative aliquots, failed-transfer recovery and repeat measurements. These starting settings require bench validation.

The proposed fivefold scale uses 250 µL reaction plus 250 µL workup, keeping final LC product/IS concentrations unchanged. Workup and LC diluent each use two capacity-checked reservoir channels.

Stock tubes use ordinary plastic racks; metal blocks are only for reaction vials. We now request conventional off-robot heating with magnetic stirring. Current generated reaction files still use the OT-2 heater-shaker and will need adaptation if HTEL confirms that alternative. Exact rack/stir-bar geometry, simultaneous heating, solvent delivery, extraction, analytical method and timing remain pending. The requested **1.7-minute LC method** gives a provisional **686-minute** schedule, leaving 34 minutes within the 720-minute limit if 1.7 minutes is the full cycle. Method suitability, cycle overhead and simultaneous glass-vial heating remain unconfirmed. [Organizer update and compliance](docs/organizer-updates.md).

## Contents

| Path | Purpose |
|---|---|
| `hte/` | Planning, repeated scoring, analytics, protocol generation and local watcher |
| `hte_inputs/` | Corrected ligand inventory, literature priors, embeddings and configuration templates |
| `docs/` | Operator runbook and remaining HTE configuration questions |
| `tests/hte/` | Software and protocol acceptance checks |
| `demo/` | Synthetic demonstration and generated handoffs |

## Sources and license

The repeated-scoring approach builds on the [Agentic AI for Catalyst Design thesis repository](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Catalyst-Design). Language-model representations are inspired by [GoLLuM](https://github.com/schwallergroup/gollum); optional raw-DAD processing uses [MOCCA](https://github.com/bayer-group/MOCCA). Chemical priors and hardware references are linked in the runbook.

Original project code is [MIT licensed](LICENSE). Vendored GoLLuM utilities retain their [Apache-2.0 license and attribution](hte/vendor/GOLLUM_NOTICE.txt).
