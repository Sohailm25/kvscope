ABOUTME: Versioned event schema for replay-capable cache traces.
ABOUTME: The schema must preserve enough block lifecycle detail to support honest policy replay and live-to-replay comparison.

# KVTrace Schema v2

## Purpose

Represent cache-relevant serving events in a way that supports:

- replay against baseline and alternative policies
- block-alignment-aware analysis
- clear separation between measured, derived, and inferred fields
- bridge comparisons between live behavior and offline replay

## File Format

Default format:

- newline-delimited JSON

One file contains events from one run.

See:

- [kvtrace-v2.example.ndjson](artifacts/examples/kvtrace-v2.example.ndjson)

## Global Requirements

Every event must include:

- `schema_version`
- `run_id`
- `event_type`
- `timestamp_ns`
- `source_kind`
- `engine`
- `model`
- `workload_id`

Where:

- `source_kind = measured | derived | inferred`

## Event Families

### Request lifecycle

- `request_arrival`
- `request_dispatch`
- `request_complete`

### Request-level cache summary

- `prefix_cache_query`

### Block lifecycle

- `block_lookup`
- `block_hit`
- `block_insert`
- `block_pin`
- `block_unpin`
- `block_evict`

Without insert, lookup, and eviction events, the trace is not strong enough for serious replay.

## Common Request Fields

Request-scoped events should include:

- `request_id`

Useful optional request fields include:

- `prompt_tokens`
- `shared_prefix_tokens`
- `output_tokens_target`
- `block_size_tokens`

## Common Block Fields

Block-scoped events should include:

- `block_key`
- `block_index` when the event refers to a block within a request prefix

Useful optional block fields include:

- `token_start`
- `token_end`
- `block_id` if the engine exposes a runtime-specific identifier
- `prefix_group_id`

`block_key` is the replay identity.

`block_id` is runtime-local metadata only.

## Event Types

### `request_arrival`

Required fields:

- `request_id`
- `prompt_tokens`
- `output_tokens_target` when known

### `request_dispatch`

Required fields:

- `request_id`

### `prefix_cache_query`

Required fields:

- `request_id`
- `shared_prefix_tokens`
- `block_size_tokens`

Optional:

- `cache_salt`
- `adapter_id`

### `block_lookup`

Purpose:

- records that a request referenced a reusable full block candidate

Required fields:

- `request_id`
- `block_key`
- `block_index`
- `token_start`
- `token_end`
- `block_size_tokens`

### `block_hit`

Purpose:

- records that a looked-up block was found resident

Required fields:

- `request_id`
- `block_key`
- `block_index`

### `block_insert`

Purpose:

- records that a reusable block became resident

Required fields:

- `request_id`
- `block_key`
- `block_index`
- `token_start`
- `token_end`
- `block_size_tokens`

### `block_pin`

Purpose:

- records that a resident block became temporarily non-evictable because an active request depends on it

Required fields:

- `request_id`
- `block_key`
- `active_sequence_count`

### `block_unpin`

Purpose:

- records that a previously pinned block became evictable again

Required fields:

- `request_id`
- `block_key`
- `active_sequence_count`

### `block_evict`

Purpose:

- records eviction from the live cache when visible

Required fields:

- `block_key`
- `eviction_reason`

Optional:

- `priority`
- `estimated_reuse_score`
- `active_sequence_count`

### `request_complete`

Required fields:

- `request_id`
- `status`

Optional:

- `ttft_ms`
- `itl_p50_ms`

## Invariants

- timestamps must be monotonic within a file
- `block_hit` must follow a matching `block_lookup`
- `block_unpin` must correspond to a prior `block_pin`
- `block_evict` must not claim a block was evicted while still pinned

## Honesty Rule

Fields such as `estimated_reuse_score` must never be marked as `measured` unless the engine exposes them directly.

If a block lifecycle is reconstructed from logs rather than emitted directly, mark the relevant events as `derived`.

## Initial Replay Policies

- LRU baseline
- one stronger comparison policy using the same trace fields

The schema is designed so replay can move beyond pure recency without a redesign.
