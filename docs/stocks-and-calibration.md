# Stocks and calibration

Use `stock_preparation.csv` for masses/reserves; load only the stage's `deck_loads.csv` quantities. **Bulk volume is not deck fill.** Correct masses for COA assay. Prepare ligands in the glovebox.

## Reaction stocks

| Stock | Bulk preparation at 100% assay | Per reaction |
|---|---|---|
| SM, MW 161.16 | **10.00 mL, 500 mM in DCM:** 805.8 mg; make to volume in a capped 20 mL glass vial | 50 µL; evaporate fully |
| Each ligand | **40 mM in toluene**; masses and reserves in CSV | 37.5 µL each |
| Pd(COD)(DQ), MW 378.8 | **40 mM in toluene**; current plan 9.53 mL, 144.399 mg | 75 µL |
| Mesitylene, MW 120.19 | **5.00 mL, 100 mM in toluene:** 60.095 mg | 25 µL, after dry-down |
| Toluene | Current reserve plan 15.57 mL | 75 µL |

Capped glass bulk reserves; ordinary plastic working racks, maximum 1.4 mL/tube; common liquids in the 12-channel reservoir. CSVs include 50% working margin, dead volume and conservative R2 reserves. Refill stage sources; never return working liquid to bulk.

## Workup solvents - no internal standard

| Solution | Prepare | Use |
|---|---|---|
| Quench | **100 mL, 9:1 ACN/water +0.15% v/v formic acid:** 150 µL acid, make to volume with premixed solvent | 500 µL; recap, 1500 rpm, 2 min |
| LC diluent | **125 mL, 1:1 water/ACN +0.1% v/v formic acid:** 125 µL acid, make to volume with premixed solvent | 980 µL +20 µL extract |

## Analytical stocks - matched matrix

**Matrix, 100 mL:** 0.6667 mL toluene +50.1492 mL ACN +0.1000 mL formic acid; water to volume. Approximate diluted-extract matrix; ignores volume contraction. Prepare all analytical stocks in it.

**Separate 10 mM analyte masters, 10.00 mL:** SM 16.116 mg; product 9.709 mg. No IS. For 1 mM working stocks, dilute 100 µL master to 1.00 mL. Make check masters by **independent weighing**.

**Analytical mesitylene, 5 mM, 20.00 mL:** 12.019 mg in matched matrix. Do not use the reaction mesitylene/toluene stock.

## Calibration during hold one - 14 injections

Prepare seven **1.00 mL vials per analyte**. Every vial, including blank/check, receives **13.333 µL of 5 mM mesitylene** (66.667 µM final IS). Add the quantities below; cap, mix and use `calibration_template.csv` IDs.

| Analyte, µM | Role | Stock, mM | Analyte, µL | Matrix, µL |
|---:|---|---:|---:|---:|
| 0 | Fit blank | None | 0 | 986.667 |
| 10 | Fit | 1 | 10 | 976.667 |
| 50 | Fit | 1 | 50 | 936.667 |
| 150 | Fit | 10 | 15 | 971.667 |
| 350 | Fit | 10 | 35 | 951.667 |
| 800 | Fit | 10 | 80 | 906.667 |
| 666.667 | Independent check | 10, independent | 66.667 | 920.000 |

Fit blank +five levels; exclude the check. Require **R² >=0.995**, **check error <=15%**, separation and measured LOQs on the actual method. The lowest standard is not automatically the LOQ. Record method, wavelength and injection volume.

Maximum sample: 666.667 µM analyte; 64.7 µg/mL product or 107.4 µg/mL SM. Calibration must establish the detector range. [LC import and pilot replay](htel-lc-import.md) covers reviewed blank absences and optional mixed-standard practice. Retain failed checks/rejected measurements.
