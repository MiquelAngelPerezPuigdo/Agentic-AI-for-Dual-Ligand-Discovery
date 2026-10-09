# Software rehearsal results

The offline first-feedback-loop rehearsal completed successfully. All chemistry results and Claude responses in this exercise were synthetic; no paid API call or physical robot run occurred.

| Check | Observed result |
|---|---|
| Real frozen T5 embeddings loaded | 465 unordered pairs, 768 dimensions |
| Initial scoring request contract | Five mocked requests, each covering 465 pairs |
| Initial batch | 65 distinct pairs plus one tBuBrettPhos reference |
| Mandatory pair coverage | All 31 ligands represented; minimum one pair well per ligand, with the single reference excluded |
| LC processing | 66 calibrated synthetic results; batch QC passed |
| Feedback scoring request contract | Five mocked requests, each receiving all 66 results and scoring 400 untested pairs |
| Next dosing CSV | Ten new pair assignments using only LLM scores, with no pair repeats |
| Predosed substrate | All ten second-round substrate doses remain zero |
| Predosed internal standard | 0.050 µmol naphthalene per well retained in the plan; no second substrate/IS stock or workup IS dose |
| Calibration | Five nonzero levels plus an IS-containing blank per analyte; independent checks excluded from each fit |
| Incomplete LC export | Ignored until the completion marker was published |
| Repeated completion event | Ignored; no additional scoring calls |
| Physical protocol generation by watcher | Disabled because bench validations remain incomplete |
| Optional GoLLuM execution | Actual attributed upstream optimizer, real embeddings, 61 uncensored synthetic pair priors, 465 finite acquisition values |
| Local API key file | Mocked scoring reads `anthropic.key`; environment takes precedence; malformed entries stop without echoing contents; no key saved in outputs |
| Local acceptance suite | 88 passed, zero failures/errors/skips |

Adversarial selector tests also cover a ligand whose every pair is below the Claude percentile floor, tight coverage within 16 wells, impossible coverage, and a manually edited design where the L17 reference is present but L17 is absent from all pairs. Coverage overrides are audited; missing pair coverage blocks export. The current offline loop uses the same mandatory coverage rule and completes all 31 ligands without extra wells.

The repository audit added regression checks for calibration roles/levels/blanks, CSV/XLSX normalization, stale dosing, repeated pairs, ties, live LC/timing gates, file races, concurrent processes and interrupted API calls. No additional paid requests were made. See the [audit record](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery/blob/main/docs/rehearsal-results.md#repository-audit).

The campaign rehearsal also rejects any call to a GoLLuM yield optimizer and verifies that every second-round assignment uses the LLM selection method. GoLLuM-inspired initialization needs no pair yields.

The historical optional GoLLuM check did not change the second-round design. Its local GP adapter trained a projection over frozen embeddings, keeping the language-model weights unchanged.

To reproduce the feedback loop from the repository root:

```bash
python -m hte.cli rehearse-loop --output output/fake-first-loop
```

Use a fresh output directory. `rehearsal_report.json` records the checks and the relative location of `next_dosing.csv`. The generated rankings use an explicitly labeled arbitrary emulator; they are unsuitable for deciding real experiments. The real initial selection requires the operator's Claude API key and the [first-batch setup](start-here.md).

## Separate live API checks

On 9 October 2026, three small Opus 4.8 smoke tests each scored four pairs twice. The current scores-only v4 prompt returned valid complete JSON with no reasoning or hypothesis field; both provider responses contained only text blocks with extended thinking disabled. The second response reported **5,174 cached read tokens**. The v4 test cost approximately **$0.0570**, bringing total estimated returned-usage spending across six generation requests to **$0.4023**, below the $1 smoke-test allowance.

The earlier v2/v3 tests used a different prompt and output contract; their $0.3453 combined cost is included in that total. A conservative preflight stopped one earlier v3 attempt before generation. The scores-only offline feedback rehearsal was rerun successfully: all 66 synthetic first-round results reached the prompt, 400 untested pairs were scored in five mocked calls and ten new pairs were exported without substrate/IS redosing.

These checks establish live model access, structured-response parsing and cache reuse for the smoke requests. The full 465-pair initial campaign has not been generated, and the model scores are not measured chemistry yields. The [prompt guide](scoring-prompt.md) supplies the identities, SI evidence and output contract. Raw responses and keys remain outside the public handoff.

## Repository audit

The 9 October review checked all source modules, tests, campaign inputs, documentation and generated handoffs. The 31 ligand identities were compared with the original workbook; molecular weights and phosphorus counts were checked from the structures. Re-extraction of the 18 same-substrate single-ligand SI yields reproduced the stored evidence. The exact first-round prompt preview matched the published prompt; its scores-only contract and prompt caching remain unchanged.

The audit corrected these operational issues:

- Live export now requires complete analytical settings and a measured schedule within the competition deadline, alongside bench validations.
- Designs and imported dosing files are checked for the configured reference, unique pair identities, ligand coverage and all calculated quantities. Live round-two export requires the actual first-round history and rejects repeated pairs.
- Calibration requires the configured five nonzero levels, measured zero blanks and independent checks. CSV/XLSX import rejects incomplete exports while preserving measured zero peak areas.
- Equal scores/distances receive equal average ranks. Initial selection remains 50/50 Claude and embedding diversity; feedback selection remains entirely Claude.
- Process locks prevent duplicate local jobs. Attempt records prevent automatic repayment after a charged request is interrupted. Completed input/output hashes detect changes, and existing or partially written protocol exports cannot be overwritten.
- Production commands consistently use the campaign-specific configuration. The staff checklist remains two pages; the complete handbook retains the technical reference.

All **88 tests passed**, including actual Opentrons simulation and the offline LC-to-Claude feedback loop. Additional direct demo and feedback rehearsals use synthetic results and mocked API responses. No new paid calls were made for this audit. The historical live smoke-test total remains approximately $0.4023.

The full real first-batch ranking has not been generated. No physical chemistry or hardware run was performed. HTE must still validate glass hardware, solvent handling, IS recovery, extraction, the LC method and actual timing. The template's **729-minute** schedule exceeds the **720-minute** limit and is deliberately blocked from live release until measured timings fit.
