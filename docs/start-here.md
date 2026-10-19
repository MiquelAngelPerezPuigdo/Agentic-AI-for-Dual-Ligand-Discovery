# Local pipeline

Official **48 pairs (24 consensus +24 Sobol)**: `campaigns/hackathon2026/round1_design.csv`. Already prepared; no GPU or paid R1 rerun. Python quantifies UV data; cached Claude scoring selects R2. **Regenerate stocks/protocols/maps after updating the repository; earlier R1 exports use different pairs.** Physical actions: [bench sheet](HTE-staff-checklist.pdf).

## Install and configure

Python 3.12: **`uv sync --locked --python 3.12 --extra sources --extra robot`**; prefix commands with `uv run`. Or install `.[sources,robot]` in a venv. Copy config to **`local_data/campaign.json`**, calibration template to `local_data/calibration-plan.csv`, key example to **`anthropic.key`**. Put the raw Claude key there; preserve existing keys. Never send it to the robot/Git.

Use schema **6** and naphthalene IS; replace older configs/protocols. Preserve confirmed hardware/method facts, **re-establish IS retention time and calibration with naphthalene**; old mesitylene calibration is invalid. Both open shakes are **750 rpm /2 min**. Regenerate preparation/protocol files; leave workup vials open through sampling, recap for storage. Configure method/channel, full cycle and RTs/LOQs. Choose nondetection policy: default `reject` stops a missing-analyte result; `censor` reports bounds after RT/LOQ validation. **Default bulk-source reach fails:** supply actual suitable short-container/rack geometry before live release. Concentrations use nominal solvent addition. Twelve hours is advisory; record real times.

## Robot preparation, then R1

Generate a guarded preview; fill actual masses/assays in `local_data/charges.csv` from its template. Pd: **22.8 mg each in 4 A3/B3/C3; 21.6 mg in 4 A4**, 90 mg total. **IS_SOURCE: 60 mg naphthalene in 1 C2; IS_MASTER empty.** Follow carrier/raw-load CSVs. After local checks:

```bash
python -m hte.cli --config local_data/campaign.json prepare-stocks \
  --output output/prep-preview
python -m hte.cli --config local_data/campaign.json prepare-stocks \
  --charges local_data/charges.csv --output local_data/stock-prep --live
```

Run **`local_data/stock-prep/prepare_stocks.py`** locally: p300 single left /p1000 single right. Preserve its manifest at the default configured path. Follow swaps; afterward change right to p300 multi and tips 8/9 to 300 µL through the App installation/calibration workflow.

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

Start with **48 NEW EMPTY R1 vials**. Robot adds 25 µL SM/IS per vial, then catalysts, and heats the capped block. Retain **SM/IS tube 4 D2**, capped between rounds; its 1.89 mL initial fill covers both rounds. Robot makes standards/workup fluids during the hold. Send calibration plate to LC using generated map. [Import/calibrate](htel-lc-import.md); set `lc_calibration_validated=true` after success. Export R1 workup with the SAME command/design, changing to **`--output output/r1-workup --stage workup`**. Keep prepared reservoir 2; use a fresh final LC plate.

## R2 and finish

Complete actual injection maps. After ALL 48 results:

```bash
python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv --output output/r1-decision
```

Calibration defaults to `local_data/calibration.csv`. QC precedes Claude: **387 untested pairs →22 +L17 reference**, L03 max four. **After interruption rerun the SAME command/output**; accepted scores are reused. Inspect uncertain API requests; a new folder may repeat charges. Run printed **`refill_stocks.py` FIRST** for ligand top-ups; retain SM/IS **4 D2** and all four Pd tubes without refilling. Fit **23 NEW EMPTY vials** in the same block and a NEW EMPTY reservoir 2; R2 Python adds **25 µL SM/IS per vial, then catalysts**. If unreleased, export `next_design.csv` with R1 `--history`, `--live` and a new export folder. After 23 final injections, run helper **`final`**; no Claude.

## Return records

Keep actual weights, preparation/source ledgers, LC exports/maps, calibration/QC, Claude records and matching doses/protocols. Copy robot JSON to `local_data/robot_logs/`, raw LC/MS/method files to `local_data/instrument_raw/`, times/deviations to `local_data/run-notes.txt`. Stop writers; **`python scripts/hte-return-package.py`** creates **`transfer/hte-results.zip`** with hashes, credentials excluded. Send privately; Git does not preserve local run data.
