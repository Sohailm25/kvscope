ABOUTME: Readiness assessment after the hardening pass that locks scope, contracts, and first-step execution order.
ABOUTME: Use this document to answer whether the repo is ready for implementation and what still counts as implementation risk.

> Supporting decision document.
> This file does not override the final project outline, implementation roadmap, or ADRs.

# Execution Readiness

## Status

`KVScope` is ready to implement.

That claim has now been validated by the first live implementation slice.

The repo has moved from implementation-ready into early implementation with real artifact bundles.

That does not mean the technical risks are gone.

It means the repo now has enough clarity, contract surface, and guardrails to start building without reopening project identity, MVP shape, or basic evidence conventions.

## What Is Locked

- serving baseline:
  - `vLLM` first
- deployment baseline:
  - one-replica Modal path with explicit confound controls
- profile source:
  - `perf` as the primary sampled-profile source
- workload sources:
  - ShareGPT-style public prompts plus bounded docs-style inputs if needed
- artifact layout:
  - manifest-first packaging
- trace contract:
  - block-lifecycle-aware `kvtrace` schema
- readiness enforcement:
  - real example fixtures plus validator and tests

## Why We Can Start Now

The repo now answers the questions that previously blocked implementation:

- what the project is actually for
- what the core MVP is
- which engine we are starting with
- what artifacts runs must produce
- what a replay-capable trace must contain
- how to verify that the planning docs have not drifted back into stale wording

It also now contains proof that those decisions are enough to produce real outputs:

- live Modal-backed `vLLM` runs
- paired aligned-prefix and no-overlap artifact bundles
- a near-aligned boundary-case artifact bundle
- a mixed-long-short artifact bundle with recorded arrival offsets and per-request timing
- a bursty-arrivals artifact bundle with two aligned bursts and recorded overlap timing
- a three-run clean aligned-prefix repetition set
- a repeated no-overlap control family
- cross-run summary reports under `artifacts/manifests/`
- a live cache-toggle report built from scraped engine metrics
- an expanded live cache-toggle report spanning aligned-prefix and eviction-ordering
- a further expanded live cache-toggle report spanning aligned-prefix, eviction-ordering, and hotset-scan
- a repeated tradeoff live cache-toggle report spanning aligned-prefix, eviction-ordering, hotset-scan, and locality-shift
- a policy-surface live cache-toggle report that adds locality-return
- replayable `kvtrace` derived from those same runs
- a first live-to-replay bridge report tying those traces back to the live workload families
- a repeated-family spread report covering aligned, near-aligned, mixed, bursty, and control slices
- a repeated live-derived replay slice that separates `fifo` from `lru`
- a live-derived replay headroom slice that separates `fifo`, `lru`, and `lfu` on one bounded workload
- a live-derived replay adaptation slice where `lru` beats `lfu` once locality shifts
- a second live-derived recency-versus-frequency slice where locality-return flips between recency advantage and LFU headroom as replay capacity changes
- a replay-capacity sweep that shows where reuse and policy differences first appear across the current trace set
- a reviewer-facing result bundle that ties the repeated serving, live cache, and replay slices together
- a repeated benchmark-table artifact generated directly from those same summary reports
- a narrow figure bundle generated directly from the expanded cache-toggle and capacity-sweep summaries
- a pinned runtime contract that fixes the discovered `vLLM` and `transformers` compatibility bug

## Remaining Implementation Risks

These are no longer planning gaps.

They are implementation risks that need to be handled in code and experiments.

### 1. Engine observability may still be shallower than we want

If `vLLM` does not expose enough cache detail without invasive hooks, the live serving layer may only tell part of the story.

Response:

- keep measured and replayed claims separate
- make the live-to-replay bridge a first-class deliverable

Observed note:

- the aligned-prefix, eviction-ordering, hotset-scan, and locality-shift cache-toggle slices now prove that `vLLM` exposes enough surface for direct prefix-cache counters
- locality-return now adds a second recency-versus-frequency geometry with repeated direct live prefix-cache hits and lower measured prefill time across two cache-on/cache-off pairs, while client TTFT remains mixed
- it still does not fully explain client-observed TTFT, so Phase 3 claims must stay narrower than full latency decomposition
- aligned-prefix, eviction-ordering, and hotset-scan also show lower measured prefill time with cache-on
- locality-shift now adds repeated direct live cache-hit evidence without a cleaner prefill or TTFT result, which is still useful because it sharpens the replay tradeoff story
- hotset-scan replay headroom is now repeated across the baseline and revisit geometries
- locality-return replay crossover is now repeated across the baseline and concentrated geometries

### 2. Modal may contaminate the benchmark story

Modal is a pragmatic baseline, not a claim about production cluster architecture.

Response:

- separate warmup and cold-start runs
- pin configuration in manifests
- avoid autoscaling during benchmark comparisons
- weaken or bound claims if platform effects dominate

Observed note:

- the first slices are clearly usable as engineering evidence, but they are still single-replica cloud runs and not yet strong enough to support strong production-performance claims
- the current aligned, near-aligned, mixed-long-short, bursty, and control slices show the expected qualitative ordering, but the TTFT spread is still too wide for stable latency-envelope claims

### 3. `profiles/` may remain appendix-only

This lane is interesting but high-risk.

Response:

- require synthetic truth and calibration before promotion
- keep it off the critical path of the initial implementation

### 4. `ingest/` can still become scope creep

Response:

- use fixed corpora first whenever possible
- implement only the smallest deterministic corpus-builder if it materially improves realism

## Immediate Build Order

1. keep the new local artifact corpus and index as the retrieval substrate rather than falling back to manual report scanning
2. use the new MCP tool surface plus the thin FastAPI app as the default demo path rather than falling back to ad hoc report walkthroughs
3. keep the seeded harness as the contract layer while widening held-out Anthropic coverage beyond the current locked `15` tasks before broadening agent behavior further
4. keep claim wording narrow where client TTFT remains noisy or live metrics do not show a cleaner prefill story
5. keep the figure bundle and eval dashboards tied to report JSONs rather than becoming manual reporting surfaces
6. optional promotion decisions for `profiles/` and `ingest/`

## Readiness Checks

Run these before claiming the repo is still implementation-ready:

```bash
.venv/bin/python scripts/validate_repo_readiness.py
.venv/bin/python -m unittest discover -s tests
```

## What Would Reopen Planning

Only reopen the broad project plan if one of these happens:

- `vLLM` cannot support the minimum artifact story even with bounded instrumentation
- Modal platform effects make the results fundamentally uninterpretable
- the trace contract proves too weak once live events exist
- the core `serve + bench + kvtrace` MVP stops answering the project thesis
