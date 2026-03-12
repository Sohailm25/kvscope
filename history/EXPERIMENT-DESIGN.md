ABOUTME: Research-grounded experiment design for the serving, cache-policy, and profile-to-phase parts of the project.
ABOUTME: This file replaces generic benchmark advice with concrete workload, metric, and validation requirements.

> Current experiment authority.
> If earlier notes conflict with this file, trust this file.

# Experiment Design

## Purpose

This document defines the minimum experiment design needed for the project to be credible.

If a proposed feature cannot be evaluated within this framework, it should not be part of the MVP.

## Primary questions

### Serving and cache observability

- How much do prefix/KV reuse characteristics change TTFT, tail latency, and goodput?
- Which workload properties matter most: overlap ratio, block alignment, prompt length mix, or burstiness?
- Can we explain the observed latency shifts with cache and scheduler evidence rather than speculation?

### Cache-policy experiments

- Does an alternative policy improve miss ratio or latency under realistic trace shapes?
- Are gains robust under scan-like or low-overlap workloads, or only under toy high-overlap traffic?

### Profile-to-phase inference

- Can sampled, time-preserving profiles recover coarse serving phases with usable accuracy?
- Are the confidence estimates calibrated, or are we just drawing persuasive pictures?

## Metrics

### Serving metrics

- TTFT: p50, p95, p99
- inter-token latency: p50, p95, p99
- throughput: requests/sec and tokens/sec
- goodput under declared SLOs
- queueing delay separated from TTFT

### Cache metrics

- prefix cache queries and hits when the engine exposes them
- eviction count or rate when exposed
- occupancy or a defensible proxy
- block-aligned reuse versus partial-prefix reuse behavior

### Policy metrics

- miss ratio
- miss-ratio reduction relative to baseline
- tail-latency deltas attributable to policy change

### Profile-to-phase metrics

- boundary error
- interval IoU against traced truth
- duration error
- detection rate and false phase rate
- calibration of reported confidence

## Minimum workload suite

### 1. Public realistic baseline

Use a public prompt dataset such as ShareGPT-style requests to establish a realistic chat baseline.

Purpose:

- prevent the project from becoming a synthetic-only benchmark

### 2. No-overlap control

Construct prompts with effectively unique prefixes.

Purpose:

- verify that any measured cache win disappears when reuse disappears

### 3. Full-block-aligned prefix-sharing workload

Construct repeated prefixes whose shared length lands exactly on cache block boundaries.

Purpose:

- measure the best-case behavior the engine can actually realize

### 4. Near-aligned prefix-sharing workload

Construct repeated prefixes that are almost identical but miss one full block boundary.

Purpose:

- expose the full-block caching constraint and prevent inflated conclusions

### 5. Mixed long/short workload

Mix long-prompt requests with short interactive ones.

Purpose:

- expose prefill/decode interference and fairness problems

### 6. Bursty arrival workload

Send requests in bursts rather than only at steady uniform rates.

Purpose:

- reveal queueing behavior and Modal warm/cold confounds

### 7. Adversarial scan-like workload

Issue many low-reuse prefixes in sequence after a warm reusable working set.

Purpose:

- evaluate whether the policy or engine behaves badly under cache pollution

## Run protocol

- fix engine configuration for the whole comparison unless a specific ablation changes it
- pin infrastructure conditions during benchmark runs
- separate steady-state, warmup, and cold-start runs
- run at least three repetitions per configuration
- persist raw artifacts, not just summary plots

## Required ablations

### Serving ablations

- prefix caching on versus off
- cache size or usable KV budget sweep if the engine allows it
- request-rate sweep from low load to saturation
- mixed versus uniform prompt lengths

### Policy ablations

- baseline policy versus one alternative
- high-overlap versus low-overlap traces
- scan-mixed traces

### Profile-to-phase ablations

- sample-rate sweep
- single-thread versus multi-thread workload
- simple threshold baseline versus change-point-based inference

## Validation requirements for profile-to-phase inference

- use a time-preserving profile source such as `perf` or JFR
- generate traced ground truth for synthetic workloads
- compare inferred segments to truth using interval metrics
- publish both a degradation curve and a calibration plot
- explicitly report what phase durations are below the detection limit at each sample rate

## Evidence thresholds for a serious README

At minimum:

- one latency-throughput or goodput curve across at least three workload families
- one cache-policy comparison that shows both a win case and a failure case
- one profile-to-phase validation figure against traced truth with uncertainty shown
- one written caveat section explaining what the project does not claim

## What invalidates results

- only reporting mean latency
- only using high-overlap workloads
- mixing autoscaling changes into a benchmark unintentionally
- reporting profile-derived timelines without ground-truth validation
- claiming a policy win without describing the workload and cache-size regime
- drawing conclusions from single runs
