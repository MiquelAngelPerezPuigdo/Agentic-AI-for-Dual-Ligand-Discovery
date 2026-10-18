# Bench sheet - setup

**48 pairs, then 22 pairs + L17 reference.** One 48 × 2 mL Para-Dox, 71 fresh reaction vials. Manual caps and labware moves. **All precise liquid handling is robotic**, including stocks, standards, R2 predoses and source refills.

## Load chemicals

- Weigh labeled charges from **`weighed_charges_template.csv`**; enter actual masses/assays. Weigh ligands in the glovebox. Robot adjusts solvent addition; respect mass limits.
- Coarse-load raw solvents to CSV minimum fills. Supplied **8 ×30 mL A1-H1 reservoir: single-channel ONLY**. No manual aliquoting or volumetric top-up.
- **Release blocked:** default bulk sources fail the conservative no-nozzle-entry check. Supply actual short, solvent-compatible stock containers/rack JSON; regenerate and check reach. Carrier slots **3/6**; retain capped reserves and original working tubes.
- Have **three compatible 96-well LC plates**, 2.2 mL geometry, 1 mL/sample, carrier/seals. Confirm offsets, mounting, caps and actual 1.7-min method/cycle. Import/simulate locally.

## Pipettes

**Initial preparation:** p300 single left /p1000 single right; 300 µL tips in 5, 1000 µL in 8/9. After preparation, change RIGHT to **p300 eight-channel GEN2** and tips 8/9 to 300 µL via the App installation/calibration workflow. Left stays installed.

## Stocks - all liquids prepared by robot

| Stock | Rule |
|---|---|
| Ligands | Nominal **20 mM**, generous reserves. Weighed charges in mapped carriers. |
| RockPhos L03 | **~7.50 mg pure equivalent**, assay-corrected; 10 mg available. Robot makes **~800 µL in 1 C1**. Retain SAME tube; **max 4 R2 wells**. |
| Pd(COD)(DQ) | **90 mg maximum**, nominal **40 mM /~5.94 mL**. SAME bulk both rounds; **10 mg solid reserved for scope**. |
| SM + mesitylene | **~322.32 mg SM** at 100% assay; robot adds neat IS/toluene: nominal **1 M /100 mM**, ~2 mL. **4 D2: 1.88 mL** for all 71 vials. |

Concentrations use nominal solvent addition. **No hand refills or R2 stock remake.**

## Reaction-stage deck

| Slot | Contents |
|---|---|
| 1 /4 | 2 mL working tubes, max 1.95 mL. Neat IS **1 C2**, SM/IS **4 D2**, Pd **4 A3/B3**. |
| 2 | EMPTY 12-channel reservoir; robot makes quench A4/A6/A9 and diluent A5/A7/A10/A11/A12. |
| 3 /10 | Reaction block: pipetting /heater-shaker. During holds, raw solvents temporarily occupy 3. |
| 4 /6 in R1 hold | Prepared analytical rack temporarily in 4; calibration plate in 6, then directly to LC. Later, 6 takes each final LC plate. |
| 5 /8 /9 | Tips. Keep **7 and 11 empty**. |

---

# Bench sheet - run

**Operator / start:** ____________________ **LC method / channel:** ____________________

Follow App pauses and matching loading CSVs. Staff handle weighing, coarse liquid loading, caps, rack/plate moves and local starts. Robot preparation counts inside the campaign.

| Step | Action |
|---|---|
| 1 / Stocks | Run **`prepare_stocks.py`** from actual weights. Load requested carriers uncapped; cap/store when removed. Retain the preparation manifest. Make the one right-pipette/tip-rack change after preparation. |
| 2 / R2 predose first | Load **23 NEW R2 vials** in the SAME reaction block. R1 Python doses **25 µL SM/IS each**. Hand-cap/store them, then fit **48 NEW EMPTY R1 vials** and uncap. No manual pipetting. |
| 3 / R1 reaction | Robot doses **25 µL SM/IS +75 µL ligand A +75 µL ligand B +75 µL Pd**. Hand-cap; move/latch. **95 °C, 500 rpm, 4 h. Start the external timer when the App announces the hold starts.** |
| 4 / During R1 hold | Leave reaction on 10. Load raw solvents in 3 and analytical rack in 4 at prompts. Robot makes **14 standards** and quench/diluent in 2. Seal/move calibration plate **6 → HPLC**; start sequence. Restore rack 4; remove raw reservoir. **Monitor the timer:** pauses do not stop heating. If the deadline arrives while paused, stop heat/shaking via App and record the overrun; do not resume dosing. |
| 5 / Cool / quench | Move sealed block to 3; cool before opening. Robot adds **500 µL quench**. Hand-recap ALL; shake **1500 rpm, 2 min**, heater off; return to 3. |
| 6 / LC samples | Let bubbles clear; uncap indicated vials. Robot adds **20 µL extract to 980 µL diluent**, fresh sample tips. Recap reaction vials. |
| 7 / Final plate | Move **6 → cooled shaker 10**. Robot shakes **UNCOVERED, heater OFF, 1000 rpm, 2 min** at confirmed splash-free speed. Move **10 → HPLC**, seal and inject directly. No manual dilution/vial transfers. |
| 8 / R2 select/refill | After all **48 valid R1 results**, Claude selects **22 new pairs +L17 reference**. Run **`refill_stocks.py` FIRST**: present original bulk carriers; robot tops up original working tubes. Retain RockPhos. |
| 9 / R2 | Restore the SAME block with 23 capped robot-predosed vials. Replace reservoir 2 with a NEW EMPTY one. Uncap all 23; run R2 Python. **No SM/IS redose.** Reference uses **150 µL L17**, no B. Repeat reaction/workup; robot prepares workup fluids during this hold too. **R2 H3 is diluent only: do not inject.** |

Calibration: each analyte blank +**10, 50, 150, 350, 800 µM**, independent **666.7 µM** check; constant **66.7 µM mesitylene**. Python calculates calibrated yields from integrated UV areas. Stop the clock after all 23 final injections and quantitative analysis.

Pause for blocked tips, persistent bubbles, air uptake, obvious layers or tip contact. Do not guess liquid top-ups or repair a dilution by hand. Report deviations so stock accounting can be corrected.

**Timing:** 12 h is advisory, not demonstrated. Record actual times and hold deviations. Give logs/raw LC files/stock records to the pipeline operator; return using **`python scripts/hte-return-package.py`**.
