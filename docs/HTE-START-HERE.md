# HTE campaign: start here

Use one local computer for the pipeline and the Opentrons App. The OT-2 is operated locally. The guide never starts the robot or sends a message.

## Start the guide

In the repository folder, install the project once and start the guide:

```bash
uv sync --locked --python 3.12 --extra sources --extra robot
uv run python scripts/hte-guide.py
```

The guide creates `local_data/campaign.json`, `local_data/calibration-plan.csv` and an `anthropic.key` template if missing; it never replaces existing copies. Before step 8, open `anthropic.key` in the repository root and replace its placeholder with the Claude key. Do not paste the key into the guide or send it with the results.

The [two-page bench sheet](HTE-staff-checklist.pdf) is for physical actions. The [weighing map](weighing-list.md) gives each mass, reservoir and channel. No weighing spreadsheet needs to be filled in.

## Follow the menu in order

| Guide step | What the operator does |
|---|---|
| **1. Status** | See the LC settings and local checks still needed. |
| **2. LC settings/checks** | Enter the real method, UV channel, full LC cycle and measured Axygen residual. Enter measured retention times, windows and LOQs when available; confirm checks only after HTE has performed them. The guide does not validate the hardware itself. |
| **3. Stock preview** | Generate stock and R1 protocol previews plus loading maps. Simulate the previews in the local Opentrons App and complete the physical checks before live export. |
| **4. Live stock protocol** | Generate `local_data/stock-prep/prepare_stocks.py`. Weigh and load according to the maps; import and run the Python in the App. Follow the pauses and change the right pipette when requested. |
| **5. R1 dosing** | Generate and run `output/r1-dose/dose_and_react.py` with 48 empty vials. Cap and start the 4 h reaction; use an external timer. During the hold the robot prepares the calibration plate and workup liquids. |
| **6. Calibration** | Run the 14 standards during the first hold. Provide the completed LC export and its reviewed injection map. After the guide saves `local_data/calibration.csv`, review the chromatograms and confirm calibration in step 2. |
| **7. R1 workup** | Generate and run `output/r1-workup/workup.py` after the reaction and cooling. Transfer the prepared LC plate for analysis; retain the generated sequence and injection map. |
| **8. R1 results / choose R2** | Supply every completed R1 export and its reviewed map. The guide validates and processes all 48 samples before Claude selects the next 22 pairs. **This step can incur API charges.** |
| **9. R2 protocols** | Use the existing R2 protocols, or generate them after resolving any live-export check. Run `refill_stocks.py`, then `dose_and_react.py`; after reaction and cooling, run `workup.py`. Load 23 new empty vials. |
| **10. Final results** | Supply the R2 LC export(s) and reviewed map(s). The guide processes all 23 samples; this step does not call Claude. |
| **11. Return package** | Copy instrument files, robot logs and run notes into `local_data/`, then create `transfer/hte-results.zip` and send it privately. |
| **12. Practice** | Run a synthetic end-to-end rehearsal. It makes no paid API calls and cannot run the robot. |

Steps 1–5 can begin before calibration; steps 6 and 7 occur around the first reaction. The guide gives filenames after each step. Never assume injection numbering or plate positions: review each map against the actual LC sequence.

## If something stops

- Read the displayed error and keep the existing output folder. The guide does not overwrite generated protocols or calibration.
- If step 8 is interrupted, repeat **step 8 with the same input files**. Its fixed output location preserves accepted scoring and prevents an ordinary retry from buying those scores again. Do not alter inputs during a retry; inspect any uncertain paid attempt.
- If the R2 decision is complete but protocol export was blocked, resolve the printed local check, then use **step 9**. Do not repeat the decision just to regenerate protocols.
- Missing peaks, failed calibration, ambiguous identity, unsafe liquid handling or an incorrect injection map need HTE review before continuing.

The [operator handbook](HTE-operator-handbook.pdf), [detailed commands](start-here.md), [LC instructions](htel-lc-import.md) and [remaining local checks](hte-questions.md) are available if the guide asks for more detail. The API key and private instrument data stay local.
