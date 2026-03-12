ABOUTME: Architecture decision record for the initial deployment baseline.
ABOUTME: This captures why Modal is acceptable for the first implementation and how claims stay bounded.

# ADR-0006: Use Modal As The Initial Deployment Baseline

## Status

Accepted

## Context

`KVScope` needs a practical way to run one GPU-backed serving baseline early enough to generate real artifacts.

The project does not need a production cluster manager in Phase 1.

It does need:

- a fast path to one stable serving replica
- reproducible environment capture
- enough control to separate warmup, cold-start, and steady-state behavior

## Decision

Use Modal as the initial deployment baseline for the first `vLLM` implementation slice.

Do not treat Modal as a stand-in for a custom serving fabric or for distributed KV infrastructure.

## Rationale

- it is the fastest path from repo to one GPU-backed baseline
- it keeps the first implementation slice focused on observability and evidence capture rather than platform plumbing
- it is sufficient for the single-replica claims this project intends to make first

## Claim Boundaries

Allowed:

- claims about behavior on one engine, one deployment setup, and declared workload families
- claims that explicitly separate platform effects when they are visible

Not allowed:

- claims that Modal behavior generalizes to custom low-latency serving stacks
- claims that serverless orchestration answers distributed KV questions

## Required Controls

- warmup runs separated from steady-state analysis
- cold-start runs separated from warm runs
- autoscaling changes avoided during controlled comparisons
- run manifests capturing engine, model, GPU, and relevant flags

## Revisit Conditions

- if Modal injects too much variance to support the benchmark story
- if required engine instrumentation is blocked by the deployment model
- if the project needs stronger host-level control for credible comparisons
