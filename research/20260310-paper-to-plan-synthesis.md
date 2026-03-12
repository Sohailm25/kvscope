ABOUTME: Primary-source synthesis mapping papers and official system docs to concrete project design decisions.
ABOUTME: Use this file to justify scope cuts, benchmark choices, and implementation sequencing with explicit evidence.

# Paper-To-Plan Synthesis

_Date anchor: March 10, 2026._

## Executive synthesis

The current evidence supports a narrower and more defensible project than the original concept.

The project should be built around:

- one serving engine, not a new engine
- one GPU replica, not a distributed KV story
- strong observability and benchmark design
- offline replay or simulation for cache-policy comparisons when invasive engine modifications are not justified
- approximate phase inference from time-preserving sampled profiles with explicit uncertainty

The evidence does not support making a crawler, a standalone concurrent LRU, or distributed KV infrastructure central to the MVP.

## Source-to-decision matrix

### vLLM: automatic prefix caching and observability

Source:

- vLLM docs on automatic prefix caching
- vLLM metrics documentation
- vLLM benchmark suite docs
- vLLM disaggregated prefilling docs

Primary findings:

- prefix caching is implemented by hashing KV blocks
- only full blocks are cached
- the hash key can include parent hash, block tokens, and extra discriminators such as LoRA IDs, multimodal hashes, and cache salts
- vLLM surfaces cache-relevant metrics including prefix cache queries and hits
- vLLM benchmark tooling explicitly supports percentile latency and goodput
- disaggregated prefill is documented but explicitly experimental

Design implications:

- workload design must include both full-block-aligned and near-aligned prefixes, otherwise cache wins will be overstated
- any correctness-sensitive reuse experiment must respect cache identity inputs such as adapter IDs and salts
- use vLLM's existing benchmark tooling as the baseline harness rather than inventing a new one
- keep disaggregated prefill out of the MVP and, at most, treat it as an appendix

Changes to current plan:

- Phase 1 benchmark workloads must include partial-block controls
- Phase 2 metrics must distinguish direct metrics from inferred metrics
- Phase 5 distributed work stays optional and late

### SGLang: radix-style reuse, HiCache, and PD disaggregation

Source:

- SGLang repository README
- SGLang HiCache docs
- SGLang PD disaggregation docs

Primary findings:

- SGLang explicitly centers RadixAttention and a zero-overhead batch scheduler
- HiCache is a hierarchical KV cache design
- PD disaggregation is a documented feature

Design implications:

- SGLang remains a credible candidate for the tractability spike, especially if reuse visibility is easier to instrument than in vLLM
- hierarchical or remote KV ideas are real and current, but they are not good MVP material on Modal
- if the project later explores multi-tier caching, it should do so from a single-replica observability baseline first

Changes to current plan:

- Phase 0 must compare vLLM versus SGLang specifically on instrumentation tractability
- remote and hierarchical KV remain stretch or appendix work only

### TensorRT-LLM: reuse, eviction priority, and offloading

Source:

- TensorRT-LLM docs on KV cache reuse
- TensorRT-LLM docs on priority-based eviction
- TensorRT-LLM docs on KV cache offloading

Primary findings:

- current serving systems expose reuse semantics, explicit eviction priorities, and offloading tiers
- this is already a real engineering surface in mature runtimes, not a hypothetical research direction

Design implications:

- policy experiments should not stop at "LRU versus not LRU"; they should treat eviction metadata and workload class as first-class concepts
- for MVP, keep the policy comparison simple
- for later work, reserve space for policy inputs like priority, pinning, and tier preference

Changes to current plan:

- `kvtrace/` should store more than recency if possible
- policy experiments can start simple, but the trace schema should not assume plain LRU forever

### LMCache and Mooncake: external and multi-tier KV systems are real, but expensive

Source:

- LMCache docs
- Mooncake paper and project docs

Primary findings:

- LMCache is an external KV cache layer spanning GPU, CPU, and storage backends
- Mooncake argues explicitly for trading storage for less recomputation in a KV-cache-centric architecture

Design implications:

- external KV systems are real enough to learn from, but costly enough that they should not be the baseline project
- the project should treat remote or tiered KV as evidence that the problem matters, not as a requirement to reimplement it

Changes to current plan:

- remote/tiered KV remains a literature-backed appendix idea, not MVP

### DistServe and fairness work: benchmark goodput and mixed workloads, not raw throughput alone

Source:

- DistServe paper
- FairBatching paper
- vLLM benchmark docs

Primary findings:

- prefill and decode interfere with each other
- decoupling or better scheduling is motivated by goodput, not just raw tokens/sec
- fairness under mixed long/short workloads remains an active problem

Design implications:

- the benchmark matrix must include mixed prompt lengths and bursty arrivals
- goodput should be a first-class metric, not a side note
- long-only or uniform-only workloads are insufficient

Changes to current plan:

- Phase 1 and Phase 2 benchmark outputs must include goodput
- benchmark design must include mixed long/short request distributions

### S3-FIFO and libCacheSim: offline policy replay is a strong path

Source:

- S3-FIFO paper
- libCacheSim repository docs

Primary findings:

- modern cache-policy work emphasizes high-throughput simple eviction structures
- libCacheSim demonstrates the value of trace-driven evaluation at very high request rates

Design implications:

- do not force policy comparisons into the live serving engine if trace replay answers the question more cleanly
- a CacheBench-like `kvtrace/` layer is a serious systems contribution if grounded in realistic traces

Changes to current plan:

- `kvtrace/` is now a core design hedge, not a side idea
- Phase 3 should accept offline replay as a first-class success path

### pprof, async-profiler, Perfetto, and OpenTelemetry profiles

Source:

- pprof `profile.proto`
- async-profiler docs
- Perfetto docs
- OpenTelemetry profiling spec pages

Primary findings:

- pprof's profile format can store timestamps, but many common uses are still aggregate-oriented
- async-profiler can emit JFR, which preserves time ordering more naturally for timeline work
- Perfetto is timeline-oriented and suitable for truth-versus-inference comparison workflows
- OpenTelemetry profiling remains a developing signal and should not be treated as a stable dependency for the core project

Design implications:

- do not base timeline claims on aggregate pprof dumps alone
- choose a time-preserving collection path such as `perf` or JFR early
- generate traced ground truth for synthetic workloads and compare inference against it
- treat OTel profiling integration as future-facing, not as a core dependency

Changes to current plan:

- Phase 4 now explicitly requires time-preserving profiles
- validation artifacts must include calibration and degradation plots

### Modal docs: platform fit and platform traps

Source:

- Modal docs on cold starts
- Modal docs on preemption
- Modal docs on input concurrency
- Modal docs on queues, Dict, and GPU snapshots

Primary findings:

- GPU functions are preemptible
- input concurrency is supported and useful for continuous-batching backends
- Dict and Queue are fine for metadata and coordination, not low-latency KV transfer
- GPU snapshots are experimental

Design implications:

- single-replica serving remains the right MVP
- benchmark runs must pin infrastructure conditions and separate warm from cold behavior
- Dict and Queue should not appear in the hot path for KV movement
- GPU snapshots should be treated as an experimental operational optimization, not part of the core claim

Changes to current plan:

- Phase 1 must separate steady-state from cold-start evaluation
- distributed or cross-container KV work stays out of the core scope

## Research-grounded benchmark requirements

The current source base strongly supports the following minimum benchmark rules:

- report p50, p95, and p99 for TTFT and inter-token latency
- report throughput and goodput under explicit SLOs
- include at least one mixed long/short workload
- include at least one low-overlap or no-overlap control
- include at least one full-block-aligned and one near-aligned prefix-sharing workload
- discard warmup separately and report cold-start behavior independently
- run multiple repetitions and store raw artifacts

## What is still unresolved

- vLLM versus SGLang for the first implementation pass
- how much cache-policy experimentation can happen inside the chosen engine before it becomes a maintenance burden
- whether bounded ingestion changes benchmark conclusions enough to justify its scope
- whether profile-to-phase inference remains novel by the time the project is published

## Sources

- vLLM automatic prefix caching: https://docs.vllm.ai/en/latest/design/v1/prefix_caching.html
- vLLM benchmark suite: https://docs.vllm.ai/en/latest/contributing/benchmarks.html
- vLLM metrics: https://docs.vllm.ai/en/latest/design/metrics.html
- vLLM disaggregated prefilling: https://docs.vllm.ai/en/latest/features/disagg_prefill.html
- SGLang repository: https://github.com/sgl-project/sglang
- SGLang HiCache docs: https://docs.sglang.ai/advanced_features/hicache.html
- SGLang PD disaggregation docs: https://docs.sglang.ai/advanced_features/pd_disaggregation.html
- TensorRT-LLM KV reuse: https://nvidia.github.io/TensorRT-LLM/advanced/kv-cache-reuse.html
- TensorRT-LLM priority eviction: https://nvidia.github.io/TensorRT-LLM/advanced/kv-cache-reuse.html#priority-based-kv-cache-eviction
- TensorRT-LLM offloading: https://nvidia.github.io/TensorRT-LLM/advanced/kv-cache-offloading.html
- LMCache docs: https://docs.lmcache.ai/
- Mooncake paper: https://arxiv.org/abs/2407.00079
- DistServe paper: https://arxiv.org/abs/2401.09670
- FairBatching paper: https://arxiv.org/abs/2510.14392
- S3-FIFO paper: https://arxiv.org/abs/2310.15999
- libCacheSim: https://github.com/1a1a11a/libCacheSim
- pprof profile proto: https://github.com/google/pprof/blob/main/proto/profile.proto
- async-profiler docs: https://github.com/async-profiler/async-profiler
- Perfetto docs: https://perfetto.dev/docs/
- OpenTelemetry profiles: https://opentelemetry.io/docs/specs/otel/profiles/
- Modal cold starts: https://modal.com/docs/guide/cold-start
- Modal preemption: https://modal.com/docs/guide/preemption
- Modal input concurrency: https://modal.com/docs/guide/concurrent-inputs
- Modal Dict: https://modal.com/docs/reference/modal.Dict
- Modal Queue: https://modal.com/docs/reference/modal.Queue
- Modal GPU snapshots example: https://modal.com/docs/examples/gpu_packing
