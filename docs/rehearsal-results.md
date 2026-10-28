# Validation and rehearsal evidence

[software_validation.json](../software_validation.json) records the final submission review of **21 October 2026**. A fresh archived checkout installed successfully into a new Python 3.12 environment from `uv.lock`; **all 364 tests passed**. The installed CLI reproduced the exact 48-pair first batch, covering all 30 ligands, and generated guarded protocols. A private return-package roundtrip verified all 133 file hashes, including a synthetic raw-data directory. No new software defect was found and no runtime/chemistry change was needed. **Naphthalene availability at HTEL is confirmed; the planned charge remains 60 mg.**

The **22 October sharing review** found one operator handoff gap: R2 workup/map paths and the final-analysis command needed to be explicit. These are now provided; **57 relevant helper/resume/repository checks passed again**. Chemistry, selection, quantification and generated robot behavior are unchanged.

On **28 October**, all **379 tests passed**, including checks that the browser procedure's links resolve and its solvent loading table matches the robot plan. The optional technical menu completed a synthetic end-to-end rehearsal. Earlier six-stage Opentrons 8.8.2 simulations passed (**16,827 commands**) with the Axygen layout, frozen R1 design and synthetic R2. Fourteen synthetic LC challenge scenarios also passed. No API spending or hardware execution occurred. Earlier review records remain in Git history.

**No physical robot experiment, real calibration or 95 °C pair measurement has been performed.** All physical release flags remain false. The Axygen layout replaces the earlier deep-tube plan; local geometry, liquid recovery, compatibility and hardware validation remain necessary before live release.

## Campaign checks

| Part | Verified software behavior |
|---|---|
| Initial design | David's 24 retained consensus +24 Sobol selection covers all 30 active ligands. L07 is excluded. The production selector reproduces the contributor's selection; paid scores and inferred vectors remain unchanged. |
| Stock preparation | Target masses drive robot solvent addition, mixing and working-tube loading; no mass-entry CSV is required. Inadequate planned stock, excess planned Pd/RockPhos and altered manifests stop release. |
| Naphthalene | Robot prepares the planned 60 mg source in 1 C2 at 500 mM. It supplies the combined 1 M SM/100 mM IS stock and the 8 mL/2 mM analytical master. A visible-clear-stock pause precedes use. Component ledgers verify solute and solvent amounts in all 14 calibration wells and seven optional pilot wells. |
| Scarce reagents | Four direct Pd tubes target 22.8/22.8/22.8/21.6 mg, totaling 90 mg; 10 mg remains for scope. All four are retained without bulk transfer/refill. RockPhos is retained in 1 C1, with at most four R2 wells. |
| Dosing | R1 starts with 48 empty vials; R2 starts with 23 new empty vials in the same block. Each receives 25 µL combined SM/IS immediately before catalysts. The SM working source is retained; no early R2 dosing or SM refill. |
| Protocols | Simulated stages: initial preparation, R1 dosing/reaction, R1 workup, R2 refill, R2 dosing/reaction and R2 workup. Command traces verify source uncapping, pipette changes, cap/move pauses, liquid accounting and correct operation order. |
| Workup | LC wells are prefilled before quenching. Cooled reaction extracts and final LC plates mix uncovered at 750 rpm for two minutes, heater off. Reaction vials remain open through sampling, then receive one archive recap. Sealed reaction shaking remains 500 rpm. |
| Calibration | Fourteen robot-prepared standards include independent FIT/CHECK weighings and constant 66.7 µM IS. Every nonzero fit level must back-calculate within 15% (20% at the lowest level). Quantification starts at the greater of measured LOQ and the lowest nonzero calibrator. |
| Identity and data | Calibration and pilot CSVs require `internal_standard_identity=naphthalene` and `internal_standard_cas=91-20-3`. Old or unlabeled standards, ambiguous/missing peaks, partial/overlapping exports and invalid calibration are rejected before feedback. |
| R2 | All 48 accepted R1 results feed Claude-only ranking of 387 untested pairs. Python applies feasibility limits and selects 22 new pairs plus the L17 reference. Unchanged retries reuse saved scores; changed inputs or uncertain paid attempts stop. |

The [stock instructions](stocks-and-calibration.md) and [operator runbook](hte-runbook.md) contain the operating details. Regenerate local configuration, charge sheets, protocols and standards when migrating from an older schema. Mesitylene calibration measurements cannot be relabeled as naphthalene.

## Mock loop and analytical practice

The complete offline loop uses the frozen first batch, synthetic yields and **660 mocked Claude requests**. Both prompt stages contain the 17 available same-substrate single-ligand SI yields, five scores per pair and at most eight partners per request. It accepts the 48-sample first round, generates 22 new pairs plus the reference and passes the final 23-sample analysis. Incomplete/duplicate events are rejected. No pair repeats or duplicate SM/IS dosing occur. **Zero paid API calls; mock R2 choices are practice only.**

Analytical practice runs 14 calibration injections and seven known-mixture samples through the real CSV importer, calibration and QC functions. All nine challenge scenarios behave as expected. Fourteen visual mock LC trials accept six valid cases, block six detectable faults and expose two hidden area biases using known-mixture truth. Those two biases can pass ordinary unknown-sample QC: integrated-area CSVs cannot establish peak purity. Trace shapes, retention times and responses are synthetic; this does not validate the proposed 1.7-minute separation. [Practice/replay commands](htel-lc-import.md).

An optional seven-mixture pilot can be robot-prepared from independent CHECK dilutions if enabled before preparing the campaign. It is off by default. Real calibration, separation and LOQs still require authentic standards.

## Real initial scoring and frozen provenance

[Saved campaign evidence](../campaigns/hackathon2026/) contains **435 pairs ×five scores** from 340 accepted Claude requests, with strict IDs and thinking disabled. Estimated accepted usage was **$2.7599745**; 311 requests reported cache hits, totaling 1,578,979 cache-read tokens. Including earlier rejected requests and smoke tests, recorded estimated usage is **$3.387529**. No real R2 scoring has occurred.

The adopted first batch retains 26 earlier pairs and replaces 22. Three Sobol selections intentionally fall below the baseline Claude cutoff. Its SHA-256 is `3c68d4fe7429cd5b880cdbec25debd4fd6d6e794e95022c88c317c07c5d5dd27`. The selection, metadata, scores, responses, vectors and extracted SI data are retained; contributor prototypes and superseded audits remain recoverable in Git.

Historical paid prompts described mesitylene and glovebox-prepared stocks. They remain unchanged as provenance. Current prompts use naphthalene and preparation under air after glovebox weighing. No paid rescoring or new embedding inference was performed for that change. See [ML strategy](ml-strategy.md).

## Remaining local validation and data return

- **Stock geometry:** the supplied Axygen definition passes the conservative simulated tip-reach calculation. Verify the physical reservoir matches that definition, and measure recoverable volume: the default 500 µL bulk residual is an assumption. Confirm toluene exposure and cover effectiveness. Pd, RockPhos and the naphthalene source are prepared directly in retained 2 mL tubes; SM/IS is prepared in an Axygen channel.
- **Robot performance:** confirm mounting, offsets, pipette generation/change, cap clearance, solvent delivery, heating/cooling and uncovered shaking locally. SDK execution does not demonstrate dissolution, homogeneous sampling, splash containment or extraction recovery.
- **LC:** establish the actual method/channel, RTs, LOQs and naphthalene calibration with authentic standards. Quantification is local Python from integrated UV areas; the optimizer does not calculate experimental yields.
- **Timing:** preparation counts inside the campaign. Initial pumping/waits alone take approximately 93 programmed minutes, excluding motion and staff handling. A 12-hour completion has not been demonstrated. Calibration runs during R1; an external operator timer is still needed during blocking App pauses.

The [private return command](development.md#return-the-campaign-to-miquel) preserves source, local/run data, preparation ledgers, decisions and SHA-256 hashes. It excludes credentials, refuses overwrites or changing files and works without Git. Copy external robot logs, LC/MS/method/sequence files and deviations into `local_data/` first; software cannot automatically capture files left on instruments.
