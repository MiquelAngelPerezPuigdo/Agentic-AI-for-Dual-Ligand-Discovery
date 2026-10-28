# Research provenance

The current bench run is **[one 48-reaction screen](../../run/README.md)**. This directory preserves the scientific initialization and its historical records, separate from the bench procedure.

- [Method explanation](METHOD.md) and [initialization diagnostics](initialization-review.md).
- `code/`: scoring, pair embeddings and the consensus/Sobol selector, with supporting I/O.
- `inputs/`: frozen embeddings, SI single-ligand evidence and historical two-round settings. These settings are not used by the current robot files.
- David's contributor notebook is linked from the method explanation at its original commit.
- `previous-software-validation.json`: the earlier release's software report; current checks are described in [software checks](../README.md).

No research model, API key or paid call is required to run or quantify the current fixed batch.

Frozen provenance keeps the original input paths. Their original inventory/settings copies are under `inputs/`; the active `hte_inputs/ligands.csv` is the 30-ligand chemical catalogue with obsolete deck-position columns removed.
