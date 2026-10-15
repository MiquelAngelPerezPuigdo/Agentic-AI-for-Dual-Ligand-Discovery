# HTE operator reference

The [staff sheet](HTE-staff-checklist.pdf) is the action sequence. This reference explains the quantities, release steps and analytical handling. Use generated CSVs from the same export as the Python protocol; they are the authority for well identities and source loads.

## Fixed experiment and comparison

Substrate: **pyridine-2-sulfonyl fluoride / PyFluor**, `FS(C1=NC=CC=C1)(=O)=O`. Product: **2-fluoropyridine**, `FC1=NC=CC=C1`. Each 250 µL reaction contains 25 µmol substrate in toluene, each ligand 1.5 µmol, Pd(COD)(DQ) 3 µmol and mesitylene 2.5 µmol. Hold at 95 °C for four hours under air, 500 rpm. No added base or external fluoride. Prepare ligand stocks in the glovebox and preserve capped reserves.

Round one is 48 distinct pairs covering all 30 available ligands. Round two is 22 untested pairs plus L17 tBuBrettPhos at **12 mol% total ligand**, otherwise identical. This gives a minimal measured single-ligand reference; without repeats or both corresponding single ligands, a higher pair yield supports improved performance relative to that reference, not a statistical or mechanistic proof of synergy.

## Labware, pipettes and manual caps

Use the supplied 48 × 2 mL JSON and derived heater-stack definition in `hte_inputs/labware/`. Wells have **13 mm pitch**, so reaction transfers use p300 single GEN2 on the left. The p300 multi GEN2 on the right doses the standard 96-well LC preparation plate, not the reaction block. Standard footprint does not establish multichannel compatibility.

All vial pipetting happens in slot 3, away from the heater-shaker. Slot 10 has the universal flat adapter; slots 7 and 11 remain empty. The derived JSON preserves all supplied well coordinates and adds a zero-overlap flat stacking declaration and **45 mm capped travel envelope**. Local setup must establish secure mounting/latch closure and cap height within this envelope. The JSON/simulator cannot establish physical fit or temperature transfer. [Opentrons adapters](https://docs.opentrons.com/heater-shaker/adapters/).

The OT-2 has no gripper. Every block move, cap opening/closing and tip-rack replacement is a local pause. Caps must be removed before aspiration and hand-tightened before reaction or high-speed workup shaking. During sampling, other vials stay capped; only the indicated batch is opened. No stir bars are used. Inspect actual source tubes and vial bottoms when setting offsets; defaults are **1.5 mm above bottom**, not bottom contact or assumed liquid-level tracking.

## Dosing and overlapped preparation

Dose 50 µL of 500 mM SM in DCM. The protocol moves the block OFF_DECK at a pause for the facility's approved ventilated evaporation. Confirm dry SM before adding mesitylene or catalysts; residual DCM would alter the reaction solvent/volume. Return the cooled block to slot 3. Add 25 µL 100 mM mesitylene, 37.5 µL each 40 mM ligand, 75 µL 40 mM Pd, and 75 µL toluene: **250 µL total**. For L17 single reference, replace both ligand portions with 75 µL L17.

During the first four-hour hold, staff prepare/inject the 14 calibration samples and manually predose the 23 second-round vials with **SM only** in an ordinary off-deck rack. Evaporate, label and cap dry SM. Keep these separate from the active block. After first-round sampling, archive its 48 vials and reuse the one block with the 23 fresh predosed vials. Mesitylene is dosed once after dry-down in each round. Neither workup nor LC diluent contains additional IS.

Common stocks use the 12-channel Axygen reservoir; ligand stocks use ordinary plastic source racks in slots 1 and 4. Prepare bulk glass stocks separately and load only `deck_loads.csv` quantities. The stock table includes 50% working margin, dead volumes and conservative reserve for any second-round choice. Refill fresh stage sources; never pour recovered working liquid into bulk reserves.

## Quench, mixing and representative sampling

Cool the sealed reaction block off the heater before opening. Add **500 µL 9:1 ACN/water +0.15% v/v formic acid**, giving nominal **750 µL extract, 0.1% acid** and 1.25 mL nominal headspace. Hand-recap every vial, then shake **1500 rpm for two minutes**, heater off, and return to slot 3. Ensure the module/block has cooled sufficiently for the intended workup temperature. High rpm mixes the liquid but does not establish chemical quench completeness or single-phase extraction.

The ACN-rich mixture is chosen to reduce the phase-separation concern from adding equal water/ACN to toluene. Separate formal recovery/homogeneity studies are waived by the user. Inspect visible appearance; persistent separate layers, solids at the aspiration path or bubbles require a pause, not selecting whichever layer is convenient. Do not filter/centrifuge/decant without documenting and assessing analyte/IS recovery. [Toluene/ACN/water phase-equilibrium evidence](https://iris.uniroma1.it/handle/11573/457505).

Sample in batches of eight to overlap LC with preparation. Before each batch, gently invert/remix the indicated **capped** vials, let obvious bubbles settle and remove only those caps. Fresh robot sample tips perform two slow same-well prewet cycles before the measured aspiration, with no air blowout into the sample. Then aspirate 21 µL at 1.5 mm, retain 1 µL reverse-pipetting surplus, add a 2 µL air gap, dispense the nominal **20 µL sample** noncontact into **980 µL diluent**, and discard the tip. The source is never revisited after LC contact.

At the robot pause, recap the sampled reaction vials. Keep the preparation plate seated in slot 6. With **one fresh manual tip per completed LC sample**, mix 500 µL five times without drawing air, transfer 900 µL into its labelled HPLC screw-cap vial, cap and invert briefly. Keep maps explicit: reaction A1-F8 is different from LC A1-H6. Submit each completed batch before resuming the robot. Round two has 8/8/7 samples; H3 gets only diluent and is excluded from LC injections.

## Solvent delivery and failed transfers

Condition fresh dosing tips twice with their own source; work from capped reserves and uncover active sources immediately before use. Slow aspiration, short settling delays, a small air gap and reverse surplus are starting settings for volatile organic solutions. Avoid immersing tips too deeply or touching walls/bottoms. A source must stay above the aspiration point after dead-volume allowance. Do not aspirate a suspension as though it were a known stock concentration; repeated aspiration can add bubbles without dissolving solids.

Tip reuse is restricted to consecutive deliveries of the **same source stock**, with destination dispensing above the top and no contact, mixing or destination aspiration. Different ligands and every analytical sample require fresh tips. If source/destination contact, dripping or unintended air occurs, pause, change the tip and record the affected sample. Refill according to source maps rather than guessing a top-up. For an uncertain analytical dilution, prepare a new dilution from freshly remixed original extract and record its mapping; do not rescue it by estimated liquid addition. Keep one accepted measurement per sample, with rejected measurements retained and a reason. Do not choose the larger yield from repeats.

## Local processing and records

The [start page](start-here.md) gives initial release, LC helper and second-round export commands; [LC import](htel-lc-import.md) covers detector/method and calibration configuration. Robots remain islands: no API key or optimizer installation goes on the OT-2, and no script remotely starts it.

Archive source exports/maps, stock preparation/assay records, actual method and wavelength, calibration/checks, ready markers, all QC results, paid scoring responses/cache ledger, final CSVs, matching generated protocols and robot JSON logs. Keep experimental data private until the team authorizes publication. The handoff does not contain a Claude key.
