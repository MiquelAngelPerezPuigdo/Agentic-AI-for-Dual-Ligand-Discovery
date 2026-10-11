# Start here: organizers, HTE operators and the first batch

Review the [organizer updates and deadlines](organizer-updates.md). Send the organizers the [HTE configuration checklist](hte-questions.md) and give the experimental operators the **[two-page staff checklist](HTE-staff-checklist.pdf)**. The [complete runbook](hte-runbook.md) remains a technical reference. The checklist requests the unresolved facts; the runbook explains stock preparation, deck loading, each reaction/analysis stage and the automated decision.

## What to ask the organizers

1. **Reaction hardware:** Can sealed glass vials run on conventional heater/magnetic stirrer(s), using aluminum blocks and a small stir bar per vial? Ask for the rack JSON, simultaneous 95 °C heating/stirring/sealing, thermal lag and a second predose array. Current exported files still use the OT-2 heater-shaker; off-robot heating needs revision. The email mentions 24 × 4 mL vials but the ZIP lacks their rack JSON. Confirm capacity to heat all 60 first-round reactions together.
2. **LC method and data:** Request the existing 1.7-minute method, its measured full injection cycle, quantitative channel/wavelength, retention times, injection volume and a representative CSV/XLSX export. Include well/sample mapping, failed injections, nondetections and an end-of-sequence signal. Raw DAD data are needed only for optional MOCCA processing.
3. **Extraction and calibration:** Confirm recovery and homogeneous sampling from the toluene/water/ACN mixture, acceptable dilution/concentration, calibration and naphthalene suitability, and the LC plate/seal. Validate naphthalene added with SM through capped predose storage/heating before treating its area as a yield reference. Schedule five nonzero analyte levels at fixed IS, blanks and independent checks while the first reaction runs; use the [stock and calibration instructions](stocks-and-calibration.md).
4. **Stocks and liquid handling:** Use ordinary plastic stock racks, glovebox preparation, the proposed 20/40 mM ligand/Pd stocks, capped reserves, and validated pipetting/tip reuse; no separate catalyst-solubility study is requested. Validate aspiration heights and capped second-round predose storage, including retained toluene volume.
5. **Time and access:** Request a timed rehearsal, continuous LC availability, local OT-2 App access, a shaker for the analytical plate and a workstation allowed to contact Anthropic. Stock preparation and initial selection are outside the clock; the final ten analyses end it.

The requested 1.7-minute full-cycle scenario gives 599 minutes for chemistry and reaction-sample LC, plus 87 minutes of provisional operations: **686 minutes** total. HTEL must confirm the method separates all three compounds and measure the full cycle. A 3-minute serial method would take 777 minutes.

## What HTE follows

| Stage | Operator action | Software handoff |
|---|---|---|
| Before the clock | Confirm 250 µL scale/rack/method, prepare stocks in the glovebox, calibrate handling and rehearse | Campaign configuration; real first-batch selection; printed stock and deck-load CSVs |
| First assembly | Dose 25 µL combined SM/IS/toluene into 60 wells, add ligands/Pd, seal and begin the four-hour hold | Local first-round dosing/reaction protocol |
| During first hold | Measure authentic standards/calibration; predose and promptly cap ten second-round SM/IS/toluene wells | Calibration CSV and ten-well predose manifest |
| First workup and LC | Cool, work up, dilute and measure all 60 samples; publish the complete export | Local workup protocol; peak CSV plus completion marker |
| Decision | Review QC and the ten new pair assignments | Watcher produces `next_design.csv` and `next_dosing.csv` |
| Second assembly | Verify capped predoses retain their 25 µL stock volume; add the selected catalysts, seal and hold four hours | Local second-round protocol; substrate and IS are not dosed again |
| Final workup and LC | Work up and measure all ten samples; stop the clock | Final calibrated results and logs |

Staff follow the short checklist; the runbook supplies the detailed reference. Exact glass hardware, extraction and analytical settings are still pending; they must be resolved before physical execution.

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

The script uses the local key file and runs five real scoring calls over the 435 pairs, followed by the 50/50 score/diversity selection. Its output is `output/first-batch-<timestamp>/first_batch.csv`: **59 pair assignments plus one L17 tBuBrettPhos reference**, including well and sample IDs. All 30 active ligands must occur in the pair wells; the single reference does not count toward coverage. `first_batch.csv.ligand_coverage.csv` lists each ligand and its pair-well count, and the selection trace flags any coverage-driven Claude-cutoff override. Scoring files preserve the exact prompts, individual scores, token usage and the cost preflight. Responses contain scores only; extended thinking is disabled. These are paid calls within the configured estimated $20 campaign cap. No key belongs in a committed file or chat message.

The script accepts an output folder and campaign path, for example `zsh scripts/first-batch.zsh output/real-first-batch local_data/campaign.json`; an optional third argument supplies the inventory path. Use that same campaign file throughout export and LC feedback. The first batch can be selected before the organizers finalize hardware and LC details. Protocol/stock exports use the confirmed campaign configuration as described in the runbook. Do not use the synthetic demo ranking for experiments.

Review the [structured prompt and SI evidence](scoring-prompt.md) before scoring. To inspect the exact current API requests without a key or paid calls, run `python -m hte.cli preview-prompts --output output/prompt-review`. Scoring also saves the exact request JSON and a readable prompt beside every response.

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

The report verifies 60 first-round measurements reach the scorer, only 376 untested pairs are rescored, ten new pair assignments are generated, substrate is not dosed again, incomplete exports are ignored and repeated completion events do not trigger more calls. `rehearsal_report.json` points to the resulting `next_dosing.csv`. Scores and yields from this exercise demonstrate data flow only.

## What has run from GoLLuM

Real T5-base inference generated the original 465 × 768 pair embeddings; the included library selects its 435 unchanged active rows, averaging both ligand orders. Initial selection uses those embeddings for diversity, following the language-model representation idea that motivated GoLLuM. With no measured pair yields, it does not fit a yield model.

The attributed upstream optimizer ran on synthetic observations with a GP projection over frozen embeddings; this was a historical adapter check. The campaign uses embedding diversity only for initialization. After measured yields arrive, Claude alone selects round two.
