# Combined reaction stock and five-level calibration

The reaction stock contains starting material and naphthalene together. A separate reservoir channel holds the LC dilution solvent. Calibration solutions use separate authentic analyte stocks and a pure analytical naphthalene stock, so analyte concentration can vary while the reference concentration stays fixed.

## Reaction stock, container and deck source

Prepare **5.00 mL of 250 mM PyFluor + 2.50 mM naphthalene in DCM** before the clock. At the nominal molecular weights and 100% assay, this contains **201.45 mg PyFluor and 1.6021 mg naphthalene**. The stock planner reports both solutes, with separate assay corrections under `substrate_DCM` and `naphthalene`. Bring the solution to its final volume; adding 5 mL solvent to solids is not a final-volume preparation.

Avoid weighing 1.6 mg directly unless the balance supports that measurement. One preparation route is:

1. Prepare a separate **50.0 mM naphthalene master in DCM**, for example 12.817 mg in a final 2.00 mL, correcting for the applicable assay. Use a larger scale if the balance requires it.
2. Weigh the corrected PyFluor mass into a **20 mL glass vial with a DCM-compatible PTFE-faced closure**.
3. Add **250 µL of the 50.0 mM DCM master**, dissolve in DCM, and bring the combined solution to **5.00 mL final volume** using validated volumetric handling.
4. Label both concentrations, solvent, assays, lots, preparation time and expiry/recheck conditions. Store the reserve capped off deck.

The vial is the preparation/storage container. The pipetting source is **A1 of the 12-channel reservoir in OT-2 slot 2**, with nominal 15 mL capacity per channel. It is not a Falcon tube. All eight tips can aspirate from the same long channel to dose full columns. The default source-dedicated tip-reuse plan loads approximately **2.54 mL** for the 66 first-round wells and ten second-round predoses, including the provisional 1 mL aspiration allowance. Fresh-tip mode requires approximately 2.60 mL. **Use the generated `deck_loads.csv` for the exact campaign load**, and retain the rest of the prepared 5 mL capped.

The library reservoir is a geometry placeholder. HTE must confirm the actual reservoir and DCM contact compatibility for the short dosing interval. The [NEST product specification](https://www.nest-biotech.com/reagent-reserviors/59178414.html) identifies a polypropylene 12-channel reservoir; a matching footprint alone does not establish solvent compatibility. Keep the bulk DCM reserve in glass and do not assume a polypropylene centrifuge tube or reservoir is suitable for prolonged storage.

Each **20 µL** combined-stock dose supplies **5.00 µmol substrate and 0.050 µmol naphthalene**, equivalent to 1 mol% naphthalene relative to substrate. Evaporate DCM using the validated first-round procedure. The ten second-round wells receive this same combined stock during the first hold and undergo ambient evaporation; their second-round catalyst protocol adds neither substrate nor naphthalene again. Both amounts appear in `dosing.csv` and `round2_predose.csv`.

## Workup and sample dilution

Reservoir **A4** holds the workup solvent: 1:1 water/ACN with 1% v/v HCOOH, **without additional naphthalene**. Add 50 µL per reaction and mix for two minutes after cooling/opening under HTE's SOP.

Reservoir **A5** holds the LC diluent: the validated 1:1 water/ACN with 1% v/v HCOOH, **without naphthalene or analyte**. Dispense 180 µL into each LC destination first, then transfer 20 µL of homogeneous extract with fresh sample tips, and mix the LC plate for two minutes. Full columns use eight channels for both solvent dispensing and sample transfer.

With quantitative retention/recovery, 0.050 µmol IS in a nominal 100 µL extract is 500 µM. The 20 + 180 µL dilution gives **50 µM naphthalene** and, at 100% yield, **5,000 µM product**. Sample dilution reduces both analyte and IS concentration; their concentration ratio stays constant. Changing the aliquot to 5 µL plus 195 µL gives 12.5 µM IS and a 1,250 µM maximum product concentration. It also changes sample transfer to p20 single. Update the configuration, standards and generated files together; the code checks their IS concentration agreement.

## Separate analytical stocks

Prepare these before the clock, then prepare/run the working standards while the first reaction runs. Use the actual bottle/COA molecular weights and an HTE-approved LC-compatible solvent. ACN is a proposed stock solvent, subject to solubility and method validation.

| Analytical stock | Proposed final volume | Nominal preparation at 100% assay |
|---|---:|---|
| Authentic PyFluor, 100 mM, no IS | 2.00 mL | 32.232 mg, MW 161.16 |
| Authentic 2-fluoropyridine, 100 mM, no IS | 2.00 mL | Approximately 19.418 mg, MW 97.09; verify bottle |
| Pure naphthalene, 50 mM, in LC-compatible solvent | 2.00 mL | 12.817 mg, MW 128.17 |
| Each analyte working stock, 10 mM, no IS | 1.00 mL each | 100 µL of its 100 mM stock, bring to 1.00 mL |
| Pure analytical IS working stock, 1 mM | 2.00 mL | 40 µL of the 50 mM analytical master, bring to 2.00 mL |

Keep the **DCM naphthalene master for reaction dosing** and the **LC-compatible naphthalene master for calibration** distinctly labeled. Do not introduce DCM into the calibration series through an unvalidated solvent substitution. Do not add authentic SM/product calibration solutions to reaction wells.

## Five nonzero analyte levels with fixed reference

Prepare one series for SM and one for product. Each standard below has **1.00 mL final volume**, **50 µM naphthalene**, and the indicated known analyte concentration. The five nonzero fitted levels are 100, 500, 1,000, 2,500 and 6,000 µM. Also prepare an IS-containing zero-analyte blank and an independently prepared 5,000 µM check for each series. This gives **14 injections**, scheduled during the first four-hour reaction. These analytical blanks/checks do not occupy additional reaction wells.

| Final analyte, µM | Analyte stock | Analyte volume, µL | 1 mM IS, µL | Remaining solvent volume to final 1 mL, µL | Role |
|---:|---|---:|---:|---:|---|
| 0 | None | 0 | 50 | 950 | Zero-analyte calibration blank |
| 100 | 10 mM | 10 | 50 | 940 | Calibration level 1 |
| 500 | 10 mM | 50 | 50 | 900 | Calibration level 2 |
| 1,000 | 10 mM | 100 | 50 | 850 | Calibration level 3 |
| 2,500 | 100 mM | 25 | 50 | 925 | Calibration level 4 |
| 6,000 | 100 mM | 60 | 50 | 890 | Calibration level 5 |
| 5,000 | 100 mM | 50 | 50 | 900 | Independent check, excluded from fit |

The remaining solvent must be adjusted for the solvent introduced by both stocks to obtain the **same validated final matrix across standards and samples**. This table specifies solute amounts and volume arithmetic; HTE must supply the final matrix recipe after assessing phase behavior, recovery and the LC method. Adding the same nominal 1:1 diluent to every row without accounting for variable stock solvent would change the matrix. These standards are unsuitable for live quantification until that method validation is complete.

Use the sample IDs and roles in `hte_inputs/calibration_template.csv`, replacing empty area/method/channel fields with measured values. A blank analyte area of zero must represent a verified blank measurement, not a missing export. The fitter uses the blank and five nonzero levels; rows marked `check` remain outside the fit. The proposed independent-check acceptance is ±15% relative concentration error, configurable under `analytics.calibration_check_tolerance_fraction`; HTE must approve this criterion and the fitted range/LOQs for the actual detector.

Serial dilution of the combined reaction stock alone cannot make these fixed-IS standards: it keeps the SM:IS ratio at 100:1 and lowers both concentrations together. At 50 µM naphthalene it would supply 5,000 µM SM. Separate authentic analyte and pure analytical IS stocks let HTE vary the analyte while holding naphthalene at 50 µM.

## Validation of IS added before the reaction

HTE must verify naphthalene retention/recovery through first-round heated DCM removal, second-round ambient DCM removal, the sealed 95 °C hold and the complete extraction/dilution. Confirm that this low loading does not alter the intended chemistry or interfere with the selected peaks. Naphthalene has a reported nonzero vapor pressure; its survival through an open dry-down is an experimental question. [Manufacturer properties](https://www.sigmaaldrich.com/IE/en/product/mm/820846).

IS loss lowers its peak area and can overestimate analyte yield from the area ratio. The software has no measured loss correction; a detector-area check alone cannot establish quantitative recovery. Record the completed bench assessment in `validation.pre_reaction_internal_standard_validated`. Live export remains gated until it and the other applicable validations pass. Any revised IS identity, loading or addition stage requires consistent chemistry context, calibration, stock plan and regenerated protocols.
