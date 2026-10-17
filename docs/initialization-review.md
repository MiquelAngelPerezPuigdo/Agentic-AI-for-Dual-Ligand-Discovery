# Initial ligand-selection review

**The minimum-once constraint is enabled and passed: all 30 available ligands occur in the 48 first-round pair experiments.** L07 is excluded because it is unavailable.

![Frozen initialization: embedding map, pair network and ligand frequencies](initialization-map.svg)

## Frozen-batch statistics

| Measure | Value |
|---|---:|
| Unique pair experiments | 48 /435 (11.0%) |
| Ligands covered | 30 /30 |
| Uses per ligand | 1–7; mean 3.2; median 2.5 |
| Mean Claude score, selected /whole library | 57.34 /45.05 |
| Median repeat-scoring SD, selected | 2.19 score units |
| Overlap with the unconstrained top 48 scores | 22 /48 |
| All-ligand coverage completed | Selection step 16 |
| LLM-floor overrides | 0 |
| Pairing-network components | 1 |
| Ligand-usage Gini (0 = equal use) | 0.326 |

Five ligands appear only once: **L12 VBRIDP**, **L14 CataCXium ABn**, **L23 SPhos**, **L27 tris(3-chlorophenyl)phosphine**, **L30 N-XantPhos**.
Three appear seven times: **L17 t-BuBrettPhos**, **L18 dtbpf**, **L25 MeDalPhos**.

The PCA map retains **54.5%** of embedding variance. Points are pairs, not individual ligands; the network displays the individual ligand IDs and tested pairings. Two-dimensional visual separation is an approximation. Diversity statistics below use all 768 raw T5 dimensions.

## Weight previews from the same paid scores

| Method | Ligands covered | Uses | Mean score | Mean nearest squared distance | Usage Gini | Shared pairs |
|---|---:|---:|---:|---:|---:|---:|
| Frozen batch: 50% LLM / 50% diversity | 30/30 | 1–7 | 57.34 | 0.1708 | 0.326 | 48/48 |
| Preview: 25% LLM, coverage enforced | 30/30 | 1–8 | 54.44 | 0.1696 | 0.308 | 26/48 |
| Preview: 75% LLM, coverage enforced | 30/30 | 1–10 | 59.01 | 0.1860 | 0.382 | 28/48 |
| Preview: 100% LLM, coverage enforced | 30/30 | 1–14 | 60.75 | 0.2186 | 0.448 | 23/48 |
| Diagnostic: top 48 scores, no coverage rule | 22/30 | 0–15 | 62.27 | 0.2456 | 0.574 | 22/48 |

Lower mean nearest squared distance indicates broader embedding coverage: average squared distance from every library pair to its nearest selected pair. Mean scores quantify Claude's relative ranking, not expected experimental yield. Weighted previews all retain the existing coverage rule and LLM floor. The top-score-only diagnostic omits coverage deliberately.

## Interpreting possible refinement

Minimum-once coverage ensures inclusion, not balanced sampling. We can compare score/diversity weights with the existing cached scores; enforcing a larger minimum or maximum ligand frequency would be a separate selector change. No preview here changes the frozen batch, well assignments or stock plan. Experimental performance can only be assessed after measured yields.

Generate the self-contained interactive report and machine-readable statistics locally:

    python -m pip install -e '.[reports]'
    python scripts/initialization-report.py --output output/initialization-review

Open output/initialization-review/initialization-review.html. The folder also contains SVG/PNG, statistics.json, comparison.csv and ligand_counts.csv. No API key or paid calls are needed.

[ML strategy](ml-strategy.md) · [Exact frozen ligand coverage](../campaigns/hackathon2026/round1_design.csv.ligand_coverage.csv)

Design SHA-256: 7c2ad21967f468857938989fcbe5901d2409a86dcae8d785f7247032ef301104
