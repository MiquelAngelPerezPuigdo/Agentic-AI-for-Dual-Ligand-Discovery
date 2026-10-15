# Scoring prompt and first-batch method

[Read the exact first request](claude-scoring-prompt.txt). It is an actual accepted live request, with the full individual-ligand catalogue and required output schema. Every request carries the same single-ligand prior data in both initialization and feedback stages. [All 2,175 repeated scores](../campaigns/hackathon2026/scoring/repeated_scores.csv) are retained.

## Prompt contract

The fixed input gives the chemical names and SMILES of SM/product, 250 µL /0.1 M /95 °C /4 h conditions, Pd(COD)(DQ), catalyst loadings, solvent, mesitylene and all **30 active ligand IDs, names and SMILES**. It includes **17 same-substrate Table S2 yields**; the other 13 are `null`, not zero. These are published high-temperature single-ligand 19F NMR yields, not 95 °C results. The literature narrative is not sent. L07's source SI value remains archived but unavailable L07 is excluded from requests.

The final query supplies **one anchor ligand and up to eight different partner ligand IDs**, each defining a two-different-ligand combination. It does not supply the complete 435-pair catalogue. Claude considers **ligand cooperativity**, complementarity, competition and catalyst stability, then returns only:

```json
{"scores":{"L02":61.5,"L03":72}}
```

Here the anchor comes from the query; these values score its mixtures with L02 and L03, not the individual ligands. The exact required partner IDs are fixed by each request's JSON schema. Python constructs canonical pair IDs, rejects missing/extra/duplicate/non-numeric/out-of-range values and averages **five scores per pair**, retaining standard deviations. Scores rank relative promise; they are not predicted yield percentages. No prose/reasoning is requested; extended thinking is disabled.

## Selection

The real initial campaign scored all **435 pairs in 340 small requests**. Frozen symmetric T5-base representations are **435 ×768** vectors, an exact active-ligand subset of previously inferred vectors. Selection combines **50% Claude performance percentile +50% distance/diversity percentile**, first satisfying all-ligand coverage and then filling the batch. A lower-quartile Claude floor discourages diversity-only poor choices; coverage can override that floor with an audited flag. The real 48-pair batch covers **30/30**, with **zero overrides**. Pair yields are unnecessary for this initialization. This is GoLLuM-inspired embedding/diversity initialization, not a trained GoLLuM yield predictor.

After all 48 calibrated experimental results pass QC, Claude receives valid measurements/upper bounds and the same individual ligand catalogue/SI yields, scores **387 untested pairs** in small requests and chooses the top **22**. The L17 single control is appended separately in round two; it is not invented as first-round evidence. No GoLLuM acquisition, embedding diversity or repeated pair experiment enters this decision. Practice loops demonstrate this plumbing using synthetic data only.

Export new previews without a key or paid calls:

```bash
python -m hte.cli preview-prompts --output output/prompt-preview
```

Measured-feedback previews can be produced with `--observations` pointing to a real `analysis/results.csv`. Do not submit synthetic results as experimental feedback. The original repeated-scoring benchmark is preserved in the [thesis repository](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Catalyst-Design); the [GoLLuM initializer](https://github.com/schwallergroup/gollum/blob/main/src/gollum/initialization/initializers.py) motivates the initialization concept.
