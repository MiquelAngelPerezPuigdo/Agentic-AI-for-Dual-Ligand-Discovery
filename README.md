# Agentic AI for Dual-Ligand Discovery

Local OT-2 dosing, calibrated LC quantification and Claude-guided selection for Pd-catalyzed desulfonylative fluorination of pyridine-2-sulfonyl fluoride to 2-fluoropyridine.

**Release status: preparation preview only.** Axygen 12-channel reservoirs are configured for bulk stocks, including the combined SM/IS stock. Before live release, HTE must check the physical reservoir definition, solvent/cover compatibility, liquid recovery, hardware and LC method. [Weighing and loading map](docs/weighing-list.md) · [Outstanding checks](docs/hte-questions.md) · [Software evidence](docs/rehearsal-results.md).

## Run the campaign

**Start here:** [HTE experimental procedure](docs/HTE-START-HERE.md). Open it in a browser and follow the linked weighing and deck maps.

| Task | Instructions |
|---|---|
| Follow the campaign step by step | **[HTE start guide](docs/HTE-START-HERE.md)** |
| Solvent amounts and deck positions | **[Deck loading](docs/deck-loading.md)** |
| OT-2 files for the first round and follow-up instructions | **[OT-2 protocols](protocols/round1-preview/README.md)** |
| Staff actions at the bench | **[Two-page checklist](docs/HTE-staff-checklist.pdf)** |
| Install, prepare files and process R1/R2 results | **[Local pipeline commands](docs/start-here.md)** |
| Complete operator reference | [Four-page handbook](docs/HTE-operator-handbook.pdf) |
| Amounts to weigh for stocks and standards | **[Complete weighing list](docs/weighing-list.md)** · [Stock recipes](docs/stocks-and-calibration.md) |
| LC import, quantification and QC | [Analytical workflow](docs/htel-lc-import.md) |
| Scientific method and selection | [ML/LLM strategy](docs/ml-strategy.md) · [Initialization map/statistics](docs/initialization-review.md) |
| Test, reproduce or maintain the code | [Development guide](docs/development.md) · [Update PDFs](docs/updating-the-handbook.md) |

**30 ligands, 435 possible pairs.** The prepared [first batch](campaigns/hackathon2026/round1_design.csv) tests **48 pairs covering every ligand**: David Ming Segura's 24-consensus +24-Sobol initialization. It uses frozen T5 embeddings and paid Claude scores. After all 48 calibrated results pass QC, Claude selects **22 new pairs**, followed by one L17 tBuBrettPhos reference. RockPhos is limited to four R2 wells. [Selection provenance](campaigns/hackathon2026/README.md).

Each reaction is **250 µL, 0.1 M SM, 95 °C for four hours**, with 6 mol% each ligand and 12 mol% Pd(COD)(DQ). **Naphthalene is the internal standard**, dosed with SM in toluene. The robot prepares stocks from weighed chemicals, doses both rounds, and prepares calibration and LC samples. Staff weigh/load chemicals, handle caps and labware, start local protocols and change one pipette. The OT-2 is operated locally. [Canonical settings](hte_inputs/campaign.json).

![OT-2 deck, stock positions and manual labware moves](docs/figures/ot2-deck-setup.svg)

## Install and practice

Use Python 3.12 and the committed dependency lock:

```bash
uv sync --locked --python 3.12 --extra sources --extra robot
uv run hte check
uv run hte rehearse-loop --output output/practice
```

The rehearsal uses synthetic measurements and mocked Claude responses, with no paid calls. It exercises calibration, both rounds and the feedback decision. Normal operation uses the prepared first batch; no GPU or model download is needed. First-round simulation files are provided in [OT-2 protocols](protocols/round1-preview/README.md). Locally generated files stay in ignored `output/`; actual settings/data go in ignored `local_data/`. Follow the [local pipeline](docs/start-here.md) to generate current live protocols and process real measurements.

**API key:** copy [anthropic.key.example](anthropic.key.example) to **`anthropic.key` in the repository root**, then replace the placeholder with the raw Claude key. Preserve any existing key. The pipeline reads it automatically; `ANTHROPIC_API_KEY` takes precedence. Keys stay local and are excluded from Git and data packages.

**Return the campaign:** save robot logs, original LC/MS files and run notes under `local_data/`, then run `uv run python scripts/hte-return-package.py`. Send **`transfer/hte-results.zip` privately**. It contains source, local records, outputs and integrity hashes, excluding credentials. [Return/replay details](docs/development.md#return-the-campaign-to-miquel). Git does not retain experimental data.

**Timing:** two four-hour reactions leave approximately four hours of a 12-hour target for preparation, handling and LC. Calibration and workup-fluid preparation overlap reaction holds. The target is advisory; physical completion time has not been demonstrated. Simulations establish software behavior, while local mounting, solvent handling, source reach and the actual LC method remain to be validated.

Keep correspondence, meeting notes and experimental records outside this public repository. Method attribution is in the [expert guide](docs/ml-strategy.md); original project code is [MIT licensed](LICENSE).
