# Software and supporting records

HTE staff only need **[the run folder](../run/README.md)**. This folder contains the analysis code, build tools, tests, inputs and historical records. Run the commands below from the repository root.

| Folder | Purpose |
|---|---|
| `hte/` | Current generator and quantitative analysis |
| `hte_inputs/` | Ligand catalogue and labware definitions |
| `scripts/`, `tests/` | Rebuild and verify the handoff |
| `research/`, `campaigns/` | Scientific method and frozen pair-selection evidence |
| `archive/`, `docs/` | Historical files and earlier entry points |

## Build and verify

The staff-facing entry is **[run/README.md](../run/README.md)**. `support/hte/single_run.py` generates one self-contained OT-2 program, source/mass/LC tables and volume ledger. The supplied stock-holder well geometry is retained; only its travel-height envelope is increased to 45 mm so neighboring capped stock vials are included in clearance planning. Confirm actual capped height locally. `support/hte/run_analysis.py` uses the existing peak importer and calibrated quantification in `support/hte/analytics.py`.

Use Python 3.12:

```bash
uv sync --locked --python 3.12 --extra test --extra docs
uv run python support/scripts/build-run.py
uv run python support/scripts/draw-run.py
uv run python support/scripts/build-bench-pdf.py
uv run python -m pytest -q
uv run python support/scripts/build-bench-pdf.py --check
```

The complete continuous protocol is simulated through the Opentrons SDK in the tests. The tests also propagate solutes/solvent through all transfers, check stock and reservoir residues, verify that tips are used once across all phases, reproduce the published program, and exercise synthetic HTEL exports through calibrated yields and deliberately faulty inputs.

`run/tables/files.sha256.json` covers the generated machine files; `run/tables/bench-sheet.build.json` covers its PDF and sources. Regenerate all artifacts together after changing the plan. The plan is fixed at 48 pairs / 100 µL; changing chemistry requires rechecking the dose arithmetic and calibration range. The new 60 mM Pd stock is prepared directly in one vial; its actual suitability remains a local chemical-handling check.

The common reservoir is prefilled by HTE. Its channel allocator preserves 1.5 mL per channel. Each stock source retains at least 150 µL and stays below 1.6 mL nominal fill. No use of the stock holder with the eight-channel pipette is permitted: vial pitch is 13 mm. All source pipetting and reaction sampling use the single; only LC diluent distribution uses eight channels.

`run/run_screen.py` keeps one protocol context and the same loaded pipettes from stocks through sampling. Tip tracking continues automatically; no starting-tip override or protocol restart is required. Preserve all tip racks and the LC plate throughout. Do not skip operations or silently substitute stocks; record deviations and reconcile the actual source ledger before continuing.

The SDK establishes software command validity, not mounting, offsets, solvent compatibility, splash containment, dissolution or LC separation. The local App/setup checks and real calibration remain necessary. An integrated-area CSV cannot detect every coelution or verify upstream peak integration.

The initialization code, embeddings, scores and historical settings under `research/` are scientific provenance. Previous operational materials/tests are retained under `archive/`, outside the active package and test suite. They are not current bench instructions. The complete prior tree remains available at Git commit `dba4824`.
