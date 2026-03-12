ABOUTME: Research memo on what already exists in open source and whether a combined project would look novel or contrived.
ABOUTME: Favor bluntness over optimistic positioning so the final project direction stays high-signal.

# OSS Landscape And Feasibility

_Date anchor: March 10, 2026._

## Executive take

Yes, it is possible to build one open source project that touches all four topics.

No, it is not automatically a good idea.

If you bolt together:

- a crawler
- an LRU cache
- an LLM serving stack
- a profile-to-trace visualizer

without a real throughline, a reviewer can absolutely see it as performative.

The defensible version is a monorepo with one operational story:

`crawl documents -> extract/serve with an LLM -> observe latency/capacity behavior -> use inferred timelines when tracing is missing`

That is coherent.

The non-defensible version is one binary that pretends these are naturally one product.

## What already exists

### Concurrent caches

This is not novel space.

Representative OSS:

- Caffeine for Java: high-performance eviction and admission design far beyond naive LRU
- Ristretto for Go: concurrent cache tuned for throughput and hit ratio
- Moka for Rust: production-grade concurrent cache library

What that means:

- "I built an LRU cache" is useful only as an educational artifact.
- It is not novel as a standalone OSS project.

### Web crawlers

This is very crowded.

Representative OSS:

- Scrapy
- StormCrawler
- Heritrix
- Crawl4AI
- Firecrawl

What that means:

- a new crawler is not novel unless it has a sharp angle
- "LLM-ready extraction" is also no longer novel by itself

### LLM inference / KV cache infra

This is crowded but still moving fast.

Representative OSS:

- vLLM
- SGLang
- TensorRT-LLM
- LMCache
- AIBrix

What that means:

- a general-purpose serving stack is not a realistic novelty claim
- a small system with unusually clear instrumentation, pedagogical value, or a narrow experiment angle can still be valuable

### Continuous profiling and profile tooling

This is established, but profile-to-trace inference is much less saturated.

Representative OSS:

- Pyroscope
- Parca
- pprof
- speedscope
- Perfetto

What that means:

- flamegraphs and sampled-profile viewers are old news
- exact trace reconstruction is not credible
- approximate timeline inference from statistical profiles is a more interesting niche, but must be framed carefully

## What is actually novel enough to claim

Not novel:

- "an LLM crawler"
- "a GPU inference service on Modal"
- "an LRU cache implementation"
- "a profile viewer"

Potentially novel enough:

- a deliberately educational but production-minded monorepo that connects serving bottlenecks to observability evidence
- a small inference playground where prefix-cache, KV eviction, and offload policies can be visualized and compared
- a profile-to-trace approximation layer that is honest about uncertainty and built specifically around LLM serving workloads

The novelty would not be "first ever."

The novelty would be:

- unusually coherent cross-layer instrumentation
- unusually honest treatment of uncertainty and tradeoffs
- a workload story that makes all components necessary rather than decorative

## The best project framing

The strongest framing I see is:

`Inference Observatory: a crawl-to-serve LLM systems lab with cache-aware serving and profile-derived timeline analysis`

Why this framing works:

- crawler provides real input corpus
- cache gives you a real hot-path systems component
- inference serving gives you the GPU and KV story
- profile inference gives you observability depth on the same workload

Why this framing can still fail:

- if the crawler is too generic, it looks like filler
- if the cache is hidden and unimportant, it looks forced
- if the profiler work is detached from the serving path, it looks tacked on

## What belongs together naturally

- web crawler + extraction/indexing pipeline
- inference serving + KV cache management
- inference serving + profiling/observability

## What does not belong together naturally without careful framing

- generic concurrent LRU cache + crawler
- profile-to-trace reconstruction + crawler

So if you include the cache, give it a real role:

- fetch-result cache
- robots/cache metadata cache
- content fingerprint cache
- prefix metadata cache in the serving path

And if you include profile-to-trace inference, make it serve the same system:

- infer missing request-phase timelines for the inference service when only sampled profiles are available

## What reviewers are likely to respect

- measured scope
- a real bottleneck you can explain
- simple baseline before optimization
- clear invariants
- honest claims about what is approximate
- evidence that you know where existing OSS ends and your work begins

## What reviewers are likely to scoff at

- calling the crawler novel
- hand-waving around GPU scheduling
- claiming exactness for profile-derived traces
- packing too many features into an under-tested toy
- using Modal as if it makes distributed systems hard parts disappear

## Modal feasibility

Most feasible on Modal:

- one or a few GPU replicas
- one model family
- local prefix caching
- offline or semi-online crawl/extract pipeline
- benchmarkable experiments around batching and KV residency

Feasible with work:

- multiple GPU classes
- routing based on model/tenant class
- CPU spill tier for KV or prompt artifacts
- controlled experiments for disaggregated prefill

Not the right first project on Modal:

- cluster-wide remote KV cache with very low tail latency expectations
- highly stateful low-latency routing that depends on instant cross-replica KV metadata
- pretending serverless GPU orchestration is the same as a custom high-performance serving fabric

## What is actually difficult

### 1. Making the project feel like one thing

This is the hardest product problem.

The code can work and still feel incoherent.

### 2. Getting useful KV experiments without building half of vLLM

You need just enough serving logic to make cache policy experiments meaningful.

Too little:

- the project looks shallow

Too much:

- you disappear into infrastructure work for months

### 3. Profiler-to-trace inference quality

It is easy to build a bad demo that invents pretty timelines.

The hard part is:

- calibration
- uncertainty scoring
- synthetic workloads with known ground truth
- explaining limitations without undermining the whole feature

### 4. Crawler scope control

Every crawler grows heads:

- JS rendering
- auth
- sitemaps
- dedupe
- anti-bot
- partial retries

You need a brutally tight scope or this swallows the project.

### 5. Benchmark credibility

If you claim a cache or serving optimization matters, you need:

- workload description
- baseline
- controlled changes
- honest results

Without this, the project reads like blogware.

## Second review pass: caveats and assumptions

### Caveats

- These topics may not map directly to the later Anthropic loop.
- The newest serving ideas in docs may be ahead of what most teams run in stable production.
- Modal is a deployment convenience, not proof of systems sophistication.
- A monorepo can still be incoherent if the interfaces are artificial.
- "Educational project" and "production-grade system" are different goals; trying to fully satisfy both can stall progress.

### Assumptions we are making

- you want a high-signal project more than a fast portfolio piece
- Python is acceptable for the control plane because Modal fits it well
- you can rely on existing serving engines rather than writing CUDA or kernels
- reviewers will value clear systems judgment over raw feature count
- you are willing to cut scope aggressively if the profiler or distributed KV work gets mushy

### Biases we need to watch

- novelty bias: wanting the project to be original enough to overshoot useful scope
- infrastructure bias: assuming more distributed pieces always read as stronger
- benchmark bias: overvaluing microbenchmarks that do not reflect the serving story
- observability bias: building fancy visualizations without strong inference validity
- resume bias: adding components because they look impressive rather than because they tighten the narrative

## Recommendation

My blunt recommendation is:

- do not build one giant "all-in-one system" application
- do build one monorepo with two tightly related subprojects

Suggested split:

1. `serve/`
   - crawler-backed corpus ingestion
   - minimal LLM serving path
   - local KV and prefix-cache experiments
   - Modal deployment

2. `observe/`
   - profile ingestion
   - approximate timeline reconstruction
   - validation on synthetic serving workloads

Why this is better:

- still one coherent story
- less contrived than forcing everything into one runtime
- easier to test and explain
- gives you something real to demo even if the trace inference remains approximate

## MVP recommendation

If you want the highest signal-to-effort path:

### MVP

- crawl a bounded corpus from 1-3 documentation domains
- convert content into clean text/markdown
- serve a single open model on Modal
- implement request queueing, continuous batching awareness, and local prefix-cache metrics
- build one sampled-profile to coarse-phase inference prototype for the serving path

### Do not build in MVP

- browser-heavy crawling
- multi-tenant auth
- remote cluster-wide KV cache
- generalized distributed scheduler
- exact trace reconstruction claims

### Stretch if MVP is genuinely solid

- compare local-only vs CPU spill vs remote-KV experiments
- add tenant or prompt-priority scheduling
- compare synthetic workloads and inferred timelines against traced ground truth

## Sources

- Caffeine: https://github.com/ben-manes/caffeine/wiki/Eviction
- Ristretto: https://github.com/hypermodeinc/ristretto
- Scrapy: https://docs.scrapy.org/en/latest/topics/broad-crawls.html
- RFC 9309: https://www.rfc-editor.org/rfc/rfc9309.html
- Common Crawl: https://commoncrawl.org/overview
- Crawl4AI: https://github.com/unclecode/crawl4ai
- Firecrawl: https://github.com/firecrawl/firecrawl
- StormCrawler: https://github.com/apache/incubator-stormcrawler
- Heritrix: https://github.com/internetarchive/heritrix3
- Modal docs: https://modal.com/docs
- vLLM docs: https://docs.vllm.ai/en/latest/
- SGLang docs: https://docs.sglang.ai/
- LMCache docs: https://docs.lmcache.ai/
- TensorRT-LLM docs: https://nvidia.github.io/TensorRT-LLM/
- AIBrix docs: https://aibrix.readthedocs.io/latest/
- Pyroscope docs: https://grafana.com/docs/pyroscope/latest/
- Parca docs: https://www.parca.dev/docs/overview/
- pprof: https://github.com/google/pprof
- speedscope: https://www.speedscope.app/
- Perfetto: https://perfetto.dev/docs/getting-started/cpu-profiling
