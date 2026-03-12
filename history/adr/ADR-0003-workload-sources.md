ABOUTME: Architecture decision record for workload and corpus sources.
ABOUTME: Fixing sources early prevents scope drift and cherry-picked workloads.

# ADR-0003: Lock Initial Workload Sources

## Status

Accepted

## Context

KVScope needs:

- one public realistic workload
- one bounded crawled corpus
- deterministic synthetic templates

## Decision

Use the following initial sources:

- public realistic prompts:
  - ShareGPT-style chat prompts compatible with existing serving benchmarks
- bounded crawl domains:
  - `docs.vllm.ai`
  - `docs.sglang.ai`
  - `modal.com/docs`
- synthetic workload families:
  - no-overlap
  - full-block-aligned reuse
  - near-aligned reuse
  - mixed long/short
  - bursty arrivals
  - scan-like adversarial

## Rationale

- ShareGPT-style prompts are recognizable and realistic enough to avoid synthetic-only evaluation
- documentation domains provide highly structured, repeated-template pages suitable for repeated-context workloads
- synthetic families are required to isolate specific cache and scheduling effects

## Consequences

Positive:

- bounded ingestion scope
- easier reproducibility
- clearer mapping from workload type to systems hypothesis

Negative:

- conclusions will not generalize to arbitrary web content
- crawled workloads may still need later pruning if they are too similar or too noisy

## Revisit conditions

- if robots or crawl practicality make any chosen domain awkward
- if the crawled corpus does not materially improve workload realism
