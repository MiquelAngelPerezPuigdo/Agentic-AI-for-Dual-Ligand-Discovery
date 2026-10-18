# Agentic AI for Dual-Ligand Discovery

A local OT-2 / LC workflow to search for productive dual-ligand systems in Pd-catalyzed desulfonylative fluorination of pyridine-2-sulfonyl fluoride to 2-fluoropyridine.

## Start with your role

| Reader | Start here |
|---|---|
| HTE staff running the experiment | **[Two-page staff checklist](docs/HTE-staff-checklist.pdf)** |
| Colleague operating the local pipeline | **[Setup and run commands](docs/start-here.md)** |
| Chemistry / ML reviewer | **[ML/LLM strategy, equations and limitations](docs/ml-strategy.md)** |
| Developer | **[Architecture, testing and reproduction](docs/development.md)** |
| Stock / analytical preparation | [Stock and calibration recipes](docs/stocks-and-calibration.md) |

**The OT-2 prepares stocks from weighed chemicals and bulk solvents**, fills its working sources, predoses R2, prepares calibration standards and workup fluids during reaction holds, and refills sources for R2. Staff handle weighing, coarse loading, caps, labeled labware moves, local starts and one pipette change.

The [four-page operator reference](docs/HTE-operator-handbook.pdf) covers the experiment, calibration and local pipeline. Its [Markdown sources remain editable](docs/updating-the-handbook.md).

## Campaign at a glance

**30 available ligands, 435 distinct unordered pairs.** Round one tests **48 pairs covering every ligand**. Round two tests **22 new pairs + one L17 tBuBrettPhos single-ligand reference**. One 48-position Para-Dox block is reused with 71 fresh 2 mL glass vials and manually handled screw caps.

![OT-2 deck map with robot stock preparation, source positions and manual block/plate routes](docs/figures/ot2-deck-setup.svg)

[Download the setup figure as PNG](docs/figures/ot2-deck-setup.png). The deck map shows the pipetting positions; the block and LC plate occupy the heater-shaker sequentially.

Each reaction, nominal under the solvent-addition approximation: **250 µL, 0.1 M substrate, 95 °C /4 h, 6 mol% each ligand, 12 mol% Pd(COD)(DQ)**. Dose **25 µL combined 1 M SM /100 mM mesitylene in toluene**, then 75 µL each of two **20 mM ligand stocks** and 75 µL **40 mM Pd**. Solvent is retained. The robot prepares **one 90 mg Pd bulk** (nominal 40 mM, ~5.94 mL at 100% assay); keep **10 mg solid for scope**. It makes the combined SM/IS stock with neat mesitylene. Low-dead-volume working tubes and automated source mixing are included. RockPhos L03 is limited to **four R2 wells**, with **10 mg available**. [Canonical configuration](hte_inputs/campaign.json), [remaining HTEL setup facts](docs/hte-questions.md).

The **[real initial batch is prepared](campaigns/hackathon2026/round1_design.csv)** using 50/50 Claude rank and T5 embedding diversity. Both scoring stages include ligand identities/SMILES and 17 available single-ligand SI yields. The second selection uses Claude with all 48 measured first-round results. [Frozen scores and selection audit](campaigns/hackathon2026/README.md).

**[View the initialization map and statistics](docs/initialization-review.md)**: pair-space coverage, a ligand-pairing network, use counts for every ligand, and alternative weight previews from the same saved scores. All-ligand inclusion is enforced; use frequencies are unequal.

## Install and practice

Use Python 3.12 on the local workstation. With uv: `uv sync --python 3.12 --extra sources`, then `uv run hte check`. With an activated virtual environment:

```bash
python -m pip install -e '.[sources]'
python -m hte.cli check
python -m hte.cli rehearse-loop --output output/practice
```

Practice uses synthetic yields and mocked Claude responses, with zero paid calls. Robot protocols, CSV setup files and practice outputs are generated locally under ignored `output/`; [setup commands](docs/start-here.md) produce the matching files. The frozen initial selection remains versioned.

The rehearsal includes HTEL-format peak exports, calibration and known-mixture challenges. Run only those with `python -m hte.cli practice-analytics --output output/analytics-practice`; [LC instructions](docs/htel-lc-import.md) cover the generated preparation tables and `verify-pilot` replay of actual HTEL files. HTEL supplies integrated UV areas; Python calculates calibrated concentrations and yields using mesitylene. No Chromeleon installation or vendor-calculated concentration file is required. Claude selects conditions after quantitative QC.

For a visual test, install `.[reports]` and run `python scripts/mock-hplc-trials.py --output output/mock-hplc`. Open the generated `mock-hplc-report.html` to compare 14 illustrative chromatograms with the pipeline's accepted, blocked and undetected-bias outcomes. No API calls or actual raw-trace integration are involved.

**API key:** create **`anthropic.key` in the repository root** from [the placeholder](anthropic.key.example), replacing its line with the raw key. Keep an existing key file. The pipeline reads it automatically; an environment `ANTHROPIC_API_KEY` takes precedence. Keys stay local and are excluded from Git and handoff packages.

**Return the data:** after staff save instrument logs/raw files and notes into `local_data/`, run `python scripts/hte-return-package.py`. Send `transfer/hte-results.zip` privately: code, local data, run outputs and file hashes, with credentials excluded. [What is saved and what staff must supply](docs/development.md#return-the-campaign-to-miquel). A Git push alone does not include experimental data.

Keep correspondence, meeting notes, registration details and team schedules outside this public repository. The shared documentation describes the project and its operating requirements.

## Evidence and scope

**Timing target: two 4 h reaction holds plus approximately 4 h for remaining tasks, including LC.** Stock preparation is inside the campaign; calibration and workup-fluid preparation overlap reaction holds. Actual stage times are recorded. The 12 h target is advisory and does not block export.

Use one final LC plate per round, with automated dilution/shaking and direct plate injection; no R1 split. Calibration uses a separate plate, pipette-mixed during hold one. [Software evidence](docs/rehearsal-results.md) and [machine-readable record](software_validation.json) distinguish simulation from physical execution. Local mounting, source-container compatibility, pipetting and actual LC validation remain required.

The method builds on the [thesis benchmark](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Catalyst-Design) and [GoLLuM's representation/diversity initialization](https://github.com/schwallergroup/gollum). Original project code is [MIT licensed](LICENSE).
