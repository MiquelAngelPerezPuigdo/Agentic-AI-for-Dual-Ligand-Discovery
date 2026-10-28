# OT-2 deck and solvent loading

These are the **default campaign** positions. Use the `bulk_carriers.csv`, `deck_loads.csv` and `raw_reagents_to_load.csv` generated with the current protocol if settings have changed. The optional analytical pilot is off in this plan. Confirm the actual reservoir model, capacities, solvent compatibility and liquid recovery before running.

[View the reaction-stage deck picture](figures/ot2-deck-setup.png) · [Weighed chemicals and reservoir channels](weighing-list.md) · [Return to the experimental procedure](HTE-START-HERE.md).

## Initial stock preparation

- **Slot 1 and slot 4:** 2 mL working-tube racks. RockPhos is at **1 C1**, naphthalene at **1 C2**; four Pd charges are at **4 A3/B3/C3/A4**. Leave the other working tubes empty unless the loading file says otherwise; the robot fills them. Leave **4 D3** empty for the robot-prepared acid stock.
- **Slots 3 and 6:** the six labeled 12-channel Axygen stock reservoirs are presented in batches when requested. The [weighing map](weighing-list.md) identifies the carrier and channel for each solid.
- **Slot 2:** the supplied **eight-channel, 30 mL horizontal raw-solvent reservoir**. Pour at least the amounts below, keeping each channel below 29 mL. These are coarse loads, not precision transfers. The robot uses the **single-channel** pipette in this reservoir.
- **Slot 5:** 300 µL tips. **Slots 8 and 9:** 1000 µL tips. Left pipette: p300 single; right: p1000 single. Keep slots 7 and 11 empty.

| Phase | Slot | Channel | Liquid | Minimum (mL) |
|---|---:|---|---|---:|
| Stocks | 2 | A1 | Toluene | 27.5 |
| Stocks | 2 | B1 | Toluene | 27.5 |
| Stocks | 2 | C1 | Toluene | 27.5 |
| Stocks | 2 | D1 | Toluene | 27.5 |
| Stocks | 2 | E1 | Water | 27.5 |
| Stocks | 2 | F1 | Acetonitrile | 27.5 |
| Stocks | 2 | G1 | Formic acid | 2.0 |

Leave **H1 empty** for robot preparation. The starting-material/naphthalene stock is made in **BULK-01-3 A1** and the robot transfers it to working tube **4 D2**.

## Reaction-stage deck

After stock preparation, change the right pipette to the **p300 eight-channel** and load 300 µL tips in slots 8 and 9. The left p300 single and its tips in slot 5 stay in place.

| Slot | Use |
|---:|---|
| 1 and 4 | Retained working-tube racks; ligand positions are shown in the [deck picture](figures/ot2-deck-setup.png). |
| 2 | New **empty 12-channel** workup reservoir; the robot prepares quench and diluent here during the hold. |
| 3 | Para-Dox reaction block for pipetting; during each hold, temporarily used for the raw-solvent reservoir below. |
| 6 | Calibration plate during the first hold; later a fresh LC sample plate for each round. |
| 10 | Heater-shaker: reaction block or LC plate, one at a time. |
| 5, 8, 9 | 300 µL tips. Keep 7 and 11 empty. |

## Raw solvents during each reaction hold

At the App prompt, place a freshly loaded **eight-channel, 30 mL horizontal reservoir in slot 3**. Pour at least the amounts below and leave **H1 empty** for the robot. Use a fresh load for each hold; no precise manual transfer is needed.

| Phase | Slot | Channel | Liquid | Minimum (mL) |
|---|---:|---|---|---:|
| Hold | 3 | A1 | Acetonitrile | 25.0 |
| Hold | 3 | B1 | Acetonitrile | 25.0 |
| Hold | 3 | C1 | Acetonitrile | 25.0 |
| Hold | 3 | D1 | Water | 25.0 |
| Hold | 3 | E1 | Water | 25.0 |
| Hold | 3 | F1 | Toluene | 2.0 |
| Hold | 3 | G1 | Formic acid | 2.5 |

Remove the raw reservoir and restore the reaction-stage deck when the App asks. The capped reaction block stays on the heater-shaker while these liquids and the first calibration plate are prepared.
