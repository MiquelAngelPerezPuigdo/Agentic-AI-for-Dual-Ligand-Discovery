# Stocks and calibration

**Staff weigh; the OT-2 measures liquids.** Enter actual masses/assays in the charges CSV; follow `bulk_carriers.csv`. Concentrations use nominal solvent addition; no hand aliquoting or volumetric top-up.

## Reaction stocks

| Stock | Preparation target at 100% assay | Per reaction |
|---|---|---|
| SM + mesitylene | **~322.32 mg SM**, nominal 2 mL, **1 M SM +100 mM IS**. Robot adds ~27.82 µL NEAT mesitylene (0.864 g/mL) and the remaining toluene; calculated from actual SM mass/assays. | **25 µL**, retained |
| Each ligand | **20 mM toluene**; weighed charges/reserves in CSV. Robot prepares bulk, mixes and fills working tubes. | **75 µL each**; reference 150 µL L17 |
| Pd(COD)(DQ) | Direct in **4 A3/B3/C3: 22.8 mg each; A4: 21.6 mg**. Robot adds ~1.50/~1.43 mL toluene for **40 mM**. Total **90 mg**, ~5.94 mL; **10 mg for scope**. | 75 µL |
| RockPhos L03 | **~800 µL /20 mM**, 7.50 mg pure equivalent; 7.73 mg at 97%. Prepared directly in **1 C1**; retain that tube. **10 mg available, max 4 R2 wells.** | 75 µL |

Working tubes: 2 mL, max 1.95 mL. **4 D2: 1.88 mL SM/IS** for 71 vials; acid **4 D3**. Retain all four Pd tubes, without refilling: R1 **18/18/12** doses from A3/B3/C3; R2 **6 C3 +17 A4**. CSVs give exact additions from actual masses/assays, checked per tube and in total. Remaining 15 mL bulk sources fail conservative reach; supply suitable geometry. R2 ligand refills use original reserves; record losses.

## Robot-made workup fluids

During EACH hold, robot makes 10% aqueous FA then prepares reservoir 2. Coarse-load raw solvents from CSV into A1-H1 reservoir in temporary slot 3; prepared fluids stay in 2.

| Fluid | Composition | Use |
|---|---|---|
| Quench | **9:1 ACN/water, 0.15% v/v FA**, no IS | 500 µL; capped 1500 rpm /2 min |
| LC diluent | **1:1 water/ACN, 0.1% v/v FA**, no IS | 980 µL +20 µL extract |

## Robot-made authentic standards

Independently weigh FIT and CHECK per analyte: **at least 5 mg each**, assay-corrected; use exact CSV targets and enter actual masses. Product is a liquid: weigh by difference. Robot makes nominal **10 mM** masters (SM: ~6.45 mg /4 mL; product: ~5.83 mg /6 mL), matched matrix and **0.5/5 mM FIT dilutions**; retain reserves.

Robot makes analytical **20 mM mesitylene from 25 µL neat IS**, then a **2 mM working stock**. Each standard gets **33.333 µL**. [Supplier density](https://www.sigmaaldrich.com/US/en/product/aldrich/140864): 0.864 g/mL at 25 °C; configure actual assay.

## Calibration during hold one - 14 injections

Robot fills/pipette-mixes **CALIBRATION**: SM A1-G1, product A2-G2. Seal/move directly to LC during R1. Follow generated preparation and injection maps.

| Analyte, µM | Role | Stock, mM | Analyte, µL | Matrix, µL |
|---:|---|---:|---:|---:|
| 0 | Fit blank | None | 0 | 966.667 |
| 10 | Fit | 0.5 | 20 | 946.667 |
| 50 | Fit | 0.5 | 100 | 866.667 |
| 150 | Fit | 5 | 30 | 936.667 |
| 350 | Fit | 5 | 70 | 896.667 |
| 800 | Fit | 5 | 160 | 806.667 |
| 666.667 | Independent check | 10, CHECK | 66.667 | 900.000 |

Every row receives 33.333 µL IS. Fit blank +five levels; exclude CHECK. Require **R² >=0.995**, **check error <=15%**, fitted-level recovery within **15%** (**20%** at 10 µM), measured separation/LOQs. Quantitative lower bound is the greater of measured LOQ and lowest nonzero calibrator. HTEL exports integrated UV areas; local Python calculates yields. [LC processing](htel-lc-import.md).
