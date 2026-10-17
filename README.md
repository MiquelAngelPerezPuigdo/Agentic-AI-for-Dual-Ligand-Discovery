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

The [four-page operator reference](docs/HTE-operator-handbook.pdf) covers the experiment, calibration and local pipeline. Its [Markdown sources remain editable](docs/updating-the-handbook.md).

## Campaign at a glance

**30 available ligands, 435 distinct unordered pairs.** Round one tests **48 pairs covering every ligand**. Round two tests **22 new pairs + one L17 tBuBrettPhos single-ligand reference**. One 48-position Para-Dox block is reused with 71 fresh 2 mL glass vials and manually handled screw caps.

Each reaction: **250 µL, 0.1 M substrate, 95 °C /4 h, 6 mol% each ligand, 12 mol% Pd(COD)(DQ)**. SM/DCM is evaporated before adding separate mesitylene and toluene/catalyst stocks. [Canonical configuration](hte_inputs/campaign.json), [remaining HTEL setup facts](docs/hte-questions.md).

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

**API key:** create **`anthropic.key` in the repository root** from [the placeholder](anthropic.key.example), replacing its line with the raw key. Keep an existing key file. The pipeline reads it automatically; an environment `ANTHROPIC_API_KEY` takes precedence. Keys stay local and are excluded from Git and handoff packages.

## Evidence and scope

[Validation record](software_validation.json), [human-readable verification](docs/rehearsal-results.md). The requested 1.7-minute LC cycle and staged handling give an **unmeasured 717.7-minute target**, with 2.3 minutes spare; physical setup, calibration and throughput remain HTEL checks. Operation uses local App import/start.

The method builds on the [thesis benchmark](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Catalyst-Design) and [GoLLuM's representation/diversity initialization](https://github.com/schwallergroup/gollum). Original project code is [MIT licensed](LICENSE).
