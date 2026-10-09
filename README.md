# Agentic AI for Dual-Ligand Discovery

Local OT-2 experiment planning and LC-to-LLM iteration for Pd-catalyzed desulfonylative fluorination. The campaign searches 465 pairs from 31 ligands using repeated mechanism-informed Claude scoring and diversity across language-model embeddings.

Start with [organizer questions and first-batch setup](docs/start-here.md), the [operator runbook](docs/hte-runbook.md) and [HTE configuration checklist](docs/hte-questions.md).

The [HTE PDF handbook](docs/HTE-operator-handbook.pdf) combines the operator instructions, stock/calibration plan and checklist. Its [editable sources and rebuild command](docs/updating-the-handbook.md) let us refresh it as the pipeline changes.

## Campaign

- Round 1: 65 distinct ligand pairs and one tBuBrettPhos single-ligand reference.
- Round 2: 10 new pairs selected after the first LC results arrive.
- Fixed conditions: 5 µmol substrate, 50 µL toluene, 0.1 M, 95 °C for four hours, 6 mol% of each ligand and 12 mol% Pd(COD)(DQ).
- Initial selection combines Claude ranking and T5 embedding diversity at 50/50. The iterative selection uses Claude scoring informed by calibrated first-round results.
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

The optional ML dependencies support rebuilding embeddings and the measured-prior GoLLuM adapter. Precomputed real T5-base embeddings for all 465 pairs are included, so initial selection does not require downloading model weights. [Tested package versions](requirements-hte-tested.txt) document the local acceptance environment.

To score and select the first batch, set `ANTHROPIC_API_KEY` through a local secret mechanism, then run:

```bash
python -m hte.cli score --output output/round1-scoring
python -m hte.cli design --ranking output/round1-scoring/ranking.csv \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output output/round1-design.csv
```

The [first-batch script](scripts/first-batch.zsh) combines hidden key entry and these two steps. After confirming the hardware configuration, see the runbook for protocol/stock exports, calibration, the LC watcher, pipetting settings and live operation. Keep API keys and experimental outputs outside version control.

[Anthropic prompt caching](docs/prompt-caching.md) is enabled by default in both rounds, with a one-hour lifetime and provider-reported usage/cost records in `cache_summary.json`.

## Validation status

The local acceptance exercise passed **39 tests**, including OT-2 simulation, combined SM/IS dosing and dilution, LC calibration/QC with independent checks, MOCCA raw-DAD integration on synthetic data, the GoLLuM adapter and a complete watcher/scoring rehearsal with mocked Claude responses. [Validation record](software_validation.json), [rehearsal results](docs/rehearsal-results.md).

`demo/` contains **synthetic chemistry results and selections**. Its protocols refuse physical execution. No real Claude scoring campaign or physical robot run has been performed.

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
