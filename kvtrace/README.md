ABOUTME: Module boundary for trace-driven cache-policy replay.
ABOUTME: This module matters only if the trace contract is strong enough to support honest replay claims.

# KVTrace

Responsibilities:

- trace schema
- event ingestion
- policy replay
- miss-ratio and eviction analysis
- live-to-replay bridge comparison

Planned first input:

- one `kvtrace-v2` NDJSON file emitted from `serve/`

Planned first outputs:

- replay summary JSON
- policy comparison table
- one bridge note explaining what the replay result does and does not prove

Baseline policy:

- LRU

First stronger comparison:

- one simple alternative such as S3-FIFO-style replay
