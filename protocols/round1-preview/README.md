# OT-2 protocols for the first round

These are generated from the committed campaign settings and the selected 48-pair design. Download the `.py` files to import them into the local Opentrons App for **simulation and review**:

1. [prepare_stocks.py](stock-preparation/prepare_stocks.py) — solvent addition, stock mixing and transfer to working tubes. Its maps are [bulk carriers](stock-preparation/bulk_carriers.csv) and [raw solvents](stock-preparation/raw_reagents_to_load.csv).
2. [dose_and_react.py](reaction/dose_and_react.py) — dose the 48 reactions, run the reaction and prepare the workup liquids and calibration plate during the hold.
3. [workup.py](reaction/workup.py) — quench and prepare the first-round LC samples after cooling.

The [reaction folder](reaction/) also contains the intended dosing, deck, solvent, calibration and LC maps. These are **previews**, not records of what was actually loaded or injected.

**Simulation only:** these files deliberately stop if started on a physical robot. They are not cleared for a live run. HTE must confirm the actual equipment, labware, source recovery and LC method, then generate the live files from its local configuration. Use the resulting live maps together with the matching live protocols. Custom labware definitions are embedded in the Python files, but their geometry and fit still require local confirmation.

## Generate the live first-round files

The software operator should follow the complete [local pipeline](../../docs/start-here.md), including installation, local configuration and the [remaining checks](../../docs/hte-questions.md). The sequence is:

1. Generate the live stock preparation in `local_data/stock-prep/` using `prepare-stocks --live`, then run `prepare_stocks.py` locally. Keep its preparation manifest.
2. Generate `dose_and_react.py` for the committed first-round design using `export --live --stage dose_and_react`. Run it after stock preparation and the pipette change.
3. During the reaction, acquire and validate the authentic calibration. After updating the configuration to reflect the completed calibration, generate `workup.py` using `export --live --stage workup`, with the same first-round design and preparation manifest. Run it after the reaction and cooling.

From the repository root, after installation and local configuration:

```bash
uv run python -m hte.cli --config local_data/campaign.json prepare-stocks \
  --output local_data/stock-prep --live
uv run python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-dose --live --stage dose_and_react
```

Then, after the calibration passes and the local configuration is updated:

```bash
uv run python -m hte.cli --config local_data/campaign.json export \
  --design campaigns/hackathon2026/round1_design.csv \
  --output output/r1-workup --live --stage workup
```

See the [pipeline instructions](../../docs/start-here.md#robot-preparation-then-r1) for the configuration and manifest. Exported files and configuration are local; do not commit the API key, instrument data or private records.

## Generate the second-round files

Once all 48 first-round LC results have passed QC, follow the [R2 commands](../../docs/start-here.md#r2-and-finish). The pipeline uses the measured results and Claude to select 22 new pairs and includes the L17 reference. It generates the next dosing design and prints the locations of the R2 files. Run the generated `refill_stocks.py` first, then `dose_and_react.py`, and after cooling run `workup.py`. Keep the first-round dosing history, preparation manifest, calibration and actual LC maps with the local records; they are needed for a consistent second-round export.

```bash
uv run python scripts/hte-lc-results.py next \
  --dosing output/r1-dose/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv --output output/r1-decision
```

Use the actual local export and injection-map filenames. The command also needs the completed calibration and the Claude API key as described in the linked instructions.

For the bench sequence and manual moves, follow the [HTE experimental procedure](../../docs/HTE-START-HERE.md).
