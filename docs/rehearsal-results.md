# Validation and rehearsal evidence

Current record: [software_validation.json](../software_validation.json). **230 tests pass**; no physical robot experiment, real calibration or 95 °C pair measurement has been performed. The canonical configuration retains all physical release flags as false.

## Current campaign audit - schema 5

| Part | Software-checked behavior |
|---|---|
| Initial design | Frozen real 48 pairs regenerate byte for byte; all 30 active ligands covered. L07 excluded. Paid scores/vectors unchanged. |
| Stock preparation | Actual weighed-charge/assay CSV → robot solvent addition, mixing and working-tube filling. Nominal solvent-addition concentrations are explicit; no volumetric-mark reading. Missing/duplicate charges, inadequate stock, excessive Pd/RockPhos and changed manifests are rejected. |
| Bulk handling | 36 bulk positions in labeled carriers, plus direct RockPhos tube. Six 15 mL positions per carrier; temporary slots 3/6. Solvent-compatible containers and geometry remain a local check. Supplied horizontal A1-H1 raw reservoir is single-channel only. |
| Pipettes | Preparation: p300 single left, p1000 single right. One App-guided right-pipette change to p300 multi; tips 8/9 also change. Reaction vials remain single-channel at 13 mm pitch; LC dilution uses eight channels at 9 mm pitch. |
| Chemistry | Nominal 250 µL, 25 µmol SM, 6+6 mol% ligands, 12 mol% Pd, 95 °C/4 h. SM/IS 1 M/100 mM in retained toluene; 25 µL once. Ligands 20 mM/75 µL each; Pd 40 mM/75 µL. No evaporation. |
| Scarce stocks | One 90 mg Pd charge, 10 mg solid reserved. R1 4 A3/B3: 1.91 mL each; R2 original A3 is robot-topped-up. 98% Pd assay remains covered; 95% fails. RockPhos nominal 800 µL in original 1 C1 throughout; 10 mg available, max four R2 wells. |
| SM and predosing | Robot loads 1.88 mL combined SM/IS into 4 D2 from nominal 2 mL bulk. R1 Python FIRST predoses 23 new R2 vials; staff cap/store and replace with 48 empty R1 vials. No manual aliquots or later SM/IS redose. |
| Parallel preparation | Reaction stays sealed on heater-shaker 10. Robot prepares 14 calibration wells and workup fluids during R1, fresh workup fluids during R2. Hardware subtracts elapsed preparation/pauses from the remaining hold; simulator does not model real pumping wall time. |
| Calibration | Independently weighed FIT/CHECK masters; robot 0.5/5 mM FIT dilutions and 2 mM IS. Fourteen 1 mL wells: blank +10/50/150/350/800 µM per analyte, independent 666.7 µM check, constant 66.7 µM IS. All nonzero standard aliquots ≥20 µL. Pipette-mixed; direct transfer to LC during R1. |
| Workup/LC | Robot-made 500 µL quench; manual recap, heater OFF 1500 rpm/2 min; 20 µL extract +980 µL diluent. Fresh sample tips, same-sample prewetting and bottom clearance. One final LC plate per round, uncovered 1000 rpm/2 min, seal afterward. H3 padding never injected. Three LC plates total including calibration. |
| R2 | All 48 valid R1 results → Claude-only ranking of 387 untested pairs →22 new pairs +L17 reference. Robot refill uses original reserves and calculated residuals, with matching completed R1 history; no new weighing. Reference: 150 µL L17. |
| Data integrity | Explicit injection maps, exact coverage, stable hashes and accepted quantitative QC before scoring. Partial/duplicate/overlapping exports, ambiguous/missing peaks and invalid calibration stop feedback. Original files, effective settings, records and protocols are preserved. |
| Timing | Stock preparation counts inside the campaign. Twelve hours is advisory: eight hours holds leave about four hours for remaining tasks including LC. Generic allowances are unmeasured; no completion-time guarantee. |

## Opentrons and analytical checks

All **six current stages** execute in the installed **Opentrons 8.8.2 simulator**: initial stock preparation, R1 dosing/reaction, R1 workup, R2 refill, R2 dosing/reaction, R2 workup. Additional regressions exercise actual SDK temperature/cooling behavior, new-vial uncapping, source/plate geometry, tip replacement, fresh-tip/p20 alternatives, source recirculation and both-round volume accounting. Calculated workup pumping/waits plus shaking total about **33.5 min**, excluding motion, caps, cooling and other staff handling; this is not elapsed campaign time.

The full offline loop uses the frozen first batch, **650 mocked Claude requests** and synthetic yields. Both prompt stages contain the **17 available single-ligand SI yields**, five scores per pair, at most eight partners per anchor. It accepts 48 synthetic LC results, produces 22 new pairs +reference, and passes the final 23-sample analysis. It rejects incomplete/repeated events and verifies no repeated pairs or SM/IS redosing. **Zero paid API calls.** The mock next batch is practice, not a recommendation.

Analytical practice replays 14 calibration injections and seven known-mixture samples through the real CSV importer/calibration/QC functions. Nine challenge scenarios behave as expected. Fourteen visual mock LC trials accept six valid cases, reject six detectable faults and expose two hidden area biases using known-mixture truth. Hidden coelution/area loss can pass ordinary unknown-sample QC; area-only CSVs cannot prove peak purity. Shapes, RTs and detector responses are synthetic, not a validated 1.7-minute separation. [Practice/replay commands](htel-lc-import.md).

An optional real seven-mixture pilot can also be robot-prepared: enable `automation.prepare_optional_pilot` **before** generating preparation/R1 files. Independent CHECK dilutions fill A3-G3 of the calibration plate; acquire a separate mapped sequence. Default campaign leaves it off. Actual calibration/separation/LOQs still require authentic standards.

## Real initial Claude run

Saved [campaign evidence](../campaigns/hackathon2026/) contains **435 pairs ×five repeats**, 340 accepted small requests, strict IDs/scores and thinking disabled. Accepted estimated usage: **$2.7599745**; 311 requests reported cache hits and 1,578,979 cache-read tokens. The consensus covers all 30 ligands with zero lower-quartile floor overrides. Source hashes, responses, repeated scores, mean/SD ranking and selection are retained. The archived prompt described glovebox-prepared stocks; schema 5 prepares stocks under air on the robot after glovebox weighing. Reaction atmosphere remains air; the frozen selection is retained. Prior rejected formats/smoke tests remain separately accounted for; all known estimated usage is $3.387529. No real R2 scoring has occurred.

## Physical release and return

Confirm stock-container compatibility, exact source geometry, p1000 generation/change, mounting/offsets/cap clearance, solvent delivery, vial heating/cooling and splash-free plate shaking locally. Validate the actual 1.7-minute method, UV channel, RTs, LOQs and calibration with standards. Simulation establishes code execution, not physical performance or extraction recovery. Separate solubility/homogeneity studies are outside scope; pauses address visible faults.

The private return command preserves source, all local/run data and hashes, excludes credentials, refuses overwrites/changing files and works without Git. Copy external robot JSON, LC/MS/method/sequence files and deviations into `local_data/` first. Actual weights and preparation/refill ledgers are retained with every campaign. Presence of instrument files is not a completeness check. [Return instructions](development.md#return-the-campaign-to-miquel).
