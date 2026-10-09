# Start here: organizers, HTE operators and the first batch

Send the organizers the [HTE configuration checklist](hte-questions.md) and give the experimental operators the [complete runbook](hte-runbook.md). The checklist requests the unresolved facts; the runbook explains stock preparation, deck loading, each reaction/analysis stage and the automated decision.

## What to ask the organizers

1. **Reaction hardware:** Which sealed glass-vial array, insert and seal can they supply and securely mount on the OT-2 heater-shaker? Ask for the measured labware JSON, validated 95 °C heating/shaking/sealing, actual thermal lag and a second vial array for predosing round two. Para-Dox 104960 is a candidate, with compatibility pending.
2. **LC method and data:** Ask for the exact method, measured full two-minute injection cycle, quantitative channel/wavelength, retention times, injection volume and a representative CSV/XLSX export. Include well/sample mapping, failed injections, nondetections and an end-of-sequence signal. Raw DAD data are needed only for optional MOCCA processing.
3. **Extraction and calibration:** Confirm recovery and homogeneous sampling from the toluene/water/ACN mixture, acceptable dilution/concentration, calibration and naphthalene suitability, and the LC plate/seal. Validate naphthalene added with SM through drying/heating before treating its area as a yield reference. Schedule five nonzero analyte levels at fixed IS, blanks and independent checks while the first reaction runs; use the [stock and calibration instructions](stocks-and-calibration.md).
4. **Stocks and liquid handling:** Confirm identity/assay, solubility of every proposed stock, glovebox stock preparation, containers/dead volumes, solvent pipetting and acceptable source-dedicated tip reuse. Validate aspiration heights and the dry endpoint for ambient second-round DCM evaporation.
5. **Time and access:** Request a timed rehearsal, continuous LC availability, local OT-2 App access, a shaker for the analytical plate and a workstation allowed to contact Anthropic. Stock preparation and initial selection are outside the clock; the final ten analyses end it.

The chemistry and two-minute analyses already occupy 632 of 720 minutes. The complete provisional plan is 729 minutes; the organizers need to help establish a measured plan that fits.

## What HTE follows

| Stage | Operator action | Software handoff |
|---|---|---|
| Before the clock | Confirm equipment/method, prepare stocks in the glovebox, calibrate handling and rehearse | Campaign configuration; real first-batch selection; printed stock and deck-load CSVs |
| First assembly | Dose combined SM/IS into 66 wells, remove DCM, add ligands/Pd/toluene, seal and begin the four-hour hold | Local first-round dosing/reaction protocol |
| During first hold | Measure authentic standards/calibration; predose ten second-round SM/IS wells and allow ambient DCM evaporation | Calibration CSV and ten-well predose manifest |
| First workup and LC | Cool, work up, dilute and measure all 66 samples; publish the complete export | Local workup protocol; peak CSV plus completion marker |
| Decision | Review QC and the ten new pair assignments | Watcher produces `next_design.csv` and `next_dosing.csv` |
| Second assembly | Verify predosed wells are dry; add the selected catalysts and toluene, seal and hold four hours | Local second-round protocol; substrate and IS are not dosed again |
| Final workup and LC | Work up and measure all ten samples; stop the clock | Final calibrated results and logs |

The runbook supplies the details and stop points. Exact glass hardware, extraction and analytical settings are still pending; they must be resolved before physical execution.

## Where to put the Claude API key

Use the key on the **operator laptop**. Create `anthropic.key` in the repository root by copying `anthropic.key.example`, then replace its single placeholder line with your Anthropic API key. Paste only the key, with no quotes or `ANTHROPIC_API_KEY=` prefix. Scoring and the watcher read this file automatically when run from the repository root. The robot does not need it.

`anthropic.key` is excluded from Git and the HTE handoff. Keep it on the operator laptop. An existing `ANTHROPIC_API_KEY` environment variable takes precedence; `.env` files are not automatically loaded.

From the repository root, create/activate a Python environment and install the package:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp anthropic.key.example anthropic.key
# Open anthropic.key in a text editor and replace the placeholder.
zsh scripts/first-batch.zsh
```

The script uses the local key file and runs five real scoring calls over the 465 pairs, followed by the 50/50 score/diversity selection. Its output is `output/first-batch-<timestamp>/first_batch.csv`: **65 pair assignments plus one L17 tBuBrettPhos reference**, including well and sample IDs. Scoring files preserve hypotheses, individual scores, token usage and the cost preflight. These are paid calls within the configured estimated $20 campaign cap. No key belongs in a committed file or chat message.

The first batch can be selected before the organizers finalize hardware and LC details. Protocol/stock exports use the confirmed campaign configuration as described in the runbook. Do not use the synthetic demo ranking for experiments.

The later watcher can read the same `anthropic.key` file. As an alternative, set the key for a terminal with hidden input:

```zsh
read -rs 'ANTHROPIC_API_KEY?Claude API key: '
export ANTHROPIC_API_KEY
```

If no key file or environment variable exists, the first-batch script asks for hidden input. A prompted key stays in that process; it is not saved to disk or set in the parent terminal. Real model access is checked before scoring, and access failures stop the campaign without silently selecting another model.

[Prompt caching](prompt-caching.md) is already enabled for both rounds. Shared context uses a one-hour lifetime, and the score command prints the provider-reported cache status. Inspect `scoring/cache_summary.json` for read/write tokens and estimated cost. No additional key setting is needed.

## Fake first feedback loop

Install the test dependencies if they are not present, then run:

```bash
python -m pip install -e '.[test]'
python -m hte.cli rehearse-loop --output output/fake-first-loop
```

Use a fresh output directory for each rehearsal. This uses the real frozen T5 pair embeddings, **synthetic LC results**, and an explicitly mocked Claude client. It makes zero paid calls and needs no key. It runs both scoring campaigns through the real scoring code and the first-round event through the real watcher.

The report verifies 66 first-round measurements reach the scorer, only 400 untested pairs are rescored, ten new pair assignments are generated, substrate is not dosed again, incomplete exports are ignored and repeated completion events do not trigger more calls. `rehearsal_report.json` points to the resulting `next_dosing.csv`. Scores and yields from this exercise demonstrate data flow only.

## What has run from GoLLuM

Real T5-base inference generated the included 465 × 768 pair embeddings, averaging both ligand orders. Initial selection uses those embeddings for diversity, following the language-model representation idea that motivated GoLLuM. With no measured pair yields, it does not fit a yield model.

The attributed upstream GoLLuM optimizer has been executed with a local GP-trained projection over frozen embeddings and synthetic observations. This adapter keeps the original language-model weights frozen; it is not the full upstream fine-tuning pipeline. It is optional and is not used to decide the approved all-LLM second round. The runbook documents how to run it later on valid same-condition pair measurements.
