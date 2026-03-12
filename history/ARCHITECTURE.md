> Historical architecture synthesis: useful for context, but not the top source of truth.
> Use `history/FINAL-PROJECT-OUTLINE.md`, module specs, ADRs, and `history/DOCUMENT-MAP.md` for current implementation authority.

# Reconciled Architecture

## Bottom line

The project should stop trying to be "one thing for each systems topic."

It should become one coherent systems lab with two tightly related tracks:

1. serving and cache observability
2. profile-to-phase inference

Optional ingestion exists only to produce better workloads, not to be a product area.

## Reconciled thesis

The best current thesis is:

`Instrument a mature single-replica LLM serving engine to study how prefix/KV behavior affects tail latency and goodput, and build an approximate profile-to-phase inference module that explains serving behavior without overclaiming trace fidelity.`

This is narrower than the original concept and stronger.

## Where the agents agreed

- Reimplementing serving internals is a bad use of time.
- Modal is fine for a single-replica lab and bad as the basis for a stateful distributed KV story.
- A standalone concurrent LRU cache is not a novel OSS contribution.
- A generic crawler is a crowded space and weak as a central claim.
- Timeline reconstruction from sampling must be framed as approximate and uncertainty-aware.
- The project must live or die on measurement quality, not feature count.

## Where the agents diverged

### Crawler scope

Agent 1 pushed to drop the crawler entirely.

Agent 2 treated it as a plausible stretch if it creates more realistic prefix-sharing workloads.

Reconciled decision:

- crawler and ingestion are optional
- they are not MVP
- they should only exist if synthetic and public datasets fail to create convincing workload realism

### Cache-policy experimentation mechanism

Agent 1 leaned toward a CacheBench-for-KV-caches style contribution.

Agent 2 leaned toward instrumenting a serving engine and, if tractable, swapping policies in or around it.

Reconciled decision:

- do not commit early to invasive engine policy surgery
- design the project so policy experimentation can happen offline via extracted traces if needed
- prefer a `kvtrace/` replay path over a fragile engine fork

This is a key change because it preserves the experimental thesis without forcing a bad implementation bet.

## Current architectural throughline

### `serve/`

Purpose:

- run one engine replica on Modal
- expose minimal inference entrypoints
- collect queueing, latency, and cache-related metrics

Expected contents:

- engine adapter for vLLM or SGLang
- Modal deployment code
- instrumentation hooks or metric collectors
- result emission for downstream analysis

Specific research-grounded requirement:

- expose enough data to reason about prefix cache hits, misses, and block-boundary effects without immediately forking engine internals

### `bench/`

Purpose:

- define workloads
- execute controlled runs
- store reproducible artifacts

Expected contents:

- synthetic prompt generators
- public prompt dataset runners
- goodput and percentile reporting
- warmup and cold-start controls

Specific research-grounded requirement:

- include full-block-aligned and near-aligned prefix-sharing workloads because current engines only reuse full cached blocks

### `kvtrace/`

Purpose:

- convert serving runs into cache-relevant traces
- replay policies offline without rewriting core engine internals

Expected contents:

- trace schema for prefix/block events
- policy implementations for comparison
- miss-ratio and eviction analysis

Specific research-grounded requirement:

- prefer trace-driven policy evaluation first, following the logic of tools like libCacheSim, before committing to fragile live-engine policy surgery

Why this module matters:

It gives the project a strong systems core even if the serving engine resists internal modification.

### `profiles/`

Purpose:

- ingest time-preserving sampled profiles
- infer coarse serving phases
- validate against traced ground truth

Expected contents:

- parsers for profile input formats
- segmentation and boundary inference
- uncertainty and calibration reporting

Specific research-grounded requirement:

- use time-preserving profile inputs such as `perf` or JFR; aggregate-only profile dumps are not enough for timeline claims

### `ingest/`

Purpose:

- optionally create workload corpora

Expected contents:

- deterministic corpus preparation only
- no ambition to be a generic crawler product

## Strong recommendation

If we lock the direction now, the project should center:

- `serve/`
- `bench/`
- `kvtrace/`
- `profiles/`

with `ingest/` implemented only in the smallest bounded form needed for end-to-end realism.

## What we should not claim

- not a new serving engine
- not a production distributed KV system
- not a novel crawler
- not exact trace reconstruction
- not a general observability platform

## What we can credibly claim if executed well

- strong cache-aware serving instrumentation
- honest policy experiments grounded in real or replayed traces
- careful treatment of Modal as a constrained deployment environment
- approximate sampled-profile phase inference with explicit uncertainty

## Risks now considered real

- engine instrumentation may be harder than it looks
- Modal lifecycle behavior can confound measurements
- cache wins can be fake if workloads are too overlap-heavy
- cache wins can also be fake if workloads ignore full-block reuse constraints
- the profile-to-phase module can become decorative if validation is weak
- adding ingestion too early can quietly turn this into two projects

## Remaining execution questions

- vLLM or SGLang for the first tractability spike
- online policy swapping versus offline replay as the main cache experiment path
- exact benchmark matrix and publishable evidence thresholds
- how small `ingest/` can stay while still improving the story
