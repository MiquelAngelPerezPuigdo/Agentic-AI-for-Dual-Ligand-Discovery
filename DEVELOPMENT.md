# Build and verify the current run

The staff-facing entry is **[run/README.md](run/README.md)**. `hte/single_run.py` generates the two self-contained OT-2 files, source/mass/LC tables and volume ledger. The supplied stock-holder well geometry is retained; only its travel-height envelope is increased to 45 mm so neighboring capped stock vials are included in clearance planning. Confirm actual capped height locally. `hte/run_analysis.py` uses the existing peak importer and calibrated quantification in `hte/analytics.py`.

Use Python 3.12:

```bash
uv sync --locked --extra test --extra docs
uv run python scripts/build-run.py
uv run python scripts/draw-run.py
uv run python scripts/build-bench-pdf.py
uv run python -m pytest -q
uv run python scripts/build-bench-pdf.py --check
```

Both protocols are simulated through the Opentrons SDK in the tests. The tests also propagate solutes/solvent through all transfers, check stock and reservoir residues, verify single-channel tip continuation across the two files, reproduce the published programs, and exercise synthetic HTEL exports through calibrated yields and deliberately faulty inputs.

`run/files.sha256.json` covers the generated machine files; `bench-sheet.build.json` covers its PDF and sources. Regenerate all artifacts together after changing the plan. The plan is fixed at 48 pairs / 100 µL; changing chemistry requires rechecking the dose arithmetic and calibration range. The new 60 mM Pd stock is prepared directly in one vial; its actual suitability remains a local chemical-handling check.

The common reservoir is prefilled by HTE. Its channel allocator preserves 1.5 mL per channel. Each stock source retains at least 150 µL and stays below 1.6 mL nominal fill. No use of the stock holder with the eight-channel pipette is permitted: vial pitch is 13 mm. All source pipetting and reaction sampling use the single; only LC diluent distribution uses eight channels.

`02_workup.py` starts at the next unused single-channel tip after file 1. Preserve the tip racks and LC plate between files. Do not skip operations or silently substitute stocks; record deviations and reconcile the actual source ledger before continuing.

The SDK establishes software command validity, not mounting, offsets, solvent compatibility, splash containment, dissolution or LC separation. The local App/setup checks and real calibration remain necessary. An integrated-area CSV cannot detect every coelution or verify upstream peak integration.

The initialization code, embeddings, scores and historical settings under `research/` are scientific provenance. Previous operational materials/tests are retained under `archive/`, outside the active package and test suite. They are not current bench instructions. The complete prior tree remains available at Git commit `dba4824`.
