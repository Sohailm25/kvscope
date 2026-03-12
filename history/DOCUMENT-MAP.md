ABOUTME: Source-of-truth map for the repo.
ABOUTME: Incoming agents should read this first to avoid treating historical planning notes or exploratory research as current authority.

# Document Map

## Purpose

This file defines which documents are authoritative, which are supporting, and which are historical context only.

If two documents appear to conflict, use this file to resolve the conflict.

## Tier 1: Current Authority

These define what the project is and what the evidence shows.

- [README.md](../../README.md)
- [CORE-V1-CLAIMS.md](CORE-V1-CLAIMS.md)
- [CLAIMS-AND-NON-CLAIMS.md](CLAIMS-AND-NON-CLAIMS.md)
- [DESIGN-RATIONALE.md](DESIGN-RATIONALE.md)
- [docs/kvscope_result_bundle.md](../../docs/kvscope_result_bundle.md)
- [research-card.yaml](../../research-card.yaml)
- [EXPERIMENT-DESIGN.md](EXPERIMENT-DESIGN.md)
- [ARTIFACT-CONVENTIONS.md](ARTIFACT-CONVENTIONS.md)
- ADRs under [history/adr](adr)
- [kvtrace/TRACE-SCHEMA.md](../../kvtrace/TRACE-SCHEMA.md)
- [bench/WORKLOAD-SPEC.md](../../bench/WORKLOAD-SPEC.md)

## Tier 2: Supporting Current Context

These are useful, but they do not override Tier 1.

- [KNOWLEDGE-SYSTEM-DESIGN.md](KNOWLEDGE-SYSTEM-DESIGN.md)
- [EXPERIMENTAL-PLAN-V1.md](EXPERIMENTAL-PLAN-V1.md)
- [ENGINE-SCORECARD.md](ENGINE-SCORECARD.md)
- [EXECUTION-READINESS.md](EXECUTION-READINESS.md)
- [LIVE-TO-REPLAY-BRIDGE.md](LIVE-TO-REPLAY-BRIDGE.md)
- [BENCHMARK-VALIDITY-HARNESS.md](BENCHMARK-VALIDITY-HARNESS.md)
- module READMEs in `serve/`, `bench/`, `kvtrace/`, and `artifacts/`

## Tier 3: Historical Context Only

These explain how we got here. They are not implementation authority.

- [PLAN.md](PLAN.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [IMPLEMENTATION.md](IMPLEMENTATION.md)
- [FINAL-PROJECT-OUTLINE.md](FINAL-PROJECT-OUTLINE.md)
- [INVESTIGATOR-BUILD-SPEC.md](INVESTIGATOR-BUILD-SPEC.md) — investigator layer was removed (see DESIGN-RATIONALE.md §7)
- [journal/current_state.md](../../journal/current_state.md)
- files under [journal/logs](../../journal/logs)
- archived docs under [history/archive](archive)

## Research

Everything under [research](../../research) is exploratory input.

It is useful context, but it is not authoritative by itself.

Research should influence Tier 1 only after it has been synthesized into Tier 1 or Tier 2 documents.

## Conflict Resolution Rule

If there is a conflict:

1. trust Tier 1
2. then Tier 2
3. treat Tier 3 and `research/` as historical context only
