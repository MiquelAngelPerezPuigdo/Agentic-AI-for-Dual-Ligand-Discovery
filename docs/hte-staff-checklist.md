# HTE staff checklist - setup

**Campaign folder:** ____________________ **Operator/date:** ____________________

**Before use:** HTE must release the block/seal/mount, pipetting heights, extraction/IS recovery, LC method/matrix and a measured plan within 12 h. These remain pending; live export enforces LC settings and timing. Use released files.

## Before the clock

- Have the real batch/stock/deck CSVs, LC sequences and Python protocols. Check **65 pairs + one L17 reference; all 31 ligands covered in pairs**. Start the local export hook/watcher; key file: `anthropic.key` on the laptop.
- Prepare stocks from `stock_preparation.csv`, including reserves and assay corrections. Prepare ligands in the glovebox. Label IDs/addresses; dispense only homogeneous stocks; cap reserves.

| Stock | Preparation / dispensing concentration |
|---|---|
| SM + naphthalene | 250 mM SM + 2.5 mM IS in DCM; prepare at least 5.00 mL. |
| All 31 ligands | 30 mM in toluene; CSV gives each mass and reserve. |
| Pd(COD)(DQ) | 60 mM in toluene; verify identity/assay and solubility. |
| Toluene | Neat. |
| Workup / LC diluent | Separate sources: 1:1 water/ACN + 1% v/v HCOOH; no IS. |

**SM:** pyridine-2-sulfonyl fluoride (PyFluor). **Product:** 2-fluoropyridine. Combined-stock recipe at 100% assay: 201.45 mg SM + 250 uL of 50 mM naphthalene/DCM master; DCM to final 5.00 mL in a capped 20 mL glass/PTFE vial. Naphthalene master: 12.817 mg to final 2.00 mL; prepare separate DCM and LC-compatible masters.

## OT-2 deck - load stage quantities from `deck_loads.csv`

**Left:** p20 single GEN2. **Right:** p300 eight-channel GEN2. Manual block moves only.

| Slot | Contents |
|---|---|
| 1 / 4 | Ligand racks: L01-L24 / L25-L31, at the exact CSV well addresses. |
| 2 | 12-channel reservoir: A1 SM/IS/DCM; A2 Pd; A3 toluene; A4 workup; A5 LC diluent. |
| 3 / 10 | Reaction glass-vial block for dosing/cooling / heater-shaker with released adapter. |
| 6 | Second-round substrate array during first dosing; LC plate during workup. |
| 5 / 8 / 9 | p20 tips / p300 tips / p300 tips. Keep slots 7 and 11 empty. |

## LC calibration - prepare stocks now; run standards during round one

Authentic SM/product stocks: **100 mM, 2.00 mL each, no IS** (SM 32.232 mg; product 19.418 mg at 100% assay; correct from COA). Working analyte: 100 uL of 100 mM to 1.00 mL (10 mM). Analytical IS: 40 uL of LC-compatible 50 mM master to 2.00 mL (1 mM).

For **each analyte**, make 1.00 mL per concentration column, with **50 uL of 1 mM IS in every tube**. Use the approved matrix recipe, accounting for stock solvents.

| Analyte, uM | 0 blank | 100 | 500 | 1,000 | 2,500 | 6,000 | 5,000 check |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stock, mM | None | 10 | 10 | 10 | 100 | 100 | 100 |
| Analyte, uL | 0 | 10 | 50 | 100 | 25 | 60 | 50 |
| Matrix solvent, uL | 950 | 940 | 900 | 850 | 925 | 890 | 900 |

Fit the blank and five nonzero levels; keep the independent 5,000 uM check outside the fit. **14 injections total**, during the first reaction.

---

# HTE staff checklist - run

**Block/seal:** ____________________ **LC method/channel:** ____________________

Follow the local App's pauses and the released CSV well maps. Keep plate orientation and sample IDs intact. Start the competition timer with first-round dosing; stocks and first-batch selection are prepared beforehand.

| Step | Staff action |
|---|---|
| 1. First dosing | Import `round1/dose_and_react.py` into the local OT-2 App. Confirm offsets/deck. Dose **20 uL combined SM/IS/DCM into 66 wells** in slot 3. |
| 2. Remove DCM | Manually move the open block to slot 10. Use the released dry-down procedure (initial proposal: 37 C, 300 rpm, 10 min; requires HTE validation). Verify the dry endpoint; return to slot 3 as prompted. |
| 3. Assemble and react | Per pair: **10 uL ligand A + 10 uL ligand B + 20 uL toluene + 10 uL Pd stock**. Reference: **20 uL L17 + 20 uL toluene + 10 uL Pd**. Seal, move to slot 10 and run **95 C / 500 rpm / 4 h**, using the validated thermal-lag procedure. |
| 4. While reacting | At the App pause, predose **20 uL SM/IS/DCM into ten second-round wells** using `round2_predose.csv`. Remove that array to the approved ventilated ambient-evaporation location; resume promptly. Run the **14 calibration injections** in parallel. Cap/remove volatile sources at the permitted pauses; remove covers before any aspiration. |
| 5. Cool | At the end of four hours, follow the manual-move prompt and thermal-handling SOP. Move the sealed block off the heater to slot 3. Cool before opening. |
| 6. Work up | Load LC plate in slot 6 and run `round1/workup.py`. Add **50 uL workup solvent, without additional IS**, then shake the reaction block **2 min without heating** using the released method. Return to slot 3. |
| 7. Dilute and analyze | Verify homogeneous extract. Robot adds **180 uL LC diluent**, then **20 uL extract** to the mapped LC wells with fresh sample tips. Seal and mix LC plate **2 min** on the approved shaker. Run all **66 samples** using `lc_sequence.csv`. |
| 8. Trigger next batch | Export the complete integrated peak list and publish its completion marker through the configured local hook. Wait for QC to pass and for `next_design.csv` / `next_dosing.csv` (**ten new pairs**). Follow the configured round-two export to obtain the released local protocols and deck-load CSV. If QC or export stops, resolve it before dosing. |
| 9. Second reaction | Check the ten predosed wells and orientation; **verify DCM is gone**. Load stage quantities from the new deck CSV. Run the released second-round dosing protocol: add the selected ligands, toluene and Pd as in step 3; **do not redose SM/IS or perform a second heater dry-down**. Seal and react at **95 C / 500 rpm / 4 h**. |
| 10. Finish | Cool sealed, then repeat steps 6-7 with the second-round workup protocol for **ten samples**. Stop the clock when all ten analyses are complete. Save calibrated results, QC, stock/refill records and Opentrons JSON logs. |

## Pause and correct before resuming

- A tip hits the bottom, touches recipient liquid during dispensing, aspirates air, drips unexpectedly, or shows bubbles/solids: pause; correct the cause. Do not force repeated aspirations through an insoluble stock. Starting heights (1 mm above bottom; dispense 2 mm above top) require actual clearance and immersion validation.
- Reuse a dosing tip only for its same stock with validated noncontact dispensing. Sample tips stay fresh between wells/columns. Replace racks when prompted; recap stocks at permitted pauses.
- If the extract is visibly two-phase or contains solids, stop sampling and use the approved extraction method. Keep the reaction sealed through heating/cooling; open only under HTE's thermal-handling SOP.

**Per reaction:** 5 umol SM, 50 uL final toluene solution, 0.1 M; 6 mol% each ligand, 12 mol% Pd; no base or external fluoride. **Timing:** 2 min per LC sample; 76 reaction samples total. The provisional 729-min plan must be shortened and measured before release against the 720-min limit.

Detailed procedures and unresolved settings remain in the [reference handbook](HTE-operator-handbook.pdf) and [HTE configuration checklist](hte-questions.md).
