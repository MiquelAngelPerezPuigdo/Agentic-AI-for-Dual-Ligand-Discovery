# Validation and rehearsal evidence

Current machine-readable record: [software_validation.json](../software_validation.json). Software checks validate implementation and simulation; no physical robot experiment, real calibration or 95 °C pair measurement has been performed.

## Real initial Claude campaign

The real initial run is frozen in [campaigns/hackathon2026](../campaigns/hackathon2026/). **435 pairs ×five repeats**, **340 accepted small anchor/partner requests**, all requested IDs validated, scores0-100, thinking disabled. Accepted usage estimate **$2.7599745**; 311 requests reported cache hits, 1,578,979 cache-read tokens. The 48-pair consensus covers **all30 active ligands**, with zero lower-quartile floor overrides. Exact accepted request, repeated scores, mean/SD ranking, source hashes and response IDs are saved. Initial scoring used two workers and took approximately9 min; this is not a measured feedback-loop latency.

Earlier full-size schema/array formats were rejected and never used for selection. Their costs and historical smoke tests are recorded in the audit; known combined estimated usage is$3.387529. No real second-round scoring has occurred.

## Offline practice loop

`python -m hte.cli rehearse-loop --output output/practice` uses real frozen T5 vectors but mocks every Claude response and every chemistry yield. Current practice completed **650 mocked requests**, including340 initial requests and310 feedback requests for387 remaining pairs. Both stages contain **17 available individual SI yields**; each pair has five scores. All batches contain at most eight partners for one anchor.

The practice selects48 pairs covering30 ligands, accepts all48 synthetic LC results, then creates **22 untested pairs +L17 reference**. The complete second-round synthetic analysis also passes. It verifies no repeated pair, no SM redose and exactly one mesitylene dose after dry-down, ignores incomplete exports and repeated watcher events, and makes **zero paid API calls**. The generated practice next batch is not a scientific recommendation. No GoLLuM optimizer is invoked after feedback.

## Acceptance scope

The active suite passes **143 tests** after removal of two obsolete GP/MOCCA adapter tests. All campaign checks remain. The initial design regenerates byte for byte from saved scores/vectors, and complete robot/stock outputs are generated locally rather than checked in.

Tests cover stoichiometry/reserves/deck loads, supplied geometry and cap envelope, reaction-to-LC maps, acid/dilution arithmetic, ligand coverage, strict scoring, caching/budget stops and interrupted requests. Chromeleon batches with reset injection numbers require explicit maps and full coverage; partial/overlapping/duplicate exports are rejected. Calibration and quantitative QC are enforced.

Actual Opentrons8.8.2 simulations execute both rounds with custom labware, manual moves/cap pauses and tip replacement. Unused historical GP/MOCCA adapters and checked-in generated runs have been removed. Active simulations and the offline scoring/LC rehearsal remain tested.

## Practical limits

Simulation does not establish physical fit, liquid temperature, extraction/IS recovery or LC separation. Formal separate homogeneity/solubility studies are not requested; pauses handle visible faults.

The 1.7-min full-cycle assumption and35-min handling overlap give717.7 min (752.7 min serial). No physical trial has demonstrated12 h. Record actual timings and [remaining setup facts](hte-questions.md); generated previews retain physical-execution guards pending local release.
