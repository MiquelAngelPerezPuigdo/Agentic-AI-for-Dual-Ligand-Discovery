# Experiment

Use the [two-page bench sheet](HTE-staff-checklist.pdf) at the robot. Keep the protocol and its generated CSVs together; `dosing.csv` gives well identities and `deck_loads.csv` gives stage-specific source fills.

## Reaction and design

**Pyridine-2-sulfonyl fluoride (PyFluor) to 2-fluoropyridine.** Per vial: 25 µmol SM, 1.5 µmol each ligand, 3 µmol Pd(COD)(DQ), 2.5 µmol mesitylene; 250 µL toluene, 95 °C, 500 rpm, 4 h under air. No base or external fluoride.

Round one: **48 distinct pairs, all 30 available ligands**; L07 is unavailable. Round two: **22 new pairs + L17 tBuBrettPhos at 12 mol% total ligand**. No repeats. A better pair yield establishes improvement against this reference; it does not establish reproducibility or ligand synergy.

## Before the clock starts

- Fit **p300 single GEN2 left; p300 eight-channel GEN2 right**. Reaction vials have 13 mm pitch: use the single only. The multi serves the standard 96-well LC preparation plate.
- Check the supplied block on the flat adapter: secure mounting, latch closure, cap clearance within **45 mm**, offsets and thermal transfer. Pipette **1.5 mm above the bottom** by default; check actual immersion. Caps are manual; no stir bars or gripper.
- Confirm the existing **1.7-min full LC cycle**, method ID, injection volume, UV channel/wavelength and authentic-standard RT/LOQ settings. Requested 210 nm is provisional; the old example wavelengths are not our method. Record local evidence before release.
- Prepare stocks, caps, tips, 71 fresh reaction vials, 71 sample HPLC vials plus standards, and two LC preparation plates. App-simulate the released Python. [Open setup details](hte-questions.md).

| Slot | Load |
|---|---|
| 1 / 4 | Ligand source racks; exact CSV addresses, L07 absent |
| 2 | A1 SM/DCM; A2 Pd; A3 toluene; A8 mesitylene. Quench A4/A6/A9; diluent A5/A7/A10/A11/A12 |
| 3 / 10 | Vial block for pipetting / heater-shaker with universal flat adapter |
| 6 | Standard 96-well LC preparation plate; keep seated during sampling |
| 5 / 8 / 9 | Single tips / multi tips / multi tips. Keep slots 7 and 11 empty |

## Dose and react

1. Robot doses **50 µL 500 mM SM/DCM** per vial. At the pause, move the block off deck and evaporate completely by HTEL's ventilated procedure. Cool; return to slot 3.
2. Add **25 µL mesitylene +37.5 µL ligand A +37.5 µL ligand B +75 µL Pd +75 µL toluene =250 µL**. Stocks: mesitylene 100 mM; ligands/Pd 40 mM. Reference: use 75 µL L17 instead of the two ligand portions.
3. Hand-tighten all caps. Move/latch at the local pauses; run **95 °C, 500 rpm, 4 h**. Every block move, cap change and tip-rack replacement is manual.
4. During hold one, run the **14 calibration injections**. Hand-dose **23 labelled fresh vials with SM/DCM only** in an ordinary off-deck rack; evaporate fully and cap the dry SM. Add mesitylene/catalysts only after round two is selected. Reuse the same reaction block.

**Timing:** 717.7 min planned against 720 min, requiring 35 min LC/handling overlap. This remains unmeasured, with about two minutes spare. Record actual heating, cooling, cap handling and LC cycle times.

---

## Workup and LC sampling

1. **Cool sealed vials off the heater.** Open for addition; add **500 µL 9:1 ACN/water +0.15% formic acid**. Nominal extract: 750 µL, 0.1% acid, 1.25 mL headspace. Quench and diluent contain no IS.
2. **Hand-recap every vial.** Shake **1500 rpm, 2 min**, heater off; return to slot 3. The block must have cooled for workup.
3. **Sample eight at a time.** Gently remix the indicated capped vials; let bubbles settle. Open only that batch. Other vials stay capped.
4. **Robot dilution:** fresh tip per sample; two slow same-well prewet cycles, without blowing air into the extract. Aspirate 21 µL at 1.5 mm, retain 1 µL reverse surplus, add 2 µL air gap and dispense nominal **20 µL into 980 µL LC diluent**, noncontact. Discard the tip; never revisit the source after destination contact.
5. **At the pause:** recap sampled reaction vials. Keep the preparation plate seated. With a fresh manual tip per completed LC well, mix **500 µL five times**, avoiding air; transfer **900 µL** to the labelled HPLC vial. Cap and invert briefly.
6. **Start that LC batch before resuming the robot.** Never transfer unfinished wells. R1: six batches of eight. R2: 8/8/7; preparation well **H3 is diluent only and must not be injected**. Reaction A1-F8 and LC A1-H6 are different maps.

Final sample: 1.00 mL; maximum SM/product **666.7 µM**; mesitylene **66.7 µM**; formic acid **0.1%**; toluene **0.667%**. Set injection volume from the actual calibrated method.

## Pipetting and transfer faults

Condition fresh dosing tips twice in their own stock. Use slow aspiration, short settling delays, a small air gap and reverse surplus for the organic stocks. Keep active sources covered between stages and bulk reserves capped. Follow CSV fills and dead volumes; never return working liquid to bulk stock.

Reuse a tip only for consecutive **same-stock, noncontact** dosing above the destination top. Different ligands and all analytical samples use fresh tips. Avoid deep immersion, walls and bottoms. Repeated aspiration does not dissolve an insoluble stock and may introduce bubbles.

Pause for persistent layers, solids at the aspiration point, bubbles, air uptake, dripping or tip contact. Do not sample an arbitrary layer. Do not filter, centrifuge or decant without recording its effect on analyte/IS recovery. High rpm alone does not establish quench completeness or extraction recovery; no separate homogeneity study is planned.

For an uncertain LC dilution, remix the original extract and prepare a fresh documented dilution. Do not guess a top-up. Retain rejected measurements with a reason and accept one result per sample; do not select the highest yield.

## Changeover and finish

After all **48 R1 results** pass analytical QC, the local pipeline selects **22 new pairs + L17 reference**. Archive R1 vials; fit the 23 dry predosed vials into the same block and verify orientation. Refill sources using R2 deck loads. **No SM redosing; mesitylene is added once after dry-down.** Repeat reaction and workup.

Stop the clock after all 23 final injections and quantitative analysis. Archive source exports, maps, assay/stock records, method/channel, calibration, QC, times, scoring/cache records, final CSVs, matching protocols and robot JSON logs. Keep experimental data private pending team agreement.
