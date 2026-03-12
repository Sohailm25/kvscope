# Benchmark Validity Harness

## Purpose

Prevent accidental fake wins.

## Required run metadata

Every benchmark run must capture:

- git commit
- engine name and version
- model name
- GPU type
- relevant engine flags
- warmup configuration
- whether snapshots were used
- whether prefix caching was enabled
- workload ID
- run timestamp

## Required outputs

- raw JSON result artifact
- percentile summary
- goodput summary
- run manifest
- stderr/stdout log capture

## Required separations

- warmup separate from steady-state
- cold-start separate from warm-run analysis
- infrastructure effects called out explicitly if they occur

## Invalid benchmark patterns

- only mean latency
- no no-overlap control
- no mixed long/short workload
- no repeat runs
- changing multiple experimental variables at once
- hidden autoscaling changes during a run

## Minimum sanity checks

- same workload repeated three times produces similar ordering of results
- no-overlap workload shows limited cache benefit
- near-aligned workload performs worse than fully aligned reuse workload
- tail latency is reported, not just throughput

## Packaging rule

If a result cannot be traced back to a manifest and raw artifact, it should not be cited.
