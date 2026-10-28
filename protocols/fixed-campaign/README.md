# Download the planned OT-2 protocols

Download each `.py` file using GitHub's **Download raw file** button and import it into the local Opentrons App. These files can run on the robot. The project owner confirmed the planned setup; the first App pause asks the local operator to check the actual hardware, offsets, source recovery and solvent handling before continuing. Simulate each file in the local App as well. The files embed the planned custom labware definitions.

| Order | File | When to run it |
|---|---|---|
| 1 | [Stock preparation](stock-preparation/prepare_stocks.py) | After weighing and loading. Use its [bulk map](stock-preparation/bulk_carriers.csv) and [solvent map](stock-preparation/raw_reagents_to_load.csv). |
| 2 | [Round 1 dosing and reaction](round1/dose_and_react.py) | After stock preparation and the pipette change. It also prepares workup liquids and the calibration plate during the hold. Use the [dosing](round1/dosing.csv), [deck](round1/deck_loads.csv), [solvent](round1/raw_reagents_to_load.csv) and [calibration](round1/calibration_injection_map.csv) maps. |
| 3 | [Round 1 workup](round1/workup.py) | After the reaction and cooling. Use the [LC sequence](round1/lc_sequence.csv). |
| 4 | **R2 stock refill and dosing** | Generated locally after the R1 results; ligand sources are not yet known. |
| 5 | [Round 2 workup](round2-workup/workup.py) | After R2 and cooling, **only if** the selected R2 layout matches the [fixed well map](round2-workup/well-map.csv). Otherwise use the workup generated for the actual design. |

The R2 workup contains only workup, diluent and sample transfers; it contains no guessed ligand dosing. Its 23 fixed sample positions were checked against different possible R2 selections. H3 of the LC plate receives diluent only and is not a sample.

**These files do not establish LC performance or quantitative calibration.** Run and review the authentic standards during the first reaction, record the actual method and injection maps, and complete calibration before interpreting yields or selecting R2. If hardware, geometry, source volumes, stock recipes or the first-round design differ from the planned setup, stop and regenerate matching files and maps with the pipeline operator. Follow the [bench procedure](../../docs/HTE-START-HERE.md) for the manual caps and moves.

## Software operator: prepare for round two

Follow [local setup and calibration](../../docs/start-here.md) on the workstation. The API key remains on this computer. The published `round1/dosing.csv` is the first-round dosing input; fill the actual injection maps and use real HTEL LC exports.

The software also needs a local stock-preparation manifest for the stock actually made. After entering the confirmed local configuration, generate the manifest with `prepare-stocks --live` as in the [pipeline instructions](../../docs/start-here.md#robot-preparation-then-r1); **do not run stock preparation a second time**. Check that its recipe and design match the published protocol:

```bash
uv run python scripts/check-fixed-campaign.py \
  --preparation local_data/stock-prep/preparation_manifest.json
```

If this check fails, reconcile the actual stock preparation with the software operator before continuing. After real calibration and all 48 R1 LC results pass QC, run:

```bash
uv run python scripts/hte-lc-results.py next \
  --dosing protocols/fixed-campaign/round1/dosing.csv \
  --exports local_data/r1-batch*.csv \
  --injections local_data/r1-map*.csv --output output/r1-decision
```

Replace the filename patterns with the actual local files. The command prints the selected `next_dosing.csv` and, when release checks pass, the R2 `refill_stocks.py`, `dose_and_react.py`, `workup.py` and their maps. Run the printed refill first, then dosing. To use the prepublished R2 workup, check the printed next-dosing path:

```bash
uv run python scripts/check-fixed-campaign.py --r2-dosing "PASTE THE NEXT DOSING PATH HERE"
```

If the positions differ, use the generated R2 workup instead. After the 23 R2 measurements, follow the [final analysis and data-return steps](../../docs/start-here.md#r2-and-finish).
