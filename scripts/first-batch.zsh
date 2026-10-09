#!/bin/zsh
# Run after activating Python. Use local anthropic.key or hidden input.
set -euo pipefail
repo_root=${0:A:h:h}
cd "$repo_root"
campaign="${1:-output/first-batch-$(date +%Y%m%d-%H%M%S)}"

if [[ -z ${ANTHROPIC_API_KEY:-} && ! -f anthropic.key ]]; then
  read -rs 'ANTHROPIC_API_KEY?Claude API key (hidden): '
  printf '\n'
  export ANTHROPIC_API_KEY
fi

python -m hte.cli score --output "$campaign/scoring"
python -m hte.cli design --ranking "$campaign/scoring/ranking.csv" \
  --embeddings hte_inputs/pair_embeddings_t5-base.npz \
  --output "$campaign/first_batch.csv"
printf 'First batch: %s\n' "$campaign/first_batch.csv"
printf 'Scores and request records: %s\n' "$campaign/scoring"
