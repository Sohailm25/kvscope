ABOUTME: Execution plan reconciled against agent-1 and agent-2 research outputs.
ABOUTME: Keep the project centered on one falsifiable systems thesis and cut anything that weakens measurement quality.

> Historical planning note: this file is preserved for context.
> Current implementation authority lives in `README.md`, `history/FINAL-PROJECT-OUTLINE.md`, `history/IMPLEMENTATION.md`, and `history/DOCUMENT-MAP.md`.

# Project Plan

## Reconciled goal

Build a serious-but-bounded systems lab that answers one core question:

`How do prefix/KV cache behavior and cache-policy choices affect tail latency and goodput in single-replica LLM serving, and how much of those serving phases can we recover from sampling profiles with honest uncertainty?`

That is the current center of gravity.

Everything else is subordinate to that question.

## Reconciled non-goals

- building a new general-purpose crawler
- building a new general-purpose concurrent cache library
- building a better serving engine than vLLM or SGLang
- reimplementing paged attention, custom KV allocators, or scheduler internals as the primary project
- making multi-replica Modal routing the core story
- claiming exact trace reconstruction from sampled profiles
- shipping a large platform before there is a benchmarked single-replica core

## Core thesis

The strongest defensible project direction after reconciling the two agent sets is:

- use an existing serving engine
- instrument prefix/KV behavior deeply
- run controlled workloads with honest baselines
- treat profile-to-timeline inference as approximate phase segmentation with confidence
- keep ingestion/crawling optional unless it materially improves workload realism

## Proposed repo shape

- `docs/`
  - study guide
  - architecture notes
  - benchmark writeups
- `ingest/`
  - bounded crawler and deterministic corpus builder
- `serve/`
  - engine wrapper
  - Modal deployment
  - metrics and instrumentation
- `bench/`
  - workload definitions
  - benchmark runners
  - result artifacts and report generation
- `kvtrace/`
  - extraction of cache-relevant traces from serving runs
  - offline policy replay or simulation for LRU/S3-FIFO-style comparisons
- `profiles/`
  - profile ingestion
  - phase inference
  - validation and uncertainty calibration

## Phase 0: tractability spike

Deliver:

- choose between vLLM and SGLang based on instrumentation tractability, not hype
- identify what prefix/KV metrics are externally observable without forking
- identify whether policy experiments should happen inside the engine or via offline trace replay

Exit criteria:

- written engine choice with concrete reasons
- list of metrics available now versus only with invasive hooks
- decision on online policy swap versus offline replay

Kill criteria:

- if deep engine surgery is required just to get meaningful metrics, pivot to an observability-first and trace-replay-first design

## Phase 1: single-replica serving baseline on Modal

Deliver:

- one model family
- one GPU class
- one serving replica
- request queueing and streaming
- reproducible benchmark harness
- explicit handling of warmup, cold start, and steady-state runs
- at least one public realistic workload and one synthetic no-overlap control

Exit criteria:

- stable repeated benchmark runs on the same workload
- exported TTFT and inter-token latency percentiles, throughput, and goodput
- separate reporting for warm and cold behavior

Kill criteria:

- if Modal-specific instability dominates measurement, move part of the harness local or reduce the Modal dependency to deployment only

## Phase 2: prefix/KV instrumentation baseline

Deliver:

- prefix cache hit and miss metrics
- eviction metrics if available
- KV occupancy or proxy metrics if available
- cache on/off comparison on at least three workload families, including full-block-aligned and near-aligned prefix cases

Exit criteria:

- one publishable baseline comparison with honest caveats
- clear statement of what is directly measured versus inferred

Kill criteria:

- if cache metrics are too opaque inside the chosen engine, fall back to trace extraction and offline replay rather than forcing internal rewrites

## Phase 3: cache policy experiments

Deliver:

- baseline policy comparison rooted in real serving traces
- offline `kvtrace` replay or simulation if online policy swapping is too invasive
- at least one serious alternative to LRU, likely S3-FIFO-style or another simple policy with strong literature support

Exit criteria:

- one clear plot showing when the alternative helps and when it does not
- explanation tied to workload shape, not just aggregate win numbers

Kill criteria:

- if the experiment only produces toy wins under unrealistic overlap, stop and improve workloads before adding more policies

## Phase 4: profile ingestion and approximate timeline inference

Deliver:

- ingestion from time-preserving profile sources such as `perf` or JFR-style samples
- synthetic workload with traced ground truth
- phase segmentation and boundary inference with uncertainty
- degradation and calibration plots

Exit criteria:

- inferred timelines compared against traced truth
- uncertainty surfaced explicitly
- clear statement of what cannot be recovered from sampling

Kill criteria:

- if the output is mostly a pretty timeline without strong validation, keep it as a research appendix rather than a headline feature

## Phase 5: bounded ingestion for end-to-end realism

Deliver in the smallest bounded form that earns its keep:

- bounded domain ingestion or public corpus preparation
- deterministic extraction for repeatable prompt templates
- evidence that the added workload materially changes the cache experiment

Exit criteria:

- the ingestion pipeline produces repeatable, cache-relevant workload inputs

Kill criteria:

- if it behaves like a separate project, cut it
- if synthetic and public datasets already exercise the hypothesis well, do not build this phase

## Phase 6: integration and narrative

Deliver:

- benchmark report
- architecture writeup
- "what is measured, inferred, and impossible" section
- minimal demo path

Exit criteria:

- a skeptical systems reviewer can understand the thesis, evidence, and scope cuts quickly

## Immediate decisions from reconciliation

### What moved into the MVP core

- single-replica serving on Modal
- benchmark harness
- prefix/KV observability
- workload design
- profile-to-timeline validation as a parallel track
- bounded ingestion in the smallest form needed for an end-to-end story

### What moved out of the MVP core

- standalone concurrent LRU implementation
- custom engine internals
- multi-replica routing
- remote/disaggregated KV
- polished UI

## What to cut first if time gets tight

1. bounded ingestion or crawler work
2. online policy swapping inside engine internals
3. custom visualization
4. any distributed Modal experiment
5. any novelty claim not backed by measured evidence

## What makes this project high-signal now

- one falsifiable systems thesis
- realistic respect for Modal's statefulness limits
- strong baselines and goodput-oriented benchmarking
- observability that explains engine behavior instead of pretending to replace the engine
- explicit separation between exact measurement, inferred behavior, and impossible claims
- workload design that respects full-block prefix caching behavior instead of assuming arbitrary prefix reuse
