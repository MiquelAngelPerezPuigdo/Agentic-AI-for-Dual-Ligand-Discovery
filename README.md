# Dual-ligand screen — one 48-reaction run

**HTE staff: [follow the procedure here](run/README.md).** This is the current plan. It replaces the earlier two-round setup.

| You need | Open |
|---|---|
| Steps, reservoir loads and Python download | **[Run procedure](run/README.md)** |
| Ready-to-run OT-2 program | **[run_screen.py](run/run_screen.py)** |
| Chemicals and masses to weigh | **[Weighing sheet](run/WEIGHING.md)** |
| Vial positions and robot deck | [Stock-vial map](run/stock-map.png) · [Deck map](run/deck.png) |
| Printable instructions | [Bench sheet PDF](run/bench-sheet.pdf) |
| Calculate yields from the LC export | [Analysis instructions](run/ANALYSIS.md) |

**One stock-vial holder, one reservoir, one reaction block and one LC plate.** Each ligand is weighed once. The robot prepares and doses stocks from those same glass vials. No bulk ligand plates, refills, rack swaps or pipette changes. The 48 selected pairs cover all 30 ligands.

Each reaction is **100 µL, 0.1 M substrate, 95 °C, four hours**, with 6 mol% each ligand, 12 mol% Pd(COD)(DQ) and naphthalene internal standard. HTE prepares the two bulk workup liquids. Seven mixed standards and 48 reaction samples share one LC plate, handed to LC once at the end. Liquid reserves and headspace are included.

One OT-2 program runs locally through the Opentrons App, from stock preparation through reaction sampling. Load once and resume at the manual cap, cover and shaker-move prompts; keep the same labware and tip racks throughout. Quantification uses authentic standards and the HTEL integrated-peak CSV; it requires the actual LC settings. **No API key or paid model call is needed for this run.** Keep instrument data and credentials out of Git.

For method developers: [how the pairs were selected](research/METHOD.md), [frozen selection evidence](campaigns/hackathon2026/), and [build/test instructions](DEVELOPMENT.md). Superseded materials are preserved in [archive/](archive/README.md); they are excluded from the current bench workflow.
