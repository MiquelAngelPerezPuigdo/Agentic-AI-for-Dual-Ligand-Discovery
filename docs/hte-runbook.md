# Local OT-2 dual-ligand fluorination: operator runbook

The 250 µL reaction scale is provisional for larger glass vials; it requires a confirmed rack and simultaneous heating setup.

This package screens 59 distinct ligand pairs plus one tBuBrettPhos reference, then 10 new pairs. It converts completed LC peak exports into calibrated yields, sends those results to five repeated Claude scoring calls, and generates the next dosing CSV. Robot operation stays local through the Opentrons OT-2 App. A workstation with permitted internet access makes the Anthropic calls; the robot never needs internet or remote control.

**Software verification is separate from bench readiness.** The provided demo is synthetic and its protocols refuse physical execution. The real campaign still needs an exact glass-block definition and mounting/seal validation, solvent delivery checks, a homogeneous extraction, and the HTEL analytical method. The real first-round selection must be generated with the operator's Claude key; no synthetic ranking should be used for chemistry.

## Fixed experiment and interpretation

| Item | Campaign plan; scale pending confirmation |
|---|---|
| Substrate | Pyridine-2-sulfonyl fluoride / PyFluor, `FS(C1=NC=CC=C1)(=O)=O` |
| Product standard | 2-Fluoropyridine, `FC1=NC=CC=C1` |
| Amount / concentration | 25 µmol / 0.1 M in 250 µL final toluene solution |
| Pair ligands | 1.50 µmol each, 6 mol% each; loading counts ligand molecules |
| Pd | 3.00 µmol Pd(COD)(DQ), 12 mol%; one Pd per complex |
| Reference | L17 tBuBrettPhos, 3.00 µmol / 12 mol% total ligand; same Pd and conditions |
| Temperature / hold | 95 °C / 240 minutes after the module reaches the setpoint |
| Atmosphere | Reaction assembly under air; ligand stocks prepared/stored in glovebox |
| Additional reagents | 0.250 µmol naphthalene analytical IS added with SM; no base or external fluoride source |
| Round 1 | 59 pairs + 1 reference = 60 wells |
| Round 2 | 10 untested pairs; no reaction repeats or additional controls |
| Objective | Calibrated product yield; conversion is diagnostic |

The reference is a fair, resource-efficient comparison against a good single ligand at the same temperature, total ligand loading and Pd loading. An improvement over this reference supports a better mixture under these conditions. It does not prove synergy relative to both individual partners, reproducibility, or a broader substrate scope. Those claims require subsequent partner controls, repeats and scope experiments. Score SD measures disagreement among model calls, not experimental error.

The supplied Chemical Science SI Table S2, p. S35, contains 18 single-ligand yields for this substrate. These are captured in `hte_inputs/literature.json`, including tBuBrettPhos 77%, AdBrettPhos 78%, MorDalPhos 77%, Me4tBuXPhos 72%, RockPhos 63% and Me3OMe-tBuXPhos 61%. They are high-temperature qualitative priors, not 95 °C measurements. The SI's air example uses a different Pd source at 150 °C. Do not merge these data with the main-text ligand table or train a 95 °C pair surrogate on them. [Paper and SI](https://pubs.rsc.org/en/content/articlehtml/2025/sc/d5sc00912j).

The thesis benchmark motivates repeated mechanism-informed scoring, but its dual-ligand benchmark is decarbonylative Suzuki coupling. Ligand relay in the fluorination remains a hypothesis. The Nature multicatalysis paper is contextual inspiration rather than this campaign's measured training data. [Nature paper](https://www.nature.com/articles/s41586-025-09813-2).

## Before the competition: resolve hardware and analytics

Use the [HTE configuration checklist](hte-questions.md) to obtain the remaining facts. The [start-here guide](start-here.md) explains responsibilities and hidden API-key entry; [rehearsal results](rehearsal-results.md) document the fake feedback loop. Record confirmed facts in a campaign-specific copy of `hte_inputs/campaign.json`. Keep that copy, inventory, calibration, protocol exports and run logs together. The production commands below use `local_data/campaign.json`; create it once and edit it as HTE confirms the settings:

```bash
mkdir -p local_data
cp hte_inputs/campaign.json local_data/campaign.json
```

Do not recopy the template over a configured campaign. Initial selection can run with provisional hardware fields; live protocol export requires the released configuration.

HTEL publicly lists a Thermo Vanquish Horizon Duo with ISQ-EM, tandem column operation, and a DAD detector. UZH's Chromeleon page lists `LC-ISQ-HTL-01`. HTEL confirmed Chromeleon, supplied the wide integrated-peak export and MS-only Thermo RAW, and described 1.7-minute, 3-minute and 5-6-minute methods. We request the existing 1.7-minute method. Its suitability, full cycle, quantitative wavelength, retention windows and injection volume remain pending. Prefer a validated DAD calibration for yield and use MS to confirm peak identity. Naphthalene may be unsuitable for HESI quantification: do not assume an MS internal-standard signal. [HTEL equipment](https://www.chem.uzh.ch/en/research/services/htel/Equipment.html), [Chromeleon instruments](https://www.chem.uzh.ch/en/research/services/massspec/Open-access_LC-and_GC-MS_with_Chromeleon.html).

If a measured thermal lag requires additional equilibration after the module reaches 95 °C, set `chemistry.thermal_equilibration_minutes` to that validated time. The generator adds it before starting the 240-minute hold. Include both rounds' extra equilibration in the measured heating-overhead estimate. The initial zero is an unresolved bench placeholder, not proof of instant equilibration.

The earlier unconfirmed 96-position option is the [Para-Dox Gen II 96-position parallel-synthesis block 104960](https://www.analytical-sales.com/product/standard-96-position-parallel-synthesis-reaction-block-gen-ii/) with 8 × 30 mm, 1 mL glass inserts, preferably the manufacturer's assembled tray 884001. Its drawing gives 127.8 × 85.5 mm, 9 mm pitch, and approximately 46.2 mm assembled height. The footprint matches ordinary microplates; this alone does not establish heater-shaker compatibility. [Block drawing](https://www.analytical-sales.com/drawings/104960_rev1c_PUBLIC.pdf), [regular microplate dimensions](https://www.corning.com/catalog/cls/documents/drawings/LSR00181.pdf).

HTE must check the complete block on the supplied universal flat adapter: latch engagement, closed lid/bolt clearance, mass during shaking, stable contact, vial seating, thermal performance and sealing with toluene at 95 °C. A module setpoint does not prove a large aluminum block's liquids are at that temperature. Validate the thermal lag with a representative filled vial and include the resulting procedure in the hold timing. The revised 250 µL reaction gives 500 µL after workup; original 50 µL reactions were shallow in larger vials; aspiration immersion needs particular attention.

Use a combined block-plus-vial custom Opentrons JSON with measured **open-block** height, well opening diameter, depth, vial-bottom Z and A1 position. Do not substitute a PCR definition for glass. The manufacturer's drawing does not establish all internal vial dimensions or measured deck offsets. Set `reaction_definition_path` to that JSON, `reaction_labware` to null, and the true working volume. If a custom adapter is needed, the supplied adapter loading code must be reviewed for that adapter before use. A block that cannot be latched securely cannot be shaken by this protocol. For custom labware, contact johannes.schoergenhumer@chem.uzh.ch.

The well coordinates describe the open vials, but travel clearance must also account for the sealed block's maximum height. HTE must check both states; the model cannot treat a removed lid as proof of clearance while a sealed block is on the heater.

Follow the manufacturer's PFA-film/rubber-mat stack and cross-pattern sealing instructions, including the specified torque for the exact reactor. Validate solvent loss for a four-hour hold and gas/pressure compatibility: this reaction releases SO₂. Recheck after cooling before opening. Ordinary plate seals are not evidence of a suitable reaction seal. [Assembly instructions](https://www.analytical-sales.com/manuals/GenII_reactor_block_instructions_web.pdf).

The existing generator requires a 96-position, 9 mm-pitch reaction array and simultaneous heating of all 60 first-round reactions. Round two needs a second compatible array for capped liquid predoses during round one. HTEL mentions 24 × 4 mL vials, but the ZIP contains a 24-well plastic-plate surrogate, not the vial-rack definition. A single 24-position heater cannot meet the deadline through sequential holds. Obtain the actual geometry/heating plan and redesign before using 24-vial blocks. Confirm a second block or removable tray that preserves vial mapping during capped storage.

For the LC plate, use the appropriate library definition for HTE's PP plate, substituting the exact brand/geometry as necessary. `nest_96_wellplate_2ml_deep` is a representative placeholder, not an instruction to use a 2 mL plate. A validated 200 µL working-volume PP plate may be more economical, provided its actual working volume, mixing, autosampler access, seal and needle-height requirements are satisfied. Avoid PS for this solvent-containing workflow unless HTE has verified compatibility.

## Releasing round one before calibration

Calibration is measured during the first reaction, so release the first dosing protocol separately after all hardware/solvent/heating/timing checks pass and HTEL confirms the actual method ID:

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design output/real-first-batch/first_batch.csv --output output/hte-round1 \
  --live --stage dose_and_react
```

This exports only `dose_and_react.py`; it does not release workup. During the hold, normalize standards, run `calibration-from-peaks`, record accepted analytical settings and mark completed calibration validation. Archive each configuration revision. Then release the first workup into a new folder:

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design output/real-first-batch/first_batch.csv --output output/hte-round1-workup \
  --live --stage workup
```

Use that folder's workup protocol and stage deck loads. It must describe the same reaction identities, amounts and well map; never change chemistry while filling analytical metadata. Round two and workup retain the full calibration/QC release checks. A false validation flag records missing work; it must not be toggled simply to bypass a gate.

## Install and rehearse locally

Use Python 3.12 on the operator workstation, not the robot's internal Python. From the package root:

```bash
python3.12 -m venv .hte-venv
source .hte-venv/bin/activate
python -m pip install -e '.[sources,test,analytics,embeddings]'
# Optional embedding rebuilds and historical adapter tests:
python -m pip install -r requirements-gollum.txt
python -m pytest -q tests/hte
python -m hte.cli demo --output output/hte-rehearsal
```

`requirements-hte-tested.txt` pins the principal versions used here; for the same principal package versions, install it before `python -m pip install -e .`. It is a tested version list, not a complete lock of all transitive dependencies.

The demo supplies a synthetic LC method and a library 2 mL deepwell plate/deepwell adapter only for software simulation. The available universal flat adapter is not interchangeable with that test adapter. It has 60 first-round and 10 second-round samples, valid nondetection bounds, no repeated pairs, and no second substrate dose. Never use its selections, calibration or labware as real experimental inputs.

Simulate each of its four Python files with the pinned OT-2-capable package:

```bash
python -m opentrons.simulate output/hte-rehearsal/round1/dose_and_react.py
python -m opentrons.simulate output/hte-rehearsal/round1/workup.py
python -m opentrons.simulate output/hte-rehearsal/round2/dose_and_react.py
python -m opentrons.simulate output/hte-rehearsal/round2/workup.py
```

Opentrons 8.8.2 is pinned for workstation tests because the installed 9.1.2 simulator rejected OT-2 protocols. Protocol files use API 2.18. HTE must also analyze them in its actual local OT-2 App/robot software, confirm the version supports this API, and perform Labware Position Checks. Simulation checks command compatibility and deck restrictions, not glass fit, organic-solvent volume accuracy, phase behavior or temperature in the liquid.

Do a measured rehearsal of both dosing/workup stages with the final hardware and liquids or appropriate validated surrogates. Record real heating/cooling, manual handling and injection-cycle times. Test Claude model access and a scoring campaign before the competition. Do not discover a quota or schema issue during the second-round decision.

## Inventory, embeddings and first-round selection

`hte_inputs/ligands.csv` preserves all 31 workbook ligands; `design.excluded_ligands` removes L07 AdJohnPhos (CAS 224311-55-1) from this campaign. The 30 available rows retain their original IDs, source locations and molecular weights. The original workbook remains unchanged. Two user-authorized corrections are recorded in the CSV: L11 now contains the methoxy oxygen; L27 is tris(3-chlorophenyl)phosphine. Commercial Me3(OMe)tBuXPhos can be a regioisomer mixture; preserve the actual supplier/lot identity rather than claiming a pure regioisomer from one representative SMILES. [Original ligand study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3387921/).

There are 435 unordered distinct pairs. The included `hte_inputs/pair_embeddings_t5-base.npz` contains real, frozen T5-base text embeddings, 768 dimensions per pair. Both ligand orders are encoded and averaged. Provenance and model revision are saved beside it. This uses names, structures and the fixed reaction context, without manually calculated steric/electronic descriptors. It is inspired by the language-model representation approach in [GoLLuM](https://github.com/schwallergroup/gollum), and is not a trained GoLLuM yield model. Rebuild after changing ligand identities/names or inventory metadata:

```bash
python -m hte.cli embeddings --model google-t5/t5-base --download \
  --output output/hte-embeddings/rebuilt.npz
```

With no measured pair yields, GoLLuM contributes its language-model representation approach rather than a trained yield model. Our frozen T5-base encoder embeds the names, SMILES and reaction context for all 435 pairs; averaging both ligand orders makes each representation symmetric. Claude independently scores every pair five times. Software converts the mean scores to rank percentiles, then combines 50% Claude rank and 50% embedding-diversity rank at each greedy selection. Initial diversity uses distance from the embedding centroid; later diversity uses minimum distance from selected pairs. Equal scores/distances receive average ranks, so ligand IDs do not create a preference between ties. These ranks are selection preferences, not calibrated chemical probabilities. Initialization needs no measured pair yields: [upstream initializers](https://github.com/schwallergroup/gollum/blob/main/src/gollum/initialization/initializers.py) select from input representations. After round one, only Claude receives measured feedback and selects ten new pairs; GoLLuM is not used again.

**All 30 active ligands must appear in at least one of the 59 first-round pair wells.** The L17 single-ligand reference does not satisfy this pair-coverage requirement. Coverage is secured first: eligible pairs that introduce two unseen ligands are preferred where possible, and the same 50/50 consensus chooses between them. Once all ligands are represented, ordinary consensus filling completes the 59 pairs. The usual Claude percentile floor is 0.25; a coverage choice may go below that floor when necessary, and its override is recorded. This requirement adds no wells, singles or repeats.

`*.selection.csv` records the two ranks, coverage phase, newly covered ligand IDs and any floor override. `*.ligand_coverage.csv` lists each ID/name and number of pair wells; verify 30 covered and no zero counts before stock preparation. The metadata also records coverage and overrides. Design creation, dosing export and LC feedback processing reject missing required ligands. Keep `design.require_all_ligands_in_round1_pairs = true` in the campaign configuration. Conditions are randomized across occupied wells in column-major order to use full eight-well columns efficiently.

Store the Claude key on the operator workstation. Copy `anthropic.key.example` to `anthropic.key` in the repository root and replace the single placeholder line with the raw key, without quotes or an `ANTHROPIC_API_KEY=` prefix. Scoring and the watcher automatically read this file when run from the repository root. The file is ignored by Git and excluded from this handoff. It must not appear in a protocol, CSV, notebook output or committed file.

An existing `ANTHROPIC_API_KEY` environment variable takes precedence over the file; `.env` files are not automatically loaded. On macOS zsh, hidden entry can set that variable without putting the key in command history:

```zsh
read -rs 'ANTHROPIC_API_KEY?Claude API key: '
export ANTHROPIC_API_KEY
```

Run scoring or the watcher from the repository root. The local key file works on other platforms too; use HTE's approved secret setup if required by the workstation policy.

```bash
python -m hte.cli --config local_data/campaign.json score --output output/hte-round1-scoring
python -m hte.cli --config local_data/campaign.json \
  design --ranking output/hte-round1-scoring/ranking.csv \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output output/hte-round1-design.csv
```

Five calls independently score every pair after shuffled candidate ordering. The [scoring prompt guide](scoring-prompt.md) lists all 30 active IDs/names/SMILES and 17 active CAS-matched SI Table S2 yields (18 in the source evidence). The prompt names pyridine-2-sulfonyl fluoride (PyFluor) and 2-fluoropyridine, asks about potential ligand cooperativity and scores expected relative product-yield performance. Only individual literature yields and their brief condition label are sent; the 13 unreported active values remain unknown. An explicit catalog maps every pair ID to its two ligand IDs.

Run `python -m hte.cli preview-prompts --output output/prompt-review` to inspect the exact requests without API calls. Paid scoring saves the same readable prompts and request JSON beside each response. The parser accepts only `scores`, with one finite numeric 0-100 score for every requested ID. It rejects reasoning fields, missing/duplicate/extra IDs, numeric strings, nulls and booleans. Extended thinking is disabled. Raw responses, usage and repeated scores are retained. Fixed experimental conditions remain configured by the operator.

[Prompt caching](prompt-caching.md) is enabled by default with a one-hour TTL in both rounds. Shared chemistry context and measured feedback are cached; shuffled candidate IDs remain outside the cached prefix. Stable schemas and a first scoring response before parallel followers preserve reuse. Each scoring directory contains `cache_summary.json` and response cost breakdowns; inspect the provider's read counters to verify live hits. Cache expiry across the reaction requires a fresh write in round two. The budget preflight includes the write premium and assumes no cache hits.

Claude Opus 4.8 is explicitly configured; the code checks access and never silently substitutes a model. At the verified $5/M input and $25/M output token prices, five requests each using the full 10,000-output-token allowance cost at most $1.25 for output, before input and retries. A $20 cap per campaign is therefore plausibly ample for the present prompts, but the code performs a token-count preflight, reserves one retry, and refuses a campaign whose estimated bound exceeds the cap. The two rounds have separate $20 caps; this is not a shared $20 project budget. A preflight is an estimate, not a provider-enforced spending limit; use a provider limit too if required. [Model and pricing](https://platform.claude.com/docs/en/models/opus-4-8/overview).

Resume the same scoring directory only with identical inputs; successful calls are reused. An interrupted request may have been charged even when no response was saved. A saved attempt or unvalidated raw response blocks automatic repayment: inspect it and deliberately start a new campaign if a replacement call is needed. OS locks prevent concurrent scoring/watchers on the same directory and release after a crash; the empty lock file can remain.

## Stock preparation before the clock starts

Once exact hardware is configured, export for simulation/review without `--live`:

```bash
python -m hte.cli --config local_data/campaign.json export --design output/hte-round1-design.csv \
  --output output/hte-round1-review
```

After completing the bench checks, LC settings and measured timing, release the actual protocols into a separate folder:

```bash
python -m hte.cli --config local_data/campaign.json export \
  --design output/hte-round1-design.csv --output output/hte-round1 --live --stage dose_and_react
```

Verify the first-batch ligand coverage CSV, then print `stock_preparation.csv`, `deck_loads.csv`, `dosing.csv`, `round2_predose.csv`, `lc_sequence.csv` and `tip_budget.json`. **Use that campaign's generated quantities**, not the synthetic demo's quantities. `stock_preparation.csv` specifies total solution to prepare; `deck_loads.csv` specifies how much to place at each source for each protocol. The remaining prepared stock stays capped off deck. Source capacities are checked; large solvent reserves are not all loaded into a single well.

The stock planner includes first-round consumption, tip surplus, a conservative reserve for any ligand to be selected throughout round two, 50% extra usable stock and dead volume. Default dead volumes are 100 µL per 1.5 mL tube and 1,500 µL per reservoir channel. These are provisional aspiration allowances and need measurement with the actual source geometry. The second-round substrate is already included in first-round stock consumption. The ledger column `protocol_consumption_ul` reports consumption for the exported round, including any first-round predosing. Keep enough fresh tips/racks for the printed budget plus contingency; a source-dedicated reuse setting must be validated before physical execution.

| Stock | Concentration / solvent | Per pair well | Preparation basis |
|---|---|---|---|
| PyFluor + naphthalene | 1,000 mM SM + 10 mM IS in toluene | 25 µL, retained | 25 µmol SM + 0.250 µmol IS; prepare at least 5 mL |
| Each ligand | 20 mM in toluene | 75 µL each | 0.02 × molecular weight in mg/mL |
| Pd(COD)(DQ) | 40 mM in toluene | 75 µL | 15.152 mg/mL, MW 378.80 |
| Additional toluene | Stock solvents provide all toluene | 0 µL | SM stock + ligand stocks + Pd total 250 µL |
| Reference ligand L17 | Same 20 mM stock | 150 µL | Other ligand zero; 12 mol% total ligand |
| Workup reagent | 1:1 water/ACN, 1% v/v HCOOH, **without naphthalene** | 250 µL | IS was added with substrate |
| LC diluent | Same approved composition, **without naphthalene** | 180 µL | Add before the sample aliquot |

Bring solutions to their final volume after weighing. If the COA gives an applicable assay fraction, enter it in `stock_preparation.assay_fractions`, keyed by ligand ID, `Pd`, `substrate_stock` or `naphthalene`; weighed mass is then corrected by dividing by that fraction. Without a supplied fraction the code assumes 1.0. Check molecular weights against the actual bottle identity, including salts/adducts/solvates; a SMILES-derived weight is not a substitute for a COA.

The `substrate_stock` row reports PyFluor and naphthalene separately. Prepare at least 5 mL in a capped 10 mL glass/PTFE vial: nominally 805.80 mg SM + 1.00 mL of 50 mM naphthalene/toluene, toluene to 5.00 mL. The default source load is approximately 3.27 mL; use generated CSV quantities. Detailed recipes and separate calibration stocks are in [stock instructions](stocks-and-calibration.md).

Open ligands and prepare stocks in the glovebox. Label ID, name, CAS, concentration, solvent, assay correction, lot, preparation date, and rack position. Use suitably sealed compatible containers and return capped reserves to inert storage promptly after dispensing, preserving them after the hackathon. Pd(COD)(DQ) identity is distinct from Pd₂(dba)₃; verify the bottle and its purity. [Manufacturer identity](https://www.sigmaaldrich.com/GB/en/product/aldrich/938718).

**All stocks must be homogeneous at dispensing temperature.** The user reports SM soluble at 1 M in toluene; verify the combined SM/IS stock, 40 mM Pd and every 20 mM ligand separately. If a stock cannot be prepared, change its concentration and recompute volume balance through a reviewed change; the implementation uses a common ligand concentration. Stop for particles/bubbles. Repeated aspiration cannot establish the dissolved concentration or deliver a known dose.

## Deck and liquid locations

Left mount: p300 single GEN2 (proposed; confirm installation). Right mount: p300 eight-channel GEN2. The same setup is used in both rounds.

| OT-2 slot | Contents |
|---|---|
| 1 | Opentrons 24-position 1.5 mL tube rack; L01–L24 at exact CSV addresses |
| 2 | 12-well reservoir; A1 combined SM/naphthalene/toluene, A2 Pd/toluene, A3 neat toluene, A4/A6 workup without IS, A5/A7 LC diluent without IS |
| 3 | Open reaction block for dispensing/sampling; returns here for off-module cooling |
| 4 | Second 24-position tube rack; L25–L31 at exact CSV addresses |
| 5 | p300 single-channel tip rack |
| 6 | First dosing protocol: second-round substrate array; workup protocols: LC plate |
| 7 | Empty |
| 8 | p300 tip rack |
| 9 | p300 tip rack |
| 10 | Heater-shaker with validated standalone adapter |
| 11 | Empty |

Load only the reagents used in that stage, according to `deck_loads.csv`. Source addresses do not change between stages. The tube rack is the library `opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap`; reservoir is `nest_12_reservoir_15ml`; substitute actual brands only with verified definitions. Remove tube caps for dosing and recap afterward. Do not place uncovered solvent stocks next to the hot block for four hours; remove/cap sources once dosing is finished at the appropriate paused stage.

Slots 7 and 11 remain empty because adjacent eight-channel access is restricted. Slot 8 is a tip rack, which is the documented exception immediately in front of the heater-shaker. All block transfers are manual through `move_labware(..., use_gripper=False)` prompts. Do not add a gripper command on OT-2. [Heater-shaker restrictions](https://docs.opentrons.com/python-api/modules/heater-shaker/), [manual moves](https://docs.opentrons.com/python-api/moving-labware/).

## Pipetting method and tip economy

Full columns use eight channels for 25 µL SM/IS, 75 µL Pd, 250 µL workup, 180 µL diluent and 20 µL samples. Ligands and partial columns use the proposed p300 single; pair ligand doses are 75 µL each, reference 150 µL. No neat toluene is added. If p20 single is retained, explicitly configure `robot.single` and remeasure split-transfer timing. This array is a simulation/planning profile; 24-vial geometry requires revision. Workup uses A4/A6 and diluent A5/A7; loads stay below 11.9 mL with 1.5 mL dead volume.

The initial recipe uses two source prewet cycles, slow aspiration, 0.5-second delays, a 2 µL air gap and 1 µL retained reverse-pipetting surplus. Fresh stock tips prewet in their stock source before visiting any destination. Fresh analytical sample tips use the separate same-well conditioning sequence below. Reused stock tips do not return the retained surplus to the source. Volume planning includes surplus losses. No blowout into the destination is used, because that would deliver an uncontrolled surplus.

`reuse_tips: true` means one tip can serve consecutive transfers of the **same stock** during the same stage, dispensing above the destination without touching it. No tips move between different ligands/stocks. Sample-transfer tips are never reused between samples. This requires a measured contamination and delivery check; disable reuse if contact, splash, droplet carryover or unreliable noncontact delivery occurs. The live exporter checks the validation setting. If reuse is disabled, additional tip-rack replacement prompts are expected; replace all racks for that pipette with fresh racks in their original slots, then resume.

Toluene air-displacement delivery may drip or lose volume. Validate speeds, prewetting and air-gap/reverse pipetting in the actual geometry. Check volume with a calibrated method accounting for evaporation during weighing. Cap reserves, minimize open time and monitor first transfers. Pause for bubbles or insufficient immersion; reaspiration does not restore a known dose.

Protect the toluene stock concentration between initial dosing and round-two predosing using validated source covers. Remove covers before aspiration. Cap every 25 µL round-two predose promptly and validate retained solvent volume/storage time. If solvent has been lost, record the problem and prepare a documented fresh predose; a remaining volume does not establish concentration. Preserve sample IDs and regenerate affected records.

The code aspirates at `bottom(1.5 mm)` and dispenses at `top(+2 mm)`, so it never intentionally touches the bottom or recipient liquid. **These are starting heights for bench validation.** Confirm bottom clearance and adequate immersion at the lowest source volume, particularly in a actual 500 µL glass extract. Check position offsets and vial seating. If a positive bottom clearance leaves the tip above the meniscus, change the validated height/source volume/geometry; do not set a negative clearance. Use a larger allowance if reservoir depletion exposes any of eight tips. The App's simulated liquid level is not proof of actual immersion.

## During the clock: operator sequence

1. Start the timer with first-round dosing, after stocks, preselection, code installation and hardware/analytical validation are complete. Import only the live `round1/dose_and_react.py` with its matching CSVs into the local OT-2 App. Confirm offsets, sources and deck.
2. Dose **25 µL of combined 1 M SM/10 mM naphthalene in toluene** into the 60 first-round wells in slot 3. Retain the solvent and proceed directly to catalyst dosing.
3. Add **75 µL each 20 mM ligand + 75 µL 40 mM Pd** per pair; reference **150 µL L17 + 75 µL Pd**. The retained SM stock completes 250 µL. Seal and move to slot 10; run 95 °C / 500 rpm. The four-hour hold starts after the module setpoint and validated thermal equilibration.
4. During round one, predose **25 µL SM/IS/toluene into ten round-two wells** in slot 6 without ligand choices. Cap promptly at the pause and store under the approved conditions. Resume promptly; predosing/pause time is part of the hold. Retain all stock solvent and preserve the manifest mapping.
5. In parallel, prepare and run authentic-standard/calibration solutions on LC. Use the standards already purchased; never spike the authentic SM/product standards into reaction wells. Record retention references, area response and naphthalene response. Complete calibration before first-round samples reach the autosampler. Cap/remove dosing sources without altering required labware positions during active motion.
6. At the end of the hold, heating/shaking deactivate. Follow the validated thermal-handling SOP at the manual move prompt to transfer the sealed block off the heater to slot 3 and cool. Keep sealed until the validated opening temperature. If HTE's handling SOP requires white module status first, wait for it. Do not improvise hot-block handling to rescue the deadline.
7. Load the exact LC plate into slot 6 and start the separately released first-round workup protocol with the cooled block in slot 3. Open under HTE's SOP. Add 250 µL workup solvent **without extra naphthalene**; manually move to the heater-shaker, shake 2 minutes without heating, and return to slot 3.
8. Confirm the validated homogeneous extract. Add 180 µL LC diluent to the mapped LC wells, then transfer 20 µL extract from the corresponding reaction wells. Seal and shake the LC plate for 2 minutes with HTE's validated plate/adapter method, then submit using `lc_sequence.csv`. The final LC-plate mixing is an operator step; do not assume the reaction block's adapter works with the LC plate.
9. Run all 60 injections. After the complete export is available, normalize it and publish its completion manifest as described below. The local watcher computes yields, checks QC, performs five fresh LLM scoring calls using all valid first-round data, and creates `next_design.csv` and `next_dosing.csv` for ten untested pairs.
10. Verify the ten capped predoses retain 25 µL stock containing 25 µmol SM plus 0.250 µmol naphthalene. Refill sources from capped reserves using second-round deck loads. The released protocol adds zero new SM/IS and counts the retained stock solvent: catalysts add 225 µL. Assemble, seal, react four hours, then repeat cooling/workup/dilution/mixing.
11. Run the final ten injections and quantify them. Stop the competition clock when those analyses are complete, as agreed. Save protocols, Opentrons JSON logs, all LC/calibration files, raw model responses and actual timestamps.

HTEL lists plate shakers among its equipment, but confirm which device and settings are available for the last LC-plate mix. If only the OT-2 heater-shaker is used, a validated LC adapter/plate swap must be added to the local operator procedure and its time counted. [HTEL equipment](https://www.chem.uzh.ch/en/research/services/htel/Equipment.html).

## Extraction and analytical calibration

**The requested toluene + aqueous ACN workup may be biphasic.** A fixed aliquot from one phase is not a known fraction of total product, and vigorous shaking does not guarantee a homogeneous sample. Before the campaign, HTE must demonstrate a homogeneous sampling matrix with known recovery for substrate/product/IS, or establish and document a quantitatively validated extraction alternative and update the configured volumes. Until then `homogeneous_sampling_validated` remains false. Visible solids or two phases stop sampling. Also verify analyte stability in the acidic workup and autosampler hold.

### Representative aliquots and gentle liquid handling

Use this sequence for both rounds. Parameters below are proposed starting settings, not measured accuracy claims. Release them through the existing solvent-pipetting and homogeneous-sampling bench checks.

| Action | Analytical handling rule |
|---|---|
| Cool and homogenize | Keep reactions sealed through cooling. After workup, use the validated two-minute mixing procedure and a consistent mixing-to-sampling interval. Remix under the approved method if delayed. A clear upper layer is not proof of quantitative recovery. |
| Condition each fresh sample tip | Before visiting the LC well, aspirate and return the transfer volume plus the planned surplus **twice into the same reaction well**, below the surface at the validated positive clearance. Each channel returns to its own well. No air gap or blowout during these cycles; allow liquid to settle. This conditions the tip; it does not validate an emulsion or dissolve solids. |
| Aspirate the aliquot | Hold the tip vertical, below the meniscus and above the bottom. Check immersion at the lowest remaining volume for every channel. Aspirate slowly, pause while immersed, then form the small air gap above liquid at a slow rate. A travel air gap is intentional; bubbles inside the measured liquid slug are a fault. |
| Dispense the aliquot | Add LC diluent first, then the measured extract, using the released noncontact position close to the well opening. Pause for droplet delivery. Discard the retained surplus with the sample tip; never blow it into the LC well. Never touch an LC well and return that tip to the reaction or solvent reservoir. |
| Mix and prepare for injection | Seal and shake the LC plate for two minutes. Let bubbles clear for a validated, consistent interval; inspect for precipitation. Filtration, centrifugation or taking only supernatant requires validated analyte/IS recovery. Confirm autosampler needle height and enough liquid for the injection, draw losses and any authorized repeats. Keep samples sealed at the validated hold temperature/time. |
| Recover an uncertain transfer | Quarantine that LC well. Use a new tip and fresh LC destination with the complete correct diluent load and a new aliquot of the rehomogenized extract, provided sufficient extract remains. Preserve the failed preparation and its record. Never guess a top-up volume, add more IS, or restart the full workup to repair one well. |

Sample settings are `sample_prewet_cycles=2`, `sample_aspirate_height_mm=1.5`, `sample_flow_rate_multiplier=0.5`, `sample_air_gap_rate=0.1` and `sample_pause_seconds=1`. Both proposed p300 pipettes start at 7.5/15 µL/s sample aspirate/dispense; air-gap aspiration uses one tenth of the liquid aspiration flow. Returns during prewetting stay in the original sample well. Account for discarded surplus. Revalidate and update measured workup timing after changing settings.

Before the clock, challenge the complete extraction/dilution with known low/mid/high analyte amounts in the actual matrix. Compare independently prepared reference dilutions and repeated preparations, including all eight channels and near-depleted source conditions; record bias, variability and analyte/IS recovery against HTE's method criteria. The 20 µL transfer is small relative to the p300 capacity: validate it specifically. If inadequate, revise the aliquot/dilution or use a reviewed p20 sampling plan and account for its time/tips. IS ratios can compensate for common injection/dilution variation but cannot prove selective analyte recovery, IS survival or absence of coelution.

Prewetting, delays and air-gap settings need solvent-specific validation; reverse pipetting is not inherently more accurate for volatile liquids. [Opentrons volatile-liquid study](https://insights.opentrons.com/hubfs/Applications/General%20liquid%20handling/Volatile%20Liquid%20Handling%20App%20Note.pdf), [API liquid-handling commands](https://docs.opentrons.com/python-api/building-block-commands/). Thermo identifies low sample volume, incorrect needle height and trapped air as causes of poor area precision. [Vanquish troubleshooting](https://knowledge1.thermofisher.com/Chromatography/Liquid_Chromatography/LC_Knowledge/Peak_Area_Precision).

The proposed 20 µL + 180 µL dilution is tenfold from a nominal 500 µL homogeneous extract. At 100% yield, final product is 5 mM; final naphthalene is 50 µM. This helps eight-channel throughput but may be too concentrated for the chosen LC/MS response or injected toluene content. HTE must validate separation, injection solvent, calibration range and absence of detector saturation/ion suppression. It is not a finalized LC dilution solely because it fits a plate.

If 5 µL + 195 µL is required, set those volumes and regenerate all files. It is a fortyfold dilution and requires `robot.single = "p20_single_gen2"` plus renewed setup/handling validation. The preloaded 0.250 µmol naphthalene now gives 12.5 µM final IS; update `internal_standard_final_uM` and prepare standards at that concentration. The code rejects inconsistent IS concentrations. Change aliquot/dilution only before the complete campaign is frozen, or explicitly record a new validated configuration with calibration matching the actual samples.

Prepare authentic substrate/product calibration stocks in an LC-compatible solvent at measured concentrations; weigh with COA corrections. A proposed 100 mM stock is 16.116 mg/mL PyFluor or approximately 9.709 mg/mL 2-fluoropyridine, subject to solubility/stability verification. Stocks can be prepared before the clock; working standards and injections can be prepared during the first hold. Naphthalene needs a detector where its response is reliable.

Use five nonzero fitted levels of each analyte: 100, 500, 1,000, 2,500 and 6,000 µM, each with **fixed 50 µM naphthalene**, plus an IS-containing zero-analyte blank. Add an independently prepared 5,000 µM check excluded from the fit. Match the validated final sample solvent/matrix and IS concentration, including the solvent introduced by the analytical stocks. Use the lower working-stock concentration for the lowest levels. The [preparation table](stocks-and-calibration.md) avoids sub-microliter transfers. Standards above the validated linear range require a revised dilution, not extrapolation.

The default 14-injection sequence contains five nonzero levels, a zero-analyte blank and an independent check for each of SM and product. The single-analyte series and IS-containing blanks also provide retention identity references, subject to LC/MS confirmation. All 14 are scheduled during the first four-hour hold. In `calibration_template.csv`, rows marked `calibration` enter the fit and rows marked `check` are assessed independently, with a provisional ±15% relative concentration tolerance. Any additional identity, blank or repeat injections must be added to the timing configuration.

Validate naphthalene recovery through capped predose storage, sealed heating and extraction, plus chemical compatibility. IS loss can inflate yield ratios; no unmeasured correction is applied. Live export requires `pre_reaction_internal_standard_validated`. See [stock instructions](stocks-and-calibration.md).

For each analyte fit `area_analyte / area_IS = slope × final_concentration_µM + intercept`. Substrate and product have separate response factors. Do not use area%, TIC% or an uncalibrated MS area as yield. The current campaign requires five distinct nonzero concentrations, a measured zero-analyte blank and at least one independent check per analyte, positive slopes and the configured fit threshold. R² ≥0.995 is a software gate, not complete method validation; verify accuracy, precision, blanks, LOQ, recovery and linearity with HTE. Set measured LOQs and nonoverlapping retention windows from authentic standards. MS confirmation must support the assigned analyte peak, especially if a short method coelutes other components.

If HTE's complete integrated peak list omits nondetected analytes, set `missing_analyte_policy` to `censor` **only after verifying that export behavior**. A valid IS and completed injection/export are required. The reader then reports `yield_upper_bound_percent`, not zero; below-LOQ detected peaks are also represented as bounds. The default is `reject` because a missing row could mean a bad export. Multiple peaks in the reference window, absent/invalid IS, inconsistent method, out-of-range calibration or implausible mass balance are QC failures. Invalid numerical results are removed before LLM feedback. With the current zero-tolerance batch QC setting, resolve a failed measurement/export before the loop proceeds; reaction failure itself is valid data when analytically measured.

### Repeat injections and repeat preparations

A second injection from the same LC well checks injection/integration repeatability; a new independent dilution from the reaction extract checks sample preparation. Neither is a repeat reaction. During pre-campaign validation, check needle-wash effectiveness and inject a matrix blank after a high standard to measure carryover. Use HTE-approved criteria for area-ratio agreement, recovery and blank response. Configure the actual wash/needle settings; do not copy settings from another autosampler. [Thermo carryover guidance](https://knowledge1.thermofisher.com/Mass_Spectrometry/Mass_Spectrometry_Knowledge/Carryover_and_Contamination).

During the competition, remeasure only when QC or a documented instrument/transfer fault requires it. Record the original and replacement IDs, reason, injection order, dilution and acceptance decision. Retain all raw results; choose the valid record by the predefined QC rule, never by highest yield. The quantitative export must contain one accepted result per original reaction sample ID; the current reader rejects duplicate/ambiguous peaks and does not average replicates automatically. Review discrepancies before publishing a completion marker. Every added injection costs its measured full cycle, 1.7 minutes in the requested scenario, plus any cycle overhead, and belongs in the timing plan; these checks are not silently added to the 14-standard or 70-sample sequence.

## Export contract and automatic second-round decision

Set `analytics.method_id`, `channel`, `references`, `quantification_limit_uM`, `column_mapping` and, for XLSX, `export_sheet` to actual HTE values. `references` must have `substrate`, `product` and `internal_standard`, each with `retention_time_min` and `window_min`. Do not fill these from the demo. The software/instrument public listings are descriptive provenance, not active method identifiers.

Example mapping structure, with placeholders replaced by exact Chromeleon export headers:

```json
{
  "sample_id": "EXACT_SAMPLE_HEADER",
  "retention_time_min": "EXACT_RT_HEADER",
  "area": "EXACT_AREA_HEADER",
  "channel": "EXACT_CHANNEL_HEADER",
  "method_id": "EXACT_METHOD_HEADER"
}
```

For the supplied Chromeleon wide CSV, use [the HTEL import instructions](htel-lc-import.md). Set the actual method ID and selected `UV_VIS_1`..`UV_VIS_4` channel, and supply `--injections` with an explicit injection-number map. The export's peak-detection channel does not choose the quantitative wavelength. Blank placeholder rows are omitted, measured zero is preserved, and incomplete peak counts receive QC flags. Do not use old example standards as campaign calibration.

The normalized CSV has one row per peak: `sample_id,retention_time_min,area,channel,method_id,qc_flag`. Retention times are minutes. `sample_id` must exactly match `R1-001` etc. from `lc_sequence.csv`; retain full peak lists on the selected quantitative channel. Other channels are ignored, never summed. Per-channel spreadsheets that omit channel/method columns need those columns added from verified acquisition metadata before normalization. The selected channel must not change between calibration and samples.

`calibration.csv` follows `hte_inputs/calibration_template.csv`: sample ID, role (`calibration` or `check`), authentic analyte label (`substrate` or `product`), final concentration, its integrated area, IS area, final IS concentration, method and channel. The two analytes may come from the same validated mixed-standard injection; include a row for each and update the injection count. Use the supplied template with explicit roles; a legacy CSV without independent `check` rows fails the calibration gate.

Prepare the watcher before first-round LC finishes:

```bash
python -m hte.cli --config local_data/campaign.json watch --inbox output/hte-lc-inbox \
  --dosing output/hte-round1/dosing.csv --calibration output/hte-calibration.csv \
  --output output/hte-iteration
```

After all 60 injections have finished, run from a second terminal (or a verified Chromeleon post-sequence hook):

```bash
python -m hte.cli --config local_data/campaign.json normalize path/to/complete_vendor_export.csv \
  --injections local_data/round1-injections.csv --output output/hte-lc-inbox/round1.csv
python -m hte.cli --config local_data/campaign.json \
  complete-export --peaks output/hte-lc-inbox/round1.csv \
  --dosing output/hte-round1/dosing.csv \
  --output output/hte-lc-inbox/round1.ready.json
```

The `complete-export` command is an operator attestation that every expected injection has finished. A stable CSV alone does not establish sequence completion. If the export is already normalized, place it directly at `round1.csv`, then publish the manifest. The manifest verifies expected sample IDs, method and SHA256 file hashes. The watcher responds only to `*.ready.json` with a matching CSV; partial, mismatched or changed exports cannot trigger a valid batch. Input hashes are checked before and after ingestion, and the completed iteration hashes its analysis, scoring and handoff files. Publishing the same event twice does not repeat paid calls; changed inputs or archived outputs are rejected. Failed events are recorded once; correct the data/configuration and publish a corrected event instead of repeatedly charging requests.

Restart the watcher after changing its configuration, inventory or evidence, because those inputs are loaded when it starts. Calibration/export files are read for the event. Set the API key before starting the watcher.

The output directory is printed as `output/hte-iteration/iteration-...`. Inspect `analysis/results.csv`, `analysis/qc_report.json`, `scoring/ranking.csv`, `next_design.csv` and `next_dosing.csv`. The second round uses only LLM mean-score ranking of the 376 untested pairs, incorporating first-round calibrated observations and the single reference. It does not use an exploratory split or GoLLuM acquisition.

Live protocols are generated automatically when the bench validations, analytical settings and measured timing pass the release checks; otherwise the next dosing CSV is still produced for review. Explicit export uses:

```bash
python -m hte.cli --config local_data/campaign.json \
  export --design output/hte-iteration/iteration-REPLACE/next_design.csv \
  --history output/hte-round1/dosing.csv \
  --output output/hte-round2 --live
```

For round two, `--history` must point to the actual first-round dosing file; repeated pairs or edited dose amounts stop export. Use a new output directory each time, including after a partial export, to preserve earlier files. Validate the local App analysis and compare sample IDs, wells, substrate predose and stock loads before running. The watcher does not start the robot or upload protocols remotely.

For final second-round results, normalize/publish a manifest in the same way, then:

```bash
python -m hte.cli --config local_data/campaign.json analyze --dosing output/hte-round2/dosing.csv \
  --peaks output/hte-round2-peaks.csv --ready output/hte-round2-peaks.ready.json \
  --calibration output/hte-calibration.csv --output output/hte-final-analysis
```

## Optional MOCCA integration

HTE's standard integrated peak exports are the default analytics path. MOCCA2 is available when **raw HPLC-DAD time × wavelength data** can be exported, with authentic standards processed through the same pipeline. It does not reconstruct chromatograms from peak-area CSVs and does not process ISQ MS spectra. Native Chromeleon raw data are not assumed to match MOCCA's parsers. Provide a supported raw export or a verified conversion to the time/wavelength matrix format used by the tested adapter. [MOCCA2 documentation](https://bayer-group.github.io/MOCCA/).

`mocca_manifest_template.json` maps raw paths to sample IDs. For a ChemStation-style matrix CSV, the first row is wavelengths in nm, first column is time in minutes, remaining cells are detector responses, and encoding is UTF-16. Paths are relative to the manifest. The included settings are a starting template, not a validated method:

```bash
python -m hte.cli mocca --manifest path/to/raw_manifest.json \
  --settings hte_inputs/mocca_settings.json --output output/hte-mocca
```

This calls actual MOCCA baseline correction, peak detection and Fraser–Suzuki deconvolution, reports physical time integrals at the selected wavelength, and marks unresolved peaks as QC failures. Test cases use synthetic raw DAD data. Calibration areas must be generated with exactly the same preprocessing/units, not copied from Chromeleon if their integration definitions differ. Confirm the required detector channel matches the adapter's emitted name, e.g. `MOCCA_DAD_254nm`.


## Timing and validation record

At the requested **1.7-minute full cycle**, 70 reaction injections take **119 minutes**. Fourteen calibration injections take 23.8 minutes and run during the first hold, together with capped round-two substrate predosing.

Provisional overheads: dosing 30 min, heating 12, cooling 12, workup 20, decision 8 and other 5; **no evaporation**, **87 min** total. Two four-hour holds plus LC give **686 min / 11 h 26 min**, leaving **34 min**. Measure the full injection cycle and larger-scale operations; a serial 3-minute method gives 777 min. Keep both four-hour holds. See [timing and deadlines](organizer-updates.md).

`python -m hte.cli check` reports timing and pending bench fields. Live release requires confirmed chemistry, block/adapter/seal, pipetting, heating, capped predose storage, homogeneous sampling, IS compatibility, App simulation, full LC cycle and simultaneous heating; noncontact tip reuse when enabled. Workup/round two also require calibrated analytical settings, RT windows and LOQs. These flags record completed work; changing a Boolean is not validation. Reassess affected checks after changing labware, solvent, stocks, dilution or heights.

Keep a campaign folder containing inventory/COAs, configuration, embedding provenance, all scoring responses, designs, dosing/deck/stock CSVs, exact labware JSONs, App analysis and Opentrons JSON logs, standards/LC exports/raw data, QC reports and actual timestamps. The offline demo and tests establish software behavior; they cannot establish chemical success or a 12-hour physical run.
