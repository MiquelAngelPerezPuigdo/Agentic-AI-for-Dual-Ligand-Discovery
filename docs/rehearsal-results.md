# Validation and rehearsal evidence

Current machine-readable record: [software_validation.json](../software_validation.json). Software checks validate implementation and simulation; no physical robot experiment, real calibration or 95 °C pair measurement has been performed.

## Campaign review - 18 October

| Campaign point | Checked result / remaining local fact |
|---|---|
| Inventory and R1 | 30 active ligands; L07 excluded. Frozen 48-pair selection regenerates byte for byte and covers every active ligand. |
| Chemistry and stocks | 1 M SM +100 mM mesitylene/toluene, 25 µL combined dose; no evaporation. Ligands 20 mM /75 µL each; Pd 40 mM /75 µL. SM ~10% allowance, rounded to 2.0 mL; ligand 50% margin. 25 µmol SM; 250 µL final reaction; 6+6 mol% ligands and 12 mol% Pd. Doses, source fills, surplus, dead volumes and conservative R2 reserves reconcile. 2 mL working tubes stay below 1.95 mL; worst-case 22 L17 pairs +reference loads 1.910 mL. L03 has 10 mg available and at most four R2 wells; frozen-R1 reserve prepares 800 µL /7.50 mg pure equivalent. |
| Deck and pipettes | p300 single left, p300 multi right. Reaction rack stays single-channel at 13 mm pitch; LC dilution uses 9 mm pitch. Custom reservoir centering/span and aspiration depths are checked before export. Actual offsets, immersion and mounting remain local. |
| R1 dosing and heat | Empty/uncapped vial check, combined SM/IS dose in retained toluene, catalyst assembly, hand-cap pause, manual move, 95 °C/4 h hold, heater/shaker shutdown. |
| Parallel work | Calibration and 23 new combined SM/IS predoses during R1 hold; R2 physical changeover after R1 sampling can overlap R1 LC. No active block is moved during the hold. |
| Cooling and workup | Corrected the actual SDK property to `current_temperature`. Heater-off/cool-module guard now precedes quench and LC shaking. Separate pause confirms cooled vials before opening. Quench shaking shuts down in a `finally` block. |
| LC preparation | 500 µL quench; capped 1500 rpm/2 min; 20 µL extract into 980 µL diluent; fresh sample tips and source-only prewetting. One LC plate per round, uncovered 1000 rpm/2 min with heater off; seal afterward. H3 is never injected. |
| Calibration and yield | Fixed 66.7 µM mesitylene, five analyte levels, blank and independent check. Python uses measured UV response; method, RTs, separation and LOQs still require authentic-standard data on the requested 1.7-min method. |
| Export and analytical faults | Explicit injection maps, complete coverage and stable hashes; source changes, overlaps and incomplete exports stop processing. Final staff analysis now validates doses and saves stable input hashes. Failed analytical QC returns a failing command status. |
| R2 decision and dosing | All 48 valid R1 results before Claude-only ranking of 387 untested pairs. Select 22 plus L17 reference. Confirm the 23 fresh capped liquid-predosed vials are loaded and **uncapped**; no repeated changeover or SM/IS redose; L03 at most four R2 wells. |
| Final analysis and archive | All 23 samples required. Original exports/maps/dosing, effective settings and calibration are snapshotted. One private return-ZIP command preserves code, data and decision records with file hashes; staff supply instrument logs/raw files and notes. No remote robot control. |
| Timing and handoff | 12-hour target; 119.3 min cap for all handling/decision/contingency after holds and LC. No R1 split. Physical cycle/handling measurements remain outstanding; live release retains the deadline check. Two-page staff sheet and four-page reference follow the corrected pauses. |

The audit found a hardware-path API defect hidden by ordinary simulation; tests now exercise that branch using the installed Opentrons API, including a hot-module pause. [Opentrons heater-shaker API](https://docs.opentrons.com/python-api/reference/heater-shaker/) confirms `current_temperature`; deactivating the heater provides passive cooling. Module temperature alone does not establish vial temperature. No paid API calls or physical experiments were made during this review. The 18 October update adds combined-stock/source-loss, hard RockPhos cap/available-mass, worst-case 2 mL source and small independent analytical-master regressions. The real initial pair CSV remains byte-identical.

## Private return archive

The return-package checks preserve exact input bytes and every archived file hash, retain raw-file directories, work without Git, exclude credential files/symlinks, reject a Claude key pasted into an ordinary file, reject overlapping input/archive paths, refuse overwrites and stop for changing files. The staff `next` and `final` rehearsals verify original exports/maps/doses plus effective settings/calibration snapshots. A full 650-request mocked loop was also packaged and read back; no paid API call or physical experiment occurred. External instrument records must be supplied by staff; the manifest reports presence, not experimental completeness. [Return instructions](development.md#return-the-campaign-to-miquel).

## Real initial Claude campaign

The real initial run is frozen in [campaigns/hackathon2026](../campaigns/hackathon2026/). **435 pairs ×five repeats**, **340 accepted small anchor/partner requests**, all requested IDs validated, scores0-100, thinking disabled. Accepted usage estimate **$2.7599745**; 311 requests reported cache hits, 1,578,979 cache-read tokens. The 48-pair consensus covers **all30 active ligands**, with zero lower-quartile floor overrides. Exact accepted request, repeated scores, mean/SD ranking, source hashes and response IDs are saved. Initial scoring used two workers and took approximately9 min; this is not a measured feedback-loop latency.

Earlier full-size schema/array formats were rejected and never used for selection. Their costs and historical smoke tests are recorded in the audit; known combined estimated usage is$3.387529. No real second-round scoring has occurred.

## Offline practice loop

`python -m hte.cli rehearse-loop --output output/practice` verifies the real frozen T5 vectors and uses the frozen real first-batch assignments, with every Claude response and chemistry yield mocked. Current practice completed **650 mocked requests**, including340 initial requests and310 feedback requests for387 remaining pairs. Both stages contain **17 available individual SI yields**; each pair has five scores. All batches contain at most eight partners for one anchor.

The practice uses the frozen48 pairs covering30 ligands, accepts all 48 synthetic LC results, then creates **22 untested pairs +L17 reference**. The complete second-round synthetic analysis also passes. It verifies no repeated pair, no SM redose and exactly one mesitylene dose with SM, ignores incomplete exports and repeated watcher events, and makes **zero paid API calls**. The generated practice next batch is not a scientific recommendation. No GoLLuM optimizer is invoked after feedback.

## Acceptance scope

The active suite passes **203 tests**, including 12 analytical-practice checks and five visual mock-LC checks. Two obsolete GP/MOCCA adapter tests were removed during the earlier cleanup; all campaign checks remain. Four tests specific to the removed vendor-concentration comparison were retired with that optional feature; yield/import/QC tests remain. The initial design regenerates byte for byte from saved scores/vectors; robot/stock outputs are generated locally.

Tests cover stoichiometry/reserves/deck loads, supplied geometry and cap envelope, reaction-to-LC maps, acid/dilution arithmetic, ligand coverage, strict scoring, caching/budget stops and interrupted requests. HTEL peak-export batches with reset injection numbers require explicit maps and full coverage; partial/overlapping/duplicate exports are rejected. Calibration and quantitative QC are enforced.

Actual Opentrons8.8.2 simulations execute both rounds with custom labware, manual moves/cap pauses and tip replacement. Nine added checks cover automated final LC plates: both rounds in campaign whole-plate and generic synthetic multi-plate modes, complete sample/diluent volumes, fresh sample tips, no retained tips across handoffs, uncovered 2-min shaking, heater-off/cooling guard, plate/well IDs and exclusion of H3 padding. No manual LC dilution, mixing or sample-vial transfer remains. The new adapter definition preserves supplied well coordinates; physical fit is still unconfirmed. Unused historical GP/MOCCA adapters and checked-in generated runs have been removed. Active simulations and the offline scoring/LC rehearsal remain tested.

## Visual mock LC trials

`python scripts/mock-hplc-trials.py --output output/mock-hplc` generates an interactive offline report with 14 illustrative chromatograms and HTEL-format integrated exports. The real calibration/import/strict reaction-QC path accepts six valid cases and blocks six detectable faults. Two hidden biases pass unknown-sample QC: a true 50% mixture reports 59.3% with added coelution area and 40.2% with omitted product area (seed1707). The separate known-mixture audit fails both. All 14 responses match expectations declared before replay; no API calls or optimizer feedback occur.

The original example contributes format only, with source hash recorded when supplied. Peak shapes, response factors and 1.7-minute RTs are invented. Component trace areas are numerically checked, but exported integration decisions are imposed explicitly. This does not exercise upstream peak integration or validate the physical method. [Commands and scope](htel-lc-import.md#visual-mock-chromatograms).

## Practical limits

The full rehearsal now includes `practice-analytics`: mock HTEL peak tables, 14 calibration injections with reviewed blank absences, seven known-mixture pilot injections and nine perturbation scenarios. It verifies clean data/extra peaks/IS-corrected injection scaling, rejects shifted/ambiguous/missing/incomplete peaks, and catches the tested hidden area biases using the known concentration key. Those biases can still pass ordinary unknown-sample QC. `verify-pilot` replays actual HTEL files without LLM calls; no actual campaign pilot files have been acquired or validated.

Simulation does not establish physical fit, liquid temperature, extraction/IS recovery or LC separation. Formal separate homogeneity/solubility studies are not requested; pauses handle visible faults.

The presentation uses a **720-min operating target**: 480 min reaction holds, 120.7 min LC, and 119.3 min for all other tasks and contingency. Calibration/R2 SM predosing overlap hold one; R2 physical vial changeover may overlap R1 LC after sampling. One LC plate per round is retained.

The separate **unmeasured allowance scenario** sums to 744.7 min; this is not a validated duration forecast. Its generic handling allowances have not been replaced by measurements. `check` exposes the target and this audit separately. Live export still checks the actual configured allowances against the deadline; changing presentation wording cannot release a protocol. No physical trial has established completion time. Record [local setup/timing facts](hte-questions.md) before release.

## Workup timing audit

R1 stays on **one LC plate**. `robot.lc_single_plate_per_round=true` rejects a smaller batch size. Generic multi-plate software regression tests remain separate from the campaign. Each export now includes `workup_timing.json`, calculated from its actual transfer operations and configured flow rates, prewet cycles, air gaps and waits. Four simulator checks compare that subtotal against the generated protocols in both rounds and fresh/reused-tip modes. This is not a physical-duration measurement.

| Across both rounds | Calculated pumping / programmed time |
|---|---:|
| 500 µL quench, 142 single-channel strokes | 9.8 min |
| 980 µL LC diluent, 36 eight-channel strokes | 3.1 min |
| 20 µL sample transfer, 71 fresh tips, two prewet cycles | 12.6 min |
| Two extract and two LC shakes | 8.0 min |
| **Calculated subtotal** | **33.5 min** |

This excludes gantry/vertical travel, 84 tip pickup/drop cycles, module ramp/latch time, all staff pauses, 284 screw-cap actions (uncap/recap for quench, then uncap/recap for sampling), eight workup block/LC moves, sealing and HPLC loading. Cooling and chemical dosing have separate schedule allowances. Even an illustrative 2 s per cap action adds 9.5 min before the other excluded tasks. The **72-min total workup allowance remains unmeasured and plausible**; do not replace it with the calculated subtotal.

Keeping all other allowances fixed, a 720-min campaign would require workup ≤47.3 min, leaving only 13.8 min beyond the calculated subtotal for the excluded motion/handling. Measure and reschedule the complete handling workflow against the 119.3-min cap; the target is not evidence of measured feasibility. Calibration and R2 combined SM/IS predosing already overlap hold one; R2 physical vial changeover may occur during R1 LC, after sampling. Selection still requires all 48 first-round results.
