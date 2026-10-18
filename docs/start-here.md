# Local pipeline

The **initial 48 pairs are ready** in `campaigns/hackathon2026/round1_design.csv`. Python calculates calibrated yields; Claude selects R2. Staff use the [bench sheet](HTE-staff-checklist.pdf).

## Set up before the clock

Use Python 3.12: `uv sync --python 3.12 --extra sources`; prefix commands with `uv run`. Or install `python -m pip install -e '.[sources]'` in a venv.

```bash
mkdir -p local_data
cp -n hte_inputs/campaign.json local_data/campaign.json
cp -n hte_inputs/calibration_template.csv local_data/calibration-plan.csv
cp -n anthropic.key.example anthropic.key
chmod 600 anthropic.key
```

Use **schema 3**; replace older preparation settings/protocols, preserving measured LC facts.

Put the raw Claude key in **`anthropic.key`**; preserve any existing key. Never send it to the robot, Git or email.

In `local_data/campaign.json`, set method/channel, full LC cycle, measured RTs/LOQs and release evidence. Confirm LC plate compatibility, uncovered shake speed and handling within 119.3 min. Enter measured stage totals under `timing` (both rounds combined). [HTEL setup facts](hte-questions.md).

```bash
python -m hte.cli --config local_data/campaign.json check
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

App-simulate and start locally with matching CSVs. Omit `--live` for guarded previews. R1 dosing may precede calibration once other checks pass.

## During hold one

Run/import **14 calibration injections** using the [LC instructions](htel-lc-import.md). Staff predose 23 fresh vials with 25 µL combined SM/IS in toluene and cap promptly. After calibration passes, set `lc_calibration_validated=true`; export workup:

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-workup --live --stage workup
```

## After all 48 R1 results

Default: **one final LC plate/export per round, four moves total; no R1 split**. Robot dilutes and shakes. Use `lc_plates.csv` and complete `lc_batchNN_injections.csv` with actual method/sequence identities. Each export needs its own map; match glob order and exclude unrelated files.

```bash
python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv \
  --output output/r1-decision
```

Calibration defaults to `local_data/calibration.csv` (`--calibration` overrides). After all 48 results pass QC, Claude scores **387 untested pairs** and selects **22 new pairs +L17 reference**. Both prompts include 17 SI yields. R2 uses no embedding selector; L03 is capped at four wells.

The command prints the R2 Python and deck-load paths when released. The decision folder retains design/dosing CSVs, analysis and scores. If checks remain open, export `next_design.csv` with `--history output/r1-dose/dosing.csv`, a fresh folder and `--live`. Fit the 23 liquid-predosed vials; **uncap; no SM/IS redosing**.

After all 23 R2 injections, run the helper with **`final`**, R2 `dosing.csv`, the matching plate export/map and a new output folder. This calculates final results without Claude. Compare pair yields with the measured L17 reference and retain run times.

## Return the data

Imports save original exports/maps, calibration and settings. Outputs retain yields/QC, Claude requests/responses/rankings/cost/cache, doses and protocols. Keep rejected measurements too.

Copy robot JSON logs into `local_data/robot_logs/`, raw LC/MS into `local_data/instrument_raw/`, and stock assays, times/deviations into `local_data/run-notes.txt`. Stop writers; run **`python scripts/hte-return-package.py`**. Send **`transfer/hte-results.zip` privately**: code, local data, all output and file hashes; credentials excluded. Missing external records are reported. Git alone does not preserve run data.
