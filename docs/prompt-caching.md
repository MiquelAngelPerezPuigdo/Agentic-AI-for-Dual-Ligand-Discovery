# Claude prompt caching and costs

The live initial campaign used **claude-opus-4-8**, five scoring repeats per pair and small anchor/partner queries (at most eight pairs). Extended thinking is disabled and only an ID-keyed numeric score JSON is requested. The initial batch is already frozen in `campaigns/hackathon2026/`; do not pay to regenerate it as part of normal setup.

## What is cached in both stages

`hte/scoring.py` sends two stable text blocks with `cache_control={"type":"ephemeral","ttl":"1h"}`: (1) fixed chemistry, all individual ligand IDs/names/SMILES and available single-ligand SI yields, and (2) shared measured feedback. The short final block supplies one anchor and partner IDs. Cohorts/schema stay fixed across five repeats, while partner order is shuffled. The first actual scoring call warms each schema group; there is no extra paid warm-up. Shared feedback changes after experiments, so the second-round request has a new feedback prefix.

The live initial run reports **340 accepted requests, 311 cache-hit requests, 1,578,979 cache-read tokens and 147,721 cache-write tokens**. Accepted scoring cost is **$2.7599745** at the recorded rates. Prior rejected full-size output cost **$0.225235**, and earlier smoke tests **$0.4023195**: known combined estimate **$3.387529**. These are usage-based estimates, not an invoice. [Saved counters and score audit](../campaigns/hackathon2026/scoring/cache_summary.json).

## Budget / recovery

The configured **$20 cap applies to each scoring campaign**, with `prior_campaign_cost_usd` carried into that campaign's ledger. It is not a global Anthropic account spending limit. Current mode is `incremental_cached`: before each request, reserve a conservative cold-cache amount, then replace that reservation with provider-reported usage only after a validated response. No SDK retries are enabled. Stop before the next reservation would exceed the cap. The theoretical all-miss initial bound was **$28.99**, so a complete $20 run depended on caching; actual accepted usage was $2.76. `strict_all_miss` mode instead rejects a campaign when its entire worst-case bound exceeds the cap.

`cost_preflight.json`, `budget_ledger.json`, per-request usage/raw responses and `cache_summary.json` remain with the run. A failed/uncertain request retains its reservation and attempt record; the pipeline will not silently repay it on restart. An incomplete score set cannot select a batch. No paid second-round calls have been made; real cost/latency may differ because experimental feedback enlarges the prompt. Initial scoring used two workers; feedback uses four. The five-minute second-round decision allowance is a target, not measured API throughput.

## API key

Keep the raw key in **`anthropic.key` at the repository root**; copy the supplied `.example` file once and replace its placeholder. Restrict access with `chmod 600 anthropic.key`. Both initial scoring and feedback load it automatically. `ANTHROPIC_API_KEY` in the environment takes precedence. Keys are ignored by Git and excluded from the public handoff; provide HTE's key separately. Never add a key to robot Python or a configuration committed to GitHub.

Current official references: [Anthropic caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Opus 4.8](https://platform.claude.com/docs/en/models/opus-4-8/overview). Recorded rates are $5/M input, $25/M output, 0.1× cache reads and 2× one-hour cache writes. They are configurable if pricing changes.
