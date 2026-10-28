# Frozen selection evidence

`round1_design.csv` is the original 48-pair, 30-ligand selection and fixed well assignment. Its historical "round1" name is retained for traceability. The current campaign is **one run only**; use **[run/README.md](../../../run/README.md)** for its 100 µL protocols and weighing amounts.

The companion files preserve pair-selection sources, ligand coverage, initialization provenance and the five repeated Claude scores per pair. [Method explanation](../../research/METHOD.md). Historical scoring conditions are not the current liquid-loading instructions. No paid rerun or optimizer is needed to execute the selected screen.

The [original paid request](scoring/example_request.json) used 250 µL reactions and mesitylene. The current run uses 100 µL and naphthalene; the saved ranking was retained through those changes. The later readable prompt preview under `research/` was not used to generate these frozen scores.
