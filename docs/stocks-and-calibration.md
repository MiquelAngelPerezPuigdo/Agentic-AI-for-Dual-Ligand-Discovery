# Stocks and calibration

Use `stock_preparation.csv` for masses/reserves; load only the stage's `deck_loads.csv` quantities. **Bulk volume is not deck fill.** Correct masses for COA assay. Prepare ligands in the glovebox.

## Reaction stocks

| Stock | Bulk preparation at 100% assay | Per reaction |
|---|---|---|
| SM + IS | **2.0 mL, 1 M SM +100 mM mesitylene in toluene:** 322.32 mg SM +24.04 mg mesitylene; make to FINAL volume in a capped 4 mL glass vial | **25 µL**, retained; supplies both SM and IS |
| Each ligand | **20 mM in toluene**; masses/reserves and 4 or 8 mL bulk-vial sizes in CSV | **75 µL each**; reference 150 µL L17 |
| Pd(COD)(DQ) | **40 mM in toluene**; current plan 10 mL, 151.52 mg | 75 µL |
| RockPhos, L03 | **800 µL, 20 mM:** 7.50 mg at 100% assay; 7.73 mg at 97%. 4 mL bulk vial; **10 mg available, at most 4 R2 wells** | 75 µL; two frozen R1 wells |

Use capped glass bulk vials and **2 mL Eppendorf working tubes, max 1.95 mL**, in plastic racks. Combined stock: **slot 4 D2, load 1.31 mL for R1**; keep **575 µL off deck for R2**. The 2 mL preparation rounds the requested ~10% allowance; includes dead volume/surplus. Ligands retain 50% margin. Refill from reserves; never return working liquid to bulk.

## Workup solvents - no internal standard

| Solution | Prepare | Use |
|---|---|---|
| Quench | **100 mL, 9:1 ACN/water +0.15% v/v formic acid:** 150 µL acid, make to volume with premixed solvent | 500 µL; recap, 1500 rpm, 2 min |
| LC diluent | **125 mL, 1:1 water/ACN +0.1% v/v formic acid:** 125 µL acid, make to volume with premixed solvent | 980 µL +20 µL extract |

## Analytical stocks - matched matrix

**Matrix, 100 mL:** 0.6667 mL toluene +50.1492 mL ACN +0.1000 mL formic acid; water to volume. Approximate diluted-extract matrix; ignores volume contraction. Prepare all analytical stocks in it.

Use **`analytical_stock_preparation.csv`**. Prepare **two independently weighed 2 mL, 10 mM masters per analyte**: **SM 3.22 mg each; product 1.94 mg each**, corrected for assay. Use 4 mL glass vials, no IS. One master fits calibration; the other supplies the check/optional pilots. Save unused stock; increase minimum weighing if required by the balance.

**1 mM working stocks:** 20 µL FIT master +180 µL matrix; 0.5 mL tube. Use the [LC instructions](htel-lc-import.md). Prepare standards manually; use authentic SM/product masters separately from the combined reaction stock.

**Analytical mesitylene, 5 mM, 20.00 mL:** 12.019 mg in matched matrix, separate from the combined reaction stock.

## Calibration during hold one - 14 injections

Prepare seven **1 mL standards per analyte** in a compatible plate/vials. Each receives **13.333 µL of 5 mM mesitylene**. Add analyte/matrix below; mix, seal and use `calibration_template.csv` IDs.

| Analyte, µM | Role | Stock, mM | Analyte, µL | Matrix, µL |
|---:|---|---:|---:|---:|
| 0 | Fit blank | None | 0 | 986.667 |
| 10 | Fit | 1 | 10 | 976.667 |
| 50 | Fit | 1 | 50 | 936.667 |
| 150 | Fit | 10 | 15 | 971.667 |
| 350 | Fit | 10 | 35 | 951.667 |
| 800 | Fit | 10 | 80 | 906.667 |
| 666.667 | Independent check | 10, independent | 66.667 | 920.000 |

Fit blank +five levels; exclude the check. Require **R² >=0.995**, **check error <=15%**, measured separation/LOQs. Record method, wavelength and injection volume; lowest standard is not automatically the LOQ.
