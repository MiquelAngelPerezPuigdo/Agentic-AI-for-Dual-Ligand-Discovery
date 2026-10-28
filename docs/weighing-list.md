# Weighing list for stock solutions

These are approximate target masses for the current 48-pair + 22-pair campaign, assuming **100% assay**. Use labeled, separate containers. Record actual mass and assay for robot stock preparation.

## Ligands

| ID | Ligand | Target mass (mg) |
|---|---|---:|
| L01 | MorDal Phos | 27.82 |
| L02 | racBINAP | 37.36 |
| L03 | RockPhos | 7.50 |
| L04 | Alphos | 48.90 |
| L05 | AdBrettPhos | 42.30 |
| L06 | Me4t-BuXPhos | 27.88 |
| L08 | t-BuDave Phos | 19.81 |
| L09 | Xantphos | 33.56 |
| L10 | OTIPS DalPhos | 30.85 |
| L11 | Me3OMe-t-BuXPhos | 27.82 |
| L12 | VBRIDP | 19.63 |
| L13 | Trimesityl phosphine | 21.76 |
| L14 | CataCXium ABn | 23.55 |
| L15 | dppb | 27.29 |
| L16 | dcypf | 37.03 |
| L17 | t-BuBrettPhos | 32.96 |
| L18 | dtbpf | 32.26 |
| L19 | dppp | 25.57 |
| L20 | dppf | 34.37 |
| L21 | Xphos | 26.70 |
| L22 | RuPhos | 27.07 |
| L23 | SPhos | 23.81 |
| L24 | BrettPhos | 31.13 |
| L25 | MeDalPhos | 26.14 |
| L26 | Taniaphos SL-T001-2 | 41.26 |
| L27 | tris(3-chlorophenyl)phosphine | 24.13 |
| L28 | BippyPhos | 36.48 |
| L29 | meCgPPh | 17.54 |
| L30 | N-XantPhos | 31.99 |
| L31 | Trixie Phos | 23.11 |

**L03 RockPhos:** 7.50 mg is the pure-equivalent target; at 97% assay, weigh approximately 7.73 mg. Maximum available: 10 mg. L07 is unavailable and excluded.

### Containers for ligand stocks

- **29 ligands:** weigh each ligand into its own labeled, solvent-compatible bulk source container. The planned ligand stocks are approximately **2.8–3.6 mL each**. HTE must choose short, robot-accessible containers and a matching rack definition; confirm capacity, solvent compatibility and pipette reach. The configured deep 15 mL Falcon sources cannot be released for live use. The generated `bulk_carriers.csv` gives each container's carrier and position; regenerate it after choosing the labware.
- **L03 RockPhos:** weigh directly into its labeled **2 mL working tube**, rack in slot 1, well C1. The robot prepares approximately 0.8 mL in that tube; retain it for both rounds.
- **Working tubes for the other ligands:** the robot transfers prepared stock into labeled **2 mL tubes** in the racks at slots 1 and 4. The generated `deck_loads.csv` gives their working positions. The configured rack uses an Opentrons 24-position 2 mL Eppendorf-tube definition; confirm that the actual tubes and rack are compatible with the solvent and match the definition.

Other bulk sources, including the analytical matrix, require capacity for up to approximately **8 mL**; HTE should include those when choosing the bulk containers and rack.

## Other reaction stocks

| Material | Separate charge | Target mass (mg) |
|---|---|---:|
| Pyridine-2-sulfonyl fluoride (starting material) | Reaction stock: SM only | 322.32 |
| Naphthalene | IS_SOURCE | 60.00 |
| Pd(COD)(DQ) | Pd_1, tube 4 A3 | 22.80 |
| Pd(COD)(DQ) | Pd_2, tube 4 B3 | 22.80 |
| Pd(COD)(DQ) | Pd_3, tube 4 C3 | 22.80 |
| Pd(COD)(DQ) | Pd_4, tube 4 A4 | 21.60 |

Weigh **SM only** for the reaction stock; the robot adds naphthalene solution. The analytical IS_MASTER starts empty. Pd charges total **90 mg**, leaving 10 mg for scope; do not increase the Pd charges for assay correction. Check stock coverage using actual assay.

## Authentic calibration standards

| Standard | Separate charge | Target mass (mg) |
|---|---|---:|
| Starting material, FIT | SM_FIT | 6.45 |
| Starting material, CHECK | SM_CHECK | 6.45 |
| 2-Fluoropyridine product, FIT | P_FIT | 5.83 |
| 2-Fluoropyridine product, CHECK | P_CHECK | 5.83 |

Weigh FIT and CHECK independently for each analyte. Weigh the liquid product by difference.

Targets for ligand and standard masses assume 100% assay. For lower assay, adjust the required charge for equivalent pure material within the available stock and container limits. The robot uses the measured mass and assay to calculate solvent additions. For generated carrier positions and preparation files, follow [local pipeline](start-here.md). Bulk-container geometry still requires local confirmation before live operation.
