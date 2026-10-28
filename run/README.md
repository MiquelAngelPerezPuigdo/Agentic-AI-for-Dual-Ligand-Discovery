# HTE: one 48-reaction run

**Use this page and these two Python files.** This plan replaces the previous two-round workflow. Each ligand is weighed **once** into a glass vial in the supplied HTEL holder. The robot adds solvent and doses directly from the same vials. No bulk ligand reservoirs, stock transfers, refills or pipette changes.

**100 µL per reaction:** 0.1 M SM in toluene, 6 mol% of each ligand, 12 mol% Pd(COD)(DQ), 10 mol% naphthalene; **95 °C, 500 rpm, four hours**. The original 48 selected pairs and all 30 ligands are retained.

[What to weigh](WEIGHING.md) · [Source-vial map](stock-map.png) · [Deck map](deck.png) · [Printable bench sheet](bench-sheet.pdf)

## 1. Load once

Have **48 empty reaction vials with screw caps**, **42 stock/working vials**, one HTEL 48-vial source holder, the Para-Dox reaction block, one Axygen 12-channel reservoir, **one 96-well LC plate**, its cover/seal, and three 300 µL tip racks. Use the supplied vial and plate definitions; confirm offsets in the local App.

| Slot | Load |
|---:|---|
| **1** | **HTEL 48 × 2 mL glass-vial stock holder.** Load the weighed chemicals and empty working vials from the [weighing sheet](WEIGHING.md). Column 8 stays empty. |
| **2** | The **one prefilled 12-channel reservoir**, using the table below. It stays here throughout. |
| **3** | Para-Dox block with 48 empty, uncapped reaction vials. |
| **5 and 8** | Two 300 µL tip racks for the **left p300 single GEN2**. |
| **6** | One empty 96-well, 2.2 mL LC plate. It stays here until final mixing/handoff. |
| **9** | One 300 µL tip rack for the **right p300 eight-channel GEN2**. |
| **10** | Heater-shaker with the universal flat adapter. |
| **4, 7 and 11** | Empty. |

![Deck loading](deck.png)

The source holder is **not** the heated reaction block. The source holder and reservoir stay on deck. Only the reaction block and, at the end, the LC plate move to the shaker.

## 2. Prepare two bulk liquids and fill the reservoir

HTE prepares these by ordinary lab preparation:

- **Quench, 40 mL:** 36 mL ACN + 3.95 mL water + **50 µL formic acid**. This is 90% ACN, 0.125% FA. Adding 400 µL to 100 µL reaction gives 0.1% FA in the extract.
- **LC diluent, 60 mL:** 30 mL ACN + 29.94 mL water + **60 µL formic acid**. Approximately 1:1 water/ACN, 0.1% FA.

| Reservoir channels | Liquid | Load **in each channel** |
|---|---|---:|
| A1, A2 | Toluene | **9 mL** |
| A3, A4, A5 | Quench above | **9 mL** |
| A6, A7, A8, A9, A10 | LC diluent above | **10 mL** |
| A11 | Neat acetonitrile | **3.5 mL** |
| A12 | Empty | — |

These are coarse loading amounts. The program leaves at least **1.5 mL per used reservoir channel**, at least **150 µL per stock vial**, and fills source vials to at most **1.6 mL**. Reaction vials contain only **500 µL after quenching**; final LC wells contain **500 µL**. Aspiration is **1.5 mm above the defined bottom**, with fresh tips for each reaction sample.

## 3. Run the first Python file

Download **[01_prepare_dose_react.py](01_prepare_dose_react.py)** using GitHub's **Download raw file**, import it into the local Opentrons App, simulate and start it with the loading above. It is self-contained; no API key or Python installation is needed on the robot.

Start with the ligand vials in A1–F5 and SM_IS A6 / Pd B6 open. Keep analytical vials C6–F7 capped until the three-hour prompt. **Keep the same tip racks between the two files:** workup continues at the next unused tip automatically.

1. The robot adds toluene to the 30 ligand vials and to the SM/IS and Pd vials, then mixes them. **No weighing or precision liquid transfers during the run.** Pause for a visibly unsuitable stock or transfer fault.
2. It doses each reaction: **20 µL combined SM/IS + 30 µL ligand A + 30 µL ligand B + 20 µL Pd**. Vials use the single-channel pipette because their pitch is 13 mm.
3. At the App pause, hand-tighten all 48 reaction caps. Cap the stock vials and cover the reservoir and LC plate in place. Move the reaction block **3 → 10** when prompted.
4. Start an **external four-hour timer** at the App's hold-start message. The robot heats/shakes at 95 °C/500 rpm. App pauses do not stop heating: stop heat/shaking manually at the endpoint if the App remains paused and record the actual time.
5. **After three hours**, the App requests removal of the reservoir/LC covers and the ten analytical-vial caps specified on screen. The robot prepares the standards in **LC wells A7–G7**. It then requests covering the plate/reservoir and recapping those sources. No labware is exchanged.
6. At four hours, heating/shaking stops. Move the sealed block **10 → 3** when prompted and let it cool. Leave the source holder, reservoir and LC plate in place.

## 4. Run workup after cooling

Import **[02_workup.py](02_workup.py)**. Use the **same reservoir with the remaining liquids** and the **same LC plate**; never replace either with an empty one.

1. Confirm cooling. Remove the reservoir/LC covers; leave the reaction vials capped while the robot adds **480 µL LC diluent** to sample wells A1–H6 using the eight-channel pipette.
2. At the pause, unscrew the 48 reaction caps. The robot adds **400 µL quench per vial**. Move the open block **3 → 10** when prompted; shake **750 rpm for two minutes, heater off**, using the locally confirmed containment setting. Return **10 → 3**.
3. After 15 seconds for bubbles to settle, the robot transfers **20 µL extract per reaction** into its LC well, slowly and with a fresh tip. Recap the reaction vials for storage.
4. Move the uncovered LC plate **6 → 10** when prompted. Shake **750 rpm for two minutes, heater off**, then seal it and hand it to LC. **This is its only trip off the robot.**

## 5. LC and finish

Use the requested **1.7-minute method**, with its actual quantitative UV channel and authentic-standard peak assignments. Separation and detector response must be established on the real instrument. The plate contains **seven mixed standards and 48 samples: 55 injections**. The standards measure SM and product together at five levels, with a blank and an independently prepared check; naphthalene is constant.

| LC well | SM **and** product, each (µM) | Use |
|---|---:|---|
| A7 | 0 | Matrix/IS blank |
| B7 | 10 | Fit |
| C7 | 50 | Fit |
| D7 | 200 | Fit |
| E7 | 500 | Fit |
| F7 | 1000 | Fit |
| G7 | 800 | Independent check, excluded from fit |

Naphthalene is **80 µM in every standard and reaction LC sample**. The reaction samples occupy **LC wells A1–H6**; their LC coordinates come from the injection map, rather than the separate 6 × 8 reaction-block layout.

Inject the standards first, then samples, using [lc-injections.csv](lc-injections.csv). Record the **actual** injection numbers and method ID; leave all unused wells uninjected. Standards and samples now run together at the end because one four-hour reaction leaves enough room to avoid an intermediate plate trip. At 1.7 minutes per injection, the analytical sequence itself is nominally **93.5 minutes**, plus any actual wash/re-equilibration overhead.

The software operator follows [ANALYSIS.md](ANALYSIS.md) to calculate calibrated yields from the HTEL CSV. **No second reaction batch and no paid Claude call.** Save the original LC/MS data, actual map, robot logs and notes with the analysis output and return them privately to Miquel.

Pause for air aspiration, a blocked tip, persistent bubbles, unexpected liquid layers, a spill or tip contact. Record the affected vial; do not silently top up or substitute a sample.
