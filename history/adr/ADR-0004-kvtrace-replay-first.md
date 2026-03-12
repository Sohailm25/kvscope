ABOUTME: Architecture decision record for making kvtrace replay a first-class path instead of a shameful fallback.
ABOUTME: This choice is about implementation leverage and claim discipline.

# ADR-0004: Prefer Replay-First Policy Evaluation

## Status

Accepted

## Context

KVScope needs policy experiments.

Direct live-engine policy replacement is attractive, but early invasive engine changes risk:

- high maintenance burden
- weak reproducibility
- project stall before evidence is produced

## Decision

Treat `kvtrace/` replay as a first-class policy-evaluation path.

Do not frame replay as a fallback only after live instrumentation fails.

## Rationale

- trace-driven evaluation is already a serious systems method
- it preserves the core research question without forcing early engine surgery
- it allows stronger control over workloads and policy comparisons

## Consequences

Positive:

- faster path to publishable policy results
- clearer separation between live measurements and replayed analysis

Negative:

- replay claims must remain narrower than live-serving claims
- we still need one live-to-replay bridge experiment for credibility
