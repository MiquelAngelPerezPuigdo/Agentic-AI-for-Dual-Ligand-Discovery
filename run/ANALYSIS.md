# Analyze the one-run LC sequence

This step is for the software/LC operator. It calculates calibrated yields; it does not select or dose another batch. No Claude key or Chromeleon installation is needed on the workstation.

1. Install Python 3.12 and run `uv sync --locked` from the repository root.
2. Copy [lc-settings-template.json](lc-settings-template.json) to **`local_data/lc-settings.json`**. Enter the actual method ID, quantitative UV channel (`UV_VIS_1` to `UV_VIS_4`), measured SM/product/naphthalene retention windows and measured LOQs. Do not use guessed retention times.
3. Copy [lc-injections.csv](lc-injections.csv) to **`local_data/actual-injections.csv`**. Update injection numbers/order to what actually ran and fill its `method_id` column. The accepted sequence is seven standards plus all 48 samples; reinjections require an explicit reviewed map.
4. Export the HTEL integrated-peak CSV for that accepted sequence and save it as **`local_data/lc-export.csv`**. Keep the original LC/MS files too.

```bash
uv run hte-analyze --export local_data/lc-export.csv \
  --map local_data/actual-injections.csv \
  --settings local_data/lc-settings.json --output output/results
```

If the LC software omits an analyte peak from the zero-analyte calibration blank, inspect that blank first. After confirming that the SM/product peaks are absent in their reference windows, add **`--reviewed-blanks "REVIEWER NAME"`**. This records that review; it never fabricates a peak or retention time.

The pipeline matches peaks on the selected channel, fits SM/IS and product/IS responses, checks five nonzero calibration levels and the independent check, and calculates the 48 results. Valid low signals are reported as bounds, rather than invented zero yields. Ambiguous peaks, an incomplete export, failed calibration or abnormal IS response fail QC.

Open **`output/results/results.csv`** and **`qc_report.json`**. At the planned volumes, 100% product corresponds to **800 µM** and naphthalene to **80 µM** in the LC well; `yield (%) = product concentration (µM) / 8`. The five fitted levels are **10, 50, 200, 500 and 1000 µM**, plus a blank and an independent **800 µM** check. Actual LOQ and peak separation must come from real standards; an area CSV cannot prove peak purity or extraction homogeneity.

Return the complete output folder, `local_data/`, original LC/MS data, robot logs and run notes privately to Miquel. Outputs include copies of the input export, map, settings and calibration plan plus checksums. Do not publish experimental records or an API key.
