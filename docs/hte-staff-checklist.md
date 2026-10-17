# Bench sheet - setup

**48 pairs, then 22 pairs + L17 reference.** One 48 x 2 mL Para-Dox, reused with **71 fresh reaction vials**. Manual screw caps; no stir bars. Keep reaction and LC maps separate.

## Before the clock

- Fit **p300 single GEN2 left; p300 multi GEN2 right**. Single only for 13 mm-pitch reaction vials. Check block/latch, offsets, cap height <=45 mm and tips >1 mm above bottoms. Simulate released Python locally.
- Use matching `dosing.csv`, `stock_preparation.csv`, `deck_loads.csv`, `lc_sequence.csv` and `round2_predose.csv`. A software colleague handles release and LC imports. Stocks and initial scoring are outside the clock.
- Have 71 reaction vials/caps, **two final 96-well LC plates** matching the VWR 2.2 mL geometry, compatible pierceable seals and fresh tips; standards separately. Confirm plate fit on shaker AND autosampler, needle depth and **full 1.7-min LC cycle**.

## Prepare stocks

| Stock | Bulk preparation / use |
|---|---|
| SM in DCM | **500 mM, 10 mL:** 805.8 mg SM at 100% assay; capped 20 mL glass vial. Dose 50 µL; evaporate fully. |
| Ligands / Pd | **40 mM in toluene.** Use CSV masses/reserves. Open and prepare ligands in glovebox. Keep reserves capped. |
| Mesitylene | **100 mM in toluene, 5 mL:** 60.095 mg. Dose 25 µL AFTER DCM removal. |
| Quench | **100 mL, 9:1 ACN/water +0.15% formic acid:** 150 µL acid, make to volume. No IS. |
| LC diluent | **125 mL, 1:1 water/ACN +0.1% formic acid:** 125 µL acid, make to volume. No IS. |

Correct masses for assay. **Load stage-specific CSV volumes, not bulk preparations.** Refill R2 from reserves; ordinary plastic source racks are sufficient.

## Deck

| Slot | Contents |
|---|---|
| 1 / 4 | Ligand source racks; exact CSV addresses; L07 absent |
| 2 | A1 SM/DCM; A2 Pd; A3 toluene; A8 mesitylene. Quench A4/A6/A9; diluent A5/A7/A10/A11/A12 |
| 3 / 10 | Reaction block: staff move it by hand at App prompts; pipetting / heater-shaker |
| 6 | Final 96-well 2.2 mL LC plate: fill here; move to 10, then directly to HPLC |
| 5 / 8 / 9 | Single tips / multi tips / multi tips. Keep 7 and 11 empty |

## Calibration during hold one - 14 injections

**Each SM and product:** blank + **10, 50, 150, 350, 800 µM**, plus independent **666.7 µM** check. **Mesitylene stays at 66.7 µM in every standard.** Use matched matrix and [calibration recipes](stocks-and-calibration.md). HTEL exports UV areas; Python calibrates and calculates yields. The software colleague handles method/RT settings and [pilot checks](htel-lc-import.md).

---

# Bench sheet - run

**Operator / start:** ____________________ **LC method / channel:** ____________________

Follow App pauses. Hand-tighten reaction-vial caps before heating/shaking; the LC plate shakes uncovered. Record actual times and deviations.

| Step | Action |
|---|---|
| 1 / SM | Dose **50 µL SM/DCM** into 48 vials. At pause, move off deck; evaporate fully by HTEL's ventilated procedure. Cool; return to slot 3. |
| 2 / Reaction | Add **25 µL mesitylene +37.5 µL ligand A +37.5 µL ligand B +75 µL Pd +75 µL toluene =250 µL**. Hand-cap; move/latch as prompted. **95 °C, 500 rpm, 4 h.** |
| 3 / During hold | Run calibration. Hand-dose **23 labelled NEW vials with 50 µL SM/DCM each** in an off-deck rack. Evaporate fully; cap dry SM. No mesitylene/catalyst yet. |
| 4 / Cool | Move the sealed block off the heater. Cool before opening. Load workup and its matching sources. |
| 5 / Quench | Add **500 µL quench** per vial. Hand-recap ALL. Shake **1500 rpm, 2 min**, heater off; return to slot 3. |
| 6 / Sample | Let bubbles settle after shaking; uncap the indicated reaction vials. Robot adds **20 µL extract to 980 µL diluent** with fresh sample tips. |
| 7 / LC handoff | Recap reaction vials. Move the completed LC plate **6 → cooled shaker 10** at App prompt. Robot shakes **UNCOVERED, heater OFF, 1000 rpm, 2 min** (locally confirmed splash-free speed). Move **10 → HPLC**, apply compatible seal. Inject directly from this plate; **no manual dilution/mixing or vial transfers**. |
| 8 / Select R2 | After all **48 results** pass QC, software selects **22 new pairs + L17 reference**. Archive R1 vials; fit the 23 dry predosed vials into the SAME block. Check orientation. |
| 9 / R2 | Refill from R2 deck loads. **No SM redose.** Add selected stocks; reference uses **75 µL L17**, no ligand B. Cap; repeat 4 h reaction/workup. Prepare all 23 in one new LC plate. LC well **H3 is diluent only: do not inject.** |

Stop the clock after **23 final injections and quantitative analysis**. Save exports, maps, QC, protocols, times and robot JSON logs.

## If a transfer looks wrong

Pause for layers, solids at aspiration, persistent bubbles, air uptake or tip contact. Repeated aspiration does not fix solubility. Reuse tips only for approved same-stock/noncontact dosing; samples always get fresh tips. Replace an uncertain dilution with a fresh documented one; do not guess a top-up.

**Timing: 752.7 /720 min with retained allowances.** Workup allowance: 72 min across both rounds; calculated pumping/waits/shaking alone: 33.5 min, excluding caps/movement. Time actual handling before release. **Four LC-plate moves total**, excluding initial loading. [Full procedure and local commands](HTE-operator-handbook.pdf).
