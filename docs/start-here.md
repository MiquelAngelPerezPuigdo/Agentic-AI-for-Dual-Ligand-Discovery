# Local pipeline

The **initial 48 pairs are ready** in `campaigns/hackathon2026/round1_design.csv`. Use the local workstation. Chromeleon exports UV areas; Python applies our standards/calibration and calculates yields. Staff use the [bench sheet](HTE-staff-checklist.pdf).

## Set up before the clock

Use Python 3.12. Install with `uv sync --python 3.12 --extra sources` and prefix commands with `uv run`, or activate a virtual environment and run `python -m pip install -e '.[sources]'`.

```bash
mkdir -p local_data
cp -n hte_inputs/campaign.json local_data/campaign.json
cp -n hte_inputs/calibration_template.csv local_data/calibration-plan.csv
cp -n anthropic.key.example anthropic.key
chmod 600 anthropic.key
```

Keep an existing key. Replace the placeholder in **`anthropic.key`** with the raw Claude key. Keep it local; never include it in robot files, Git or email.

In `local_data/campaign.json`, enter method ID, full LC cycle, UV channel/wavelength, standard RT windows and measured SM/product LOQs. Record applicable `validation` evidence; [HTEL checks](hte-questions.md). Requested 210 nm is provisional. Review visible transfer faults; no separate homogeneity study is required.

```bash
python -m hte.cli --config local_data/campaign.json check
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

App-import/simulate `output/r1-dose/dose_and_react.py`; use matching CSVs and start locally. Before setup is complete, omit `--live`; keep the simulation guard. Dosing can precede calibration once other applicable checks and the method are recorded.

## During hold one

Run/import **14 calibration injections** using the [LC instructions](htel-lc-import.md). Staff prepare 23 dry SM-only vials. After calibration passes, set `lc_calibration_validated=true`; export workup:

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-workup --live --stage workup
```

## After all 48 R1 results

Complete `lc_batchNN_injections.csv` maps with actual method/sequence identities. Each export needs its own map, including reset injection numbers. Keep both globs in matching batch order; exclude unrelated files.

```bash
python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv \
  --output output/r1-decision
```

Calibration defaults to `local_data/calibration.csv`; override with `--calibration` if needed. The command checks all 48 samples/calibration/QC, then scores the **387 untested pairs with Claude** and outputs **22 new pairs + L17 reference**. Both prompts include the same single-ligand SI yields. Round two uses no embedding/GoLLuM selector.

The printed decision directory holds `next_design.csv`, `next_dosing.csv`, analysis, scores and `protocols/`. Use released Python and matching R2 deck loads. If release checks remain open, complete them and export from `next_design.csv` with `--history output/r1-dose/dosing.csv`, a fresh output folder and `--live`. Replace R1 vials with the 23 dry predosed vials; **do not redose SM**.

After all 23 R2 injections, run the helper with **`final`**, R2 `dosing.csv`, three matching export/map batches and a new output folder. This calculates final results without Claude. Compare pair yields with the measured L17 reference and retain run times.

## Practice and recovery

For analytical challenges and pilot recipes, run `python -m hte.cli practice-analytics --output output/pilot`. [Real pilot replay and blank reviews](htel-lc-import.md). The full `rehearse-loop` includes this plus mocked feedback. No paid calls. Use fresh import folders; review uncertain scoring attempts before retrying.

**159 tests passed; protocols simulated; initial design reproducible.** Bench results/calibration and feedback latency remain unmeasured. [Validation](rehearsal-results.md), [ML strategy](ml-strategy.md), [PDF updates](updating-the-handbook.md).
