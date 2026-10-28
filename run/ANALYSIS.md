# Analyze the one-run LC sequence

This step is for the person handling the LC export and quantification, after [staff-guide step 9](README.md#9-take-the-plate-to-hplc-ms-and-return-the-results). The OT-2 prepares calibration standards and reaction samples after the heated hold. Staff carry the completed sealed plate to HPLC-MS, where the LC operator runs **one sequence: seven standards followed by 48 reaction samples**. This page turns the exported peak areas into calibrated yields.

**LC operator hands over:** the integrated-peak CSV, original LC/MS files, actual injection list and method, measured peak assignments/UV channel and quantification limits. **Quantification operator returns:** the complete results/QC folder below, together with the robot log and run notes. These roles can be handled by the same person. No API key is needed.

The campaign requests **HTEL's medium-polarity 3-minute HPLC-MS method for all 55 injections**. Check the authentic standards before continuing with the reaction samples. Enter the actual instrument method ID and measured retention windows below; the polarity label and requested duration are not retention-time assignments.

1. Install Python 3.12 and run `uv sync --locked --python 3.12` from the repository root.
2. Copy [lc-settings-template.json](tables/lc-settings-template.json) to **`local_data/lc-settings.json`**. Enter the actual method ID, quantitative UV channel (`UV_VIS_1` to `UV_VIS_4`), measured SM/product/naphthalene retention windows and measured LOQs. Do not use guessed retention times.
3. Copy [lc-injections.csv](tables/lc-injections.csv) to **`local_data/actual-injections.csv`**. Update injection numbers/order to what actually ran and fill its `method_id` column. Keep each `sample_id` paired with its supplied `well`: that is where the robot put it. The export's physical `vial_position` must match that well; HTEL positions such as `B:C1` are supported. The accepted sequence is seven standards plus all 48 samples from this one LC plate; reinjections require an explicit reviewed map.
4. Export the HTEL integrated-peak CSV for that accepted sequence and save it as **`local_data/lc-export.csv`**. Keep the original LC/MS files too.

```bash
uv run hte-analyze --export local_data/lc-export.csv \
  --map local_data/actual-injections.csv \
  --settings local_data/lc-settings.json --output output/results
```

For a corrected rerun, choose a fresh output folder, for example **`--output output/results-02`**. Existing results are preserved.

If the LC software omits an analyte peak from the zero-analyte calibration blank, inspect that blank first. After confirming that the SM/product peaks are absent in their reference windows, add **`--reviewed-blanks "REVIEWER NAME"`**. This records that review; it never fabricates a peak or retention time.

The pipeline matches peaks on the selected channel, fits SM/IS and product/IS responses, checks five nonzero calibration levels and the independent check, and calculates the 48 results. Valid low signals are reported as bounds, rather than invented zero yields. Ambiguous peaks, an incomplete export, failed calibration or abnormal IS response fail QC.

Open **`output/results/results.csv`** and **`qc_report.json`**. At the planned volumes, 100% product corresponds to **800 µM** and naphthalene to **80 µM** in the LC well; `yield (%) = product concentration (µM) / 8`. The five fitted levels are **10, 50, 200, 500 and 1000 µM**, plus a blank and an independent **800 µM** check. Actual LOQ and peak separation must come from real standards; an area CSV cannot prove peak purity or extraction homogeneity.

Return the complete output folder, `local_data/`, original LC/MS data, robot logs and run notes privately to Miquel. Outputs include copies of the input export, map, settings and calibration plan plus checksums. Do not publish experimental records or an API key.
