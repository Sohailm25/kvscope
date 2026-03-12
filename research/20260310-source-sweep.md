ABOUTME: Source-backed research notes for systems research preparation as of 2026-03-10.
ABOUTME: This file captures what exists already, what is mature, and what could still be worth building.

# Source Sweep

## Research Goal

Build a current, honest view of four advanced systems topics:

- Concurrent LRU cache
- Web crawler
- LLM inference infrastructure with KV cache management
- Reconstructing trace-like timelines from sampling profiler data

The secondary goal is to evaluate whether these can be combined into one open source project without it feeling contrived.

## High-Level Conclusions

- A single exact LRU cache is still a good foundational exercise, but production caches at high concurrency usually abandon exact LRU in favor of better hit rate and lower contention policies.
- A crawler remains a frontier-management problem more than an HTML-parsing problem. `robots.txt`, URL canonicalization, politeness, deduplication, retries, and backpressure are the hard parts.
- Modern LLM serving is dominated by scheduler design and KV cache economics. Continuous batching, block-based KV allocation, prefix reuse, and prefill/decode separation are the current baseline.
- Reverse reconstruction from profile samples to exact traces is not a solved commodity problem. Good systems can infer approximate phase timelines with confidence bounds, but not fully recover exact causal traces from sampled stacks alone.
- A single project is possible, but only if it is framed as a systems lab or monorepo with one workload and multiple subsystems. Forcing all four into one product surface would look performative.

## What Already Exists

### Concurrent Cache Reference Points

- [Caffeine efficiency notes](https://github.com/ben-manes/caffeine/wiki/Efficiency): argues modern cache efficiency is no longer well served by plain LRU and highlights Window TinyLFU as a stronger baseline.
- [Ristretto](https://github.com/dgraph-io/ristretto): high-performance Go cache using TinyLFU admission plus SampledLFU eviction rather than exact LRU.

Implication:

- Novelty is not "I built a cache better than existing OSS."
- Signal comes from implementing the exact LRU baseline correctly, then explicitly explaining why you would not deploy that exact design on a hot multi-core production path.

### Web Crawling Reference Points

- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html): current `robots.txt` standard.
- [Scrapy broad crawls guide](https://docs.scrapy.org/en/latest/topics/broad-crawls.html): practical guidance on concurrency, DNS, memory, and breadth-first crawl behavior.
- [Crawl4AI](https://github.com/unclecode/crawl4ai): LLM-oriented crawling/extraction framework.
- [Firecrawl](https://github.com/firecrawl/firecrawl): turns sites into LLM-ready markdown and structured outputs.

Implication:

- Novelty is not "crawl websites for LLMs."
- Signal comes from showing disciplined frontier design, correctness around politeness, and good tradeoffs between plain HTTP fetching and expensive browser execution.

### LLM Serving / KV Cache Reference Points

- [vLLM Anatomy blog](https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html): detailed walkthrough of the modern serving engine structure.
- [vLLM prefix caching design](https://docs.vllm.ai/en/latest/design/v1/prefix_caching.html): hash-based reuse of prompt prefixes.
- [vLLM hybrid KV cache manager](https://docs.vllm.ai/en/latest/design/hybrid_kv_cache_manager.html): block/page management across heterogeneous attention layers.
- [SGLang HiCache design](https://docs.sglang.ai/advanced_features/hicache_design.html): multi-tier KV storage from GPU to host to storage.
- [NVIDIA TensorRT-LLM KV reuse post](https://developer.nvidia.com/blog/introducing-new-kv-cache-reuse-optimizations-in-nvidia-tensorrt-llm/): priority-aware KV eviction and event APIs.
- [LMCache docs](https://docs.lmcache.ai/): externalized and disaggregated KV reuse.
- [AIBrix release 25.11.0](https://www.aibrix.ai/blog/release-25-11-0): inference control plane work around routing, autoscaling, and cache-aware serving.

Implication:

- Novelty is not "we support prefix caching" or "we have disaggregated prefill/decode."
- Signal comes from using existing engines intelligently, measuring tradeoffs, and perhaps adding clear benchmarking or observability that helps reason about cache locality and scheduling.

### Profiling / Trace Reconstruction Reference Points

- [OpenTelemetry profiles data model](https://opentelemetry.io/docs/specs/otel/profiles/data-model/): shows profiles are becoming a first-class telemetry signal and are expected to correlate with traces, not replace them.
- [Pyroscope](https://grafana.com/oss/pyroscope/): continuous profiling with explicit correlation to metrics and traces.
- [Speedscope](https://github.com/jlfwong/speedscope): useful time-order sample visualization (`time order`, `left heavy`, `sandwich`) rather than exact distributed trace reconstruction.

Implication:

- Commodity OSS is good at visualizing profiles and correlating profiles with traces.
- Commodity OSS is not strong at reconstructing exact trace timelines from profile samples when traces are missing.
- There is room for a serious, scoped project around "profile-to-phase inference" if claims are kept modest and uncertainty is surfaced explicitly.

### Modal-Specific Reference Points

- [Modal GPU guide](https://modal.com/docs/guide/gpu): GPU-backed functions and classes across several accelerator types.
- [Modal volumes guide](https://modal.com/docs/guide/volumes): shared persistent storage, but not a substitute for a low-latency distributed state store.

Implication:

- Modal is a good fit for GPU workers, experiments, batch jobs, and moderate-scale serving prototypes.
- Modal is a weaker fit for the control plane or any design that depends on ultra-low-latency sticky routing to in-memory KV state.

## Topic-Specific Notes

### 1. Concurrent LRU Cache

Findings:

- The canonical solution is still `hash map + doubly linked list + one lock`.
- A read hit mutates recency, so most `get()` calls are logically writes.
- Reader-writer locks help less than candidates expect unless there is a real `peek()` operation that does not update recency.
- Production caches avoid global recency updates on every hit because the hottest path becomes the metadata lock, not the data lookup.

Quality signal:

- Strong answer: implement exact LRU correctly, explain invariants clearly, then say why exact LRU is usually replaced in high-throughput systems.
- Weak answer: jump straight into lock-free structures or shards without first proving the single-lock version is correct.

### 2. Web Crawler

Findings:

- RFC 9309 matters. Ignoring `robots.txt` is not a harmless omission in a serious systems project.
- Scrapy’s broad crawl guidance still lines up with real-world crawler design: higher concurrency, DNS caching, reduced per-request overhead, and breadth-first traversal when coverage matters.
- Existing OSS already covers "fetch page and turn it into markdown for LLMs."

Quality signal:

- Strong answer: separate frontier, fetcher, parser, deduper, storage, and politeness enforcement.
- Weak answer: focus on HTML parsing and skip canonicalization, per-host pacing, or duplicate suppression.

### 3. LLM Inference Infrastructure and KV Cache

Findings:

- Continuous batching is table stakes.
- Prefix caching is table stakes.
- Prefill/decode asymmetry is table stakes.
- The live question is how efficiently you preserve cache locality, allocate KV memory, route requests, and avoid fragmentation.
- Multi-tier or externalized KV caching is real, but it adds consistency, transport, and locality complexity that many prototypes understate.

Quality signal:

- Strong answer: talk about scheduler policy, cache locality, queueing, GPU memory pressure, and how the system degrades.
- Weak answer: talk mostly about model weights and barely mention the KV cache.

### 4. Reconstructing Trace-Like Timelines from Sampling Profiles

Findings:

- Trace reconstruction is fundamentally an inference problem because profile samples are sparse observations.
- Time-ordered sample visualization exists, but exact span boundaries and request causality are usually not recoverable from samples alone.
- This topic can still be made useful if framed as an approximate tool for inferring execution phases or bottlenecks when full tracing is missing or too expensive.

Quality signal:

- Strong answer: say up front what is impossible, then define a narrower target that is useful.
- Weak answer: claim exact trace recovery from sparse samples.

## Unified Project Feasibility

### What Fits Naturally

- Crawler
- LLM serving
- KV cache analysis
- Profiling/observability of that same workload

### What Fits Only Weakly

- Exact concurrent LRU as a central product feature

Why:

- It works as a small internal component or standalone library.
- It does not naturally belong as the main story in a modern LLM systems repo because exact LRU is usually the wrong end-state policy for the hot path.

### Honest Positioning

Bad pitch:

- "A novel platform that combines crawling, caching, inference, and profiling."

Why it fails:

- Too broad.
- Sounds like a grab bag of buzzwords.

Better pitch:

- "A systems lab for crawl-to-serve LLM workloads: crawl a documentation corpus, serve generation over it, and study scheduler/KV behavior plus profile-derived phase timelines under real load."

Why it works:

- There is one workload.
- Each subsystem has a clear reason to exist.
- The profiler module is an observability tool, not a random detached side quest.

## Most Feasible Modal-Friendly Project

Recommended shape:

- CPU services for crawler, parser, frontier, metadata, and observability.
- GPU worker pool on Modal running an existing engine such as vLLM or SGLang.
- External durable store for frontier/state and benchmark artifacts.
- Small LRU library used locally inside one subsystem only where exact recency semantics are actually needed.
- Profiling module that converts time-ordered samples into approximate phase timelines for crawl and inference jobs.

Not recommended for v1:

- Building a custom CUDA attention kernel
- Building a distributed KV fabric from scratch
- Claiming exact profile-to-trace recovery
- Large-scale broad crawling of the public internet

## Novelty Assessment

Probably not novel:

- Another crawler that outputs markdown for LLM ingestion
- Another wrapper around vLLM or SGLang
- Another cache library

Potentially novel enough to matter:

- A disciplined benchmark/observability lab that makes KV locality, prefix reuse, queueing, and inferred phase timelines easy to inspect on real workloads
- A scoped profile-to-phase reconstruction tool with explicit uncertainty and a concrete operational use case
- A reproducible study repo that ties simple-first implementations to production-grade upgrades and measurement

## Blunt Recommendation

- Yes, a single monorepo is feasible.
- No, a single tightly-coupled product is not the best framing.
- The safest high-signal version is a monorepo with one workload and three modules: `ingest`, `serve`, `observe`.
- If forced into one binary/app, the result is likely to feel performative to a strong reviewer.

