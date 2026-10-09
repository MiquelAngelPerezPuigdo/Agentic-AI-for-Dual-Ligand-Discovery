# Agentic AI for Dual-Ligand Discovery

Local OT-2 experiment planning and LC-to-LLM iteration for Pd-catalyzed desulfonylative fluorination. The campaign searches 465 pairs from 31 ligands using repeated Claude performance scoring with potential ligand cooperativity and diversity across language-model embeddings.

For HTE staff, use the **[two-page action checklist](docs/HTE-staff-checklist.pdf)**. Its [editable source](docs/hte-staff-checklist.md) contains setup, deck loads, calibration preparation and the run sequence.

Project setup and unresolved decisions are in [start here](docs/start-here.md) and the [HTE configuration checklist](docs/hte-questions.md).

The [full reference handbook](docs/HTE-operator-handbook.pdf) preserves the detailed procedures and explanations. Its [editable sources and rebuild command](docs/updating-the-handbook.md) let us refresh it as the pipeline changes.

## Campaign

- Round 1: 65 distinct ligand pairs and one tBuBrettPhos single-ligand reference.
- Round 2: 10 new pairs selected after the first LC results arrive.
- Fixed conditions: 5 µmol substrate, 50 µL toluene, 0.1 M, 95 °C for four hours, 6 mol% of each ligand and 12 mol% Pd(COD)(DQ).
- Initial selection combines Claude ranking and T5 embedding diversity at 50/50, with mandatory coverage of all 31 ligands in the 65 pair wells. After first-round yields arrive, the iterative selection uses only Claude scoring informed by those results; GoLLuM is not used for round two.
- Generated handoffs include dosing CSVs, stock preparation, exact deck loads, LC sequences and local Opentrons Python protocols.
- A local watcher validates complete LC exports, calculates yields and creates the next dosing plan. Robot operation uses the local Opentrons App.

The ten second-round substrate wells are predosed during the first reaction and allowed to evaporate DCM at ambient temperature, with a dry endpoint check before catalyst addition. Calibration measurements can run during the first four-hour hold.

The [combined-stock and calibration plan](docs/stocks-and-calibration.md) uses one DCM stock with 250 mM SM and 2.5 mM naphthalene, a separate reservoir channel for LC dilution solvent, and five nonzero analyte calibration levels at fixed IS concentration. Pre-reaction IS retention and compatibility require HTE validation.

## Install and verify

Use Python 3.12 on the operator workstation:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[sources,test,analytics]'
python -m pip install -r requirements-gollum.txt
python -m pytest -q
python -m hte.cli demo --output output/rehearsal
python -m hte.cli rehearse-loop --output output/fake-first-loop
```

The optional ML dependencies support rebuilding embeddings and historical adapter validation; the campaign uses GoLLuM-inspired embeddings only for initialization. Precomputed real T5-base embeddings for all 465 pairs are included, so initial selection does not require downloading model weights. [Tested package versions](requirements-hte-tested.txt) document the local acceptance environment.

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

The local acceptance exercise passed **88 tests**, including OT-2 simulation, combined SM/IS dosing and dilution, LC calibration/QC with independent checks, MOCCA raw-DAD integration on synthetic data, the GoLLuM adapter and a complete watcher/scoring rehearsal with mocked Claude responses. [Validation record](software_validation.json), [rehearsal results](docs/rehearsal-results.md), [repository audit](docs/rehearsal-results.md#repository-audit).

`demo/` contains **synthetic chemistry results and selections**. Its protocols refuse physical execution. Three live Opus 4.8 smoke tests (four pairs, two repeats each) passed. The current v4 prompt returns scores only with extended thinking disabled; provider-reported cache reuse was verified. Combined estimated test cost was $0.4023. The full first-round selection still needs to be run; physical bench validation remains open.

The glass-block definition and mounting/seal, solvent delivery, extraction, analytical method and timing still require HTE verification. The provisional schedule is **729 minutes**, nine minutes beyond the 720-minute competition limit; a measured rehearsal must resolve this before the campaign.

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
