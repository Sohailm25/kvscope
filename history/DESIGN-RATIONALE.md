# Design Rationale

This document explains the key decisions behind KVScope's architecture. Each section covers what was chosen, what was not, and why.

## 1. Derived Traces, Not Kernel Instrumentation

**Decision:** Build block-level cache traces from request/response structure using an OrderedDict LRU simulation (`kvtrace/trace_builder.py`), rather than instrumenting vLLM's internal cache manager.

**Why:** vLLM's prefix cache implementation is tightly coupled to its scheduler and memory manager. Instrumenting it would require forking vLLM, maintaining a patch against a rapidly moving codebase, and validating that the instrumentation doesn't perturb the behavior being measured. For a research question about *whether policy ordering varies with workload geometry*, derived traces are sufficient — they capture which blocks *would be accessed* given the prompt structure.

**Trade-off accepted:** Derived traces don't capture vLLM's actual eviction decisions, scheduling order, or memory pressure effects. Every trace event is tagged `source_kind="derived"` to make this explicit. The replay bridge validates directional agreement, not exact reproduction.

**What would change this:** If the research question shifted to *why does vLLM's specific implementation make the choices it does*, kernel instrumentation becomes necessary. The current design accommodates this by separating trace building from replay — a kernel-instrumented trace builder could drop in without changing the replay engine.

## 2. Tokenizer-Aligned Workload Generation

**Decision:** All workloads are constructed from token sequences first, then materialized to strings (`bench/model_workloads.py`). The `_find_stable_token_ids` function discovers tokens that survive encode-decode roundtrips.

**Why:** vLLM's prefix cache hashes at the block level (groups of tokens). If workloads are built from strings, the actual token boundaries depend on the tokenizer's merge rules — shared prefixes might not align to block boundaries as intended. By building from token IDs and verifying roundtrip stability, every workload family has guaranteed N-block prefix sharing.

**Alternative rejected:** Building prompts from natural language sentences and hoping the tokenizer produces the right block alignment. This would make cache-hit behavior dependent on tokenizer internals rather than workload design.

## 3. Prometheus Metric Scraping with Version-Aware Aliases

**Decision:** Scrape vLLM's Prometheus `/metrics` endpoint before and after each workload run, using alias dictionaries for metric names (`serve/live_metrics.py`).

**Why:** vLLM renames Prometheus metrics across versions (e.g., `vllm:prefix_cache_hits` vs `vllm:gpu_prefix_cache_hits`). Alias dictionaries map all known names to canonical keys, so analysis code doesn't break when the engine upgrades. The before/after differential isolates the benchmark's contribution from background system activity.

**Alternative rejected:** Logging from inside the vLLM process. This would require patching the server, which creates the same maintenance burden as kernel instrumentation.

## 4. Two Modal Functions for Cache On/Off

**Decision:** Separate `serve_vllm_prefix_on` and `serve_vllm_prefix_off` Modal functions in `serve/modal_vllm_app.py`, rather than a single function with a runtime parameter.

**Why:** Prefix caching mode must be set at vLLM server startup. A single function with runtime switching would need to restart the server between runs, introducing cold-start latency and potential state leakage. Separate functions bake the configuration into the container image, making each run independent.

## 5. MCP Server over REST API

**Decision:** Expose the frozen evidence corpus through a read-only MCP server (`kvscope_mcp/server.py`) using FastMCP with structured outputs, rather than a REST API.

**Why:** The corpus is consumed by Claude (via Claude Code or other MCP-aware clients), not by a web frontend. MCP provides typed tool definitions with Pydantic models, which means Claude can discover available data, parse responses without brittle JSON key assumptions, and compose queries (e.g., "compare these two runs' replay results"). A REST API would require a separate OpenAPI spec and wouldn't integrate with Claude's tool-use loop.

**Design choice within MCP:** All tools return structured Pydantic models with `structured_output=True`. The `read_artifact_text` tool supports `heading_query` to extract specific markdown sections from large reports, avoiding loading entire documents for a single data point.

## 6. Nine Workload Families

**Decision:** Design 9 specific workload families, each targeting a distinct cache-reuse geometry, rather than random or naturalistic prompts.

**Why:** The research question is about *where* policy ordering varies. Random workloads produce aggregate behavior that hides the geometry-specific effects. Each family isolates one variable:

| Family | What It Isolates |
|---|---|
| aligned-prefix | Clean positive case: shared prefix, guaranteed reuse |
| near-aligned-prefix | Boundary case: prefix miss tokens reduce reuse |
| no-overlap-control | Negative case: zero reuse expected |
| mixed-long-short | Interference: long request evicts short request's cache |
| bursty-arrivals | Pressure: burst of aligned requests under scheduling overlap |
| eviction-ordering | FIFO vs LRU under sequential eviction pressure |
| hotset-scan | Frequency-based reuse: repeated hot set benefits LFU |
| locality-shift | Temporal locality: recent access benefits LRU |
| locality-return | Capacity-dependent crossover between recency and frequency |

## 7. What Was Cut and Why

**Removed:** Investigator agent (`agent/`), web app (`web/`), eval harness (`evals/`), associated scripts and tests.

**Why they were built:** The investigator was intended as a bounded question-answering layer over the MCP corpus. The web app was a demo surface. The eval harness measured investigator quality.

**Why they were cut:**
- The investigator was a switch statement routing to canned answers via string matching. It did not demonstrate research engineering skill — it demonstrated prompt wiring.
- The Anthropic-backed investigator added a post-hoc `_enforce_route_boundaries` function doing answer surgery. This is the kind of scaffolding that looks worse the more you examine it.
- The eval harness produced perfect scores (1.0 across all metrics) because the test set was derived from the same canned answers. This is data leakage, not eval quality.
- The web app existed only to showcase the investigator.

**What remains is stronger:** The replay engine, trace builder, live metrics scraper, workload generators, and MCP server are genuine systems work. Removing the investigator layer eliminates the weakest components and lets the strong parts speak for themselves.

## 8. Honest Framing Over Confident Framing

**Decision:** Frame findings as directional with small N, rather than claiming statistical significance.

**Why:** 2-4 runs per workload family is not enough for confidence intervals, p-values, or robust effect size estimates. Claiming significance would be dishonest and immediately obvious to anyone with statistical training. Framing as "directional findings showing *where* policy differences emerge" is accurate and still interesting — the capacity crossover is a real structural finding even at N=4.

**What would strengthen it:** More runs per family (20+) would enable proper statistical testing. This is a matter of compute budget and time, not design limitation.
