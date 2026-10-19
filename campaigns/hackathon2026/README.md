# Official initial campaign

This folder contains the adopted **48-pair, 24-consensus +24-Sobol selection** and its reproducibility record. All 30 available ligands are represented; no pair-yield measurements were used.

David Ming Segura contributed the [notebook implementation](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery/blob/c2682f3db09eb496b92d11fb6725e9870157e301/notebook/batch_suggestions.ipynb) in commit `c2682f3`. The production selector preserves its defaults: raw-T5/Claude baseline; standardization →16-component PCA →[0,1] scaling; retain 24 baseline pairs by diversity with all-ligand coverage; add 24 unique Sobol matches, seed 1. The adopted batch retains 26 pairs from the previous design and replaces 22. The previous all-consensus design is preserved at parent commit `c931e47`; **use the files in this checkout for the hackathon**.

- `round1_design.csv`: canonical sample IDs, ligand pairs and reaction/LC well assignments.
- Companion `.selection.csv`, `.ligand_coverage.csv`, `.metadata.json`: selection sources/trace, inclusion counts, settings and provenance.
- `scoring/`: unchanged five accepted scores per pair, aggregate ranking, example request, model/settings, response provenance and usage/budget records.
- `initialization_provenance.json`: contributor commit, superseded-design hash and exact notebook replay check.
- `files.sha256.json`: integrity hashes for the current campaign records.

[Reproduce the design and generate robot/stock files](../../docs/development.md#reproduce-the-real-first-batch-without-spending) without paying Claude again or downloading a model. **Regenerate stock preparation, dose, protocol and LC files; previous exports refer to different pairs.** Generated files belong in local `output/`; measured local configuration belongs in `local_data/`. The authoritative default chemistry is [hte_inputs/campaign.json](../../hte_inputs/campaign.json).

The second-round **22 new pairs +L17 reference** will be selected by Claude only after all 48 experimental first-round results pass analytical QC. RockPhos remains capped at four R2 wells. Synthetic practice outputs are never experimental evidence.

Chemistry and per-vial volumes are unchanged: 250 µL reactions, combined SM/IS in retained toluene, 20 mM ligand stocks and four retained Pd sources. Historical paid scoring records stay frozen; the new initialization changes which pairs are tested. [Method, ALICE precedent and limits](../../docs/ml-strategy.md).
