# Local OT-2 dual-ligand fluorination: operator runbook

This package screens 65 distinct ligand pairs plus one tBuBrettPhos reference, then 10 new pairs. It converts completed LC peak exports into calibrated yields, sends those results to five repeated Claude scoring calls, and generates the next dosing CSV. Robot operation stays local through the Opentrons OT-2 App. A workstation with permitted internet access makes the Anthropic calls; the robot never needs internet or remote control.

**Software verification is separate from bench readiness.** The provided demo is synthetic and its protocols refuse physical execution. The real campaign still needs an exact glass-block definition and mounting/seal validation, solvent delivery checks, a homogeneous extraction, and the HTEL analytical method. The real first-round selection must be generated with the operator's Claude key; no synthetic ranking should be used for chemistry.

## Fixed experiment and interpretation

| Item | Approved campaign setting |
|---|---|
| Substrate | Pyridine-2-sulfonyl fluoride / PyFluor, `FS(C1=NC=CC=C1)(=O)=O` |
| Product standard | 2-Fluoropyridine, `FC1=NC=CC=C1` |
| Amount / concentration | 5 µmol / 0.1 M in 50 µL final toluene solution |
| Pair ligands | 0.30 µmol each, 6 mol% each; loading counts ligand molecules |
| Pd | 0.60 µmol Pd(COD)(DQ), 12 mol%; one Pd per complex |
| Reference | L17 tBuBrettPhos, 0.60 µmol / 12 mol% total ligand; same Pd and conditions |
| Temperature / hold | 95 °C / 240 minutes after the module reaches the setpoint |
| Atmosphere | Reaction assembly under air; ligand stocks prepared/stored in glovebox |
| Additional reagents | No base, additive, or external fluoride source |
| Round 1 | 65 pairs + 1 reference = 66 wells |
| Round 2 | 10 untested pairs; no reaction repeats or additional controls |
| Objective | Calibrated product yield; conversion is diagnostic |

The reference is a fair, resource-efficient comparison against a good single ligand at the same temperature, total ligand loading and Pd loading. An improvement over this reference supports a better mixture under these conditions. It does not prove synergy relative to both individual partners, reproducibility, or a broader substrate scope. Those claims require subsequent partner controls, repeats and scope experiments. Score SD measures disagreement among model calls, not experimental error.

The supplied Chemical Science SI Table S2, p. S35, contains 18 single-ligand yields for this substrate. These are captured in `hte_inputs/literature.json`, including tBuBrettPhos 77%, AdBrettPhos 78%, MorDalPhos 77%, Me4tBuXPhos 72%, RockPhos 63% and Me3OMe-tBuXPhos 61%. They are high-temperature qualitative priors, not 95 °C measurements. The SI's air example uses a different Pd source at 150 °C. Do not merge these data with the main-text ligand table or train a 95 °C pair surrogate on them. [Paper and SI](https://pubs.rsc.org/en/content/articlehtml/2025/sc/d5sc00912j).

The thesis benchmark motivates repeated mechanism-informed scoring, but its dual-ligand benchmark is decarbonylative Suzuki coupling. Ligand relay in the fluorination remains a hypothesis. The Nature multicatalysis paper is contextual inspiration rather than this campaign's measured training data. [Nature paper](https://www.nature.com/articles/s41586-025-09813-2).

## Before the competition: resolve hardware and analytics

Use the [HTE configuration checklist](hte-questions.md) to obtain the remaining facts. The [start-here guide](start-here.md) explains responsibilities and hidden API-key entry; [rehearsal results](rehearsal-results.md) document the fake feedback loop. Record confirmed facts in a campaign-specific copy of `hte_inputs/campaign.json`. Keep that copy, inventory, calibration, protocol exports and run logs together.

HTEL publicly lists a Thermo Vanquish Horizon Duo with ISQ-EM, tandem column operation, and a DAD detector. UZH's Chromeleon page lists `LC-ISQ-HTL-01`. The exact two-minute method, quantification wavelength, retention times, injection volume and export headers are not public. Prefer a validated DAD calibration for yield and use MS to confirm peak identity. Naphthalene may be unsuitable for HESI quantification: do not assume an MS internal-standard signal. [HTEL equipment](https://www.chem.uzh.ch/en/research/services/htel/Equipment.html), [Chromeleon instruments](https://www.chem.uzh.ch/en/research/services/massspec/Open-access_LC-and_GC-MS_with_Chromeleon.html).

If a measured thermal lag requires additional equilibration after the module reaches 95 °C, set `chemistry.thermal_equilibration_minutes` to that validated time. The generator adds it before starting the 240-minute hold. Include both rounds' extra equilibration in the measured heating-overhead estimate. The initial zero is an unresolved bench placeholder, not proof of instant equilibration.

A plausible glass option is the [Para-Dox Gen II 96-position parallel-synthesis block 104960](https://www.analytical-sales.com/product/standard-96-position-parallel-synthesis-reaction-block-gen-ii/) with 8 × 30 mm, 1 mL glass inserts, preferably the manufacturer's assembled tray 884001. Its drawing gives 127.8 × 85.5 mm, 9 mm pitch, and approximately 46.2 mm assembled height. The footprint matches ordinary microplates; this alone does not establish heater-shaker compatibility. [Block drawing](https://www.analytical-sales.com/drawings/104960_rev1c_PUBLIC.pdf), [regular microplate dimensions](https://www.corning.com/catalog/cls/documents/drawings/LSR00181.pdf).

HTE must check the complete block on the supplied universal flat adapter: latch engagement, closed lid/bolt clearance, mass during shaking, stable contact, vial seating, thermal performance and sealing with toluene at 95 °C. A module setpoint does not prove a large aluminum block's liquids are at that temperature. Validate the thermal lag with a representative filled vial and include the resulting procedure in the hold timing. The 1 mL vial allows the 100 µL post-quench volume, but 50 µL is shallow; aspiration immersion needs particular attention.

Use a combined block-plus-vial custom Opentrons JSON with measured **open-block** height, well opening diameter, depth, vial-bottom Z and A1 position. Do not substitute a PCR definition for glass. The manufacturer's drawing does not establish all internal vial dimensions or measured deck offsets. Set `reaction_definition_path` to that JSON, `reaction_labware` to null, and the true working volume. If a custom adapter is needed, the supplied adapter loading code must be reviewed for that adapter before use. A block that cannot be latched securely cannot be shaken by this protocol. For custom labware, contact johannes.schoergenhumer@chem.uzh.ch.

The well coordinates describe the open vials, but travel clearance must also account for the sealed block's maximum height. HTE must check both states; the model cannot treat a removed lid as proof of clearance while a sealed block is on the heater.

Follow the manufacturer's PFA-film/rubber-mat stack and cross-pattern sealing instructions, including the specified torque for the exact reactor. Validate solvent loss for a four-hour hold and gas/pressure compatibility: this reaction releases SO₂. Recheck after cooling before opening. Ordinary plate seals are not evidence of a suitable reaction seal. [Assembly instructions](https://www.analytical-sales.com/manuals/GenII_reactor_block_instructions_web.pdf).

Two reaction vial arrays are required because round two is predosed while round one reacts. Only one heater is required. HTE should confirm whether a second assembled block or a compatible removable vial tray can be used for ambient evaporation and later returned to the validated reaction block without changing well mapping.

For the LC plate, use the appropriate library definition for HTE's PP plate, substituting the exact brand/geometry as necessary. `nest_96_wellplate_2ml_deep` is a representative placeholder, not an instruction to use a 2 mL plate. A validated 200 µL working-volume PP plate may be more economical, provided its actual working volume, mixing, autosampler access, seal and needle-height requirements are satisfied. Avoid PS for this solvent-containing workflow unless HTE has verified compatibility.

## Install and rehearse locally

Use Python 3.12 on the operator workstation, not the robot's internal Python. From the package root:

```bash
python3.12 -m venv .hte-venv
source .hte-venv/bin/activate
python -m pip install -e '.[sources,test,analytics,embeddings]'
# Optional measured-prior GoLLuM variant; not needed for this two-round plan:
python -m pip install -r requirements-gollum.txt
python -m pytest -q tests/hte
python -m hte.cli demo --output output/hte-rehearsal
```

`requirements-hte-tested.txt` pins the principal versions used here; for the same principal package versions, install it before `python -m pip install -e .`. It is a tested version list, not a complete lock of all transitive dependencies.

The demo supplies a synthetic LC method and a library PCR plate only for software simulation. It has 66 first-round and 10 second-round samples, valid nondetection bounds, no repeated pairs, and no second substrate dose. Never use its selections, calibration or labware as real experimental inputs.

Simulate each of its four Python files with the pinned OT-2-capable package:

```bash
python -m opentrons.simulate output/hte-rehearsal/round1/dose_and_react.py
python -m opentrons.simulate output/hte-rehearsal/round1/workup.py
python -m opentrons.simulate output/hte-rehearsal/round2/dose_and_react.py
python -m opentrons.simulate output/hte-rehearsal/round2/workup.py
```

Opentrons 8.8.2 is pinned for workstation tests because the installed 9.1.2 simulator rejected OT-2 protocols. Protocol files use API 2.18. HTE must also analyze them in its actual local OT-2 App/robot software, confirm the version supports this API, and perform Labware Position Checks. Simulation checks command compatibility and deck restrictions, not glass fit, organic-solvent volume accuracy, dryness, phase behavior or temperature in the liquid.

Do a measured rehearsal of both dosing/workup stages with the final hardware and liquids or appropriate validated surrogates. Record real heating/cooling, manual handling and injection-cycle times. Test Claude model access and a scoring campaign before the competition. Do not discover a quota or schema issue during the second-round decision.

## Inventory, embeddings and first-round selection

`hte_inputs/ligands.csv` contains all 31 workbook ligands, source locations and molecular weights. The original workbook remains unchanged. Two user-authorized corrections are recorded in the CSV: L11 now contains the methoxy oxygen; L27 is tris(3-chlorophenyl)phosphine. Commercial Me3(OMe)tBuXPhos can be a regioisomer mixture; preserve the actual supplier/lot identity rather than claiming a pure regioisomer from one representative SMILES. [Original ligand study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3387921/).

There are 465 unordered distinct pairs. The included `hte_inputs/pair_embeddings_t5-base.npz` contains real, frozen T5-base text embeddings, 768 dimensions per pair. Both ligand orders are encoded and averaged. Provenance and model revision are saved beside it. This uses names, structures and the fixed reaction context, without manually calculated steric/electronic descriptors. It is inspired by the language-model representation approach in [GoLLuM](https://github.com/schwallergroup/gollum), and is not a trained GoLLuM yield model. Rebuild after changing ligand identities/names or inventory metadata:

```bash
python -m hte.cli embeddings --model google-t5/t5-base --download \
  --output output/hte-embeddings/rebuilt.npz
```

With no measured pair data, first-round exploration uses distance from previously selected LM embeddings. Each greedy choice combines Claude rank percentile and diversity rank percentile at 0.5/0.5, with a Claude percentile floor of 0.25. These are explicit tunable settings, not chemically calibrated probabilities. Every selected well uses both signals; there is no 32/33 split. `*.selection.csv` records the selection trace. Conditions are randomized across the occupied wells, in column-major order, to use full eight-well columns efficiently.

Store the Claude key in the local process environment using the workstation's approved secret mechanism. It must not appear in a protocol, CSV, notebook output, committed file or this handoff. The package reads `ANTHROPIC_API_KEY`; it does not automatically load `.env`.

On a macOS zsh terminal, a hidden interactive entry can set it for that terminal without typing the key into command history:

```zsh
read -rs 'ANTHROPIC_API_KEY?Claude API key: '
export ANTHROPIC_API_KEY
```

Run scoring or the watcher from that terminal. Use HTE's approved secret setup on other platforms.

```bash
python -m hte.cli score --output output/hte-round1-scoring
python -m hte.cli design --ranking output/hte-round1-scoring/ranking.csv \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output output/hte-round1-design.csv
```

Five calls independently score every pair after shuffled candidate ordering, using the mechanism, ligand structures and published single-ligand evidence. Structured output rejects incomplete, duplicate or nonnumeric scores. Raw responses, usage, hypotheses and repeated scores are retained. The protocol never changes temperature, loadings, solvent or the inventory based on an LLM suggestion.

[Prompt caching](prompt-caching.md) is enabled by default with a one-hour TTL in both rounds. Shared chemistry context and measured feedback are cached; shuffled candidate IDs remain outside the cached prefix. Stable schemas and a first scoring response before parallel followers preserve reuse. Each scoring directory contains `cache_summary.json` and response cost breakdowns; inspect the provider's read counters to verify live hits. Cache expiry across the reaction requires a fresh write in round two. The budget preflight includes the write premium and assumes no cache hits.

Claude Opus 4.8 is explicitly configured; the code checks access and never silently substitutes a model. At the verified $5/M input and $25/M output token prices, five requests each using the full 20,000-output-token allowance cost at most $2.50 for output, before input and retries. A $20 cap per campaign is therefore plausibly ample for the present prompts, but the code performs a token-count preflight, reserves one retry, and refuses a campaign whose estimated bound exceeds the cap. The two rounds have separate $20 caps; this is not a shared $20 project budget. A preflight is an estimate, not a provider-enforced spending limit; use a provider limit too if required. [Model and pricing](https://platform.claude.com/docs/en/models/opus-4-8/overview).

Resume the same scoring directory only with identical inputs; successful calls are reused. A saved response that failed validation is not automatically paid for again. Inspect it and deliberately start a new campaign if a replacement call is needed.

## Stock preparation before the clock starts

Once exact hardware is configured, export for simulation/review without `--live`:

```bash
python -m hte.cli export --design output/hte-round1-design.csv \
  --output output/hte-round1-review
```

Print `stock_preparation.csv`, `deck_loads.csv`, `dosing.csv`, `round2_predose.csv`, `lc_sequence.csv` and `tip_budget.json`. **Use that campaign's generated quantities**, not the synthetic demo's quantities. `stock_preparation.csv` specifies total solution to prepare; `deck_loads.csv` specifies how much to place at each source for each protocol. The remaining prepared stock stays capped off deck. Source capacities are checked; large solvent reserves are not all loaded into a single well.

The stock planner includes first-round consumption, tip surplus, a conservative reserve for any ligand to be selected throughout round two, 50% extra usable stock and dead volume. Default dead volumes are 100 µL per 1.5 mL tube and 1,000 µL per reservoir well. These are provisional aspiration allowances and need measurement with the actual source geometry. The second-round substrate is already included in first-round stock consumption. Keep enough fresh tips/racks for the printed budget plus contingency; a source-dedicated reuse setting must be validated before physical execution.

| Stock | Concentration / solvent | Per pair well | Preparation basis |
|---|---|---|---|
| PyFluor + naphthalene | 250 mM SM + 2.5 mM IS in DCM | 20 µL before evaporation | 5 µmol SM + 0.050 µmol IS; prepare at least 5 mL |
| Each ligand | 30 mM in toluene | 10 µL each | 0.03 × molecular weight in mg/mL |
| Pd(COD)(DQ) | 60 mM in toluene | 10 µL | 22.728 mg/mL, using MW 378.80 |
| Additional toluene | Neat | 20 µL | Final reaction solvent totals 50 µL |
| Reference ligand L17 | Same 30 mM stock | 20 µL | Other ligand volume zero |
| Workup reagent | 1:1 water/ACN, 1% v/v HCOOH, **without naphthalene** | 50 µL | IS was added with substrate |
| LC diluent | 1:1 water/ACN, 1% v/v HCOOH, **without naphthalene** | 180 µL | Add before the sample aliquot |

Bring solutions to their final volume after weighing. If the COA gives an applicable assay fraction, enter it in `stock_preparation.assay_fractions`, keyed by ligand ID, `Pd`, `substrate_DCM` or `naphthalene`; weighed mass is then corrected by dividing by that fraction. Without a supplied fraction the code assumes 1.0. Check molecular weights against the actual bottle identity, including salts/adducts/solvates; a SMILES-derived weight is not a substitute for a COA.

The `substrate_DCM` row reports PyFluor in `stock_mM`/`mass_mg` and the second solute in `naphthalene_stock_mM`/`naphthalene_mass_mg`. The `workup` row now reports zero naphthalene. Prepare the combined 5 mL stock in a capped 20 mL glass vial, using an accurately measured naphthalene master rather than directly weighing approximately 1.6 mg. Load the generated quantity into reservoir A1, approximately 2.54 mL with the default reuse plan, and retain the rest capped. The [combined-stock and calibration instructions](stocks-and-calibration.md) specify the recipe, containers, five analyte levels with fixed IS, and separate authentic/analytical stocks.

Open ligands and prepare stocks in the glovebox. Label ID, name, CAS, concentration, solvent, assay correction, lot, preparation date, and rack position. Use suitably sealed compatible containers and return capped reserves to inert storage promptly after dispensing, preserving them after the hackathon. Pd(COD)(DQ) identity is distinct from Pd₂(dba)₃; verify the bottle and its purity. [Manufacturer identity](https://www.sigmaaldrich.com/GB/en/product/aldrich/938718).

**All stocks must be homogeneous at dispensing temperature.** A proposed concentration is not a solubility measurement. Especially verify 60 mM Pd and every 30 mM ligand in toluene. If any stock cannot be prepared, change its concentration and recompute volumes through a reviewed code/configuration change; the current implementation uses one common ligand concentration. Do not pipette a suspension, aspirate repeatedly to force material through a tip, or add an unrecorded cosolvent. Particles and bubbles can cause unknown delivered concentrations. Stop, inspect, establish the actual dissolved concentration and regenerate the affected plan before proceeding.

## Deck and liquid locations

Left mount: p20 single GEN2. Right mount: p300 eight-channel GEN2. The same setup is used in both rounds.

| OT-2 slot | Contents |
|---|---|
| 1 | Opentrons 24-position 1.5 mL tube rack; L01–L24 at exact CSV addresses |
| 2 | 12-well reservoir; A1 combined SM/naphthalene/DCM, A2 Pd/toluene, A3 neat toluene, A4 workup solvent without IS, A5 LC diluent without IS |
| 3 | Open reaction block for dispensing/sampling; returns here for off-module cooling |
| 4 | Second 24-position tube rack; L25–L31 at exact CSV addresses |
| 5 | p20 tip rack |
| 6 | First dosing protocol: second-round substrate array; workup protocols: LC plate |
| 7 | Empty |
| 8 | p300 tip rack |
| 9 | p300 tip rack |
| 10 | Heater-shaker with validated standalone adapter |
| 11 | Empty |

Load only the reagents used in that stage, according to `deck_loads.csv`. Source addresses do not change between stages. The tube rack is the library `opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap`; reservoir is `nest_12_reservoir_15ml`; substitute actual brands only with verified definitions. Remove tube caps for dosing and recap afterward. Do not place uncovered solvent stocks next to the hot block for four hours; remove/cap sources once dosing is finished at the appropriate paused stage.

Slots 7 and 11 remain empty because adjacent eight-channel access is restricted. Slot 8 is a tip rack, which is the documented exception immediately in front of the heater-shaker. All block transfers are manual through `move_labware(..., use_gripper=False)` prompts. Do not add a gripper command on OT-2. [Heater-shaker restrictions](https://docs.opentrons.com/python-api/modules/heater-shaker/), [manual moves](https://docs.opentrons.com/python-api/moving-labware/).

## Pipetting method and tip economy

Full columns use eight channels for 20 µL substrate, 20 µL toluene, 50 µL workup, 180 µL dilution and 20 µL sample transfers. Ligand and 10 µL Pd transfers use p20 single; partial columns use it too. The 20 µL reference ligand transfer is split into two 10 µL portions to leave room for the air gap and surplus. Eight-channel sample tips remain fresh for each column; every channel stays with its own well.

The initial recipe uses two source prewet cycles, slow aspiration, 0.5-second delays, a 2 µL air gap and 1 µL retained reverse-pipetting surplus. Fresh tips prewet in the same stock source before visiting any destination. Reused stock tips do not return the retained surplus to the source. Volume planning includes surplus losses. No blowout into the destination is used, because that would deliver an uncontrolled surplus.

`reuse_tips: true` means one tip can serve consecutive transfers of the **same stock** during the same stage, dispensing above the destination without touching it. No tips move between different ligands/stocks. Sample-transfer tips are never reused between samples. This requires a measured contamination and delivery check; disable reuse if contact, splash, droplet carryover or unreliable noncontact delivery occurs. The live exporter checks the validation setting. If reuse is disabled, additional tip-rack replacement prompts are expected; replace all racks for that pipette with fresh racks in their original slots, then resume.

DCM and toluene are volatile and air-displacement delivery may drip or lose volume. Validate the programmed speeds, prewetting and air-gap/reverse-pipetting method using the actual solvents and source/destination geometry. Check gravimetrically or with another suitable calibrated method, allowing for evaporation during weighing. Cap bulk reserves, minimize open-source time, and monitor the first transfers from each source. Visible bubbles or a liquid level too low for immersion require a pause and correction; repeating an aspiration does not restore a known dose.

Preserve the DCM stock concentration through first-round drying/assembly/heating: use validated individual source covers for unused reservoir wells, or HTE's equivalent handling procedure. The protocol pauses before dry-down and again before second-round predosing to check covers and source accessibility. Never leave a reservoir cover in a pipetting path; remove it before resuming aspiration. If concentration has changed through evaporation, a remaining liquid volume does not establish the stock concentration. Use a verified fresh aliquot from the preprepared reserve and record the refill; include sufficient reserve for that procedure in the stock-preparation calculation.

The code aspirates at `bottom(1 mm)` and dispenses at `top(+2 mm)`, so it never intentionally touches the bottom or recipient liquid. **These are starting heights for bench validation.** Confirm bottom clearance and adequate immersion at the lowest source volume, particularly in a shallow 100 µL glass extract. Check position offsets and vial seating. If a positive bottom clearance leaves the tip above the meniscus, change the validated height/source volume/geometry; do not set a negative clearance. Use a larger allowance if reservoir depletion exposes any of eight tips. The App's simulated liquid level is not proof of actual immersion.

## During the clock: operator sequence

1. Start the timer with first-round dosing, after stocks, preselection, code installation and hardware/analytical validation are complete. Import only the live `round1/dose_and_react.py` with its matching CSVs into the local OT-2 App. Confirm offsets, sources and deck.
2. Dose 20 µL substrate/DCM into the 66 first-round wells in slot 3. Move the open block manually to heater-shaker slot 10. The initial dry-down program is 37 °C, 300 rpm and 10 minutes, **pending HTE verification**. Use the approved ventilation setup; elapsed time alone does not prove DCM removal. Inspect the dry endpoint, let it reach the handling condition and return it to slot 3.
3. Dose ligand stocks, toluene and finally Pd to reach 50 µL in each well. Seal using the validated block assembly. Move the sealed block onto the adapter and start 95 °C / 500 rpm. The programmed four-hour hold begins after the module setpoint is reached; use the validated liquid thermal-lag procedure.
4. While round one reacts, the OT-2 predoses the ten second-round substrate wells in the second array in slot 6. It writes no ligand choice into those wells yet. Remove that array at the pause to HTE's ventilated ambient-evaporation location. Resume promptly: this pause and predosing time are subtracted from the programmed hold. **No second heater dry-down is scheduled.** Verify dryness before second-round catalysts are added. Keep well IDs/orientation intact, prevent contamination, and use the printed `round2_predose.csv`.
5. In parallel, prepare and run authentic-standard/calibration solutions on LC. Use the standards already purchased; never spike the authentic SM/product standards into reaction wells. Record retention references, area response and naphthalene response. Complete calibration before first-round samples reach the autosampler. Cap/remove dosing sources without altering required labware positions during active motion.
6. At the end of the hold, heating/shaking deactivate. Follow the validated thermal-handling SOP at the manual move prompt to transfer the sealed block off the heater to slot 3 and cool. Keep sealed until the validated opening temperature. If HTE's handling SOP requires white module status first, wait for it. Do not improvise hot-block handling to rescue the deadline.
7. Load the exact LC plate into slot 6 and start `round1/workup.py` with the cooled block in slot 3. Open under HTE's SOP. Add 50 µL workup solvent **without extra naphthalene**; manually move to the heater-shaker, shake 2 minutes without heating, and return to slot 3.
8. Confirm the validated homogeneous extract. Add 180 µL LC diluent to the mapped LC wells, then transfer 20 µL extract from the corresponding reaction wells. Seal and shake the LC plate for 2 minutes with HTE's validated plate/adapter method, then submit using `lc_sequence.csv`. The final LC-plate mixing is an operator step; do not assume the reaction block's adapter works with the LC plate.
9. Run all 66 injections. After the complete export is available, normalize it and publish its completion manifest as described below. The local watcher computes yields, checks QC, performs five fresh LLM scoring calls using all valid first-round data, and creates `next_design.csv` and `next_dosing.csv` for ten untested pairs.
10. Verify the ten predosed second-round wells are dry and match the manifest for 5 µmol substrate plus 0.050 µmol naphthalene. Refill source tubes/reservoirs from the preprepared reserves according to second-round `deck_loads.csv`; keep leftovers capped. Export/import the second-round live dosing protocol, which adds **zero new substrate or IS** and contains **no DCM heater step**. Assemble, seal and run its four-hour reaction, then perform the same cooling/workup/dilution/mixing procedure.
11. Run the final ten injections and quantify them. Stop the competition clock when those analyses are complete, as agreed. Save protocols, Opentrons JSON logs, all LC/calibration files, raw model responses and actual timestamps.

HTEL lists plate shakers among its equipment, but confirm which device and settings are available for the last LC-plate mix. If only the OT-2 heater-shaker is used, a validated LC adapter/plate swap must be added to the local operator procedure and its time counted. [HTEL equipment](https://www.chem.uzh.ch/en/research/services/htel/Equipment.html).

## Extraction and analytical calibration

**The requested toluene + aqueous ACN workup may be biphasic.** A fixed aliquot from one phase is not a known fraction of total product, and vigorous shaking does not guarantee a homogeneous sample. Before the campaign, HTE must demonstrate a homogeneous sampling matrix with known recovery for substrate/product/IS, or establish and document a quantitatively validated extraction alternative and update the configured volumes. Until then `homogeneous_sampling_validated` remains false. Visible solids or two phases stop sampling. Also verify analyte stability in the acidic workup and autosampler hold.

The proposed 20 µL + 180 µL dilution is tenfold from a nominal 100 µL homogeneous extract. At 100% yield, final product is 5 mM; final naphthalene is 50 µM. This helps eight-channel throughput but may be too concentrated for the chosen LC/MS response or injected toluene content. HTE must validate separation, injection solvent, calibration range and absence of detector saturation/ion suppression. It is not a finalized LC dilution solely because it fits a plate.

If 5 µL + 195 µL is required, set those volumes and regenerate all files. It is a fortyfold dilution and uses p20 single for samples. The preloaded 0.050 µmol naphthalene now gives 12.5 µM final IS; update `internal_standard_final_uM` and prepare standards at that concentration. The code rejects inconsistent IS concentrations. Change aliquot/dilution only before the complete campaign is frozen, or explicitly record a new validated configuration with calibration matching the actual samples.

Prepare authentic substrate/product calibration stocks in an LC-compatible solvent at measured concentrations; weigh with COA corrections. A proposed 100 mM stock is 16.116 mg/mL PyFluor or approximately 9.709 mg/mL 2-fluoropyridine, subject to solubility/stability verification. Stocks can be prepared before the clock; working standards and injections can be prepared during the first hold. Naphthalene needs a detector where its response is reliable.

Use five nonzero fitted levels of each analyte: 100, 500, 1,000, 2,500 and 6,000 µM, each with **fixed 50 µM naphthalene**, plus an IS-containing zero-analyte blank. Add an independently prepared 5,000 µM check excluded from the fit. Match the validated final sample solvent/matrix and IS concentration, including the solvent introduced by the analytical stocks. Use the lower working-stock concentration for the lowest levels. The [preparation table](stocks-and-calibration.md) avoids sub-microliter transfers. Standards above the validated linear range require a revised dilution, not extrapolation.

The default 14-injection sequence contains five nonzero levels, a zero-analyte blank and an independent check for each of SM and product. The single-analyte series and IS-containing blanks also provide retention identity references, subject to LC/MS confirmation. All 14 are scheduled during the first four-hour hold. In `calibration_template.csv`, rows marked `calibration` enter the fit and rows marked `check` are assessed independently, with a provisional ±15% relative concentration tolerance. Any additional identity, blank or repeat injections must be added to the timing configuration.

Adding IS before the reaction requires HTE to verify naphthalene retention through both dry-down methods, the sealed hot reaction and extraction, and to check chemical interference. Loss of IS can inflate area-ratio yields. The software assumes quantitative recovery and does not apply an unmeasured correction. Live export requires `pre_reaction_internal_standard_validated`, as detailed in the [stock instructions](stocks-and-calibration.md).

For each analyte fit `area_analyte / area_IS = slope × final_concentration_µM + intercept`. Substrate and product have separate response factors. Do not use area%, TIC% or an uncalibrated MS area as yield. At least three distinct concentrations per analyte, positive slopes and the configured fit threshold are required. R² ≥0.995 is a software gate, not complete method validation; verify accuracy, precision, blanks, LOQ, recovery and linearity with HTE. Set measured LOQs and nonoverlapping retention windows from authentic standards. MS confirmation must support the assigned analyte peak, especially if a short method coelutes other components.

If HTE's complete integrated peak list omits nondetected analytes, set `missing_analyte_policy` to `censor` **only after verifying that export behavior**. A valid IS and completed injection/export are required. The reader then reports `yield_upper_bound_percent`, not zero; below-LOQ detected peaks are also represented as bounds. The default is `reject` because a missing row could mean a bad export. Multiple peaks in the reference window, absent/invalid IS, inconsistent method, out-of-range calibration or implausible mass balance are QC failures. Invalid numerical results are removed before LLM feedback. With the current zero-tolerance batch QC setting, resolve a failed measurement/export before the loop proceeds; reaction failure itself is valid data when analytically measured.

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

The normalized CSV has one row per peak: `sample_id,retention_time_min,area,channel,method_id,qc_flag`. Retention times are minutes. `sample_id` must exactly match `R1-001` etc. from `lc_sequence.csv`; retain full peak lists on the selected quantitative channel. Other channels are ignored, never summed. Per-channel spreadsheets that omit channel/method columns need those columns added from verified acquisition metadata before normalization. The selected channel must not change between calibration and samples.

`calibration.csv` follows `hte_inputs/calibration_template.csv`: sample ID, role (`calibration` or `check`), authentic analyte label (`substrate` or `product`), final concentration, its integrated area, IS area, final IS concentration, method and channel. The two analytes may come from the same validated mixed-standard injection; include a row for each and update the injection count. Legacy CSVs without `role` are treated as all calibration points, so use the supplied template to keep checks outside the fit.

Prepare the watcher before first-round LC finishes:

```bash
python -m hte.cli watch --inbox output/hte-lc-inbox \
  --dosing output/hte-round1/dosing.csv --calibration output/hte-calibration.csv \
  --output output/hte-iteration
```

After all 66 injections have finished, run from a second terminal (or a verified Chromeleon post-sequence hook):

```bash
python -m hte.cli normalize path/to/complete_vendor_export.xlsx \
  --output output/hte-lc-inbox/round1.csv
python -m hte.cli complete-export --peaks output/hte-lc-inbox/round1.csv \
  --dosing output/hte-round1/dosing.csv \
  --output output/hte-lc-inbox/round1.ready.json
```

The `complete-export` command is an operator attestation that every expected injection has finished. A stable CSV alone does not establish sequence completion. If the export is already normalized, place it directly at `round1.csv`, then publish the manifest. The manifest verifies expected sample IDs, method and SHA256 file hashes. The watcher responds only to `*.ready.json` with a matching CSV; partial, mismatched or changed exports cannot trigger a valid batch. Publishing the same event twice does not repeat paid calls. Failed events are recorded once; correct the data/configuration and publish a corrected event instead of repeatedly charging requests.

Restart the watcher after changing its configuration, inventory or evidence, because those inputs are loaded when it starts. Calibration/export files are read for the event. Set the API key before starting the watcher.

The output directory is printed as `output/hte-iteration/iteration-...`. Inspect `analysis/results.csv`, `analysis/qc_report.json`, `scoring/ranking.csv`, `next_design.csv` and `next_dosing.csv`. The second round uses only LLM mean-score ranking of the 400 untested pairs, incorporating first-round calibrated observations and the single reference. It does not use an exploratory split or GoLLuM acquisition.

Live protocols are generated automatically when the live bench validation settings are complete; otherwise the next dosing CSV is still produced for review. Explicit export uses:

```bash
python -m hte.cli export --design output/hte-iteration/iteration-REPLACE/next_design.csv \
  --output output/hte-round2 --live
```

Use a new output directory each time to preserve earlier exports. Validate the local App analysis and compare sample IDs, wells, substrate predose and stock loads before running. The watcher does not start the robot or upload protocols remotely.

For final second-round results, normalize/publish a manifest in the same way, then:

```bash
python -m hte.cli analyze --dosing output/hte-round2/dosing.csv \
  --peaks output/hte-round2-peaks.csv --ready output/hte-round2-peaks.ready.json \
  --calibration output/hte-calibration.csv --output output/hte-final-analysis
```

## Optional MOCCA and measured-prior GoLLuM tools

HTE's standard integrated peak exports are the default analytics path. MOCCA2 is available when **raw HPLC-DAD time × wavelength data** can be exported, with authentic standards processed through the same pipeline. It does not reconstruct chromatograms from peak-area CSVs and does not process ISQ MS spectra. Native Chromeleon raw data are not assumed to match MOCCA's parsers. Provide a supported raw export or a verified conversion to the time/wavelength matrix format used by the tested adapter. [MOCCA2 documentation](https://bayer-group.github.io/MOCCA/).

`mocca_manifest_template.json` maps raw paths to sample IDs. For a ChemStation-style matrix CSV, the first row is wavelengths in nm, first column is time in minutes, remaining cells are detector responses, and encoding is UTF-16. Paths are relative to the manifest. The included settings are a starting template, not a validated method:

```bash
python -m hte.cli mocca --manifest path/to/raw_manifest.json \
  --settings hte_inputs/mocca_settings.json --output output/hte-mocca
```

This calls actual MOCCA baseline correction, peak detection and Fraser–Suzuki deconvolution, reports physical time integrals at the selected wavelength, and marks unresolved peaks as QC failures. Test cases use synthetic raw DAD data. Calibration areas must be generated with exactly the same preprocessing/units, not copied from Chromeleon if their integration definitions differ. Confirm the required detector channel matches the adapter's emitted name, e.g. `MOCCA_DAD_254nm`.

The optional `gollum` command requires at least three valid, uncensored same-condition pair measurements. It uses attributed upstream GoLLuM optimizer utilities and a local GP-trained projection over frozen LM embeddings; language-model weights are not fine-tuned. Upstream utility files are vendored with notice because the tested upstream wheel omitted those subpackages. This variant is not part of the user-approved all-LLM second round. Keep it for future comparisons with enough data:

```bash
python -m hte.cli gollum --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --priors path/to/same_condition_pair_results.csv --output output/hte-acquisition.csv
```

## Timing and validation record

At two minutes **injection-to-injection**, 66 + 10 reaction samples require 152 minutes of LC time. The reaction holds require 480 minutes. That leaves 88 minutes within 720 for every other step. Fourteen standard injections use 28 minutes inside the first hold, so they add no serial time if completed then. Predosing and ambient second-round DCM evaporation also occur inside that hold.

The supplied provisional overheads are 30 minutes dosing, 10 first-round evaporation, 12 heating, 12 cooling, 20 workup, 8 decision and 5 other: 97 minutes, giving **729 minutes / 12 h 9 min**. This is an honest planning warning, not a verified duration. Heavy-block heating/cooling, two-minute LC overhead, noncontact delivery and API quotas can change it materially. Replace estimates with rehearsal measurements; achieve at least nine minutes of documented savings, plus a contingency margin. Prioritize off-module cooling under HTE's approved handling SOP, full-column workup/sampling, validated source-dedicated tip reuse, preconfigured LC sequences and pretested concurrent scoring. Do not shorten the specified four-hour reaction or skip method validation to make a nominal timeline fit.

`python -m hte.cli check` prints the timing and outstanding bench fields. Before live export, HTE records successful checks in `validation`: chemistry, block/adapter/seal, solvent pipetting, heating/evaporation, homogeneous sampling, LC calibration, local App simulation, ambient second-round evaporation, pre-reaction IS retention/compatibility, and noncontact tip reuse when enabled. These fields represent completed bench work; changing a Boolean is not validation. A changed plate, solvent, dilution, stock concentration or height requires review of the affected check and regenerated exports.

Keep a campaign folder containing inventory/COAs, configuration, embedding provenance, all scoring responses, designs, dosing/deck/stock CSVs, exact labware JSONs, App analysis and Opentrons JSON logs, standards/LC exports/raw data, QC reports and actual timestamps. The offline demo and tests establish software behavior; they cannot establish chemical success or a 12-hour physical run.
