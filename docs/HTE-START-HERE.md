# HTE campaign: experimental procedure

Open this page in Chrome and follow the steps in order. The linked pages contain the amounts, deck positions and extra detail. The OT-2 is operated locally; staff weigh and load chemicals, handle caps and move labware when the App pauses.

**Campaign:** 48 ligand pairs in round 1, followed by 22 new pairs and one single-ligand reference in round 2. Each reaction is **250 µL in toluene, 95 °C, 500 rpm, 4 h**. Naphthalene is added with the starting material.

**Start with:** [what to weigh and where to put it](weighing-list.md) · [solvents and deck loading](deck-loading.md) · [deck picture](figures/ot2-deck-setup.png) · [two-page bench sheet](HTE-staff-checklist.pdf).

## 1. Before starting

1. Confirm the [remaining local checks](hte-questions.md): the Axygen reservoirs and covers, their toluene compatibility and liquid recovery, the reaction block and caps, uncovered shaking, the LC plate, and the requested **1.7-minute LC method**. Check the actual injection cycle and separation using standards.
2. Have the **48 × 2 mL Para-Dox block**, **71 clean glass vials and caps** for both rounds, six labeled Axygen 12-channel stock reservoirs with suitable covers, the specified working-tube racks, tips and **three compatible 96-well LC plates** ready.
3. The pipeline operator prepares the current Python protocols and loading files and checks them in the local Opentrons App. Use those files together with this page. [Technical instructions](start-here.md).

## 2. Weigh and load the stocks

1. Weigh each of the **30 ligands**, Pd, starting material, naphthalene and calibration standards as shown in the [weighing list and position map](weighing-list.md). Weigh ligands in the glovebox and keep their original bottles there. There is no mass-entry spreadsheet to fill in.
2. Put the powders into their labeled Axygen channels or working tubes as specified in the map. **RockPhos is in tube 1 C1, naphthalene in 1 C2, Pd in 4 A3/B3/C3/A4 and starting material in BULK-01-3 A1.** Leave the analytical IS_MASTER channel empty.
3. Pour the raw solvents into the eight-channel reservoir using the amounts and positions in [deck loading](deck-loading.md). Follow the generated `raw_reagents_to_load.csv` if the pipeline operator has changed the configuration.

## 3. Let the robot prepare the stocks

1. Install the **p300 single on the left** and **p1000 single on the right**; load their tips as in [deck loading](deck-loading.md). The pipeline operator supplies `prepare_stocks.py` and its loading maps.
2. Import and start `prepare_stocks.py` in the local Opentrons App. At each pause, place the requested labeled reservoirs in slots **3 and 6**, remove their covers and resume. Cover and retain them when removed. The robot adds solvents, mixes and fills the working tubes.
3. Check that the prepared naphthalene stock is clear at the App pause. Follow the remaining prompts and retain the working tubes and reservoirs for round 2.
4. When prompted, change the **right** pipette to the **p300 eight-channel**, and replace its tip racks in slots 8 and 9 with 300 µL tips. The p300 single remains on the left.

## 4. Dose and start round 1

1. Load **48 new empty vials** in the reaction block at **slot 3**, the working racks in slots 1 and 4, and an empty workup reservoir in slot 2. Follow the [reaction deck map](deck-loading.md) and generated loading files.
2. Start the supplied R1 `dose_and_react.py` in the App. The robot doses **25 µL SM/naphthalene, 75 µL ligand A, 75 µL ligand B and 75 µL Pd** per vial.
3. At the pause, screw the vial caps on by hand and move the block from **slot 3 to the heater-shaker in slot 10**. Follow the App prompts. Start an **external four-hour timer** when the App announces the reaction hold.

## 5. During the first four-hour reaction

1. Leave the capped reaction block on the heater-shaker. At the App pauses, load the raw solvents in slot 3 and the prepared analytical source rack in slot 4. [Solvent positions and amounts](deck-loading.md#raw-solvents-during-each-reaction-hold).
2. The robot prepares the quench and LC diluent and fills a calibration plate with **14 standards**. Seal and move that plate to LC, and start the calibration sequence during the reaction. Use the generated calibration map and record the actual injection order.
3. Restore the working rack and remove the raw-solvent reservoir when the App asks. The LC operator reviews the standards and provides the calibration export and injection map to the pipeline operator. [Calibration details](stocks-and-calibration.md#calibration-during-hold-one---14-injections).
4. Watch the external timer: **an App pause does not stop heating**. If the protocol is still paused at four hours, stop heating and shaking through the App and record the deviation.

## 6. Cool, quench and prepare the R1 LC plate

1. Move the sealed block back to **slot 3** and let the vials cool before opening. Keep them capped while the robot fills the LC plate with **980 µL diluent per sample**.
2. At the App pause, unscrew the vials. The robot adds **500 µL quench** to each. Move the open block to the cooled heater-shaker and shake **750 rpm for 2 minutes, heater off**, using the locally confirmed splash-free setting.
3. Return the block to slot 3. Let bubbles settle briefly; keep the vials open. The robot transfers **20 µL extract** per sample into the prefilled LC plate with fresh sample tips, aspirating slowly at **1.5 mm above the vial bottom**. Recap the reaction vials for storage.
4. Move the LC plate from **slot 6 to the cooled heater-shaker**, shake **uncovered at 750 rpm for 2 minutes, heater off**, then move it to LC and apply the compatible seal. Inject the 48 samples using the generated sequence. [Detailed workup](hte-runbook.md#workup-and-final-lc-plates).

## 7. Select and run round 2

1. Give the pipeline operator the completed R1 LC export(s), the reviewed injection map(s) and the calibration data. After all **48 results pass QC**, the pipeline uses Claude to choose **22 new pairs**, plus the L17 reference. This selection uses the API key and can incur charges.
2. The pipeline operator supplies the R2 files. Run **`refill_stocks.py` first**: uncover the requested retained Axygen reservoirs and open the required working tubes at the App pauses. Keep the original SM/naphthalene, RockPhos and Pd tubes; there is no SM or Pd refill.
3. Load **23 new empty vials** in the same reaction block and a **new empty workup reservoir** in slot 2. Run the supplied R2 `dose_and_react.py`, cap the vials and repeat **95 °C / 500 rpm / 4 h**, with an external timer. During the hold the robot prepares fresh workup liquids.
4. After cooling, run R2 `workup.py` and repeat the quench, open shaking, robot sampling and LC-plate shaking described in step 6. Inject the **23 samples**; the generated map marks **H3 as diluent only—do not inject it**.

## 8. Finish and return the data

Give the pipeline operator the completed R2 LC export(s) and reviewed injection map(s). The pipeline calculates the final results; no further Claude selection is needed. Save the original LC/MS files, robot logs, actual injection maps, times and deviations for the [private return package](development.md#return-the-campaign-to-miquel).

If tips block, air is aspirated, bubbles persist, layers or solids are visible, or there is a spill or unexpected contact, pause and record the issue before continuing. Keep the original files and do not guess a top-up. For a fuller description see the [operator handbook](HTE-operator-handbook.pdf) or [experiment runbook](hte-runbook.md); for the software operator see the [pipeline instructions](start-here.md).
