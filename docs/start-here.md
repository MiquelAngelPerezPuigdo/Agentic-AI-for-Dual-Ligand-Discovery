# HTE start here

Use the [two-page staff checklist](HTE-staff-checklist.pdf) at the robot. This page is for the colleague running the local optimizer. The initial **48-pair design is already prepared** in `campaigns/hackathon2026/round1_design.csv`. Do not rerun paid initial scoring unless deliberately making a new campaign.

Generate stock/deck CSVs and simulation files with the preview export in [development.md](development.md#reproduce-the-real-first-batch-without-spending). Generated outputs are kept locally; the frozen design/scores are the versioned record.

## Local setup before the timed run

Run commands from the repository root. Use Python 3.12; HTEL's normal `uv sync --python 3.12 --extra sources` and `uv run` are supported. Alternatively install the project with `python -m pip install -e '.[sources]'` inside an activated virtual environment.

```bash
mkdir -p local_data
cp -n hte_inputs/campaign.json local_data/campaign.json
cp -n hte_inputs/calibration_template.csv local_data/calibration-plan.csv
cp -n anthropic.key.example anthropic.key
```

Do not overwrite an existing key. Open `anthropic.key`, replace its single placeholder line with the raw Claude key, save, and restrict access with `chmod 600 anthropic.key`. Never paste it into a protocol, CSV, GitHub or an email. No robot credentials are required.

In `local_data/campaign.json`, record the actual 1.7-minute **method ID**, UV channel, authentic-standard retention times/windows and experimentally supported SM/product LOQs. Keep the requested 210 nm wavelength distinct from the channel name. Complete applicable `validation` fields only from local setup evidence. A separate extraction-homogeneity study is not required by the team; visible layers/solids still need review. [Remaining facts](hte-questions.md).

```bash
python -m hte.cli --config local_data/campaign.json check
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

Import `output/r1-dose/dose_and_react.py` in the local App, simulate and start locally. Use its matching CSVs. If setup is incomplete, export without `--live` to inspect/simulate; never remove the `DEMO` guard manually. First dosing can be released before calibration finishes, but all other applicable checks and a known LC method are required.

## During the first four-hour hold

Prepare/run the 14 authentic-standard injections and complete [calibration import](htel-lc-import.md). Staff also predose/dry **23 SM-only vials** in an ordinary off-deck rack; no second reaction block is needed. After calibration passes, record `lc_calibration_validated=true` and export workup separately:

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-workup --live --stage workup
```

## After all 48 first-round injections

Fill each generated `lc_batchNN_injections.csv` with the actual method/sequence identities. Keep one accepted measurement per sample. Six batches may reset injection numbering; each export needs its own map.

```bash
python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv \
  --output output/r1-decision
```

Both globs must expand to matching batch order and must not include unrelated files. Calibration defaults to `local_data/calibration.csv`; use `--calibration` if elsewhere. This command checks all 48 samples, calibration and QC, then calls Claude on the **387 untested pairs** in small requests. Both stages include the same single-ligand SI yields. It outputs **22 new pairs + one L17 single reference**. No embedding/GoLLuM selection runs here.

The printed decision directory contains `next_design.csv`, `next_dosing.csv`, analysis and score records. If all setup checks pass, its `protocols/` contains released local Python. Otherwise, complete the setup evidence and export explicitly using that `next_design.csv`, `--history output/r1-dose/dosing.csv`, a fresh output directory and `--live`. Use matching second-round deck loads; replace the first 48 vials with the 23 dry predosed vials. Do not redose SM.

After the 23 second-round injections, use the same helper with **`final`**, second-round `dosing.csv`, three matching LC exports/maps and a fresh output directory. It calculates results without calling Claude. Compare both rounds' calibrated pair yields with the measured L17 reference, preserving the different run times. One reference is a resource-efficient comparison, not proof of pair synergy or reproducibility.

## Practice / recovery

`python -m hte.cli rehearse-loop --output output/practice` makes no paid calls and changes no robot. All practice yields/next pairs are synthetic. Use new output directories for corrected LC imports. Scoring can reuse validated responses from its exact original scoring directory, but an interrupted/uncertain request requires inspecting its attempt/raw files before any deliberate repayment. Never repeatedly relaunch a failed watcher event blindly.
