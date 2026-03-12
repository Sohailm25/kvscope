ABOUTME: Repository entrypoint for KVScope — a cache-aware AI observability lab.
ABOUTME: Leads with findings, describes system architecture, and points to reproduction steps.

# KVScope

A cache-aware AI observability lab studying KV cache policy behavior on vLLM serving workloads.

## Key Findings

**Cache policy ordering depends on workload geometry, and it flips.**

Across 9 workload families run on vLLM (Modal), with live Prometheus metric scraping and offline replay through LRU/FIFO/LFU simulators:

- **Capacity crossover (locality-return):** LRU > LFU at cache capacities 2-3, then LFU > LRU at capacity 4. The "best" eviction policy depends on how much cache you have.
- **Workload-specific policy selection:** hotset-scan consistently shows LFU > LRU > FIFO across capacities 2-5. locality-shift consistently shows LRU > LFU. No single policy wins everywhere.
- **Live cache evidence:** Cache-on vs cache-off toggles across 5 families confirm the engine's prefix cache is active and measurable (e.g., aligned-prefix: 0.5 hit rate on, 0.0 off; eviction-ordering: 0.417 on, 0.0 off).
- **Replay-live agreement:** Derived traces replayed through simulated policies preserve the same directional ordering as live measurements.

These are directional findings on small N (2-4 runs per family). They show *where* policy differences emerge, not production-grade effect sizes.

## System Architecture

```
serve/          vLLM on Modal + Prometheus metric scraping
bench/          9 workload families (aligned-prefix, near-aligned, mixed-long-short,
                bursty-arrivals, eviction-ordering, hotset-scan, locality-shift,
                locality-return, no-overlap-control)
kvtrace/        Trace builder (live → derived blocks) + LRU/FIFO/LFU replay engine
analysis/       Corpus index + frozen claim registry
kvscope_mcp/    Read-only MCP server over frozen evidence corpus
scripts/        Build pipelines: reports, tables, figures, capacity sweeps
artifacts/      Run directories, manifests, figures
```

### How It Works

1. **Serve:** `modal run serve/modal_vllm_app.py` launches a vLLM instance, sends a workload, scrapes Prometheus metrics (prefix cache hits/queries, prefill latency), and writes structured run artifacts.
2. **Trace:** `kvtrace/trace_builder.py` derives block-level cache traces from live run data. These are *derived* from request/response structure, not vLLM kernel instrumentation.
3. **Replay:** `kvtrace/replay.py` replays derived traces through textbook LRU/FIFO/LFU simulators at varying cache capacities.
4. **Bridge:** Scripts compare live cache behavior against replay predictions to check directional agreement.
5. **Query:** The MCP server exposes the frozen corpus for structured search (runs, metrics, findings, replay summaries, capacity curves).

### Honest Limitations

- Traces are derived from request structure using OrderedDict simulation, not vLLM kernel-level instrumentation. They model *what blocks would be accessed*, not exact engine state.
- Sample sizes are small (2-4 runs per family). Claims are directional, not statistically significant.
- Client TTFT is noisy. Direct claims are limited to live cache-hit visibility and directional prefill improvement.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests
```

## Reproduce Key Results

```bash
# Run a cache-on / cache-off pair for aligned-prefix
.venv/bin/modal run serve/modal_vllm_app.py \
  --workload-family aligned-prefix --num-requests 2 \
  --shared-prefix-blocks 4 --unique-suffix-tokens 8 --output-tokens 8 \
  --prefix-caching-mode on --run-slug repro-aligned-cache-on

.venv/bin/modal run serve/modal_vllm_app.py \
  --workload-family aligned-prefix --num-requests 2 \
  --shared-prefix-blocks 4 --unique-suffix-tokens 8 --output-tokens 8 \
  --prefix-caching-mode off --run-slug repro-aligned-cache-off

# Build replay capacity sweep from existing traces
.venv/bin/python scripts/build_replay_capacity_sweep.py

# Query the MCP corpus
.venv/bin/python scripts/run_kvscope_mcp_server.py
```

## Evidence

- Frozen claims: [history/CORE-V1-CLAIMS.md](history/CORE-V1-CLAIMS.md)
- Result bundle: [docs/kvscope_result_bundle.md](docs/kvscope_result_bundle.md)
- Benchmark figures: [artifacts/figures/](artifacts/figures/)
- Design rationale: [history/DESIGN-RATIONALE.md](history/DESIGN-RATIONALE.md)
