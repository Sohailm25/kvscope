ABOUTME: Concrete implementation roadmap for KVScope after the pre-implementation hardening pass.
ABOUTME: This document should be actionable enough to start coding without reopening project identity or scope.

> Current execution authority.
> If planning-era docs conflict with this file, trust this file.

# Implementation Roadmap

## Ground Rules

- Build the smallest credible slice first.
- Every phase must produce an inspectable artifact.
- Every major claim must have a validation path.
- Secondary lanes must earn promotion into the main story.

## Phase 0: Hardening And Decision Lock

Status:

- complete

Deliverables now in place:

- reconciled thesis and scope docs
- locked engine and deployment baseline
- machine-checkable example fixtures
- readiness validator and tests
- updated artifact conventions and trace contract

Exit criteria:

- the repo is ready to move from planning into implementation without another broad design pass

## Phase 1: Serving Baseline

Goal:

- make one `vLLM` replica stable, benchmarkable, and artifact-producing

Status:

- first slice implemented

What is already done:

- single-replica Modal baseline implemented in `serve/`
- live benchmark client writes manifests, results, workloads, and `kvtrace`
- aligned-prefix live run completed
- no-overlap-control live run completed
- second no-overlap-control run completed
- near-aligned-prefix live run completed
- mixed-long-short live run completed with recorded arrival offsets
- bursty-arrivals live run completed with two aligned bursts
- second aligned-prefix rerun completed after runtime cleanup
- third and fourth aligned-prefix clean repeats completed
- runtime dependency contract pinned to `transformers==4.51.3` for `vLLM==0.8.3`
- invocation command capture now includes workload geometry for newer manifests
- cross-run reports emitted under `artifacts/manifests/`

Tasks:

- deploy one `vLLM` baseline on Modal
- expose the minimal request path needed for benchmark runs
- write manifests, stdout/stderr capture, and raw result artifacts
- capture TTFT, ITL, throughput, and queueing data
- separate warmup and cold-start behavior

Deliverables:

- stable single-replica endpoint
- first run manifest and raw results bundle
- one repeated-run sanity check on the same workload

Exit criteria:

- three repeated runs on one workload show stable ordering and artifact quality good enough to trust Phase 2

Current note:

- the aligned-prefix family now satisfies the three-run repetition bar
- artifact quality is good enough to move forward
- performance spread remains material, so the current claim is qualitative cache separation, not a tight latency bound

## Phase 2: Workload And Benchmark Harness

Goal:

- generate the minimum workload suite needed to test reuse honestly

Status:

- positive case, boundary case, interference case, burst-pressure case, negative control, replay-differentiation workload, policy-headroom workload, and two recency-versus-frequency tradeoff workloads implemented

What is already done:

- aligned-prefix workload generator implemented
- near-aligned-prefix workload generator implemented
- mixed-long-short workload generator implemented
- bursty-arrivals workload generator implemented
- no-overlap-control workload generator implemented
- eviction-ordering workload generator implemented for replay policy differentiation
- hotset-scan workload generator implemented for replay policy headroom
- locality-shift workload generator implemented for recency-versus-frequency tradeoffs
- locality-return workload generator implemented for a return-to-hotset policy crossover case
- repeated artifact bundles exist under `artifacts/runs/`

Tasks:

- implement aligned-prefix and no-overlap workloads first
- add near-aligned prefix workload
- add at least one mixed or bursty workload
- package each run with workload family labels and manifests
- preserve arrival offsets and per-request timing when the workload depends on overlap

Deliverables:

- first benchmarkable workload generator
- one negative control
- one alignment-sensitive positive case

Exit criteria:

- the benchmark harness can demonstrate both a plausible win case and a plausible no-win case

Current note:

- the current artifact set already shows the intended qualitative separation:
  - aligned-prefix: derived prefix hits on the second request
  - near-aligned-prefix: reduced derived prefix hits from missing the next full block boundary
  - mixed-long-short: a much shorter request still pays substantial TTFT while overlapping with the longer request
  - bursty-arrivals: a later aligned burst still pays substantial TTFT while overlapping the earlier burst
  - no-overlap-control: no derived prefix hits
- near-aligned, mixed-long-short, and bursty-arrivals now each have clean three-run slices
- the clean three-run aligned summary is captured in:
  - `artifacts/manifests/20260311-012300__serve__phase1__phase1-clean-baseline.json`
  - `artifacts/manifests/20260311-012300__serve__phase1__phase1-clean-baseline.md`
- the expanded aligned vs near-aligned vs control summary is captured in:
  - `artifacts/manifests/20260311-023401__serve__phase1__phase1-expanded-slice.json`
  - `artifacts/manifests/20260311-023401__serve__phase1__phase1-expanded-slice.md`
- the cache plus interference summary is captured in:
  - `artifacts/manifests/20260311-025009__serve__phase1__phase1-observability-slice.json`
  - `artifacts/manifests/20260311-025009__serve__phase1__phase1-observability-slice.md`
- the cache plus interference plus burst-pressure summary is captured in:
  - `artifacts/manifests/20260311-132801__serve__phase1__phase1-bursty-observability-slice.json`
  - `artifacts/manifests/20260311-132801__serve__phase1__phase1-bursty-observability-slice.md`
- the repeated-family spread summary is captured in:
  - `artifacts/manifests/20260311-142406__serve__phase1__phase1-repeated-families-slice.json`
  - `artifacts/manifests/20260311-142406__serve__phase1__phase1-repeated-families-slice.md`
- the policy-surface summary now adds the second recency-versus-frequency geometry:
  - `artifacts/runs/20260311-181625__serve__locality-return__smoke-locality-return-clean`
  - `artifacts/runs/20260311-181906__serve__locality-return__smoke-locality-return-cache-off-clean`
  - `artifacts/manifests/20260311-182034__serve__phase1__phase1-policy-surface-expanded.json`
  - `artifacts/manifests/20260311-182034__serve__phase1__phase1-policy-surface-expanded.md`
  - locality-return at the native replay capacity `2` records `5` derived block hits and a serving note of `returning-locality crossover case`

## Phase 3: Live Cache Observability

Goal:

- measure exposed cache behavior before relying on replay

Status:

- aligned, eviction, hotset, locality-shift, and locality-return cache-toggle slices implemented

What is already done:

- live `/metrics` scraping implemented in `serve/live_metrics.py`
- per-run `live_metrics.json` artifacts now land beside `manifest.json` and `results.json` when metrics are available
- cache-on versus cache-off aligned-prefix runs completed with explicit runtime toggles
- first Phase 3 report emitted under `artifacts/manifests/20260311-140423__serve__phase3__aligned-live-cache-toggle.{json,md}`
- repeated cache-on eviction-ordering runs completed with a matching cache-off control
- expanded Phase 3 report emitted under `artifacts/manifests/20260311-163728__serve__phase3__live-cache-toggle-expanded.{json,md}`
- repeated cache-on hotset-scan runs completed with a matching cache-off control
- expanded Phase 3 report emitted under `artifacts/manifests/20260311-171756__serve__phase3__live-cache-toggle-hotset-expanded.{json,md}`
- repeated locality-shift cache-on and cache-off runs completed
- repeated tradeoff Phase 3 report emitted under `artifacts/manifests/20260311-175734__serve__phase3__live-cache-toggle-tradeoffs-repeated.{json,md}`
- locality-return cache-on and cache-off runs completed
- policy-surface Phase 3 report emitted under `artifacts/manifests/20260311-182034__serve__phase3__live-cache-toggle-policy-surface-expanded.{json,md}`
- Modal cache-mode functions no longer prewarm both containers after the runtime defect was fixed with a test-backed `min_containers=0` change

Tasks:

- export live prefix-cache metrics if the engine exposes them
- capture cache-on versus cache-off comparisons where a live knob exists
- keep measured metrics separate from inferred or replayed metrics

Deliverables:

- first live cache-observability report

Exit criteria:

- at least one latency shift can be explained with live cache evidence rather than speculation

Current note:

- the aligned-prefix, eviction-ordering, hotset-scan, locality-shift, and locality-return families now satisfy the minimum Phase 3 bar:
  - cache-on mean live prefix-cache hit rate: `0.5`
  - cache-off mean live prefix-cache hit rate: `0.0`
  - cache-on mean live prefill time: `35.191 ms`
  - cache-off mean live prefill time: `43.572 ms`
  - eviction-ordering cache-on mean live prefix-cache hit rate: `0.417`
  - eviction-ordering cache-off mean live prefix-cache hit rate: `0.0`
  - eviction-ordering cache-on mean live prefill time: `18.229 ms`
  - eviction-ordering cache-off mean live prefill time: `24.259 ms`
  - hotset-scan cache-on mean live prefix-cache hit rate: `0.312`
  - hotset-scan cache-off mean live prefix-cache hit rate: `0.0`
  - hotset-scan cache-on mean live prefill time: `13.946 ms`
  - hotset-scan cache-off mean live prefill time: `16.914 ms`
  - locality-shift cache-on mean live prefix-cache hit rate: `0.375`
  - locality-shift cache-off mean live prefix-cache hit rate: `0.0`
  - locality-shift cache-on mean live prefill time: `14.619 ms`
  - locality-shift cache-off mean live prefill time: `13.758 ms`
  - locality-return cache-on live prefix-cache hit rate: `0.375`
  - locality-return cache-off live prefix-cache hit rate: `0.0`
  - locality-return cache-on live prefill time: `14.326 ms`
  - locality-return cache-off live prefill time: `15.426 ms`
- the current Phase 3 claim is intentionally narrow:
  - live prefix-cache counters show direct reuse only in the cache-on slice
  - aligned-prefix shows lower live prefill time and lower client TTFT with cache-on
  - eviction-ordering shows lower live prefill time with cache-on, but client TTFT remains noisy
  - hotset-scan shows lower live prefill time with cache-on, but client TTFT remains noisy
  - locality-shift shows direct live cache hits without a cleaner client-side latency story
  - locality-return shows repeated direct live cache hits with lower live prefill time across two cache-on/cache-off pairs, but client TTFT remains mixed
  - the scraped internal `vLLM` TTFT histogram does not numerically match client TTFT, so this is not yet a full end-to-end latency decomposition

## Phase 4: `kvtrace` Replay

Goal:

- make policy replay credible and tied to real serving runs

Status:

- first bridge slice implemented
- first live-derived replay policy divergence slice implemented
- first live-derived replay policy headroom slice implemented
- first live-derived replay adaptation slice implemented
- first replay-capacity sweep implemented
- second live-derived recency-versus-frequency geometry implemented with a policy crossover

Tasks:

- emit replayable block-lifecycle traces from Phase 1 and 2 runs
- implement LRU baseline
- implement one stronger comparison policy
- rerun the live-to-replay bridge experiment after each new workload family or replay policy change

Deliverables:

- first trace replay report
- one documented bridge result
- one explicit failure mode or non-win case

Exit criteria:

- replay produces insight that is directionally consistent with at least one live result and bounded honestly when it is not

Current note:

- the first bridge report now exists under `artifacts/manifests/20260311-025649__kvtrace__bridge__bridge-cache-ordering.{json,md}`
- replay preserves the current live family ordering across aligned, near-aligned, and no-overlap slices
- the bridge has now been rerun after adding the bursty-arrivals family:
  - `artifacts/manifests/20260311-132801__kvtrace__bridge__bridge-cache-ordering-bursty.json`
  - `artifacts/manifests/20260311-132801__kvtrace__bridge__bridge-cache-ordering-bursty.md`
- replay now has a live-derived policy-separation case:
  - `artifacts/runs/20260311-142948__serve__eviction-ordering__smoke-eviction-ordering-clean`
  - `artifacts/manifests/20260311-143006__kvtrace__bridge__bridge-cache-ordering-divergence.json`
  - `artifacts/manifests/20260311-143006__kvtrace__bridge__bridge-cache-ordering-divergence.md`
- the repeated eviction-ordering bridge is now captured in:
  - `artifacts/manifests/20260311-163320__kvtrace__bridge__bridge-cache-ordering-divergence-repeated.json`
  - `artifacts/manifests/20260311-163320__kvtrace__bridge__bridge-cache-ordering-divergence-repeated.md`
- the eviction-ordering family now repeatedly separates `fifo` from `lru` at replay capacity `2`:
  - `fifo` hit rate mean: `0.25`
  - `lru` hit rate mean: `0.417`
- all three cache-on eviction-ordering runs recorded `12` live prefix-cache queries and `5` live prefix-cache hits
- the hotset-scan family now adds a repeated live-derived replay headroom case at capacity `3`:
  - `artifacts/runs/20260311-170525__serve__hotset-scan__smoke-hotset-scan-clean`
  - `artifacts/runs/20260311-171651__serve__hotset-scan__smoke-hotset-scan-clean-2`
  - `artifacts/runs/20260311-202646__serve__hotset-scan__smoke-hotset-scan-revisit-clean`
  - `artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json`
  - `fifo` hit rate mean: `0.209`
  - `lru` hit rate mean: `0.271`
  - `lfu` hit rate mean: `0.375`
- hotset-scan now also has direct Phase 3 evidence:
  - `artifacts/runs/20260311-171651__serve__hotset-scan__smoke-hotset-scan-clean-2`
  - `artifacts/runs/20260311-171705__serve__hotset-scan__smoke-hotset-scan-cache-off-clean`
  - cache-on live prefix-cache hit rate mean: `0.312`
  - cache-off live prefix-cache hit rate mean: `0.0`
- the replay headroom claim stays narrower than the live cache claim:
  - it is now repeated across the baseline and revisit workload geometries
  - the live cache slice remains narrower because the replay variation is geometry-driven while the cache-off control still exists only for the baseline family
- the original aligned, near-aligned, bursty, and control families remain useful for directional bridge validation, but they still do not separate `fifo` from `lru`
- the locality-shift family now adds a repeated live-derived replay adaptation case at capacity `2`:
  - `artifacts/runs/20260311-173519__serve__locality-shift__smoke-locality-shift-clean`
  - `artifacts/runs/20260311-175340__serve__locality-shift__smoke-locality-shift-clean-2`
  - `artifacts/manifests/20260311-175734__kvtrace__bridge__bridge-policy-tradeoffs-repeated.json`
  - `artifacts/manifests/20260311-175734__kvtrace__bridge__bridge-policy-tradeoffs-repeated.md`
  - `fifo` hit rate mean: `0.25`
  - `lru` hit rate mean: `0.375`
  - `lfu` hit rate mean: `0.188`
- the locality-return family now adds a repeated live-derived replay adaptation slice with a capacity crossover:
  - `artifacts/runs/20260311-181625__serve__locality-return__smoke-locality-return-clean`
  - `artifacts/runs/20260311-200421__serve__locality-return__smoke-locality-return-clean-2`
  - `artifacts/runs/20260311-202901__serve__locality-return__smoke-locality-return-concentrated-clean`
  - `artifacts/runs/20260311-221055__serve__locality-return__smoke-locality-return-concentrated-clean`
  - `artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json`
  - `artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json`
  - at native replay capacity `2`: `fifo 0.219`, `lru 0.344`, `lfu 0.219`
  - the sweep then shows `lru > lfu` at capacities `2` and `3`, `lfu > lru` at capacity `4`, and equality again at `5` and `6`
- the replay-capacity sweep now makes threshold and tradeoff bands explicit:
  - `artifacts/manifests/20260311-175734__kvtrace__sweep__replay-capacity-sweep-tradeoffs-repeated.json`
  - `artifacts/manifests/20260311-175734__kvtrace__sweep__replay-capacity-sweep-tradeoffs-repeated.md`
  - aligned-prefix, near-aligned-prefix, and bursty-arrivals first reuse at `4` blocks
  - eviction-ordering first reuses at `2` blocks and keeps `lru > fifo` at capacities `2` and `3`
  - hotset-scan keeps `lfu > lru > fifo` at capacities `2`, `3`, `4`, and `5`
  - locality-shift keeps `lru > lfu` at capacities `2`, `3`, `4`, and `5`
  - locality-return shows both a recency-advantage band and an LFU-headroom band as capacity changes

## Investigator Layer Status

Goal:

- answer the locked seed questions over the MCP surface with citations and explicit caveats

Status:

- first deterministic seeded-question investigator implemented

What is already done:

- bounded answer schema implemented in `agent/answer_schema.py`
- MCP-backed seeded-question investigator implemented in `agent/investigator.py`
- manual investigator CLI implemented in `scripts/run_investigator.py`
- seeded investigator coverage now exists in `tests/test_investigator.py`
- the current investigator logs tool calls and transcripts and runs a simple overclaim self-check

Current note:

- this is still the deterministic seeded-question slice, but it is no longer pre-eval
- the first eval harness now exists and the next step is widening that eval surface before promoting to the direct-API investigator path

## Eval Layer Status

Goal:

- measure seeded investigator usefulness, citation grounding, and overclaim control before introducing model nondeterminism

Status:

- seeded deterministic eval harness implemented
- direct Anthropic-backed held-out eval harness implemented

What is already done:

- seeded task file implemented in `evals/tasks/seeded_investigator_tasks.yaml`
- held-out task file implemented in `evals/tasks/heldout_investigator_tasks.yaml`
- deterministic graders implemented in `evals/graders.py`
- seeded eval runner implemented in `evals/runner.py`
- report writer implemented in `evals/reporting.py`
- eval CLI implemented in `scripts/run_investigator_evals.py`
- direct Anthropic-backed investigator implemented in `agent/anthropic_investigator.py`
- seeded eval coverage now exists in:
  - `tests/test_eval_graders.py`
  - `tests/test_eval_runner.py`
  - `tests/test_anthropic_investigator.py`
  - `tests/test_agent_runtime.py`
- latest seeded eval artifact now lives in:
  - `artifacts/evals/20260312-001938__investigator__seeded-evals/investigator-eval-report.json`
  - `artifacts/evals/20260312-001938__investigator__seeded-evals/investigator-eval-report.md`
- latest held-out Anthropic eval artifact now lives in:
  - `artifacts/evals/20260312-031936__investigator__heldout-evals/investigator-eval-report.json`
  - `artifacts/evals/20260312-031936__investigator__heldout-evals/investigator-eval-report.md`

Current note:

- the seeded deterministic harness remains the clean contract layer
- the direct Anthropic-held-out path is now real and tool/citation-stable
- the locked held-out task set now covers `15` paraphrased tasks and scores cleanly after route-level boundary normalization and overclaim-check hardening
- the thin reviewer-facing app now exists over the frozen corpus and investigator surface:
  - `web/app.py`
  - `scripts/run_web_app.py`
  - `tests/test_web_app.py`
- the app now includes a guided reviewer path under `/demo` so the walkthrough is deliberate rather than page-by-page navigation
- the recording script now lives in:
  - `docs/kvscope_demo_script.md`
- the next step is final demo polish and broader held-out coverage rather than first app implementation

## Phase 5: Bounded Extensions

This phase contains the optional lanes that must justify themselves.

### `profiles/`

Goal:

- decide whether sampled-profile phase inference is a real contribution or an appendix

Tasks:

- build the synthetic-truth harness
- collect time-preserving profile samples
- implement a naive baseline and one stronger segmentation baseline
- compute calibration and interval-quality metrics

Exit criteria:

- promote to headline only if calibration is credible; otherwise keep as appendix or cut

### `ingest/`

Goal:

- add a tiny deterministic corpus builder only if public corpora are insufficient

Tasks:

- implement the smallest bounded crawl or corpus-build path needed for realism
- keep it deterministic and non-generic

Exit criteria:

- keep only if it materially improves workload realism or demo clarity

## Phase 6: Result Bundle

Goal:

- package the project so a skeptical reviewer can follow it without guessing

Status:

- first reviewer-facing result bundle, repeated benchmark tables, and narrow figure bundle implemented

What is already done:

- reviewer-facing summary added under `docs/kvscope_result_bundle.md`
- README now points directly at the repeated Phase 1 slice, expanded Phase 3 slice, repeated bridge slice, and the result bundle
- compact benchmark tables emitted under `artifacts/manifests/20260311-165220__serve__phase6__benchmark-tables.{json,md}`
- replay-depth-expanded benchmark tables emitted under `artifacts/manifests/20260311-170722__serve__phase6__benchmark-tables-expanded.{json,md}`
- hotset-cache-expanded benchmark tables emitted under `artifacts/manifests/20260311-171800__serve__phase6__benchmark-tables-hotset-expanded.{json,md}`
- tradeoff-expanded benchmark tables emitted under `artifacts/manifests/20260311-173725__serve__phase6__benchmark-tables-tradeoffs-expanded.{json,md}`
- repeated tradeoff benchmark tables emitted under `artifacts/manifests/20260311-175741__serve__phase6__benchmark-tables-tradeoffs-repeated.{json,md}`
- repeated tradeoff figure bundle emitted under `artifacts/manifests/20260311-175741__serve__phase6__benchmark-figures-tradeoffs-repeated.{json,md}` with PNG outputs under `artifacts/figures/`
- policy-surface-expanded benchmark tables emitted under `artifacts/manifests/20260311-182054__serve__phase6__benchmark-tables-policy-surface-expanded.{json,md}`
- policy-surface-expanded figure bundle emitted under `artifacts/manifests/20260311-182136__serve__phase6__benchmark-figures-policy-surface-expanded.{json,md}` with the same PNG outputs refreshed in place
- outward-facing wording now distinguishes between:
  - direct live cache-hit evidence
  - directional prefill evidence
  - replay-policy separation on live-derived traces
  - replay-policy headroom across repeated hotset geometries
  - replay-policy crossover on a second recency-versus-frequency geometry
  - remaining TTFT noise

Tasks:

- finalize artifact layout
- publish benchmark tables and plots
- write caveats and negative results
- tighten the README and runbook around what was actually measured

Deliverables:

- reviewer-legible result bundle
- end-to-end demo path

Exit criteria:

- a skeptical reader can reproduce the argument from manifests, raw results, and docs

## Phase 7: Investigator Layer

Goal:

- turn the current artifact lab into a grounded AI observability investigation system

Status:

- first slice implemented

What is already done:

- frozen core claim registry generated under `history/CORE-V1-CLAIMS.json` and `history/CORE-V1-CLAIMS.md`
- `analysis/` now exists with:
  - `analysis/core_claims.py`
  - `analysis/schema.py`
  - `analysis/index.py`
- local build and query scripts now exist:
  - `scripts/build_core_v1_claim_manifest.py`
  - `scripts/build_analysis_index.py`
  - `scripts/query_analysis_index.py`
- the first local SQLite corpus index now builds under `artifacts/analysis/kvscope-analysis.sqlite3`
- the first structured query path works against the real artifact set
- the first text-search path works against findings and markdown evidence

Tasks:

- keep Step 0 decisions locked while building the first code slice
- freeze `KVScope Core v1` before widening outward-facing claims
- build a queryable artifact corpus over manifests, results, live metrics, replay summaries, and report text
- expose the corpus through an MCP server with bounded investigation tools
  - status: first local-only stdio MCP slice is now implemented under `kvscope_mcp/`
- build one investigator that answers open-ended questions with citations and explicit caveats
- add an eval harness for answer quality, citation correctness, and overclaim control
- add a thin app only after the tool surface and eval loop are useful
- add standards-based export as an adapter, not a replacement for `kvtrace`

Deliverables:

- frozen core summary set with claim classes
- indexed local corpus
- MCP tool surface
- investigator answers for the seed questions
- seeded eval report
- thin app or CLI demo path

Exit criteria:

- a reviewer can ask a real observability question and get a grounded, cited, and measured answer without reading repo internals first

Current note:

- this phase now has a real first slice, not just a plan
- the analysis index and claim manifest are usable, and the full `KVScope Core v1` freeze is now complete for the current evidence surface
- Step 0 is now complete and locked in `history/INVESTIGATOR-BUILD-SPEC.md`
- the detailed module plan, execution order, acceptance gates, and kill conditions now live in `history/INVESTIGATOR-BUILD-SPEC.md`

## Immediate Next Slice

If continuing immediately, do this next:

1. expose the existing indexed corpus through MCP and only then build the bounded investigator
2. add the eval harness before broadening the agent loop or polishing the app layer
3. keep the frozen claim manifest synchronized with any future reporting-layer caveat changes
4. keep `profiles/` and `ingest/` off the critical path unless the investigator story stalls

## Kill Conditions

- if engine instrumentation requires deep forks too early, lean harder on `kvtrace/`
- if Modal behavior dominates the measurement story, reduce claims or change the deployment baseline
- if `profiles/` cannot produce calibrated results, demote it to appendix
- if `ingest/` starts acting like a product of its own, cut it
