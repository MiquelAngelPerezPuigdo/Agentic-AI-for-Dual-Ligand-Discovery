# HTE staff checklist - setup

**48 pairs, then 22 pairs + L17 reference.** Local OT-2; one 48 × 2 mL Para-Dox; **71 fresh reaction vials**. Individual screw caps by hand. No stir bars. Keep reaction and LC well maps distinct.

## Before starting the clock

- Fit p300 single GEN2 left; p300 eight-channel GEN2 right. Reaction vials use single only (13 mm pitch). Check block/flat adapter/latch, offsets, cap clearance <=45 mm and tips >1 mm above bottoms. App-simulate released Python.
- Use released `dosing.csv`, `stock_preparation.csv`, `deck_loads.csv`, `lc_sequence.csv` and `round2_predose.csv`. Initial selection is prepared; software colleague handles local release/LC import. Stocks and initial scoring are outside the clock.
- Have 71 reaction vials/caps, 71 HPLC vials/caps plus calibration vials, two LC preparation plates, fresh robot racks and >=71 manual sample tips. Confirm full 1.7-min LC cycle and staged batch handoff.

## Stocks - prepare before the run

| Stock | Preparation / use |
|---|---|
| SM in DCM | **500 mM, 10 mL minimum**; 805.8 mg SM at 100% assay. Capped 20 mL glass bulk vial. Dose 50 µL, then evaporate completely. |
| Ligands / Pd | **40 mM in toluene**; individual masses/volumes in stock CSV, including second-round reserve and margin. Open/prepare ligands in glovebox. Keep bulk stocks capped; use ordinary plastic source racks. |
| Mesitylene | **100 mM in toluene, 5 mL**; 60.095 mg at 100% assay. Separate stock; add 25 µL AFTER DCM removal. |
| Quench | **9:1 ACN/water +0.15% v/v formic acid**, no IS. Prepare 100 mL; add 150 µL acid and make to volume with premixed solvent. |
| LC diluent | **1:1 water/ACN +0.1% v/v formic acid**, no IS. Prepare 125 mL; 125 µL acid, make to volume. |

Correct masses for assay. Never load bulk preparation volumes into source tubes. Use **stage-specific deck loads**; refill for round two from reserves.

| Slot | Contents |
|---|---|
| 1 / 4 | Ligand source racks; use exact CSV addresses, leave L07 absent. |
| 2 | A1 SM/DCM; A2 Pd; A3 toluene; A8 mesitylene. Quench A4/A6/A9; LC diluent A5/A7/A10/A11/A12. |
| 3 / 10 | Reaction block for pipetting / heater-shaker with flat adapter. |
| 6 | Standard 96-well LC preparation plate, seated throughout sampling. |
| 5/8/9 | Single tips / multi tips / multi tips. Slots 7 and 11 empty. |

## Calibration during first hold - 14 injections

For **each SM and product**: blank + **10, 50, 150, 350, 800 µM**, plus independent **666.7 µM** check. **Mesitylene fixed at 66.7 µM in every vial**, including blanks/checks. Use matched matrix and recipes in [stock/calibration reference](stocks-and-calibration.md). Software colleague supplies calibrated method/channel and RT windows.

---

# HTE staff checklist - run

**Method / UV channel:** ____________________ **Operator / start:** ____________________

Follow local App pauses. Keep capped vials capped until prompted to open. Record actual times and any deviations.

| Step | Action |
|---|---|
| 1. SM | Run released R1 dosing. Robot adds **50 µL 500 mM SM/DCM** to 48 vials. Move block off deck when prompted; evaporate DCM by HTEL's ventilated procedure. Cool/return to slot 3. |
| 2. Assemble | Robot adds **25 µL mesitylene +37.5 µL ligand A +37.5 µL ligand B +75 µL Pd +75 µL toluene =250 µL**. Hand-tighten every cap; move/latch as prompted. Run **95 °C, 500 rpm, 4 h**. |
| 3. During hold | Run calibration. Separately hand-dose **23 NEW labelled vials with 50 µL SM/DCM each**, using predose map in an ordinary off-deck rack. Evaporate completely, cap dry SM; add NO mesitylene/catalyst yet. |
| 4. Cool | Move sealed block off heater as prompted. Cool before opening. Load released workup and matching sources. |
| 5. Quench | Open caps for addition. Robot adds **500 µL quench per vial**. Recap ALL by hand. Move/latch and shake **1500 rpm, 2 min**, heater off. Return to slot 3. |
| 6. Sample | At each batch pause, gently remix the indicated capped vials; settle bubbles, then uncap ONLY those targets. Robot prepares **980 µL LC diluent +20 µL extract**. Fresh sample tips; no bottom contact. |
| 7. HPLC vials | At pause, recap sampled reaction vials. Keep preparation plate in slot 6. Fresh manual tip per sample: mix completed LC well **500 µL ×5**, avoiding air, then transfer **900 µL** to labelled HPLC vial. Screw cap; invert briefly. Start LC batch BEFORE resuming robot. Never take unfinished wells. |
| 8. Decide | Complete all **48** injections. Software colleague joins exports, checks QC and generates **22 new pairs + L17 reference**. Archive first-round reaction vials. Fit 23 dry SM vials into SAME block; verify orientation. |
| 9. R2 | Refill from reserves using new deck loads. NO SM redosing. Add mesitylene/catalysts/toluene as selected; single reference uses **75 µL L17**, no ligand B. Hand-cap, run same 4 h, cool/work up/sample in batches of 8/8/7. LC preparation H3 is diluent only: DO NOT INJECT. |

Stop clock after all **23** final injections and quantitative analysis. Archive CSVs, maps, QC, protocols and robot JSON logs.

## Stop and correct

Visible layers, solids at aspiration, persistent bubbles, air aspiration or tip contact: pause/review. Repeated aspiration is not a solubility remedy. Reuse only approved same-stock/noncontact tips; samples always fresh. Uncertain transfer: fresh documented dilution, no guessed top-up.

**Timing target: 717.7 /720 min**, requiring 35 min LC/handling overlap. This is unmeasured with ~2 min margin; record real cycle/handling times. Details and local commands: [reference handbook](HTE-operator-handbook.pdf).
