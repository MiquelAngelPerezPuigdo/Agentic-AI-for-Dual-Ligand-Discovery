# Software rehearsal results

The offline first-feedback-loop rehearsal completed successfully. All chemistry results and Claude responses in this exercise were synthetic; no paid API call or physical robot run occurred.

| Check | Observed result |
|---|---|
| Real frozen T5 embeddings loaded | 465 unordered pairs, 768 dimensions |
| Initial scoring request contract | Five mocked requests, each covering 465 pairs |
| Initial batch | 65 distinct pairs plus one tBuBrettPhos reference |
| LC processing | 66 calibrated synthetic results; batch QC passed |
| Feedback scoring request contract | Five mocked requests, each receiving all 66 results and scoring 400 untested pairs |
| Next dosing CSV | Ten new pair assignments with no pair repeats |
| Predosed substrate | All ten second-round substrate doses remain zero |
| Predosed internal standard | 0.050 µmol naphthalene per well retained in the plan; no second substrate/IS stock or workup IS dose |
| Calibration | Five nonzero levels plus an IS-containing blank per analyte; independent checks excluded from each fit |
| Incomplete LC export | Ignored until the completion marker was published |
| Repeated completion event | Ignored; no additional scoring calls |
| Physical protocol generation by watcher | Disabled because bench validations remain incomplete |
| Optional GoLLuM execution | Actual attributed upstream optimizer, real embeddings, 61 uncensored synthetic pair priors, 465 finite acquisition values |
| Local API key file | Mocked scoring reads `anthropic.key`; environment takes precedence; malformed entries stop without echoing contents; no key saved in outputs |
| Local acceptance suite | 46 passed, zero failures/errors/skips |

The optional GoLLuM check did not change the second-round design. Its local GP adapter trained a projection over frozen embeddings, keeping the language-model weights unchanged.

To reproduce the feedback loop from the repository root:

```bash
python -m hte.cli rehearse-loop --output output/fake-first-loop
```

Use a fresh output directory. `rehearsal_report.json` records the checks and the relative location of `next_dosing.csv`. The generated rankings use an explicitly labeled arbitrary emulator; they are unsuitable for deciding real experiments. The real initial selection requires the operator's Claude API key and the [first-batch setup](start-here.md).

## Separate live API checks

On 9 October 2026, two small Opus 4.8 smoke tests each scored four pairs twice. The revised v3 prompt returned valid complete JSON with hypotheses of 162 and 159 words, and the second response reported 12,911 cached read tokens. Its estimated returned-usage cost was $0.1914; combined with the earlier $0.1539 test, total estimated spending was $0.3453, below the $1 test allowance. A conservative preflight stopped an earlier v3 attempt before generation when its bound exceeded the remaining allowance.

These checks establish live model access, structured-response parsing and cache reuse for the smoke requests. The full 465-pair initial campaign has not been generated, and the model scores are not measured chemistry yields. The [prompt guide](scoring-prompt.md) supplies the identities, SI evidence and output contract. Raw responses and keys remain outside the public handoff.
