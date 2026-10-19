# Stocks and calibration

**Staff weigh; the OT-2 measures liquids.** Enter actual masses/assays in the charges CSV; follow `bulk_carriers.csv`. Concentrations use nominal solvent addition; no hand aliquoting or volumetric top-up.

## Reaction stocks

| Stock | Preparation target at 100% assay | Per reaction |
|---|---|---|
| SM + mesitylene | **~322.32 mg SM /2 mL: 1 M SM +100 mM IS**. Robot adds ~27.82 µL neat IS +toluene; adjusted to actual mass/assays. | **25 µL** |
| Each ligand | **20 mM toluene**; weighed charges/reserves in CSV. Robot prepares bulk, mixes and fills working tubes. | **75 µL each**; reference 150 µL L17 |
| Pd(COD)(DQ) | Direct in **4 A3/B3/C3: 22.8 mg each; A4: 21.6 mg**. Robot adds ~1.50/~1.43 mL toluene for **40 mM**. Total **90 mg**, ~5.94 mL; **10 mg for scope**. | 75 µL |
| RockPhos L03 | **~800 µL /20 mM**, 7.50 mg pure equivalent; 7.73 mg at 97%. Prepared directly in **1 C1**; retain that tube. **10 mg available, max 4 R2 wells.** | 75 µL |

Working tubes: 2 mL, max 1.95 mL. Load **1.89 mL SM/IS into 4 D2**; retain capped, no refill. Including losses: R1 uses **1201 µL**, leaves **689 µL**; R2 uses **576 µL**, leaves **113 µL** (R2 minimum: **680 µL**). Start with **48 empty R1 /23 new empty R2 vials**; dose 25 µL SM/IS before catalysts each round.

Acid: **4 D3**. Retain all four Pd tubes, without refilling: R1 **18/18/12** doses from A3/B3/C3; R2 **6 C3 +17 A4**. CSVs give exact additions from actual masses/assays, checked per tube and in total. Remaining 15 mL bulk sources fail conservative reach; supply suitable geometry. R2 ligand refills use original reserves; record losses.

## Robot-made workup fluids

Each hold: robot makes 10% aqueous FA, then fluids in reservoir 2. Coarse-load raw solvents per CSV into A1-H1 reservoir in temporary slot 3.

| Fluid | Composition | Use |
|---|---|---|
| Quench | **9:1 ACN/water, 0.15% v/v FA**, no IS | 500 µL; open vials, heater off, 750 rpm /2 min |
| LC diluent | **1:1 water/ACN, 0.1% v/v FA**, no IS | 980 µL +20 µL extract |

## Robot-made authentic standards

Weigh separate FIT and CHECK charges per analyte: **at least 5 mg**, assay-corrected; enter actual masses. Weigh liquid product by difference. Robot makes **10 mM** masters (SM ~6.45 mg /4 mL; product ~5.83 mg /6 mL), matched matrix and **0.5/5 mM FIT dilutions**. Retain reserves.

Robot makes **20 mM mesitylene from 25 µL neat IS**, then **2 mM** working stock. [Density](https://www.sigmaaldrich.com/US/en/product/aldrich/140864): 0.864 g/mL at 25 °C; configure assay.

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

Add **33.333 µL IS to every row**. Fit blank +five levels, exclude CHECK. Require **R² >=0.995**, **check error <=15%**, fit recovery within **15%** (**20%** at 10 µM), measured separation/LOQs. Quantitative floor: greater of measured LOQ and lowest nonzero calibrator. Local Python converts integrated UV areas to yields. [LC processing](htel-lc-import.md).
