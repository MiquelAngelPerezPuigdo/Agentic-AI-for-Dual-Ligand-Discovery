# Local pipeline

Frozen **48 pairs**: `campaigns/hackathon2026/round1_design.csv`. Python quantifies UV data; cached Claude scoring selects R2. Stock preparation uses no API calls. Physical actions: [bench sheet](HTE-staff-checklist.pdf).

## Install and configure

Python 3.12: **`uv sync --python 3.12 --extra sources`**; prefix commands below with `uv run`. Or use a venv with `.[sources]`. Copy canonical config to **`local_data/campaign.json`**, calibration template to `local_data/calibration-plan.csv`, key example to **`anthropic.key`**. Put the raw Claude key in that file; preserve existing keys. Never send it to the robot/Git.

Use schema **5**; replace old protocols/settings while preserving measured LC facts. Configure method/channel, full cycle, RTs/LOQs and physical release evidence, including containers/p1000 generation. Concentrations use nominal solvent addition. `timing.enforce_deadline=false`: 12 h advisory; record real times.

## Robot preparation, then R1

Generate a guarded preview; copy its charges template to `local_data/charges.csv` and fill actual masses/assays. Follow carrier/raw-load CSVs. After local checks:

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

This robot-predoses 23 R2 vials; cap/store, replace with 48 EMPTY R1 vials. It doses/heats R1, makes standards/workup fluids during the hold. Send calibration plate to LC using generated map. [Import/calibrate](htel-lc-import.md); set `lc_calibration_validated=true` after success. Export R1 workup with the SAME command/design, changing to **`--output output/r1-workup --stage workup`**. Keep prepared reservoir 2; use a fresh final LC plate.

## R2 and finish

Complete actual injection maps. After ALL 48 results:

```bash
python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv --output output/r1-decision
```

Calibration defaults to `local_data/calibration.csv`. QC precedes Claude: **387 untested pairs →22 +L17 reference**, L03 max four. Run printed **`refill_stocks.py` FIRST** with original carriers/tubes. Load the 23 robot-predosed vials and NEW EMPTY reservoir 2. Run R2 reaction then matching workup; no SM/IS redose. If unreleased, export `next_design.csv` with R1 `--history`, `--live` and a fresh folder. After all 23 injections, use helper **`final`** with R2 doses/exports/maps; no Claude.

## Return records

Keep actual weights, preparation/source ledgers, LC exports/maps, calibration/QC, Claude records and matching doses/protocols. Copy robot JSON to `local_data/robot_logs/`, raw LC/MS/method files to `local_data/instrument_raw/`, times/deviations to `local_data/run-notes.txt`. Stop writers; **`python scripts/hte-return-package.py`** creates **`transfer/hte-results.zip`** with hashes, credentials excluded. Send privately; Git does not preserve local run data.
