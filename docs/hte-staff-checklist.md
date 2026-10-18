# Bench sheet - setup

**48 pairs, then 22 pairs + L17 reference.** One 48 x 2 mL Para-Dox, reused with **71 fresh reaction vials**. Manual screw caps; no stir bars. Keep reaction and LC maps separate.

## Before the clock

- Fit **p300 single GEN2 left; p300 multi GEN2 right**. Single only for 13 mm-pitch reaction vials. Check block/latch, offsets, cap height <=45 mm and tips >1 mm above bottoms. Simulate released Python locally.
- Use matching `dosing.csv`, `stock_preparation.csv`, `deck_loads.csv`, `lc_sequence.csv` and `round2_predose.csv`. A software colleague handles release and LC imports. Stocks and initial scoring are outside the clock.
- Have 71 reaction vials/caps, **two final 96-well LC plates** matching the VWR 2.2 mL geometry, compatible pierceable seals and fresh tips; standards separately. Confirm plate fit on shaker AND autosampler, needle depth and **full 1.7-min LC cycle**.

## Prepare stocks

| Stock | Bulk preparation / use |
|---|---|
| SM + mesitylene | **2.0 mL: 1 M SM +100 mM IS in toluene.** 322.32 mg SM +24.04 mg IS at 100% assay; make to FINAL volume, 4 mL capped vial. Dose **25 µL**; retain solvent. |
| Ligands | **20 mM in toluene.** CSV masses/reserves; prepare in glovebox. Working tubes **2 mL**, max 1.95 mL. |
| Pd(COD)(DQ) | Weigh **90 mg ONCE**, make to **5.94 mL FINAL volume**, 40 mM in toluene, capped 8 mL glass vial (100% assay). Keep **10 mg solid for scope**. |
| RockPhos L03 | **800 µL, 20 mM:** 7.50 mg pure equivalent; correct for assay. **10 mg available; maximum 4 R2 wells.** |
| Quench | **100 mL, 9:1 ACN/water +0.15% formic acid:** 150 µL acid, make to volume. No IS. |
| LC diluent | **125 mL, 1:1 water/ACN +0.1% formic acid:** 125 µL acid, make to volume. No IS. |

Correct masses for assay, **except Pd: keep 90 mg and adjust final volume** (98%: 5.82 mL). Load stage-specific CSV fills; R2 Pd comes from the SAME bulk. Mix capped glass stocks off deck; gently invert capped working tubes, let bubbles clear, return to mapped positions and open. **Do not shake plastic racks on the module.** Robot remixes catalyst sources twice, up to 100 µL, before first use and every eight transfers.

## Deck

| Slot | Contents |
|---|---|
| 1 / 4 | 2 mL working tubes: ligands at CSV addresses; **SM/IS in slot 4 D2, 1.31 mL for R1**. L07 absent. **Pd slot 4: R1 A3/B3, 1.91 mL EACH; R2 fresh A3, 1.83 mL** |
| 2 | Quench A4/A6/A9; diluent A5/A7/A10/A11/A12. A1/A2/A3/A8 unused |
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
| 1 / SM + IS | Dose **25 µL combined stock** into 48 open vials. Keep the toluene. No separate IS addition. |
| 2 / Reaction | Add **75 µL ligand A +75 µL ligand B +75 µL Pd =250 µL total**. Hand-cap; move/latch as prompted. **95 °C, 500 rpm, 4 h.** |
| 3 / During hold | Run calibration. Hand-dose **23 labelled NEW vials with 25 µL combined SM/IS stock each** from off-deck reserve. **Cap promptly; retain toluene.** No catalyst yet. |
| 4 / Cool | Move the sealed block off the heater. Cool vials before opening; App also waits for module <=30 °C. Load workup sources. |
| 5 / Quench | Add **500 µL quench** per vial. Hand-recap ALL. Shake **1500 rpm, 2 min**, heater off; return to slot 3. |
| 6 / Sample | Let bubbles settle after shaking; uncap the indicated reaction vials. Robot adds **20 µL extract to 980 µL diluent** with fresh sample tips. |
| 7 / LC handoff | Recap reaction vials. Move the completed LC plate **6 → cooled shaker 10** at App prompt. Robot shakes **UNCOVERED, heater OFF, 1000 rpm, 2 min** (locally confirmed splash-free speed). Move **10 → HPLC**, apply compatible seal. Inject directly from this plate; **no manual dilution/mixing or vial transfers**. |
| 8 / R2 setup/select | During R1 LC, archive sampled R1 vials; fit 23 capped predosed vials into the SAME block. After all 48 results pass QC, select 22 pairs +L17 reference; **RockPhos at most 4 wells**. |
| 9 / R2 | Refill R2 deck loads; **uncap all 23 NEW vials. No SM/IS redose.** Add catalysts; reference uses **150 µL L17**, no B. Cap; repeat 4 h reaction/workup. One new LC plate; **H3 is diluent only: do not inject.** |

Stop the clock after **23 final injections and quantitative analysis**. Give the pipeline operator robot JSON logs, raw LC/MS files, stock records, actual times and deviations for the private return ZIP.

## If a transfer looks wrong

Pause for layers, solids at aspiration, persistent bubbles, air uptake or tip contact. Repeated aspiration does not fix solubility. Reuse tips only for approved same-stock/noncontact dosing; samples always get fresh tips. Replace an uncertain dilution with a fresh documented one; do not guess a top-up.

**12-hour operating target:** 8 h reaction holds +120.7 min LC; **119.3 min for all other tasks and contingency**. Calibration/R2 SM predosing overlap hold one; R2 block changeover can overlap R1 LC after sampling. Confirm actual cycle/handling times before release. **Four LC-plate moves; no R1 split.** [Full procedure and local commands](HTE-operator-handbook.pdf).
