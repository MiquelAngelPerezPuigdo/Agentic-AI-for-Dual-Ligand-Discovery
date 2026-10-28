# Weighing list for stock solutions

These are approximate target masses for the current 48-pair + 22-pair campaign, assuming **100% assay**. Use labeled, separate containers. Record actual mass and assay for robot stock preparation.

## Ligands

| ID | Ligand | Target mg | Reservoir / channel |
|---|---|---:|---|
| L01 | MorDal Phos | 27.82 | BULK-03-3 / A6 |
| L02 | racBINAP | 37.36 | BULK-03-3 / A5 |
| L03 | RockPhos | 7.50 | Working rack 1 / C1 |
| L04 | Alphos | 48.90 | BULK-03-3 / A4 |
| L05 | AdBrettPhos | 42.30 | BULK-03-3 / A3 |
| L06 | Me4t-BuXPhos | 27.88 | BULK-03-3 / A2 |
| L08 | t-BuDave Phos | 19.81 | BULK-03-3 / A1 |
| L09 | Xantphos | 33.56 | BULK-02-6 / A6 |
| L10 | OTIPS DalPhos | 30.85 | BULK-02-6 / A5 |
| L11 | Me3OMe-t-BuXPhos | 27.82 | BULK-02-6 / A4 |
| L12 | VBRIDP | 19.63 | BULK-02-6 / A3 |
| L13 | Trimesityl phosphine | 21.76 | BULK-02-6 / A2 |
| L14 | CataCXium ABn | 23.55 | BULK-02-6 / A1 |
| L15 | dppb | 27.29 | BULK-02-3 / A6 |
| L16 | dcypf | 37.03 | BULK-02-3 / A5 |
| L17 | t-BuBrettPhos | 32.96 | BULK-02-3 / A4 |
| L18 | dtbpf | 32.26 | BULK-02-3 / A3 |
| L19 | dppp | 25.57 | BULK-02-3 / A2 |
| L20 | dppf | 34.37 | BULK-02-3 / A1 |
| L21 | Xphos | 26.70 | BULK-01-6 / A6 |
| L22 | RuPhos | 27.07 | BULK-01-6 / A5 |
| L23 | SPhos | 23.81 | BULK-01-6 / A4 |
| L24 | BrettPhos | 31.13 | BULK-01-6 / A3 |
| L25 | MeDalPhos | 26.14 | BULK-01-6 / A2 |
| L26 | Taniaphos SL-T001-2 | 41.26 | BULK-01-6 / A1 |
| L27 | tris(3-chlorophenyl)phosphine | 24.13 | BULK-01-3 / A6 |
| L28 | BippyPhos | 36.48 | BULK-01-3 / A5 |
| L29 | meCgPPh | 17.54 | BULK-01-3 / A4 |
| L30 | N-XantPhos | 31.99 | BULK-01-3 / A3 |
| L31 | Trixie Phos | 23.11 | BULK-01-3 / A2 |

**L03 RockPhos:** 7.50 mg is the pure-equivalent target; at 97% assay, weigh approximately 7.73 mg. Maximum available: 10 mg. L07 is unavailable and excluded.

### Containers for ligand stocks

- **29 ligands:** weigh each ligand into its assigned channel in the six labeled Axygen 12-channel reservoirs. The planned ligand stocks are approximately **2.8–3.6 mL each**. Labels `BULK-01-3` and `BULK-01-6` mean batch 01, temporary deck slots 3 and 6; subsequent batches use those same slots. Remove covers during pipetting; cover and retain reservoirs for R2. Verify the generated `bulk_carriers.csv` after any input change.
- **L03 RockPhos:** weigh directly into its labeled **2 mL working tube**, rack in slot 1, well C1. The robot prepares approximately 0.8 mL in that tube; retain it for both rounds.
- **Working tubes for the other ligands:** the robot transfers prepared stock into labeled **2 mL tubes** in the racks at slots 1 and 4. The generated `deck_loads.csv` gives their working positions. The configured rack uses an Opentrons 24-position 2 mL Eppendorf-tube definition; confirm that the actual tubes and rack are compatible with the solvent and match the definition.

Other bulk sources, including the analytical matrix, require capacity for up to approximately **8 mL**; HTE should include those when choosing the bulk containers and rack.

The supplied Axygen definition and six-carrier layout are configured, but the actual reservoir model, geometry, usable volume, cover, solvent compatibility and lowest accessible volume must be checked before live use. The software assumes 500 µL bulk dead volume; simulation cannot establish recovery. Both Axygen reservoirs and 2 mL working tubes require assessment for toluene exposure; polypropylene is [only conditionally resistant](https://www.eppendorf.com/product-media/doc/en/114794_Userguide/Eppendorf_Consumables_Userguide_023_Tubes_Tips_Chemical-stability-consumables.pdf).

The supplied Sarstedt 6- and 12-well **cell-culture** plate definitions correspond to polystyrene plates; they are **not suitable for the toluene stocks**. Their [manufacturer's specified working volumes](https://www.sarstedt.com/en/RUS/c/life-science/cell-culture/cell-culture-plates/p/cell-culture-plates-12-wells/83.3921.300) are also lower than the nominal total well capacities.

## Other reaction stocks

| Material | Separate charge | Target mass (mg) |
|---|---|---:|
| Pyridine-2-sulfonyl fluoride (starting material) | SM only, BULK-01-3 A1 | 402.90 |
| Naphthalene | IS_SOURCE, working rack 1 C2 | 60.00 |
| Pd(COD)(DQ) | Pd_1, tube 4 A3 | 22.80 |
| Pd(COD)(DQ) | Pd_2, tube 4 B3 | 22.80 |
| Pd(COD)(DQ) | Pd_3, tube 4 C3 | 22.80 |
| Pd(COD)(DQ) | Pd_4, tube 4 A4 | 21.60 |

Weigh **SM only** into Axygen channel BULK-01-3 A1; the robot adds approximately 500 µL naphthalene stock plus 2000 µL toluene, mixes and transfers 1.89 mL to tube 4 D2. Approximately 609 µL remains in the channel; verify recovery physically. Retain tube 4 D2 for both rounds. The analytical IS_MASTER starts empty at BULK-03-6 A5. Pd charges total **90 mg**, leaving 10 mg for scope; do not increase the Pd charges for assay correction. Check stock coverage using actual assay.

## Authentic calibration standards

| Standard | Separate charge | Target mass (mg) |
|---|---|---:|
| Starting material, FIT | SM_FIT, BULK-03-6 A1 | 6.45 |
| Starting material, CHECK | SM_CHECK, BULK-03-6 A2 | 6.45 |
| 2-Fluoropyridine product, FIT | P_FIT, BULK-03-6 A3 | 5.83 |
| 2-Fluoropyridine product, CHECK | P_CHECK, BULK-03-6 A4 | 5.83 |

Weigh FIT and CHECK independently for each analyte. Weigh the liquid product by difference.

Targets assume 100% assay. For lower assay, adjust within material and container limits. Record actual mass and assay; the robot calculates additions. The SM charge must cover the 1.89 mL working transfer, its surplus and the measured bulk residual. If it cannot, the program stops. For generated files, follow [local pipeline](start-here.md).
