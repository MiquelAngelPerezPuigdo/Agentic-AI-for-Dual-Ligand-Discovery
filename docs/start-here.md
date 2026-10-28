# Local pipeline

Frozen R1: **48 pairs, all 30 ligands**. No paid R1 rerun. Regenerate stocks/protocols/maps after updating the repository. Physical actions: [bench sheet](HTE-staff-checklist.pdf).

## Install and configure

Python 3.12: **`uv sync --locked --python 3.12 --extra sources --extra robot`**; prefix commands with `uv run`. Create `local_data/` (`mkdir -p local_data`). Copy `hte_inputs/campaign.json` to **`local_data/campaign.json`**, `hte_inputs/calibration_template.csv` to `local_data/calibration-plan.csv`, and `anthropic.key.example` to **`anthropic.key`**. Put the raw Claude key there; preserve existing keys. Never send it to the robot/Git.

Use schema **6** and **fresh naphthalene calibration**; old mesitylene calibration is invalid. Start from the current configuration; discard old stock-preparation outputs. Configure method/channel, cycle and RTs/LOQs. Default `reject` stops missing-analyte results; `censor` reports validated bounds. **Axygen bulk reservoirs:** check the actual geometry, solvent/cover compatibility and recoverable residual volumes before live release. Concentrations use nominal solvent addition; record actual times.

## Robot preparation, then R1

Use the [weighing list](weighing-list.md), then generate a guarded preview. `output/prep-preview/` contains `bulk_carriers.csv` and `raw_reagents_to_load.csv`. After local checks, generate the live protocol; no mass-entry CSV is needed:

```bash
python -m hte.cli --config local_data/campaign.json prepare-stocks \
  --output output/prep-preview
python -m hte.cli --config local_data/campaign.json prepare-stocks \
  --output local_data/stock-prep --live
```

Run **`local_data/stock-prep/prepare_stocks.py`** locally: p300 single left /p1000 single right. Preserve its manifest at the default configured path. Follow swaps; afterward change right to p300 multi and tips 8/9 to 300 µL through the App installation/calibration workflow.

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

Start with **48 NEW EMPTY R1 vials**. Retain **SM/IS tube 4 D2**, capped between rounds. Send the robot-prepared calibration plate to LC using its map. [Import/calibrate](htel-lc-import.md); set `lc_calibration_validated=true` after success. Export R1 workup with the SAME command/design, changing to **`--output output/r1-workup --stage workup`**. Keep reservoir 2; use a fresh final LC plate.

## R2 and finish

Complete actual injection maps. After ALL 48 results:

```bash
python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv --output output/r1-decision
```

Calibration defaults to `local_data/calibration.csv`. QC precedes Claude: **387 untested pairs →22 +L17 reference**, L03 max four. **After interruption rerun the SAME command/output**; accepted scores are reused. Inspect uncertain API requests; a new folder may repeat charges. Run printed **`refill_stocks.py` FIRST** for ligand top-ups; retain SM/IS **4 D2** and all four Pd tubes without refilling. Fit **23 NEW EMPTY vials** and a NEW EMPTY reservoir 2; run the printed dosing protocol, then **`workup.py` after reaction/cooling**. Follow the printed LC sequence; copy and complete its injection map in `local_data/`. If unreleased, resolve the validation issue and use the [R2 export command](htel-lc-import.md#reaction-results-and-final-22).

After all 23 final injections, use the printed **NEXT DOSING** path below (or `output/r2-live/dosing.csv` if exported separately). Replace the placeholder. This only analyzes results; no Claude:

```bash
python scripts/hte-lc-results.py final \
  --dosing "PASTE THE NEXT DOSING PATH HERE" \
  --exports local_data/r2-batch*.csv \
  --injections local_data/r2-map*.csv --output output/r2-final
```

## Return records

Copy robot logs to `local_data/robot_logs/`, raw LC/MS/method files to `local_data/instrument_raw/`, and times/deviations to `local_data/run-notes.txt`. Keep LC exports/maps, calibration, QC and run outputs. Stop writers; **`python scripts/hte-return-package.py`** creates **`transfer/hte-results.zip`**. Send privately.
