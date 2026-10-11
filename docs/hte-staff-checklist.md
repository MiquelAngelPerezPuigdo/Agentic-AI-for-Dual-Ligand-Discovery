# HTE staff checklist - setup

**Campaign:** ____________________ **Operator/date:** ____________________

**Draft:** 250 uL scale, 96-position mapping. A 24-vial rack needs revised protocols. Use released files after HTE confirms scale, glass geometry/seal, simultaneous heating of 60 reactions, pipetting/extraction/IS recovery and the 1.7-min LC method. Off-robot magnetic heating is requested; current files use slot 10. Release first dosing separately; calibration must pass before workup.

## Before the clock

Check **59 pairs + one L17 reference**, all 30 active ligands covered, L07 excluded. Prepare stocks/reserves from `stock_preparation.csv`; prepare ligands in the glovebox. Label IDs, assays and addresses. Use plastic stock racks; metal blocks are for reactions. Keep reserves capped. Start the local watcher; key: laptop `anthropic.key`.

| Stock | Preparation |
|---|---|
| SM + naphthalene | 1,000 mM SM + 10 mM IS in toluene; at least 5.00 mL. |
| 30 active ligands / Pd | 20 mM ligands / 40 mM Pd(COD)(DQ), in toluene. CSV gives masses/reserves. |
| Toluene | Stock solvent; no extra neat dose in the default recipe. |
| Workup / LC diluent | 1:1 water/ACN + 1% v/v HCOOH; no extra IS. |

**SM:** PyFluor (pyridine-2-sulfonyl fluoride). **Product:** 2-fluoropyridine. Combined stock at 100% assay: **805.80 mg SM + 1.00 mL of 50 mM naphthalene/toluene**, toluene to **5.00 mL** in capped **10 mL glass/PTFE vial**. Naphthalene master: **12.817 mg to 2.00 mL**; separate toluene and LC-compatible masters.

## Deck - use stage quantities from `deck_loads.csv`

**Left:** p300 single GEN2. **Right:** p300 eight-channel GEN2. Manual moves.

| Slot | Contents |
|---|---|
| 1 / 4 | Ligand racks L01-L24 excluding L07 / L25-L31; exact CSV addresses. |
| 2 | Reservoir A1 SM/IS/toluene; A2 Pd; A3 unused by default; A4/A6 workup; A5/A7 LC diluent. Fill at most 11.9 mL/channel. |
| 3 / 10 | Reaction block for dosing/cooling / heater-shaker with released mount. |
| 6 | Round-two substrate array during dosing; LC plate during workup. |
| 5 / 8 / 9 | p300 single tips / p300 multi tips / p300 multi tips. Slots 7 and 11 empty. |

## Calibration - 14 injections during round one

Authentic SM/product: **100 mM, 2.00 mL each, no IS** (SM 32.232 mg; product 19.418 mg at 100% assay). Analyte working stock: **100 uL to 1.00 mL**, 10 mM. Analytical IS: **40 uL of 50 mM to 2.00 mL**, 1 mM.

For each analyte, prepare **1.00 mL per column**, adding **50 uL of 1 mM IS to every tube**. Use the approved matrix, accounting for stock solvents.

| Analyte, uM | 0 blank | 100 | 500 | 1,000 | 2,500 | 6,000 | 5,000 check |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stock, mM | None | 10 | 10 | 10 | 100 | 100 | 100 |
| Analyte, uL | 0 | 10 | 50 | 100 | 25 | 60 | 50 |
| Matrix, uL | 950 | 940 | 900 | 850 | 925 | 890 | 900 |

Fit blank plus five levels. Keep the independent 5,000 uM check outside the fit.

---

# HTE staff checklist - run

**Block/seal:** ____________________ **LC method/channel:** ____________________

Follow App pauses and released CSV maps. Preserve orientation/sample IDs. Start the timer with first dosing; stocks/initial selection are prepared beforehand.

| Step | Staff action |
|---|---|
| 1. Dose | Import released `dose_and_react.py`. Check deck/offsets. Dose **25 uL of 1 M SM/10 mM IS in toluene into 60 wells**. Retain the solvent; proceed directly to catalyst dosing. |
| 2. React | Pair: **75 uL ligand A + 75 uL ligand B + 75 uL Pd**. Reference: **150 uL L17 + 75 uL Pd**. With the retained 25 uL SM stock, total is **250 uL**. Seal/move to slot 10; **95 C / 500 rpm / 4 h**, with validated thermal lag. |
| 3. During hold | Predose **25 uL SM/IS/toluene into ten round-two wells**. Cap promptly, label and store under the approved conditions; retain solvent. Resume promptly. Run **14 calibration injections**. Cap unused sources; uncover before aspiration. |
| 4. Cool / release | Follow the thermal-handling pause; move sealed block off heater to slot 3 and cool before opening. After calibration passes, obtain the separately released first workup protocol and deck loads. |
| 5. Work up | Load LC plate in slot 6. Run released workup: add **250 uL workup solvent, no IS**; move/shake **2 min without heating** and return as prompted. Confirm homogeneous extract; remix if delayed, clear bubbles. |
| 6. LC | Fresh sample tips prewet twice in their own well. Robot doses **180 uL diluent + 20 uL extract**. Seal/mix LC plate **2 min**, clear bubbles, check needle height/volume. Run **60 samples** in the mapped sequence. |
| 7. Decide | Normalize the complete Chromeleon export with injection-number mapping; publish completion marker. Wait for calibration/QC and **ten new pairs** in `next_dosing.csv`. Import the released second-round protocol. |
| 8. Round two | Verify retained **25 uL predoses** and mapping. Refill sources from reserves. **Do not redose SM/IS or evaporate.** Add selected catalysts, seal and run the same four-hour hold. Cool and repeat workup/LC for **ten samples**. Stop the clock after analysis; archive results/QC/logs. |

## Pause and correct

- Validate **greater than 1 mm** bottom clearance and liquid immersion; sample default is 1.5 mm. Stop for contact, unintended air, dripping, bubbles or solids.
- Reuse only validated same-stock/noncontact dosing tips. Samples use fresh tips. Never return to source after LC contact. Uncertain transfer: fresh documented dilution, no guessed top-up.
- Two phases/solids: use approved extraction before sampling. Keep sealed through heating/cooling. Retain failed results; repeat for documented QC faults, never to choose a higher yield.

**Per reaction:** 25 umol SM, 250 uL, 0.1 M; 6 mol% each ligand, 12 mol% Pd; no base/external fluoride. Requested LC: **1.7 min**, 70 reaction samples. Provisional total **686 / 720 min**; measure cycle/handling. Details: [reference handbook](HTE-operator-handbook.pdf).
