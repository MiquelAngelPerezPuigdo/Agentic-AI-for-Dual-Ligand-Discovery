# Anthropic prompt caching

Prompt caching is enabled by default for both scoring campaigns. The API key and first-batch commands remain the same. Configuration is in `hte_inputs/campaign.json`, under `llm.prompt_cache`:

```json
{
  "enabled": true,
  "ttl": "1h",
  "read_multiplier": 0.1,
  "write_5m_multiplier": 1.25,
  "write_1h_multiplier": 2.0
}
```

The one-hour lifetime accommodates long reasoning responses. The second campaign begins after the first reaction and LC sequence, so it normally writes a new cache entry. This does not preserve the initial cache across the four-hour reaction.

## Request layout

The fixed system instruction is followed by three user content blocks:

1. Fixed reaction conditions, objective, ligand structures and literature evidence, with an explicit `cache_control` breakpoint.
2. The complete measured feedback shared by the campaign's repeats, with another explicit breakpoint.
3. The shuffled candidate IDs, with no cache breakpoint.

The fixed blocks are serialized identically across repeats. Output-schema property ordering is canonical and remains identical for the same candidate cohort: schema changes can invalidate Anthropic's prompt cache. With smaller configured batches, cohorts stay fixed and their internal candidate order is shuffled independently for each repeat. The default still scores all 465 first-round candidates, or all 400 remaining second-round candidates, in each request.

The first real scoring response for each schema completes before its followers are submitted. It warms the cache without an additional paid warm-up request. Subsequent scoring requests can run in parallel. All five responses remain separately generated; previous scores or assistant answers are not supplied as cached context.

## Cost and verification

For the configured Opus 4.8 prices, one-hour writes cost 2× normal input, five-minute writes cost 1.25× and reads cost 0.1×. These multipliers are explicit configuration values. The preflight assumes every pending request misses cache, charges input at the selected write rate and reserves one retry. It does not rely on hoped-for cache savings to stay within the estimated $20 cap.

Each response record saves the provider's usage counters and a separate cost breakdown for uncached input, cache writes, cache reads and output. Detailed five-minute/one-hour write counters are used when available; otherwise the configured TTL is recorded as the pricing assumption. `input_tokens` excludes cached reads and writes, so those amounts are added separately.

After each campaign, inspect `scoring/cache_summary.json`:

- `cache_read_input_tokens > 0` and `cache_hit_requests > 0` verify reported reuse.
- `cache_creation_input_tokens > 0` with no reads means entries were written but reuse was not reported.
- Both counters zero means no cache activity was reported. Check prompt size, TTL and request consistency before a later campaign; the software does not buy extra retries solely to obtain cache hits.

The score command prints the cache status and hit counts. Cache summary costs estimate the returned responses using the configured rates; SDK retries whose usage is not returned cannot be itemized. The budget preflight reserves for them.

The mocked tests and offline rehearsal verify request layout, stable schemas, scheduling and accounting. **Live provider cache hits require a real API run** and are not established by the rehearsal. Anthropic documents a 1,024-token minimum for Opus 4.8; the normal full-inventory context is intended to exceed that threshold.

Primary references: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [structured-output cache invalidation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#prompt-modification-and-token-costs).
