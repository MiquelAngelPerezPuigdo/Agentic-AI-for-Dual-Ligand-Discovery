# Experiment

Use the [two-page bench sheet](HTE-staff-checklist.pdf). Every precise liquid transfer is robotic. Staff supply weighed chemicals/bulk liquids, handle caps and labeled labware moves, and import/start Python locally. Keep generated CSVs with their protocol.

## Chemistry and design

**Pyridine-2-sulfonyl fluoride → 2-fluoropyridine.** Nominal per vial: 25 µmol SM, 1.5 µmol each ligand, 3 µmol Pd(COD)(DQ), 2.5 µmol mesitylene; 250 µL toluene, 95 °C, 500 rpm, 4 h under air. No base/external fluoride. Solvent addition defines nominal concentrations; solute displacement/contraction are accepted approximations.

R1: **48 distinct pairs covering all 30 available ligands**; L07 excluded. R2: **22 new pairs +L17 tBuBrettPhos at 12 mol% total ligand**; L03 at most four wells. No repeats. Better yield than this reference establishes improvement for this screen, without establishing reproducibility or cooperativity experimentally.

## Robot stock preparation

1. Generate `weighed_charges_template.csv`; weigh labeled charges and enter **actual masses/assays**. Ligands are weighed in the glovebox; preserve original reagent bottles there. Stock preparation is under air on the OT-2. The robot calculates solvent volumes, adds neat mesitylene, mixes stocks and fills working tubes. Stock preparation is inside the campaign.
2. Load carrier IDs/positions from `bulk_carriers.csv`; coarse-load raw solvents from `raw_reagents_to_load.csv`. Standard-library **15 mL conical geometry is provisional**: confirm actual container/solvent compatibility for the campaign, or supply the exact compatible glass-source definition. No assumed glass-vial dimensions.
3. Run `prepare_stocks.py`: **p300 single left, p1000 single right**; tips 5 /8-9 respectively. Carriers occupy 3/6 temporarily; working racks 1/4. The supplied horizontal 8 ×30 mL reservoir in 2 is **single-channel only**. Robot prepares analytical matrix/masters/working stocks too.
4. Cap/store reserve carriers and the prepared analytical rack. Leave working tubes in mapped positions. Change right pipette to **p300 eight-channel GEN2**, replace tips 8/9 with 300 µL racks using the local App installation/calibration workflow. Keep left p300 single.

| Slot | Reaction-stage use |
|---|---|
| 1 / 4 | 2 mL working tubes; max 1.95 mL. Ligands at CSV addresses; neat IS **1 C2**, SM/IS **4 D2**, Pd **4 A3/B3**. Retain RockPhos **1 C1** throughout. |
| 2 | New EMPTY 12-channel reservoir. Robot prepares workup fluids here during the hold; no staff premixing/refills. |
| 3 / 10 | Reaction block at pipetting / heater-shaker positions; manual moves. During holds, 3 temporarily takes raw solvents. |
| 6 | Calibration plate during R1; later a fresh final sample plate per round. Three compatible 96-well LC plates total. |
| 5 / 8 / 9 | Single / multi / multi tips. Keep 7 and 11 empty. |

Confirm block/adapter/latch, offsets, <=45 mm cap clearance and liquid immersion with **1.5 mm bottom clearance**. Confirm LC plate/carrier/seal/needle depth and the requested full 1.7-min method/cycle, UV channel, RTs/LOQs. [Remaining physical setup facts](hte-questions.md).

## Predose, then run R1

Start R1 Python with **23 NEW R2 vials** in the SAME block. Robot adds **25 µL combined SM/IS** each. Cap/store those vials; replace them with 48 EMPTY R1 vials and uncap. Robot then doses R1: **25 µL SM/IS +75 µL each ligand +75 µL Pd**. No evaporation or separate reaction IS addition.

Hand-cap all R1 vials; move/latch at App prompts. Run **95 °C /500 rpm /4 h**. During this hold the robot prepares the **14 calibration standards**, pipette-mixes them and prepares quench/diluent from raw solvents. Staff swap the analytical rack into 4, raw reservoir into 3, and move the completed calibration plate directly 6→HPLC, sealing before injection. **Do not move the reaction block from 10.** Restore working rack 4 and remove raw reservoir 3 when prompted. Hardware uses elapsed time to count preparation within the four-hour hold.


---

## Workup and final LC plates

1. Move sealed block to 3; **cool vials before opening**. The App separately checks module <=30 °C. Robot adds **500 µL 9:1 ACN/water +0.15% FA** from the prepared reservoir. Nominal extract: 750 µL, 0.1% acid, 1.25 mL headspace. Quench/diluent contain no IS.
2. **Hand-recap ALL vials**; shake **1500 rpm /2 min**, heater off. Return block to 3. Let bubbles settle; open the indicated vials for sampling.
3. Robot uses a fresh sample tip, two slow same-well prewets, **21 µL aspiration at 1.5 mm**, 1 µL retained reverse surplus and 2 µL air gap. Dispense nominal **20 µL into 980 µL diluent**, noncontact; discard tip. No manual dilution or sample-vial transfer.
4. Recap reaction vials. Move final LC plate **6→cooled shaker 10**, A1 orientation unchanged. Robot shakes **UNCOVERED, heater OFF, 1000 rpm /2 min** at the locally confirmed splash-free speed. Reaction block remains in 3.
5. Move LC plate **10→HPLC**, apply compatible pierceable seal and inject directly. R1: **R1-LC01 A1-H6**, 48 samples. R2: **R2-LC01 A1-H2 plus A3-G3**, 23 samples. **H3 is diluent only; never inject.** Follow generated sequence/maps; reaction and LC coordinates differ.

Final sample: 1 mL; nominal maximum analyte **666.7 µM**, mesitylene **66.7 µM**, FA **0.1%**, toluene **0.667%**. Use the calibrated injection volume. Seal after final shaking to limit evaporation. There are four final-sample plate moves plus the calibration-plate handoff.

## R2 and finish

After ALL 48 R1 results pass QC, the pipeline selects 22 pairs +L17 reference. Run **`refill_stocks.py` before R2 dosing**. Temporarily remove block/LC plate from 3/6; present the ORIGINAL bulk carriers by ID. Robot calculates top-ups from R1 consumption and refills original working tubes. **No new catalyst weighing or hand aliquoting. Keep RockPhos in its original tube.**

Restore the SAME block with the 23 capped robot-predosed vials; replace reservoir 2 with a NEW EMPTY one. Uncap all 23. R2 Python adds catalysts only; reference receives **150 µL L17**. No SM/IS redose. During R2 hold the robot makes fresh workup fluids; no new calibration. Repeat workup and final LC analysis.

Cap stock reserves between stages. Robot mixes sources before first use/every eight transfers, without air gaps/blowouts. Same-stock dosing tips may be reused only for validated noncontact transfers. Analytical samples always use fresh tips. Mixing can disperse solids; it does not prove a settling suspension is uniform.

Pause for visible layers, blocked tips, persistent bubbles, air uptake, dripping or tip contact. Do not sample an arbitrary layer, guess a top-up or filter/decant without recording the effect. Reprepare an uncertain analytical dilution robotically and record the replacement; retain rejected measurements. No separate homogeneity study is planned.

Finish after all 23 final injections and quantitative analysis. Save robot JSON logs, raw LC/MS/method/sequence files, actual weighed charges, times and deviations under `local_data/`. Run **`python scripts/hte-return-package.py`**; send its ZIP privately. It retains code, preparation/source ledgers, inputs, results, Claude records and file hashes; credentials are excluded.
