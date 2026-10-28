# Local pipeline

Browser: [experimental procedure](HTE-START-HERE.md). Commands below are for the pipeline operator.

Frozen R1: **48 pairs, all 30 ligands**. No paid R1 rerun. The [fixed OT-2 files](../protocols/fixed-campaign/README.md) are ready for local App import after the operator's equipment check. Physical actions: [bench sheet](HTE-staff-checklist.pdf).

## Install and configure

Python 3.12: **`uv sync --locked --python 3.12 --extra sources --extra robot`**; prefix commands with `uv run`. Create `local_data/`. Copy `hte_inputs/campaign.json` to **`local_data/campaign.json`**, `hte_inputs/calibration_template.csv` to `local_data/calibration-plan.csv`, and `anthropic.key.example` to **`anthropic.key`**. Keep any existing files. Add the Claude key; never send it to the robot/Git.

Use schema **6** and **fresh naphthalene calibration**; old mesitylene calibration is invalid. Start from the current configuration; discard old stock-preparation outputs. Configure method/channel, cycle and RTs/LOQs. Default `reject` stops missing-analyte results; `censor` reports validated bounds. **Axygen bulk reservoirs:** check the actual geometry, solvent/cover compatibility and recoverable residual volumes before live release. Concentrations use nominal solvent addition; record actual times.

## Robot preparation, then R1

Use the [weighing list](weighing-list.md) and the published fixed stock preparation and R1 protocols. For the later R2 software, create a local preparation manifest with the confirmed configuration; **this generates files only, and does not run stock preparation again**. No mass-entry CSV is needed:

```bash
python -m hte.cli --config local_data/campaign.json prepare-stocks \
  --output local_data/stock-prep --live
python scripts/check-fixed-campaign.py \
  --preparation local_data/stock-prep/preparation_manifest.json
```

If the check fails, reconcile the actual stock recipe before R2. Run the [published fixed protocols](../protocols/fixed-campaign/README.md) locally: p300 single left /p1000 single right for stock preparation, then change right to p300 multi and tips 8/9 to 300 µL through the App installation/calibration workflow. Preserve the matching manifest at its default path. Start R1 with **48 NEW EMPTY vials**. Retain **SM/IS tube 4 D2**, capped between rounds. Send the robot-prepared calibration plate to LC using its map. [Import/calibrate](htel-lc-import.md); set `lc_calibration_validated=true` after success. Run the published R1 workup after cooling. Keep reservoir 2; use a fresh final LC plate.

## R2 and finish

Complete actual injection maps. After ALL 48 results:

```bash
python scripts/hte-lc-results.py next \
  --dosing protocols/fixed-campaign/round1/dosing.csv \
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

Save robot logs, raw LC/MS files, maps and run notes under `local_data/`. Stop writers and run **`python scripts/hte-return-package.py`**; send **`transfer/hte-results.zip`** privately.
