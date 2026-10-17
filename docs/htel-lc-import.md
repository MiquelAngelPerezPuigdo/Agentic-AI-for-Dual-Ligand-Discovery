# HTEL Chromeleon import / calibration

Use calibrated integrated UV peak areas for yield; MS is identity support. The old supplied CSV establishes format only. Its RTs, names and wavelength settings do not validate the requested 1.7-minute method. The supplied Thermo RAW is MS data, not raw DAD for MOCCA.

## Configure once from authentic standards

In `local_data/campaign.json`, set the actual `analytics.method_id`, one quantitative `channel` (`UV_VIS_1` to `UV_VIS_4`), `references` and `quantification_limit_uM`. References require `substrate`, `product`, `internal_standard`, each with measured `retention_time_min` and `window_min`; windows must not overlap. Record actual detector wavelength and injection volume alongside the method. We request 210 nm initially; the example's channels at 253/270/300/370 nm are historical settings. Do not sum wavelengths or substitute TIC for UV area.

The 14-sample plan is `hte_inputs/calibration_template.csv`: each analyte blank +10/50/150/350/800 µM and independent 666.667 µM check, IS66.667 µM throughout. [Preparation recipes](stocks-and-calibration.md). These injections run inside the first four-hour hold; initial dosing release can precede them. Workup release requires completed calibration.

## One explicit mapping per acquisition sequence

Chromeleon's wide export lacks method ID and may repeat names. Copy each generated `lc_batchNN_injections.csv`, fill actual `method_id` and optionally actual `vial_position`, `injection_name`, `type`. Map `inj_no` to the canonical sample ID. Do not assume numbering continues across batches. Maps must describe actual accepted injections, not just intended order; archive replacements/rejections and keep one accepted measurement per sample.

```csv
inj_no,sample_id,method_id
1,R1-001,ACTUAL_METHOD_ID
2,R1-002,ACTUAL_METHOD_ID
```

Blank mapping fields are optional identity cross-checks; supplied nonempty fields must match the source. Calibration has its own 14-row mapping using the calibration-plan sample IDs. Reaction maps and LC preparation coordinates come from the matching generated sequence; the 48-well reaction coordinates differ from the 96-well preparation plate.

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

Fit blank plus five levels and exclude independent checks from fitting. Wrong method/channel, ambiguous/missing peaks, poor fit or failed checks stop publication. A verified zero may require an explicitly reviewed integrated measurement in the template if the vendor omits zero peaks. No signal is silently set to zero. Configure measured LOQs; if missing-analyte censoring is desired, set `missing_analyte_policy="censor"` only with those LOQs, yielding upper bounds rather than invented zero yields. Default is rejection.

## Reaction results and final 22

After all 48 injections, run `scripts/hte-lc-results.py next` as shown on the [start page](start-here.md), giving six exports and six maps in corresponding order. It normalizes each sequence separately, rejects duplicate files/samples, combines them, and publishes a completion marker only for full expected sample coverage. Calibration/QC must then pass before any paid Claude call. The result is 22 new pairs plus one L17 reference, with local release status printed. Use `final` after the 23 final samples; it analyzes without Claude.

Alternatively use the separate `normalize`, `complete-export`, `analyze`/`iterate` commands or the local watcher. Do not run both helper and watcher on the same campaign deliberately: use one workflow and preserve its idempotent state. Corrected imports use fresh output directories. Retain hashes, source exports and map versions.

The importer selects one `area_uvvisN(AU*min)` column, keeps injection/peak provenance and ignores `n.a.` placeholder rows only when peak number, RT and area are all absent. A missing area on a detected peak stops import. Declared/exported peak-count mismatches are flagged `incomplete_peak_export` and fail feedback QC. The supplied old test file had two such incomplete lists; this is a source-data issue to repair, not a zero yield. The current pipeline uses the integrated peak table directly. Raw-DAD reintegration would require different source data and a separately implemented workflow.
