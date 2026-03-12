# Engine Scorecard

## Decision target

Choose the first engine for Phase 0 and Phase 1.

This choice is about:

- observability
- benchmark ergonomics
- instrumentation tractability
- stability of semantics

It is not about declaring a universal best engine.

## Candidates

- `vLLM`
- `SGLang`

## Criteria

Scoring:

- `5` = best fit for KVScope right now
- `3` = acceptable with caveats
- `1` = poor fit for Phase 0

## Scorecard

| Criterion | vLLM | SGLang | Notes |
|---|---:|---:|---|
| Benchmark tooling maturity | 5 | 3 | vLLM has clearer documented benchmark tooling and goodput support. |
| Metrics documentation | 5 | 3 | vLLM docs are stronger for explicit metric surfaces. |
| Prefix-cache semantics documentation | 5 | 4 | Both are strong; vLLM is more explicit about full-block caching details. |
| Ease of initial deployment on Modal | 4 | 4 | Both are plausible; neither is clearly dominant from research alone. |
| Cache observability without deep forks | 4 | 3 | vLLM appears easier to start with from documented surfaces. |
| Prefix-sharing richness | 3 | 5 | SGLang's radix-style reuse is compelling for later experiments. |
| Risk of fast-moving internals affecting us | 3 | 2 | SGLang appears more in flux around memory cache internals. |
| Upstream familiarity for skeptical reviewers | 5 | 4 | vLLM is easier to recognize and explain as a baseline. |

## Preliminary recommendation

Start with `vLLM` first.

Why:

- better benchmark and metrics ergonomics
- clearer documented prefix-cache semantics
- lower risk that Phase 0 becomes blocked on instrumentation ambiguity

Keep `SGLang` as the comparison engine for a bounded secondary spike.

Why not choose SGLang first:

- it may eventually be more interesting for reuse semantics
- but Phase 0 benefits more from clarity than from maximum feature richness

## What would reverse this recommendation

- if a short spike shows vLLM exposes too little cache behavior without invasive changes
- if SGLang exposes much cleaner reuse instrumentation in practice

## Recommendation status

`Accepted for Phase 0 baseline, subject to quick spike validation.`
