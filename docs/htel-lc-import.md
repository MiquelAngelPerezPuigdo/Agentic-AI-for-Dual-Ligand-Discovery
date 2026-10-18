# HTEL peak CSV import and algorithmic quantification

Use calibrated integrated UV peak areas for yield; MS is identity support. The old supplied CSV establishes format only. Its RTs, names and wavelength settings do not validate the requested 1.7-minute method. The supplied Thermo RAW is MS data, not raw DAD for MOCCA.

**Processing chain:** HTEL integrated-peak CSV → Python calibration and mesitylene normalization → yield/QC → Claude feedback. Our workstation needs no Chromeleon installation or concentration export. HTEL's instrument software performs acquisition/peak integration upstream; the importer retains compatibility with its supplied CSV layout. Standards remain required.

**Yield calculation is deterministic.** Python matches peaks to measured reference windows, fits analyte/IS area ratios against known standard concentrations, applies the recorded workup/dilution volumes and divides product amount by starting SM amount. Reaction stock concentrations and volumes are nominal under the declared solvent-addition approximation. The robot sets the SM:IS molar ratio from weighed SM and the neat IS dose. With nominal 750 µL extract, 50-fold LC dilution and 25 µmol SM, `yield (%) = 0.15 × product concentration in the LC well (µM)`. Invalid results fail QC; nondetections can be bounds rather than fabricated zeros. Claude receives accepted measurements and selects conditions; it does not calculate or estimate experimental yields.

## Configure once from authentic standards

In `local_data/campaign.json`, set the actual `analytics.method_id`, one quantitative `channel` (`UV_VIS_1` to `UV_VIS_4`), `references` and `quantification_limit_uM`. References require `substrate`, `product`, `internal_standard`, each with measured `retention_time_min` and `window_min`; windows must not overlap. Record actual detector wavelength and injection volume alongside the method. We request 210 nm initially; the example's channels at 253/270/300/370 nm are historical settings. Do not sum wavelengths or substitute TIC for UV area.

The 14-sample plan is `hte_inputs/calibration_template.csv`: each analyte blank +10/50/150/350/800 µM and independent 666.667 µM check, IS66.667 µM throughout. [Preparation recipes](stocks-and-calibration.md). The robot prepares/pipette-mixes these in the first hold; staff seal/move the plate directly to LC. Use the generated calibration_injection_map.csv. Initial dosing release can precede calibration. Workup release requires completed calibration.

## One explicit mapping per acquisition sequence

HTEL's wide peak export lacks method ID and may repeat names. Copy each generated `lc_batchNN_injections.csv`, fill actual `method_id` and optionally actual `vial_position`, `injection_name`, `type`. The generated map includes expected `lc_plate_id` and `well`; these identify the physical plate to load. Map `inj_no` to the canonical sample ID. Do not assume numbering continues across batches. Maps must describe actual accepted injections, not just intended order; archive replacements/rejections and keep one accepted measurement per sample.

```csv
inj_no,sample_id,method_id
1,R1-001,ACTUAL_METHOD_ID
2,R1-002,ACTUAL_METHOD_ID
```

Blank mapping fields are optional identity cross-checks; supplied nonempty fields must match the source. Calibration has its own 14-row mapping using the calibration-plan sample IDs. Reaction maps, final LC plate IDs and well coordinates come from the matching generated sequence; the 48-well reaction coordinates differ from the 96-well preparation plate.

## Calibration command sequence

Normalize the completed standard export, then extract analyte/IS areas and publish the validated calibration:

```bash
python -m hte.cli --config local_data/campaign.json normalize \
  local_data/calibration-vendor.csv \
  --injections local_data/calibration-map.csv \
  --output output/calibration-peaks.csv
python -m hte.cli --config local_data/campaign.json \
  calibration-from-peaks --peaks output/calibration-peaks.csv \
  --plan local_data/calibration-plan.csv \
  --output local_data/calibration.csv
```

Fit blank plus five levels; exclude independent checks. Wrong method/channel, ambiguous/missing peaks, poor fit or failed checks stop publication. For a truly absent calibration-blank analyte omitted from the export, add `--reviewed-absences local_data/calibration-absences.csv` to `calibration-from-peaks`. Fields: `sample_id,analyte,method_id,reviewed_by,note`. Enter actual review details after inspecting the blank; `practice-analytics` supplies an empty template. Only planned zero-analyte blanks qualify; reviews conflicting with measured peaks are rejected. A reviewed zero area is recorded without inventing a chromatogram peak or RT.

Configure measured LOQs. For reaction nondetections, `missing_analyte_policy="censor"` uses those LOQs to give upper bounds; default is rejection. Pilot/calibration absence reviews do not change this reaction policy.

## Practice, then replay actual known mixtures

```bash
python -m hte.cli practice-analytics --output output/analytics-practice
```

No key or paid calls. Outputs:

- `pilot_preparation.csv`: seven robot-prepared 1 mL samples using independent CHECK-master dilutions (0.5/5 mM analyte), 2 mM analytical mesitylene and matched matrix. Enable `automation.prepare_optional_pilot=true` BEFORE generating stock preparation and R1 protocols; the robot fills A3-G3 on the calibration plate. Keep its acquisition/export map separate from the 14 calibration injections.
- `pilot_plan.csv`: expected concentrations. Mixtures contain SM +product =666.667 µM; mesitylene stays at 66.667 µM. Sequence: 0/10/50/90/100% product, analyte-free IS blank immediately after the high-product sample, then an independently prepared 50/50 repeat.
- `pilot_injection_map.csv`, `calibration_injection_map.csv`, `absence_review_template.csv`: fill actual method/sequence and reviewer details locally.
- `practice_report.json`, labelled `synthetic/`: mock vendor exports → 14-injection calibration → pilot replay, plus nine challenges. Synthetic reviews, methods and RTs are never real setup evidence.

Run real pilot samples with the intended method, injection volume, wavelength and HTEL processing/export settings. Prefer a pre-hackathon run, or schedule during hold one if LC access permits. Seven extra injections take nominally 11.9 min at a verified 1.7-min cycle. They are separate from the 14 calibration injections and 71 reaction samples; the reaction counts remain unchanged and the optional seven injections are included in the timing ledger during hold one.

After acquiring actual files, record reviewed zero-analyte absences and run:

```bash
python -m hte.cli --config local_data/campaign.json verify-pilot \
  --exports local_data/pilot-vendor.csv \
  --injections local_data/pilot-map.csv \
  --calibration local_data/calibration.csv \
  --plan output/analytics-practice/pilot_plan.csv \
  --reviewed-absences local_data/pilot-absences.csv \
  --output output/real-pilot
```

Keep the concentration key out of integration/assignment; compare after processing. Replay requires exact sample coverage, valid calibration and each quantifiable analyte within **15% relative error** of its known concentration. Expected zeros require a named absence review and no detected peak in their window; they remain bounds. Failures return a nonzero command exit and write `pilot_report.json`/`comparisons.csv`. Replay never selects reactions, changes release flags or calls Claude. `PILOT-` IDs cannot substitute for real reaction results.

Optionally append post-workup Pd/ligand matrix-spike samples with `PILOT-` IDs and independently known final concentrations, accounting for background. These test interference in the chosen matrices, without establishing every ligand's recovery or quench completeness.

Have HTEL review actual pilot chromatograms for separation, identity, integration and detector clipping, using available DAD/MS support. Area-only CSVs cannot prove peak purity. The offline challenge shows merged interference/area loss passing unknown-sample QC while known pilot concentrations expose the tested biases. Freeze successful settings and retain real exports/maps/plan/reviews as a local regression set. Formal extraction-homogeneity studies remain outside scope.

### Visual mock chromatograms

```bash
python -m pip install -e '.[reports]'
python scripts/mock-hplc-trials.py --output output/mock-hplc
```

Open `output/mock-hplc/mock-hplc-report.html` locally. The offline report lets you select 14 cases and inspect illustrative traces, exported peaks and pipeline responses. `trial-results.png`, `trial_summary.csv` and per-trial exports/maps/results accompany it. Optionally pass `--example /path/to/Chromatogram.csv` to verify the supplied HTEL schema and record its hash. Use a fresh output directory each time; `--seed` fixes simulated noise, and `--no-report` skips plotting dependencies.

Six valid cases test low/high yield, small RT drift, shared injection-area loss and a resolved impurity. Six faults test RT assignment, ambiguous peaks, missing/outlier IS, incomplete export and missing selected UV area. The remaining two deliberately show hidden coelution and product-area loss passing ordinary QC but failing a known-mixture check. Truth stays separate from the concentration calculation; rejected numeric values are removed from usable feedback. No optimizer is called.

The original file contains integrated areas, not raw traces. Peak widths, 1.7-minute RTs, detector responses and noise here are invented. Trace component areas are numerically checked, but integrated export decisions are imposed explicitly: this tests the importer/calibration/QC workflow, not upstream peak integration or a real 1.7-minute separation. No API key or robot connection is used; campaign settings and the frozen first batch are unchanged.

### Assumed column and gradient scenarios

With `.[reports]` installed, run `python scripts/simulate-lc-separation.py --output output/lc-separation`, then open `separation-report.html`. It explores SM, product, toluene and mesitylene on an **assumed** 50 ×2.1 mm C18 column, 1.9 µm, 40 °C and 0.6 mL/min, using three 1.7-minute water/ACN gradient programs with 0.1% formic acid. Compare equal-area and concentration-weighted traces, change the assumed tail fraction, and inspect deliberately compressed-selectivity cases.

This is an uncalibrated linear-solvent-strength migration model. The starting retention coefficients use an explicitly invented relationship to RDKit cLogP; they are not a manufacturer's prediction or measured data. A 512-draw sensitivity sweep varies those coefficients and slopes; draw counts are not real coelution probabilities. Isocratic analytic-reference and numerical-convergence checks verify the solver only. Ionization, matrix peaks, detector saturation and full wash/re-equilibration throughput are outside the model. Gaussian-width resolution does not establish quantitative purity beside a large tailed solvent peak.

The configured dilution gives about 0.667% v/v toluene (63 mM using assumed density 0.867 g/mL), versus 66.7 µM mesitylene. Relative UV responses are unknown; the weighted display assumes equal molar response. Reports, parameter tables and illustrative traces stay in the requested output folder. This script does not change the campaign method/configuration, create robot instructions or publish optimizer observations.

## Reaction results and final 22

After all 48 injections, run `scripts/hte-lc-results.py next` as shown on the [start page](start-here.md), giving one plate export and its map per round. It normalizes each sequence separately, rejects duplicate files/samples, combines them, and publishes a completion marker only for full expected sample coverage. Calibration/QC must then pass before any paid Claude call. The result is 22 new pairs plus one L17 reference, with local release status printed. Use `final` after the 23 final samples; it analyzes without Claude.

After interruption, **repeat the exact helper command with the same output directory**. It verifies source and archive hashes, reuses completed ingestion/accepted scores, and retains uncertain-request blocks and the cost ledger. Do not choose a fresh folder merely to retry: that can create a new paid campaign. Changed inputs intentionally require a new decision directory; inspect uncertain API attempts before any recovery. Older helper outputs without `helper_inputs.json` need inspection or direct `iterate` recovery.

Alternatively use separate `normalize`, `complete-export`, `analyze`/`iterate` commands or the local watcher. Use one workflow per campaign and preserve its state. Retain hashes, original exports and map versions. Populate exported injection names/positions in the mapping when available: software coverage checks cannot prove that the physical autosampler order matches an incorrectly authored map.

Calibration QC checks R², independent checks and each nonzero fitted level's back-calculated recovery (15%; 20% for the lowest level). A high R² alone can conceal poor low-level accuracy. The quantitative lower bound is `max(measured LOQ, lowest nonzero calibrator)`; blanks remain in the fit but do not authorize quantitative extrapolation to zero.

The importer selects one `area_uvvisN(AU*min)` column, keeps injection/peak provenance and ignores `n.a.` placeholder rows only when peak number, RT and area are all absent. A missing area on a detected peak stops import. Declared/exported peak-count mismatches are flagged `incomplete_peak_export` and fail feedback QC. The supplied old test file had two such incomplete lists; this is a source-data issue to repair, not a zero yield. The current pipeline uses the integrated peak table directly. Raw-DAD reintegration would require different source data and a separately implemented workflow.
