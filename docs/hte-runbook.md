# Experiment

Use the [bench sheet](HTE-staff-checklist.pdf). Staff weigh/coarse-load chemicals, handle caps/labware and start Python locally; the robot measures liquids. Keep generated CSVs with their protocol.

## Chemistry and design

**Pyridine-2-sulfonyl fluoride → 2-fluoropyridine.** Nominal per vial: 25 µmol SM, 1.5 µmol each ligand, 3 µmol Pd(COD)(DQ), 2.5 µmol naphthalene; 250 µL toluene, 95 °C, 500 rpm, 4 h under air. No base/external fluoride. Solvent addition defines nominal concentrations; solute displacement/contraction are accepted approximations.

R1: **48 pairs covering all 30 ligands**, official 24-consensus +24-Sobol design; L07 excluded. Regenerate stocks/protocols/maps. R2: **22 pairs +L17 tBuBrettPhos at 12 mol% total ligand**; L03 at most four wells. No repeats. Higher yield identifies a preliminary candidate; batch effects, reproducibility and cooperativity need later matched controls.

## Robot stock preparation

1. Enter **actual masses/assays** in `weighed_charges_template.csv`. Weigh ligands in the glovebox; keep bottles there. Pd: **4 A3/B3/C3, 22.8 mg each; A4, 21.6 mg** (≤90 mg; keep 10 mg). Naphthalene: **60 mg in 1 C2**; `IS_MASTER` empty. Under air, the robot adds solvents, mixes and prepares reaction/analytical stocks. Preparation is inside campaign time.
2. Use six labeled **Axygen 12-channel reservoirs** as listed in [the weighing/loading map](weighing-list.md); carriers occupy slots 3/6 in batches. Verify actual geometry, solvent and cover compatibility, liquid recovery, mixing and offsets before live release. Follow generated carrier/raw-load CSVs.
3. Run `prepare_stocks.py`: **p300 single left, p1000 single right**; tips 5 /8-9 respectively. Carriers occupy 3/6 temporarily; working racks 1/4. The supplied horizontal 8 ×30 mL reservoir in 2 is **single-channel only**. Robot prepares analytical matrix/masters/working stocks too.
4. Cover/store reserve reservoirs and cap/store the prepared analytical rack. Leave working tubes in mapped positions. Change right pipette to **p300 eight-channel GEN2**, replace tips 8/9 with 300 µL racks using the local App installation/calibration workflow. Keep left p300 single.

| Slot | Reaction-stage use |
|---|---|
| 1 / 4 | 2 mL working tubes; max 1.95 mL. Ligands at CSV addresses; 500 mM IS **1 C2**, SM/IS **4 D2**, Pd **4 A3/B3/C3/A4**; prep acid **4 D3**. Retain RockPhos, SM/IS and all four Pd tubes. |
| 2 | New EMPTY 12-channel reservoir. Robot prepares workup fluids here during the hold; no staff premixing/refills. |
| 3 / 10 | Reaction block at pipetting / heater-shaker positions; manual moves. During holds, 3 temporarily takes raw solvents. |
| 6 | Calibration plate during R1; later a fresh final sample plate per round. Three compatible 96-well LC plates total. |
| 5 / 8 / 9 | Single / multi / multi tips. Keep 7 and 11 empty. |

Confirm block/adapter/latch, offsets, <=45 mm cap clearance and liquid immersion with **1.5 mm bottom clearance**. Confirm LC plate/carrier/seal/needle depth and the requested full 1.7-min method/cycle, UV channel, RTs/LOQs. [Remaining physical setup facts](hte-questions.md).

## Run R1

Start R1 Python with **48 NEW EMPTY vials** in the block at 3. Robot doses **25 µL SM/IS +75 µL each ligand +75 µL Pd**. Retain SM/IS tube **4 D2**, capped between rounds: the robot fills it with **1.89 mL** from the Axygen bulk stock; no R2 refill. Expected remainder after R1 is **689 µL**; R2 requires **at least 680 µL**. Record any loss and use the actual preparation ledger.

Hand-cap all R1 vials; move/latch at App prompts. Run **95 °C /500 rpm /4 h**. During this hold the robot prepares **14 standards** and quench/diluent. Swap analytical rack into 4 and **uncap its source tubes**; raw reservoir into 3. Seal/move calibration plate 6→HPLC. **Reaction stays on 10.** Restore rack 4 and remove raw reservoir when prompted.

**Start a 4 h external timer at each App hold-start message.** Preparation/pauses count. Code cannot stop heat while App-paused. At deadline, stop heat/shaking through the App; record deviations and do not resume dosing. Logging tolerance does not establish chemical equivalence.


---

## Workup and final LC plates

1. Move sealed block to 3; **cool vials before opening**. App separately checks module <=30 °C. **Uncover reservoir 2; keep vials capped while robot pre-fills the fresh LC plate in 6 with 980 µL diluent/well.** Then uncap; robot adds **500 µL 9:1 ACN/water +0.15% FA**. Nominal extract: 750 µL, 0.1% acid, 1.25 mL headspace. Neither fluid contains IS.
2. **Leave reaction vials OPEN**; shake **750 rpm /2 min**, heater off, at the locally confirmed splash-free setting. Return block to 3, let bubbles settle briefly and sample while open. No recap/reopen cycle before sampling.
3. Sample promptly after shaking; LC diluent is already in place. Robot uses a fresh tip, two slow same-well prewets, **21 µL aspiration at 1.5 mm**, 1 µL retained reverse surplus and 2 µL air gap. Dispense nominal **20 µL into prefilled LC wells**, noncontact; discard tip. No manual dilution/vial transfer.
4. Recap reaction vials. Move final LC plate **6→cooled shaker 10**, A1 orientation unchanged. Robot shakes **UNCOVERED, heater OFF, 750 rpm /2 min** at the locally confirmed splash-free speed. Reaction block remains in 3.
5. Move LC plate **10→HPLC**, apply compatible pierceable seal and inject directly. R1: **R1-LC01 A1-H6**, 48 samples. R2: **R2-LC01 A1-H2 plus A3-G3**, 23 samples. **H3 is diluent only; never inject.** Follow generated sequence/maps; reaction and LC coordinates differ.

Final sample: 1 mL; nominal maximum analyte **666.7 µM**, naphthalene **66.7 µM**, FA **0.1%**, toluene **0.667%**. Use the calibrated injection volume. Seal after final shaking to limit evaporation. There are four final-sample plate moves plus the calibration-plate handoff.

## R2 and finish

After ALL 48 R1 results pass QC, select 22 pairs +L17 reference. Run **`refill_stocks.py` before R2 dosing**. Remove block/LC plate from 3/6; present ORIGINAL Axygen reservoirs by ID. **Remove reservoir covers and uncap required working ligand tubes for top-ups.** No new weighing or hand aliquoting. Retain RockPhos; **keep SM/IS and all four Pd tubes capped during refill**. Pd routing: R1 **18/18/12 doses** from A3/B3/C3; R2 **six C3 +17 A4**. Actual mass/assay determines solvent additions and capacity.

Load **23 NEW EMPTY vials** in the SAME block; replace reservoir 2 with a NEW EMPTY one. Uncap required stocks. R2 Python doses **25 µL SM/IS each, then catalysts**; reference receives **150 µL L17**. Hand-cap and start the reaction. During R2 hold the robot makes fresh workup fluids; no new calibration. Repeat workup and final LC analysis.

Cap stock reserves between stages. Robot mixes sources before first use/every eight transfers, without air gaps/blowouts. Same-stock dosing tips may be reused only for validated noncontact transfers. Analytical samples always use fresh tips. Mixing can disperse solids; it does not prove a settling suspension is uniform.

Pause for visible layers, blocked tips, persistent bubbles, air uptake, dripping or tip contact. Do not sample an arbitrary layer, guess a top-up or filter/decant without recording the effect. Reprepare an uncertain analytical dilution robotically and record the replacement; retain rejected measurements. No separate homogeneity study is planned.

Finish after all 23 final injections and quantitative analysis. Save robot JSON logs, raw LC/MS/method/sequence files, actual weighed charges, times and deviations under `local_data/`. Run **`python scripts/hte-return-package.py`**; send its ZIP privately. It retains code, preparation/source ledgers, inputs, results, Claude records and file hashes; credentials are excluded.
