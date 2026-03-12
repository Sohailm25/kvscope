ABOUTME: Architecture decision record for the initial serving engine choice.
ABOUTME: This records the first implementation baseline, not a universal winner.

# ADR-0001: Start With vLLM For Phase 0

## Status

Accepted

## Context

KVScope needs an initial serving engine for:

- a stable benchmark baseline
- observable prefix-cache semantics
- a credible Phase 0 tractability spike

The contenders were `vLLM` and `SGLang`.

## Decision

Use `vLLM` first for Phase 0 and Phase 1.

Keep `SGLang` as the bounded secondary comparison engine.

## Rationale

- stronger documented benchmark tooling
- stronger documented metric surfaces
- clearer prefix-cache semantics, especially full-block caching details
- lower risk that the initial project stalls on observability ambiguity

## Consequences

Positive:

- faster path to a benchmarkable baseline
- better chance of capturing disciplined artifacts early

Negative:

- may leave some richer reuse semantics unexplored initially
- a later SGLang comparison may still be needed

## Revisit conditions

- if vLLM proves too opaque for the cache-observability goals
- if SGLang's instrumentation path is clearly cleaner in practice
