# Local pipeline

The **initial 48 pairs are ready** in `campaigns/hackathon2026/round1_design.csv`. Local Python converts integrated UV areas to calibrated yields; Claude selects the next conditions. Staff use the [bench sheet](HTE-staff-checklist.pdf).

## Set up before the clock

Use Python 3.12: `uv sync --python 3.12 --extra sources`, then prefix commands with `uv run`. Alternatively activate a venv and install `python -m pip install -e '.[sources]'`.

```bash
mkdir -p local_data
cp -n hte_inputs/campaign.json local_data/campaign.json
cp -n hte_inputs/calibration_template.csv local_data/calibration-plan.csv
cp -n anthropic.key.example anthropic.key
chmod 600 anthropic.key
```

Put the raw Claude key in **`anthropic.key`**; preserve any existing key. Never send it to the robot, Git or email.

In `local_data/campaign.json`, set actual method/channel, full LC cycle, measured reference RTs/LOQs and applicable release evidence. Confirm final-plate shaker/autosampler compatibility and uncovered shake speed; confirm the measured handling plan within the 119.3-min remaining budget before release. Enter measured stage totals under `timing` (both rounds combined); `check` separates the target from those allowances. [HTEL setup facts](hte-questions.md).

```bash
python -m hte.cli --config local_data/campaign.json check
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

App-simulate the exported Python; use matching CSVs and start locally. For previews omit `--live`; physical execution stays blocked. R1 dosing can precede calibration once other checks pass.

## During hold one

Run/import **14 calibration injections** using the [LC instructions](htel-lc-import.md). Staff prepare 23 dry SM-only vials. After calibration passes, set `lc_calibration_validated=true`; export workup:

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

Calibration defaults to `local_data/calibration.csv` (`--calibration` overrides). After all 48 results pass QC, Claude scores **387 untested pairs** and selects **22 new pairs +L17 reference**. Both prompts include the 17 individual SI yields; no embedding selector runs in R2.

The printed decision folder holds `next_design.csv`, `next_dosing.csv`, analysis, scores and `protocols/`. Use released Python and R2 deck loads. If checks remain open, export `next_design.csv` with `--history output/r1-dose/dosing.csv`, a fresh folder and `--live`. Fit the 23 dry predosed vials; **no SM redosing**.

After all 23 R2 injections, run the helper with **`final`**, R2 `dosing.csv`, the matching plate export/map and a new output folder. This calculates final results without Claude. Compare pair yields with the measured L17 reference and retain run times.

## Practice and recovery

Practice: `python -m hte.cli practice-analytics --output output/pilot`; [real pilot replay](htel-lc-import.md). `rehearse-loop` also mocks feedback; no paid calls. Use fresh import folders and review interrupted scoring before retrying.

**177 tests passed; protocols simulated; initial design reproducible.** Bench results/calibration and feedback latency remain unmeasured. [Validation](rehearsal-results.md), [ML strategy](ml-strategy.md), [PDF updates](updating-the-handbook.md).
