# HTEL Chromeleon import

Use integrated UV peak areas for calibrated yield. The supplied old test CSV demonstrates format only. Its retention times, standards, concentration labels and injection volume do not validate our chemistry or the requested 1.7-minute method. The supplied Thermo RAW is MS data; it cannot feed MOCCA's raw-DAD workflow.

## Configure the method and map injections

In `local_data/campaign.json`, set the **actual** `analytics.method_id` and quantitative `analytics.channel`: `UV_VIS_1`, `UV_VIS_2`, `UV_VIS_3` or `UV_VIS_4`. HTEL's example wavelengths were 253/270/300/370 nm respectively. Confirm the actual method settings before choosing one. Never sum channels or use TIC as calibrated UV area.

The wide export has no method ID. Record it from the acquisition sequence. Create one mapping CSV per accepted sequence:

```csv
inj_no,sample_id,method_id,injection_name,vial_position
1,R1-001,ACTUAL_METHOD_ID,ACTUAL_INJECTION_NAME,ACTUAL_POSITION
2,R1-002,ACTUAL_METHOD_ID,ACTUAL_INJECTION_NAME,ACTUAL_POSITION
```

Replace every example entry with the actual sequence. `sample_id` comes from `lc_sequence.csv` for reactions, or `calibration_template.csv` for standards. Optional `injection_name`, `vial_position` and `type` columns are cross-checked when supplied. Names can repeat, so never map by name alone. Keep only one accepted injection per sample, archive rejected/replacement injections and their reasons, and export the accepted sequence separately. Every measured injection must appear in the mapping.

```bash
python -m hte.cli --config local_data/campaign.json normalize local_data/round1_vendor.csv \
  --injections local_data/round1-injections.csv --output output/hte-lc-inbox/round1.csv
```

The importer reads `retention_time(min)` and one `area_uvvisN(AU*min)` column, keeping source injection number/name/vial/peak number. `channel_for_peak_detection` describes integration detection; it does not override the selected quantitative area column. `n.a.` padding is omitted only when peak number, RT and selected area are all missing. Missing area on a detected peak stops import. Actual numerical zero remains zero.

`round1.csv.normalization.json` records hashes, chosen area column, omitted rows and declared/exported peak-count mismatches. Mismatched injections receive `incomplete_peak_export` QC flags and cannot supply accepted yield feedback. Resolve the export in Chromeleon; do not replace missing areas with zero. The supplied test file contains two such incomplete lists. An injection with no usable peaks stops import and needs explicit review.

Release first dosing with `export --live --stage dose_and_react` after hardware/timing checks and method confirmation. This does not release workup. Complete calibration during the first hold, then release `export --live --stage workup` into a new folder. Round two retains the full calibration checks.

## Build the calibration without manual area copying

Run the requested 14 authentic-standard injections during the first reaction. Supply their own accepted-injection mapping and normalize them as above. Configure authentic-standard RT windows, LOQs and all analytical settings first. Prepare a copy of `calibration_template.csv` with actual sample IDs, roles, known concentrations and fixed IS concentration.

```bash
python -m hte.cli --config local_data/campaign.json calibration-from-peaks \
  --peaks output/calibration-peaks.csv --plan local_data/calibration-plan.csv \
  --output output/hte-calibration.csv
```

The command extracts the analyte/IS peaks using configured RT windows, fits blank plus five nonzero concentrations and checks the independent standards. It publishes the calibration only after QC passes. Ambiguous peaks, wrong method, missing IS, poor fit or failed checks stop it. A blank needs a measured integrated zero area; an omitted peak is not silently assigned zero. If Chromeleon omits verified zero signals, HTE must provide explicitly reviewed measurements through the existing calibration template.

## Complete the sequence and trigger iteration

Only after all 60 first-round injections are complete and the normalized export has been checked:

```bash
python -m hte.cli --config local_data/campaign.json complete-export \
  --peaks output/hte-lc-inbox/round1.csv --dosing output/hte-round1/dosing.csv \
  --output output/hte-lc-inbox/round1.ready.json
```

The already-running local watcher validates hashes, sample coverage and calibration/QC before Claude receives results. It scores the remaining 376 pairs and produces ten new pair assignments. The robot remains isolated; staff import/start the released Python locally. Repeat normalization/final analysis for the ten second-round samples. Keep source CSVs, mappings, normalization reports, completion markers and original MS data together in the private campaign archive.
