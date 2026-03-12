ABOUTME: Reviewer-facing result bundle summarizing KVScope findings with evidence and caveats.
ABOUTME: Leads with the capacity crossover finding, then walks through supporting evidence.

# KVScope Result Bundle

## The Headline Finding

**Cache policy ordering depends on workload geometry and cache capacity. It flips.**

On live-derived traces from locality-return workloads, replayed through LRU/FIFO/LFU simulators:
- LRU > LFU at cache capacities 2 and 3
- LFU > LRU at capacity 4

This is a capacity crossover: the "best" eviction policy changes depending on how much cache you have. It was reproduced across 4 live-derived traces.

## Supporting Evidence

### 1. Workload-Specific Policy Selection

No single cache policy wins everywhere. Across the capacity sweep:

| Workload | Consistent Winner | Capacities Tested |
|---|---|---|
| hotset-scan | LFU > LRU > FIFO | 2, 3, 4, 5 |
| locality-shift | LRU > LFU | 2, 3, 4, 5 |
| locality-return | **Flips** (LRU→LFU) | 2, 3, 4 |
| eviction-ordering | LRU > FIFO | 2, 3 |

### 2. Live Cache Evidence (5 Families)

Cache-on vs cache-off pairs confirm the engine's prefix cache is active and measurable via Prometheus scraping:

| Family | Cache-On Hit Rate | Cache-Off Hit Rate | Runs |
|---|---|---|---|
| aligned-prefix | 0.500 | 0.0 | 1 on / 1 off |
| eviction-ordering | 0.417 | 0.0 | 3 on / 1 off |
| hotset-scan | 0.312 | 0.0 | 2 on / 1 off |
| locality-shift | 0.375 | 0.0 | 2 on / 2 off |
| locality-return | 0.375 | 0.0 | 2 on / 2 off |

### 3. Qualitative Cache Ordering (Repeated)

Derived block hits show expected ordering across repeated runs:
- aligned-prefix: 12 hits across 3 runs
- near-aligned-prefix: 9 hits across 3 runs
- no-overlap-control: 0 hits across 2 runs

### 4. Replay-Live Agreement

Replay policy ordering on derived traces matches the directional behavior observed in live serving. The replay bridge is not proof that offline policy wins transfer to live — it shows the traces carry enough signal to separate policies.

## Methodology

1. **Live serving:** vLLM on Modal with Prometheus metric scraping (`serve/`)
2. **Trace derivation:** Request/response structure → derived block-level traces (`kvtrace/trace_builder.py`). These are OrderedDict simulations of block access patterns, not vLLM kernel instrumentation.
3. **Replay:** Derived traces replayed through textbook LRU/FIFO/LFU at varying cache capacities (`kvtrace/replay.py`)
4. **Bridge comparison:** Live cache metrics compared against replay predictions for directional agreement

## Artifacts

- Benchmark figures: [artifacts/figures/](../artifacts/figures/)
- Capacity sweep data: [artifacts/manifests/](../artifacts/manifests/)
- Frozen claims: [history/CORE-V1-CLAIMS.md](../history/CORE-V1-CLAIMS.md)
- MCP server over corpus: [kvscope_mcp/server.py](../kvscope_mcp/server.py)

## Caveats

- **Small N.** 2-4 runs per family. Claims are directional, not statistically significant.
- **Derived traces, not kernel traces.** Replay models what blocks *would be accessed* given request structure. It does not capture vLLM's internal eviction decisions.
- **One engine, one deployment.** All runs on vLLM via Modal. Different engines or configurations may behave differently.
- **Client TTFT is noisy.** Direct claims are limited to cache-hit visibility and directional prefill improvement, not full end-to-end latency decomposition.
- **Replay is a bridge artifact.** The capacity sweep is an offline budget exercise over live-derived traces, not a live cache-resizing experiment.
