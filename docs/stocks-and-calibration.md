# Stock and calibration recipes

Current master: `hte_inputs/campaign.json`, schema 2. Use the actual selected campaign's `stock_preparation.csv` for each ligand mass, bulk preparation volume and source address; `deck_loads.csv` supplies the different dosing/workup loads. **Preparation volume is not on-deck fill volume.** Masses below assume 100% assay; divide by the COA assay fraction and use appropriate solvent-compatible closures.

## Reaction stocks

| Reagent | Bulk preparation | Per reaction |
|---|---|---|
| SM, MW 161.16 | **10.00 mL, 500 mM in DCM**: 805.8 mg, make to final volume; capped 20 mL glass vial | 50 µL =25 µmol; evaporate ALL DCM |
| Each ligand | **40 mM in toluene**, glovebox; selected-campaign CSV contains individual quantities and reserves | 37.5 µL =1.5 µmol each |
| Pd(COD)(DQ), MW 378.8 | **40 mM in toluene**; R1 campaign stock plan prepares 9.53 mL, 144.399 mg | 75 µL =3 µmol |
| Mesitylene, MW 120.19 | **5.00 mL, 100 mM in toluene**: 60.095 mg | 25 µL =2.5 µmol, AFTER dry-down |
| Neat toluene | At least generated reserve; current plan 15.57 mL | 75 µL |

Use ordinary source racks; fancy metal hardware is only the reaction block. Keep bulk ligand reserves in capped glass vials; load the configured working tubes only to their CSV quantities (maximum 1.4 mL). Each stock includes conservative second-round reserve and 50% margin. L17 reserve includes its single reference. All 30 active sources, including small-use ligands, appear on the deck-load sheet. No separate catalyst-solubility study is requested; an observed unsolved suspension still cannot represent a known dissolved concentration.

## Quench and dilution solvent

- **Quench, 100 mL:** premix 9:1 ACN/water. Add **150 µL formic acid**, make to 100 mL with that mixture (0.15% v/v). No IS. Dose 500 µL into 250 µL reaction; recap and shake 1500 rpm for two minutes.
- **LC diluent, 125 mL:** premix 1:1 water/ACN. Add **125 µL formic acid**, make to 125 mL with that mixture (0.1% v/v). No IS. Dose 980 µL and add 20 µL extract.

Nominal final sample: **1.00 mL**, analyte maximum **666.667 µM**, mesitylene **66.667 µM**, formic acid **0.1%**, toluene **0.667%**. This is 64.7 µg/mL product or 107.4 µg/mL SM at 100% amount. The concentration is a reasonable starting load for LC-UV/MS, not an established detector range or an approved injection volume. For context, a [Thermo LC-MS technical note](https://documents.thermofisher.com/TFS-Assets/CMD/Technical-Notes/tn-74053-lc-ms-monitoring-single-quadrupole-system-tn74053-en.pdf) uses 100 µg/mL preparations; that does not validate this method/analytes. Set the actual injection volume with the facility's existing 1.7-minute method and calibration.

## Matched calibration stocks

Analyte concentration varies; **IS is constant**, including blanks/checks. Prepare separate SM and product standards, no reaction-catalyst mixture. A convenient nominal final matrix is **0.667% toluene, about 50.15% ACN, 49.08% water, 0.1% formic acid**. For 100 mL: 0.6667 mL toluene, 50.1492 mL ACN, 0.1000 mL formic acid, water to volume. This approximates the planned final diluted extract and ignores mixing-volume contraction. Prepare all analytical stocks in this same matrix, so adding them preserves solvent/acid proportions.

For each authentic analyte, prepare **10 mM, 10.00 mL**: SM **16.116 mg** or product **9.709 mg**, make to volume with matched matrix. Prepare **1 mM working** by diluting 100 µL of 10 mM to 1.00 mL. These analyte masters contain **NO mesitylene**. Prepare separate independently weighed analyte masters for the check standards; a second dilution of the same master does not check that master's preparation.

Prepare analytical mesitylene **5 mM, 20.00 mL**: **12.019 mg**, make to volume with matched matrix. This is separate from the 100 mM reaction mesitylene stock; using that toluene stock directly would change matrix proportions.

## Fourteen calibration injections during round one

Prepare the following **1.00 mL** samples for each analyte. Add **13.333 µL of 5 mM analytical mesitylene to every sample**, then the analyte aliquot and matrix to final volume. Use suitable calibrated manual pipettes. Cap, mix and label with `calibration_template.csv` IDs.

| Target analyte, µM | Role | Analyte stock, mM | Analyte aliquot, µL | Matrix, µL |
|---:|---|---:|---:|---:|
| 0 | Fit blank | None | 0 | 986.667 |
| 10 | Fit | 1 | 10 | 976.667 |
| 50 | Fit | 1 | 50 | 936.667 |
| 150 | Fit | 10 | 15 | 971.667 |
| 350 | Fit | 10 | 35 | 951.667 |
| 800 | Fit | 10 | 80 | 906.667 |
| 666.667 | Independent check | 10, independent master | 66.667 | 920.000 |

This brackets the nominal 0-100% SM/product range. Fit the blank plus five nonzero levels; keep the independent check outside the fit. Check linear response, separation from mesitylene/other compounds, and practical sensitivity on the actual detector. The lowest standard is not automatically a measured LOQ. Current software requires R² >=0.995 and independent check error <=15%; retain failed measurements rather than changing results to pass.

SM/product quantities and fixed IS are entered in the calibration plan; the importer extracts peak areas. If Chromeleon omits a verified zero peak, supply an explicitly reviewed integrated zero measurement; the software does not silently invent one. A positive omitted peak is not zero. No actual calibration or retention times are prefilled in the public campaign.
