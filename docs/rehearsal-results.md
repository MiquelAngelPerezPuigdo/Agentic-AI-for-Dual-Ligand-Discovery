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
| Local acceptance suite | 54 passed, zero failures/errors/skips |

Adversarial selector tests also cover a ligand whose every pair is below the Claude percentile floor, tight coverage within 16 wells, impossible coverage, and a manually edited design where the L17 reference is present but L17 is absent from all pairs. Coverage overrides are audited; missing pair coverage blocks export. The current offline loop uses the same mandatory coverage rule and completes all 31 ligands without extra wells.

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
