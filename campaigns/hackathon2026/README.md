# Frozen initial campaign

This folder contains the **real 48-pair selection** and its reproducibility record. All 30 available ligands are represented; no pair-yield measurements were used.

- `round1_design.csv`: canonical sample IDs, ligand pairs and reaction/LC well assignments.
- Companion `.selection.csv`, `.ligand_coverage.csv`, `.metadata.json`: greedy selection trace, inclusion counts and configuration digest.
- `scoring/`: five accepted scores per pair, aggregate ranking, example request, model/settings, response provenance and usage/budget records.
- `files.sha256.json`: integrity hashes for these frozen records.

[Reproduce the design and generate robot/stock files](../../docs/development.md#reproduce-the-real-first-batch-without-spending) without paying Claude again. Generated files belong in local `output/`; measured local configuration belongs in `local_data/`. The authoritative default chemistry is [hte_inputs/campaign.json](../../hte_inputs/campaign.json).

The real second-round 22-pair selection will be made after all 48 experimental first-round results pass analytical QC. Synthetic practice results are generated on demand and are never stored here as experimental evidence.

Preparation was revised on 18 October: combined SM/IS in retained toluene, 20 mM ligand stocks and a four-well R2 RockPhos cap. The final reaction conditions and frozen R1 pair selection remain unchanged. Historical scoring records stay frozen; generate all doses/protocols from the current canonical configuration.
