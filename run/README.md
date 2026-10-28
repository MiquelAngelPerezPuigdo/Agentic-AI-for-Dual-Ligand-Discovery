# Staff guide: one semi-automated 48-reaction screen

**Staff weigh and load. The OT-2 makes stocks, doses and prepares samples. Staff move the labware, handle caps, and take the final plate to HPLC-MS.** One Python program runs through the experiment with pauses for these actions.

We compare 48 ligand pairs for Pd-catalysed conversion of **pyridine-2-sulfonyl fluoride (SM)** to **2-fluoropyridine (product)** under air. Naphthalene is the internal standard. The LC calibration mixtures let us calculate product yields from the measured peak areas. Each reaction is 100 µL, 0.1 M SM, 6 mol% of each ligand and 12 mol% Pd(COD)(DQ), with 10 mol% naphthalene.

[Weighing sheet](WEIGHING.md) · [Stock-holder map](images/stock-map.png) · [Deck map](images/deck.png) · [Printable bench sheet](bench-sheet.pdf) · [Robot program](run_screen.py)

**[Open the nine-step flow diagram](images/workflow.png)** for the whole sequence, with staff and robot actions side by side. Standards and reaction samples are prepared after the heated hold, then analyzed together. The LC plate leaves the robot only at the end.

## 1. Prepare the chemicals

**You:** weigh the amounts in the [weighing sheet](WEIGHING.md) into the labelled 2 mL glass source vials. Weigh each ligand once, in the glovebox. Keep the original reagent bottles there. The OT-2 adds the stock solvents: **load weighed chemicals, with no stock solvent added yet**. The five working vials B7–F7 start empty.

Prepare these two bulk liquids manually, then fill the reservoir:

- **Quench, 40 mL:** 36 mL ACN + 3.95 mL water + 50 µL formic acid.
- **LC diluent, 60 mL:** 30 mL ACN + 29.94 mL water + 60 µL formic acid.

| Reservoir channels | Liquid | Load in **each** channel |
|---|---|---:|
| A1–A2 | Toluene | 9 mL |
| A3–A5 | Quench above | 9 mL |
| A6–A10 | LC diluent above | 10 mL |
| A11 | Neat ACN | 3.5 mL |
| A12 | Empty | — |

## 2. Load and start the OT-2

These are the three pieces you will handle. Label them and keep A1 at the back-left when returning them to the deck.

| Piece | What it contains | Home slot |
|---|---|---:|
| **Stock holder** | 42 source/working vials: 30 ligands, SM/IS, Pd and analytical sources/dilutions | **1** |
| **Reaction block** | Para-Dox block, 48 empty 2 mL reaction vials with screw caps available | **3** |
| **LC sample plate** | One empty **VWR 96 deep-well plate, 2.2 mL, V-bottom square wells**, with a cover and a seal available | **6** |

The **Axygen 12-channel reservoir, 12 mL/channel, high-profile V-bottom** goes in **2**. These are the plate/reservoir geometries embedded in the program. Load 300 µL tip racks in **5 and 8** for the **left p300 single GEN2**, and **9** for the **right p300 eight-channel GEN2**. Heater-shaker/flat adapter: **10**. Leave **4, 7 and 11 empty**. Have suitable hot-block handling tools.

Start with ligand vials A1–F5 and SM_IS A6 / Pd B6 **open**; analytical/working vials **C6, D6, E6, F6, A7, B7, C7, D7, E7, F7 capped**. Reaction vials and the LC plate start empty and open. Covers stay off the reservoir and LC plate for initial pipetting.

Download [run_screen.py](run_screen.py) using **Download raw file**, save it as a `.py` file and import it into the local Opentrons App. Complete the App's setup, simulation and labware-offset checks. In both the **stock holder and reaction block**, the highest fitted cap must be **≤45 mm above the holder/block base**. Check the programmed **1.5 mm bottom clearance**; with a representative source vial containing **150 µL toluene**, the tip opening must still be immersed at that height without touching the bottom. If either clearance/pickup check fails, correct the setup before starting. Use a separate test vial, then load the planned vials. Start this one program; keep the same tip racks and labware throughout.

**At each pause:** read the step number, perform the requested action and press **Resume**. For a labware move, wait for the separate App move prompt before lifting the named piece; the robot opens the latch first. Resume that prompt after the piece is seated in the stated destination.

## 3. The robot makes the stocks and doses the reactions

**Robot:** adds solvent to the weighed chemicals and pipette-mixes the 32 reaction stocks.

**You, at 3a:** leave those 32 vials open and the ten analytical vials capped. At the move prompts, move the **stock holder 1 → 10 → 1**. The robot shakes it **750 rpm for two minutes, heater off**. Its fit on the flat adapter has been confirmed by HTE.

**You, at 3b:** check that the holder is back in slot 1, A1 at the back-left, and inspect the stocks for transfer faults or persistent bubbles. Resume when ready.

**Robot:** doses all 48 reactions: **20 µL SM/naphthalene + 30 µL ligand A + 30 µL ligand B + 20 µL Pd = 100 µL**. Each ligand/Pd source is remixed before its first dose. Reaction stocks are finished afterward and may remain open.

## 4. Seal and start the reaction

**You, at 4a:** screw all **48 reaction caps** on securely. Cover the reservoir and LC plate in place. Keep the ten analytical vials capped. At the move prompt, move the **reaction block 3 → 10**.

**Robot:** heats to **95 °C** and shakes at **500 rpm**. **At 4b, start an external four-hour timer and resume promptly.** This is the beginning of the nominal heated hold. Return at its end; there is no three-hour intervention. For an agreed longer heated hold, remain at 4b until the agreed elapsed endpoint, then resume. Heating/shaking continue during this pause; actual duration is logged.

## 5. Move the sealed reactions to cool; prepare calibration

**Robot:** stops heating and shaking at the end of the hold.

**You, at 5:** remove the reservoir/LC covers and open the ten analytical vials listed in step 2. Keep all reaction vials sealed. At the move prompt, move the **sealed reaction block 10 → 3** using suitable thermal handling. It cools passively there.

**Robot:** makes the analytical stocks and seven mixed SM/product standards in **LC wells A7–G7**, while the reactions cool. HIGH, LOW, CHECK and IS_WORK are robot-made calibration mixtures; those labelled working vials started empty. Used source vials may remain open. **Leave the LC plate in slot 6**, ready for the reaction samples.

## 6. Open, quench and mix when cooled

**You, at 6:** decide when the **reaction block/vials and heater-shaker** have cooled sufficiently for opening and unheated workup. Keep the reaction vials sealed until then. Unscrew all 48 reaction caps and press **Resume** when ready. The program waits for your decision; there is no numerical cooldown threshold.

**Robot:** adds **400 µL quench** to each reaction; each vial now contains **500 µL extract**.

**You, at the next two move prompts:** move the **open reaction block 3 → 10 → 3**. Between those moves, the robot shakes it **750 rpm for two minutes, heater off**. It then waits **15 seconds** before sampling.

Four hours is nominal: longer heated holds and a wait before quenching are allowed. The log records actual heated duration and heater-off-to-quench intervals. Conversion may continue during cooling; include actual timing in the run notes.

## 7. Prepare the LC reaction samples

**Robot:** works through LC columns 1–6. For each column it transfers **20 µL extract per reaction into the eight empty LC wells first**, using fresh single-channel tips. It then adds **480 µL acidified LC diluent on top** with the eight-channel pipette, in two 240 µL additions, before continuing to the next column. Each sample well ends at **500 µL**; no staff action is needed for this step.

The **quench** was added to the reaction vials in step 6. The liquid added on top of each LC aliquot here is the separate **LC diluent containing 0.1% formic acid**.

## 8. Mix the final LC sample plate

**You, at 8:** recap the reaction vials for storage. Leave the **LC sample plate uncovered**. At the move prompt, move **only that plate 6 → 10**, preserving A1 orientation.

**Robot:** shakes the LC plate **750 rpm for two minutes, heater off**, then requests its removal from the robot.

## 9. Take the plate to HPLC-MS and return the results

**You:** remove the LC plate at the App prompt, seal it, label it with the run/date and mark A1. Resume to finish the OT-2 program. Carry the sealed plate flat to HPLC-MS with [lc-injections.csv](tables/lc-injections.csv). **This is the plate's only handoff to LC.**

| Final LC wells | Contents | Injection order |
|---|---|---|
| A7–G7 | Blank, five calibration levels and independent check | **First: 7 injections** |
| A1–H6 | 48 reaction samples | **Then: 48 injections** |
| All other wells | Empty | Leave uninjected |

**LC operator:** run the standards and reaction samples **together in one LC sequence**, using the provided injection list and its LC plate positions. Use the requested **1.7-minute method** and establish SM/product/naphthalene peak assignments and quantitative UV settings from the authentic standards. Naphthalene is **80 µM** in every prepared LC well; product at 100% yield is **800 µM**. The 55 injections take nominally **93.5 minutes**, plus instrument overhead.

Export the integrated-peak CSV and retain the original LC/MS files. The person handling quantification follows [ANALYSIS.md](ANALYSIS.md). Return the **LC/MS files, actual injection list/method, calculated yields/QC, robot logs and run notes** privately to Miquel.

If there is air aspiration, a blocked tip, persistent bubbles, tip contact or a spill, pause and note the affected vial before continuing.
