ABOUTME: Final project brief that reconciles production realism, observability value, and scope discipline.
ABOUTME: This is the main decision document for what KVScope is actually building and what must earn its place.

> Current top-level project authority.
> If planning-era docs conflict with this file, trust this file.

# Final Project Outline

## Project Name

`KVScope`

Subtitle:

`A cache-aware AI observability lab for explaining serving regressions with measured facts, replayable traces, and calibrated inference.`

## One-Sentence Thesis

Build a small, well-instrumented system that turns realistic workloads into evidence about serving behavior, separates measured facts from replayed analysis, and uses explicit uncertainty whenever we infer more than the engine directly exposes.

## The Real Problem

Teams operating LLM serving systems can usually answer:

- how many tokens per second a system produced
- whether a run felt fast or slow

They often cannot answer cleanly:

- whether prefix or KV reuse actually helped under a realistic workload
- whether a cache-policy change mattered outside a toy trace
- whether a latency shift came from queueing, prefill pressure, or some other serving phase when exact tracing is unavailable

`KVScope` exists to answer that narrower question with a better evidence model.

## Why This Project Is Coherent

The end-to-end story is:

1. generate or build a bounded workload source
2. serve that workload through one well-understood baseline
3. capture measured serving behavior and cache-relevant events
4. replay the resulting trace against policy baselines
5. publish what was measured, what was replayed, and what was inferred

Every module exists to answer the same systems question:

`What changed latency, and how confidently can we explain it?`

## Distinctive Project Traits

The value of this repo is not novelty-by-feature-count.

The value is:

- clean separation between measured, derived, and inferred data
- block-alignment-aware workload design instead of generic “cache on/off” demos
- a live-to-replay bridge so offline analysis is not detached from the real system
- explicit non-claims and negative-result expectations

## Core Build

### `serve/`

Purpose:

- run one serving baseline with strong observability discipline

Scope:

- one model family
- one GPU class
- one serving engine baseline: `vLLM`
- minimal request path and streaming support
- metrics for queueing, TTFT, ITL, throughput, and exposed cache behavior

Why it exists:

- this is the system under study

What it is not:

- not a new inference runtime
- not distributed serving infrastructure

### `bench/`

Purpose:

- generate workloads and benchmark the serving path

Scope:

- public realistic workload
- no-overlap control
- full-block-aligned prefix workload
- near-aligned prefix workload
- mixed long/short workload
- bursty arrival workload
- scan-like adversarial workload

Why it exists:

- it converts serving claims into evidence and negative controls

### `kvtrace/`

Purpose:

- turn serving runs into replayable cache traces with enough lifecycle detail to compare policies honestly

Scope:

- trace schema for lookup, hit, insert, pin/unpin, and eviction events
- LRU baseline
- one stronger comparison policy
- miss-ratio and eviction analysis
- live-to-replay bridge experiment

Why it exists:

- it creates a serious policy-analysis path without forcing premature engine surgery

What it is not:

- not proof that an offline policy win automatically improves live serving

## Bounded Extensions

These modules are useful, but they must earn their place by improving the main thesis rather than widening scope.

### `profiles/`

Purpose:

- investigate whether sampled profiles can recover coarse serving phases with calibrated uncertainty

Status:

- secondary lane
- promoted only if the synthetic-truth harness shows credible calibration

What it is not:

- not exact tracing
- not a general profiling platform

### `ingest/`

Purpose:

- build a tiny, deterministic corpus only if fixed public corpora are insufficient for realistic reuse workloads

Status:

- supporting utility, not core product surface

What it is not:

- not a generic crawler framework
- not a Firecrawl/Crawl4AI competitor

## System Design In One Page

### Main Data Flow

1. `bench/` loads public prompts and optional bounded corpus material
2. `serve/` runs the vLLM baseline on Modal and records benchmark artifacts
3. `kvtrace/` exports replayable cache events from the same runs
4. `kvtrace/` compares policy baselines on those traces
5. `profiles/` stays off the critical path and only analyzes synthetic or selected serving runs once validated
6. `docs/` and `artifacts/` publish evidence, caveats, and negative results

### Hot Path

The serving hot path is only:

- workload request
- serving engine
- metrics and trace emission

Neither `ingest/`, `kvtrace/`, nor `profiles/` belongs in the serving hot path.

## MVP Definition

The implementation MVP is:

- `serve/`
- `bench/`
- `kvtrace/`

`profiles/` is promoted only after the synthetic-truth harness clears its gate.

`ingest/` is implemented only in the smallest form needed for workload realism.

## End-To-End Demo Story

1. run two or more workload families, including a negative control
2. compare prefix-caching behavior on the same serving baseline
3. show TTFT, p99, and goodput shifts
4. export replayable traces from those same runs
5. compare LRU versus one stronger policy offline
6. show one place where replay and live behavior line up directionally

If `profiles/` clears its gate, add one validated phase-inference appendix.

## What We Will Claim

- the project gives a reproducible way to study how reuse patterns affect serving outcomes on one baseline
- the project gives a trace-driven way to compare cache policies without rewriting the serving engine
- the project keeps measured facts separate from replayed and inferred conclusions

## What We Will Not Claim

- we built a better serving engine than `vLLM`
- we solved distributed KV serving
- we built a novel crawler
- we can exactly reconstruct traces from sampling profiles
- an offline policy ranking automatically proves a production online win

## Decision Lock

Unless new evidence is unusually strong, this is the project shape we should execute.
