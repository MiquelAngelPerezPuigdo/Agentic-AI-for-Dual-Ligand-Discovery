# Experiment

Use the [two-page bench sheet](HTE-staff-checklist.pdf) at the robot. Keep the protocol and its generated CSVs together; `dosing.csv` gives well identities and `deck_loads.csv` gives stage-specific source fills.

## Reaction and design

**Pyridine-2-sulfonyl fluoride (PyFluor) to 2-fluoropyridine.** Per vial: 25 µmol SM, 1.5 µmol each ligand, 3 µmol Pd(COD)(DQ), 2.5 µmol mesitylene; 250 µL toluene, 95 °C, 500 rpm, 4 h under air. No base or external fluoride.

Round one: **48 distinct pairs, all 30 available ligands**; L07 is unavailable. Round two: **22 new pairs + L17 tBuBrettPhos at 12 mol% total ligand**. No repeats. A better pair yield establishes improvement against this reference; it does not establish reproducibility or ligand synergy.

## Before the clock starts

- Fit **p300 single GEN2 left; p300 eight-channel GEN2 right**. Reaction vials have 13 mm pitch: use the single only. The multi serves the standard 96-well LC preparation plate.
- Check the supplied block on the flat adapter: secure mounting, latch closure, cap clearance within **45 mm**, offsets and thermal transfer. Pipette **1.5 mm above the bottom** by default; check actual immersion. Caps are manual; no stir bars or gripper.
- Confirm the existing **1.7-min full LC cycle**, method ID, injection volume, UV channel/wavelength and authentic-standard RT/LOQ settings. Requested 210 nm is provisional; the old example wavelengths are not our method. Record local evidence before release.
- Prepare stocks, caps, tips, 71 fresh reaction vials, two final autosampler-compatible 96-well deep-well LC plates with pierceable seals, plus standards. The supplied VWR definition is 2.2 mL/well; confirm the physical plate fits BOTH the flat adapter and autosampler, including seal, carrier and needle depth. The derived `_hs.json` adds movement geometry only; it does not establish physical compatibility. App-simulate the released Python. [Open setup details](hte-questions.md).

| Slot | Load |
|---|---|
| 1 / 4 | 2 mL Eppendorf working tubes; ligands at CSV addresses, L07 absent; combined SM/IS in **slot 4 D2**; **Pd in slot 4 A3/B3 for R1, fresh A3 for R2** |
| 2 | Quench A4/A6/A9; diluent A5/A7/A10/A11/A12. A1/A2/A3/A8 unused |
| 3 / 10 | Reaction block: staff move it by hand at App prompts; pipetting / heater-shaker |
| 6 | VWR 96-well 2.2 mL deep-well preparation plate, or matching configured replacement; fill here, shake on 10, then directly to HPLC |
| 5 / 8 / 9 | Single tips / multi tips / multi tips. Keep slots 7 and 11 empty |

## Dose and react

1. Robot doses **25 µL combined 1 M SM +100 mM mesitylene in toluene** per open vial. The 25 µL remains in the reaction. Load **1.31 mL** in the **2 mL source tube, slot 4 D2**, and preserve the off-deck R2 reserve.
2. Add **75 µL ligand A +75 µL ligand B +75 µL Pd =250 µL total including the SM/IS stock**. Ligands are **20 mM**, Pd **40 mM**. Reference: **150 µL L17** instead of the two ligand portions. No separate IS or solvent top-up.
3. Hand-tighten all caps. Move/latch at local pauses; run **95 °C, 500 rpm, 4 h**. Every block move, cap change and tip-rack replacement is manual.
4. During hold one, run **14 calibration injections**. Hand-dose **23 labelled fresh vials with 25 µL combined SM/IS stock each** from the off-deck reserve; **cap promptly and retain the toluene**. Add catalysts only after R2 selection. Reuse the same block.

**12-hour operating target:** 480 min reaction holds +120.7 min LC; **119.3 min for all remaining handling, workups, decisions, final analysis and contingency**. Calibration and R2 SM predosing overlap hold one. After R1 sampling, prepare the R2 block while LC runs; catalyst dosing waits for all 48 results and selection. One LC plate per round, four moves total; no R1 split. Confirm the full cycle and handling times locally before release.

---

## Workup and LC sampling

1. **Cool sealed vials off the heater before opening.** The App separately waits for module temperature <=30 °C before workup; its reading does not establish vial temperature. Open for addition; add **500 µL 9:1 ACN/water +0.15% formic acid**. Nominal extract: 750 µL, 0.1% acid, 1.25 mL headspace. Quench and diluent contain no IS.
2. **Hand-recap every vial.** Shake **1500 rpm, 2 min**, heater off; return to slot 3. The block must have cooled for workup.
3. **One LC plate per round.** Let bubbles settle after the automated extract shake; open the indicated reaction vials for sampling. Other vials stay capped.
4. **Robot dilution:** fresh tip per sample; two slow same-well prewet cycles, without blowing air into the extract. Aspirate 21 µL at 1.5 mm, retain 1 µL reverse surplus, add 2 µL air gap and dispense nominal **20 µL into 980 µL LC diluent**, noncontact. Discard the tip; never revisit the source after destination contact.
5. **Recap sampled reaction vials.** The reaction block stays in slot 3. At the App move prompt, take the completed LC plate **slot 6 → cooled heater-shaker slot 10**. Keep A1 orientation. Robot latches and shakes the plate **UNCOVERED, heater OFF, 1000 rpm for 2 min**; use the locally confirmed splash-free speed. It waits for module temperature ≤30 °C before loading. No manual sample mixing/pipetting.
6. **Move directly 10 → HPLC** at the prompt; apply the confirmed pierceable autosampler seal. Load the correct carrier, plate definition and needle depth. R1 plate **R1-LC01: A1-H6, 48 samples**; R2 **R2-LC01: A1-H2 plus A3-G3, 23 samples**, column-wise. **H3 contains diluent only: do not inject.** Use `lc_plates.csv` and `lc_sequence.csv`; the 48-vial reaction map differs from the LC map. Inject directly from the plate; no individual sample-vial transfers.

Final sample: 1.00 mL; maximum SM/product **666.7 µM**; mesitylene **66.7 µM**; formic acid **0.1%**; toluene **0.667%**. Set injection volume from the actual calibrated method. Final LC plates and their headspace remain unchanged during injection; seal after shaking to limit evaporation.

## Pipetting and transfer faults

Before dosing, mix tightly capped glass bulk stocks off deck by inversion or a suitable vortex holder. Gently invert capped working tubes; let bubbles clear, restore mapped positions, then open. Plastic racks are not configured heater-shaker loads. Keep bulk stocks in glass; PP working tubes are for brief, unheated dispensing, not prolonged toluene storage.

The robot remixes each catalyst source with **two submerged cycles, up to 100 µL**, before first use and every eight transfers. This also conditions fresh tips; other fresh dosing tips receive two same-source prewets. Mixing consumes no extra stock and uses no air gap or blowout. It can redisperse particles but cannot guarantee a uniform settling suspension. Use slow dosing, small air gaps and reverse surplus. Follow CSV fills; never return working liquid to bulk stock.

Reuse a tip only for consecutive **same-stock, noncontact** dosing above the destination top. Different ligands and all analytical samples use fresh tips. Avoid deep immersion, walls and bottoms. Repeated aspiration does not dissolve an insoluble stock and may introduce bubbles.

Pause for persistent layers, solids at the aspiration point, bubbles, air uptake, dripping or tip contact. Do not sample an arbitrary layer. Do not filter, centrifuge or decant without recording its effect on analyte/IS recovery. High rpm alone does not establish quench completeness or extraction recovery; no separate homogeneity study is planned.

For an uncertain LC dilution, remix the original extract and prepare a fresh documented dilution. Do not guess a top-up. Retain rejected measurements with a reason and accept one result per sample; do not select the highest yield.

## Changeover and finish

During R1 LC, after all R1 sampling is complete, archive those vials and fit the 23 capped liquid-predosed vials into the same block; verify orientation. After all **48 R1 results** pass QC, the pipeline selects **22 new pairs +L17 reference**. The R2 pause confirms this changeover; do not replace already-loaded new vials again. Refill R2 deck loads and **remove all 23 caps before dosing**. **No SM or IS redosing. RockPhos L03 is limited to four R2 wells.** Repeat reaction/workup.

Stop the clock after all 23 final injections and quantitative analysis. Save robot JSON logs, raw LC/MS files and stock/time/deviation notes in `local_data/` as shown on the local-pipeline page. Run `python scripts/hte-return-package.py` and send the ZIP privately to Miquel. It preserves code, local settings, exports/maps, calibration/QC, results, Claude records and matching dosing/protocols, with file hashes and credentials excluded.
