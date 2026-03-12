> Current claims authority.
> Any outward-facing summary should be checked against this file.

# Claims And Non-Claims

## Claims

KVScope claims that it can:

- generate repeatable workloads from synthetic templates targeting specific cache-reuse geometries
- measure how reuse patterns affect serving behavior on one engine (vLLM) and one deployment (Modal)
- derive block-level cache traces from request/response structure (not kernel instrumentation)
- replay derived traces against LRU, FIFO, and LFU policies at varying cache capacities
- show where policy ordering depends on workload geometry and cache budget
- publish artifacts that let others inspect how conclusions were reached

## Non-Claims

KVScope does not claim that it:

- reconstructs exact kernel-level cache state (traces are derived, not instrumented)
- proves that offline replay results automatically transfer to live serving
- discovers a universally best cache policy
- provides statistically significant results (N=2-4 per family)
- decomposes full end-to-end latency (client TTFT is noisy)
- is a new inference runtime, distributed KV system, or novel crawler

## Trace Derivation Honesty

The replay engine operates on **derived traces**, not vLLM kernel instrumentation:

- `kvtrace/trace_builder.py` constructs block access sequences from request/response structure using OrderedDict-based simulation
- This models *what blocks would be accessed* given the workload geometry
- It does NOT capture vLLM's internal eviction decisions, scheduling order, or memory management
- The replay bridge validates that derived traces produce directionally consistent policy orderings — not that they exactly replicate engine behavior

## Falsification Criteria

Each major finding could be disproven by:

| Finding | Would Be Disproven If |
|---|---|
| Capacity crossover (locality-return) | Additional runs at the same capacities show LRU >= LFU at capacity 4, or LFU >= LRU at capacities 2-3 |
| Hotset-scan LFU advantage | Repeated runs fail to maintain LFU > LRU > FIFO ordering |
| Locality-shift LRU advantage | Repeated runs fail to maintain LRU > LFU ordering |
| Replay-live agreement | Live cache-on/off behavior contradicts replay policy ordering direction |
| Cache toggle signal | Cache-off runs show non-zero prefix-cache hits (would indicate measurement error) |

## Strong Wording Rules

Allowed:
- "under this workload"
- "on this engine and setup"
- "directionally consistent with live measurements"
- "on N runs" (state the N)
- "derived traces suggest"

Forbidden:
- "solves"
- "proves universally"
- "exactly reconstructs"
- "best" (without qualifying workload and capacity)
- "state of the art"
- "statistically significant" (N is too small)

## Review Rule

Any README, talk track, or result summary should be checked against this file before being considered final.
