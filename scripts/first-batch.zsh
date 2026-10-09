#!/bin/zsh
# Run after activating Python. Use local anthropic.key or hidden input.
set -euo pipefail
repo_root=${0:A:h:h}
cd "$repo_root"
campaign="${1:-output/first-batch-$(date +%Y%m%d-%H%M%S)}"
campaign_config="${2:-hte_inputs/campaign.json}"
ligand_inventory="${3:-hte_inputs/ligands.csv}"

if [[ -z ${ANTHROPIC_API_KEY:-} && ! -f anthropic.key ]]; then
  read -rs 'ANTHROPIC_API_KEY?Claude API key (hidden): '
  printf '\n'
  export ANTHROPIC_API_KEY
fi

python -m hte.cli --config "$campaign_config" --inventory "$ligand_inventory" score --output "$campaign/scoring"
python -m hte.cli --config "$campaign_config" --inventory "$ligand_inventory" design --ranking "$campaign/scoring/ranking.csv" \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output "$campaign/first_batch.csv"
printf 'First batch: %s\n' "$campaign/first_batch.csv"
printf 'Ligand coverage: %s\n' "$campaign/first_batch.csv.ligand_coverage.csv"
printf 'Scores and request records: %s\n' "$campaign/scoring"
