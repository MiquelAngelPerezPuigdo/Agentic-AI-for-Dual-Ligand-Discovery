# Agentic AI for Dual-Ligand Discovery

Local OT-2 screening of ligand cooperativity in Pd-catalyzed desulfonylative fluorination of pyridine-2-sulfonyl fluoride to 2-fluoropyridine.

HTE staff: use the **[two-page action checklist](docs/HTE-staff-checklist.pdf)**. The [reference handbook](docs/HTE-operator-handbook.pdf) contains stock recipes, local software commands and analytical handling. Both PDFs have [editable sources](docs/updating-the-handbook.md).

## Current campaign

- **Round one: 48 distinct pairs. Round two: 22 new pairs + one L17 tBuBrettPhos single-ligand reference.** One 48-position Para-Dox block; 71 fresh 2 mL reaction vials. Individual screw caps are handled manually at explicit pauses. OT-2 heater-shaker, no stir bars.
- **250 µL, 0.1 M, 25 µmol SM, 95 °C for four hours per round**, 6 mol% each ligand and 12 mol% Pd(COD)(DQ). Stocks prepared before the competition; ligand stocks in the glovebox.
- Dose **50 µL of 500 mM SM in DCM**, evaporate completely, then add **25 µL 100 mM mesitylene**, **37.5 µL each 40 mM ligand**, **75 µL 40 mM Pd**, **75 µL toluene**. Mesitylene is separate and added after DCM removal. Predose/dry the 23 second-round SM vials off deck during the first hold.
- Quench/workup: **500 µL 9:1 ACN/water + 0.15% formic acid**, recap, shake **1500 rpm for two minutes**. Prepare **20 µL extract + 980 µL 1:1 water/ACN + 0.1% formic acid**. Staff mix and transfer to HPLC vials in batches of eight. Final nominal analyte maximum **667 µM**, mesitylene **66.7 µM**, formic acid **0.1%**.
- Requested LC method **1.7 min**. Calibration runs during the first hold. The **717.7-minute planning target** assumes 35 minutes of staged LC/handling overlap; serial processing is 752.7 minutes. Full cycle time and handling throughput are unmeasured. [Timing and organizer requirements](docs/organizer-updates.md).

L07 AdJohnPhos is unavailable. Original IDs remain fixed: **30 active ligands, 435 possible distinct pairs**. No other ligand is silently removed.

## Initial batch is prepared

The real [48-pair design](campaigns/hackathon2026/round1_design.csv) combines **50% Claude performance rank + 50% diversity across T5 embeddings**, with every active ligand represented. This borrows the language-model representation/diversity initialization idea from [GoLLuM](https://github.com/schwallergroup/gollum); no pair yields or GP training are needed. **Round two uses Claude only**, after experimental feedback.

Claude Opus 4.8 scored all 435 pairs five times in **340 small anchor/partner requests**, at most eight pairs each. Both prompts include all 30 ligand IDs/names/SMILES and **17 available same-substrate single-ligand SI yields**; 13 are unknown. No full pair catalogue or reasoning is requested. [Exact example prompt](docs/claude-scoring-prompt.txt), [prompt guide](docs/scoring-prompt.md), [all repeated scores and provenance](campaigns/hackathon2026/scoring/).

Provider-reported caching: **311/340 requests**, **1,578,979 cache-read tokens**, estimated accepted scoring cost **$2.7599745**. A rejected earlier response cost $0.225235; historical smoke tests cost $0.4023195. The real second-round selection has **not** been run. Synthetic practice selections are never experimental recommendations.

The [generated round-one files](campaigns/hackathon2026/round1/) include stock quantities, exact source loads, reaction/LC maps, batch injection-map templates and self-contained Python. They are **simulation-only until locally released**. [Start here](docs/start-here.md) for release and LC-to-next-batch commands.

## Install / practice

HTEL can use its usual uv workflow: `uv sync --python 3.12 --extra sources`, then `uv run hte check`. With pip:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[sources,test,analytics]'
python -m pip install -r requirements-gollum.txt
python -m pytest -q
python -m hte.cli rehearse-loop --output output/practice
```

The practice command mocks Claude and chemistry, uses the real 435 × 768 T5 vectors and makes **zero paid calls**. `demo/` is also synthetic and refuses physical execution. The ordinary local operator installation needs only the core project plus `sources`; ML dependencies support adapter tests and rebuilding embeddings.

**API key:** copy `anthropic.key.example` to **`anthropic.key` in the repository root**, replace the placeholder with the raw key, and keep it local. Both scoring and the LC helper read it automatically. An existing `ANTHROPIC_API_KEY` environment variable takes precedence. The file is ignored by Git and excluded from handoff archives. [Prompt caching and costs](docs/prompt-caching.md).

## Project map / evidence

| Path | Purpose |
|---|---|
| `campaigns/hackathon2026/` | Real initial selection, score audit and simulation exports |
| `hte/` / `hte_inputs/` | Local pipeline / chemistry, inventory, source evidence and supplied labware |
| `scripts/hte-lc-results.py` | Join completed LC batches; select the final 22 or analyze final results |
| `docs/` | Two-page staff sheet, reference procedures, remaining setup facts |
| `tests/hte/` / `software_validation.json` | Acceptance checks and their limits |
| `demo/` | Synthetic results only |

[Rehearsal evidence](docs/rehearsal-results.md) covers software tests and actual Opentrons simulation. No physical robot runs or 95 °C pair yields exist yet. The original thesis [Agentic AI for Catalyst Design](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Catalyst-Design), [GoLLuM](https://github.com/schwallergroup/gollum) and [MOCCA](https://github.com/bayer-group/MOCCA) are credited in the reference documentation. MOCCA requires raw DAD data; the supplied integrated CSV uses Chromeleon directly.

Original project code is [MIT licensed](LICENSE). Vendored GoLLuM utilities retain [Apache-2.0 attribution](hte/vendor/GOLLUM_NOTICE.txt).
