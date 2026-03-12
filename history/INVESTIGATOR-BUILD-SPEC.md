> Current build authority for the investigator layer.
> If this file conflicts with older planning docs, trust this file and `history/DOCUMENT-MAP.md`.

# KVScope Investigator Build Spec

## Purpose

`KVScope` already has a credible evidence substrate:

- reproducible live serving runs
- bounded live cache metrics
- replayable `kvtrace`
- bridge reports
- capacity sweeps
- tables, figures, and reviewer-facing summaries

What it does not yet have is the layer most aligned with AI observability goals:

- a queryable artifact corpus
- an agent-usable tool surface
- a grounded investigation loop
- measured answer quality
- a user-facing investigation workflow

This document defines how to build that layer without destabilizing the scientific core.

## Current State

Today the repo is strong on evidence production and weak on investigation workflows.

What already exists:

- reproducible live serving runs
- bounded live cache metrics
- replayable `kvtrace`
- bridge reports and capacity sweeps
- reviewer-facing tables, figures, and result bundle
- disciplined claim boundaries around measured, replayed, and inferred evidence

What does not yet exist:

- queryable corpus over those artifacts
- stable tool surface over the corpus
- bounded investigation loop
- answer-quality evals
- user-facing investigation flow

This means the repo is already a credible artifact lab, but it is not yet the strongest possible demo of AI observability work.

## Goal State

The goal state is a reviewer-grade system with all of the following properties:

- a user can ask an observability question in plain English
- the system can retrieve the relevant runs, metrics, reports, and findings
- the system returns a cited answer with explicit caveats
- the system distinguishes measured, replayed, and inferred claims
- the system has test-backed tools and a scored eval set
- the system has a thin interface that makes the workflow legible without reading the repo first

The goal is not to become a general observability platform.

The goal is to build a small but real investigation system on top of a strong domain-specific evidence substrate.

## Scope

Build `KVScope Investigator`: a local-first AI observability system that answers open-ended questions over `KVScope` artifacts with grounded citations, explicit caveats, and measured answer quality.

The MVP must support questions like:

- which workload families show direct live cache hits
- where `lru` beats `fifo`
- where recency beats frequency and where that flips with capacity
- why cache-on helped in one family but not another
- which findings are repeated versus single-run versus exploratory

## Non-Goals

- replacing `kvtrace` with generic telemetry
- becoming a general-purpose observability SaaS
- building a many-agent architecture before the single-agent path is evaluated
- making `profiles/` or `ingest/` part of the demo-critical path
- chasing broad frontend polish before the tool surface and evals exist
- using a vector database before structured retrieval and FTS are proven insufficient

## External Grounding

This plan is shaped by the current role and current ecosystem as of March 11, 2026.

- Role emphasis:
  - AI-based monitoring systems
  - tools over large unstructured datasets
  - agentic integrations
  - user-facing apps and interfaces
  - trustworthy structured insight from messy evidence
- Engineering emphasis:
  - bounded tool-using agents
  - eval-driven iteration
  - careful context management
  - MCP-style tool ergonomics
- ecosystem convergence:
  - traces
  - datasets
  - evals
  - AI assistants
  - interoperability through MCP and trace standards

Grounding links are captured in `research/20260311-kvscope-investigator-plan.md`.

## Locked Assumptions

These are the current assumptions. If any fail, reopen the plan explicitly.

- Python remains the implementation language for the new layer.
- The current live artifacts under `artifacts/` remain the canonical evidence source.
- The current serving and replay core remains frozen during the first investigator slice except for tightly scoped evidence reinforcement.
- Local-first development matters more than cloud-native deployment for the investigation layer.
- `SQLite + FTS5` is the first storage layer.
- MCP is the first target agent/tool integration surface, but Step 0 may defer the wrapper by one slice if the internal tool contract is already stable and MCP integration friction is the blocker.
- `FastAPI` with server-rendered templates is the first user-facing app path.
- All generated answers must cite artifact paths and run IDs.
- Deterministic graders are preferred over model graders whenever possible.

## Success Criteria

The investigator layer is successful when all of the following are true:

- a user can ask an open-ended observability question without knowing repo internals
- the system retrieves the relevant artifacts without manual file scanning
- the answer cites exact files and run IDs
- the answer distinguishes measured evidence, replay evidence, and inference
- the system has an eval set with scored quality and overclaim controls
- the demo works from the app or CLI without narration carrying the entire explanation

## Step 0: Pre-Execution Lock

Goal:

- resolve the remaining research-backed ambiguities before the first implementation slice

Status:

- complete

Why this exists:

- the repo already has enough strategy
- the remaining risk is not broad uncertainty
- the remaining risk is drifting into the wrong first implementation because the tool surface, eval shape, or trust model was left implicit

Tasks:

- define the first `10` investigator questions
  - each question must specify:
    - required evidence types
    - required citations
    - allowed caveats
    - failure modes
- lock the answer taxonomy
  - claim types:
    - `measured`
    - `replay`
    - `inferred`
    - `caveat`
  - claim classes:
    - `repeated`
    - `single-run`
    - `exploratory`
- lock the MCP security and scope model
  - `stdio` transport first
  - local-only first
  - static tool registry first
  - read-only tools first
  - explicit artifact allowlist
  - no remote auth flow in the MVP
- lock the eval shape
  - task
  - trial
  - transcript
  - outcome
  - grader
  - report
- add step-level graders, not only final-answer graders
  - tool selection
  - tool parameter correctness
  - citation correctness
  - claim-type correctness
  - overclaim rate
- run the investigator harness tractability spike
  - compare direct API plus local tools
  - compare an Anthropic agent harness only if it preserves tool transparency and eval control
  - choose the simpler option that keeps transcript, citation, and grading control explicit
- lock the context-budget rules
  - search summaries before full artifacts
  - bounded artifact text reads
  - no bulk markdown dumps into the model
  - no uncontrolled tool-description bloat
- lock the differentiation note
  - explicitly state why `KVScope Investigator` is not just a generic trace viewer plus chat
  - explicitly state what generic platforms already do well
  - explicitly state the unique value of:
    - live-to-replay bridge
    - policy-surface reasoning
    - claim-boundary discipline
- lock the demo sanitization checklist
  - no secrets in manifests
  - no sensitive endpoints in screenshots
  - no hidden setup steps in the demo path

Deliverables:

- locked seed question set
- locked answer taxonomy
- locked MCP scope model
- locked eval schema
- investigator harness decision
- locked context-budget rules
- locked differentiation note
- locked demo sanitization checklist

Exit criteria:

- Step 1 can start without reopening architecture or trust-model debates
- the first implementation slice knows exactly what questions it must answer
- the first implementation slice knows exactly how it will be graded

Fallback rules:

- if MCP integration friction blocks early progress, keep the internal tool contract identical and defer the MCP wrapper by one slice
- if an Anthropic agent harness obscures transcript or grading control, use direct API plus local tool orchestration
- if corpus search quality is already good with structured filters and FTS, do not add embeddings

Current note:

- the seed question set, answer taxonomy, MCP scope model, eval schema, harness decision, context-budget rules, differentiation note, and demo sanitization checklist are now locked in this document

### Locked Investigator Questions

These are the first `10` questions the system must answer before any wider scope expansion.

1. Which workload families show direct live prefix-cache hits?
   Required evidence:
   Phase 3 live cache reports plus cited run IDs.
   Allowed caveats:
   direct hits do not automatically imply end-to-end latency wins.
   Failure modes:
   answering only from replay artifacts or omitting cache-off controls.

2. Which workload families show lower live prefill time with cache-on but still noisy client TTFT?
   Required evidence:
   Phase 3 cache-on/cache-off metrics and the caveat language from the corresponding report.
   Allowed caveats:
   client TTFT decomposition remains incomplete.
   Failure modes:
   collapsing prefill improvement into a broad latency-win claim.

3. Where does cache-on show both direct live cache hits and lower client TTFT?
   Required evidence:
   the locality-return cache-on/cache-off slice and its run artifacts.
   Allowed caveats:
   single cache-on/cache-off pair unless repeated later.
   Failure modes:
   generalizing locality-return into a global property of the system.

4. Where does `lru` beat `fifo` on live-derived replay?
   Required evidence:
   bridge reports and cited family-capacity pairs.
   Allowed caveats:
   replay is offline analysis over live-derived traces.
   Failure modes:
   presenting replay ranking as automatic online serving proof.

5. Where does `lfu` beat `lru`?
   Required evidence:
   hotset-scan bridge and capacity sweep artifacts.
   Allowed caveats:
   current headroom claim rests on one workload geometry unless expanded later.
   Failure modes:
   omitting that the evidence is geometry-sensitive.

6. Where does `lru` beat `lfu`?
   Required evidence:
   locality-shift bridge and capacity sweep artifacts.
   Allowed caveats:
   direct live hits do not imply a cleaner TTFT story.
   Failure modes:
   failing to distinguish replay advantage from live latency evidence.

7. Where do recency and frequency flip as replay capacity changes?
   Required evidence:
   locality-return bridge plus capacity sweep.
   Allowed caveats:
   current crossover rests on a limited family and limited capacities.
   Failure modes:
   claiming a general cache-law rather than a workload-specific tradeoff.

8. Which findings are repeated enough for a reviewer-facing demo?
   Required evidence:
   claim class plus repeated artifact families.
   Allowed caveats:
   some strong results remain `single-run` or `exploratory`.
   Failure modes:
   mixing repeated and single-run findings without labeling them.

9. Which findings remain exploratory or weakly supported?
   Required evidence:
   claim class, report caveats, and repetition status.
   Allowed caveats:
   unknowns and thin evidence should be surfaced directly.
   Failure modes:
   hiding weak spots or silently dropping them.

10. What is the strongest current uncertainty boundary in KVScope?
   Required evidence:
   Phase 3 caveats, replay-versus-live boundary, and any single-geometry limitations.
   Allowed caveats:
   uncertainty is a feature of the system’s epistemic discipline.
   Failure modes:
   turning uncertainty into vagueness rather than an explicit claim boundary.

### Locked Answer Taxonomy

Every answer must use the same claim model.

Claim types:

- `measured`
  - directly observed from live serving artifacts or explicit engine metrics
- `replay`
  - produced by offline analysis over live-derived `kvtrace`
- `inferred`
  - synthesis that combines measured or replay evidence without inventing new facts
- `caveat`
  - explicit uncertainty, limit, or non-claim

Claim classes:

- `repeated`
  - supported by multiple runs or repeated artifact families
- `single-run`
  - supported by one run pair or one unique artifact slice
- `exploratory`
  - early or thin evidence that should not be used as a headline claim

Answer envelope:

- `question`
- `short_answer`
- `claims`
- `limitations`
- `recommended_followups`

Every claim must include:

- `claim_type`
- `claim_class`
- `text`
- `citations`

Citation rules:

- every substantive claim cites at least one artifact path
- comparative claims cite both sides of the comparison where applicable
- claims about repeated evidence cite either the summary artifact or the underlying repeated runs

### Locked MCP Scope Model

The MVP MCP surface is intentionally narrow.

Transport and deployment:

- `stdio` transport only in the MVP
- local-only server in the MVP
- no remote HTTP transport in the MVP
- no third-party auth flow in the MVP

Capabilities:

- tools and resources only in the MVP
- no prompt catalog requirement
- no write-capable tools in the MVP
- no code-execution tool in the MVP

Tool registry:

- static tool registry in the MVP
- explicit allowlist of readable paths under:
  - `artifacts/`
  - `docs/`
  - `history/`
- no dynamic directory traversal outside repo scope

Operational constraints:

- bounded result counts by default
- bounded artifact text reads by default
- all tool calls logged with timestamp, parameters, and returned source paths
- tool outputs prefer structured fields over raw markdown blobs

Security posture:

- read-only first
- least privilege first
- no shell access from the investigator
- no mutation of artifacts during an investigation session

### Locked Eval Schema

The eval system must score both outcomes and process quality.

Task record:

- `task_id`
- `question`
- `intent`
- `required_evidence`
- `required_citations`
- `acceptable_caveats`
- `forbidden_overclaims`
- `allowed_tools`

Trial record:

- `task_id`
- `trial_id`
- `model`
- `prompt_version`
- `tool_calls`
- `transcript`
- `final_answer`
- `citations`
- `timestamp_utc`

Outcome record:

- `task_id`
- `trial_id`
- `completed`
- `failure_mode`
- `notes`

Grader set:

- final-answer factual correctness
- citation correctness
- tool selection quality
- tool parameter correctness
- omission rate
- overclaim rate
- claim-type labeling quality
- task completion

Grader policy:

- deterministic graders first
- model graders only where deterministic grading is insufficient
- held-out eval tasks required before widening the agent loop

### Locked Harness Decision

The initial investigation harness will use direct Anthropic API calls plus local typed tool orchestration.

Current implementation note:

- before live Anthropic integration, the repo now includes a deterministic MCP-backed investigator for the locked seed questions
- this is a staging slice, not a replacement for the later direct-API harness
- reason: the answer contract, tool-call transcript shape, and overclaim checks needed to be stable under test before adding model nondeterminism

Reasoning:

- Step 0 needs explicit transcript control
- Step 0 needs explicit tool-call logging
- Step 0 needs grading against exact tool parameters and citations
- the first slice is local, read-only, and artifact-centric

What this means:

- the internal investigation interface is defined first
- the MCP server is still the target tool surface
- the first investigator can call the same typed tool layer directly while MCP is being stabilized

What is deferred:

- using an Anthropic agent harness as the default execution path

Promotion rule:

- only adopt an Anthropic agent harness after the internal tool contract, transcript format, and eval reporting are stable enough that the harness does not reduce observability or grading control

### Locked Context-Budget Rules

The investigator must manage context deliberately rather than loading the corpus naively.

Rules:

- search first, read second
- fetch structured metrics before markdown summaries
- default search returns at most `8` matches
- default artifact text read returns only the bounded relevant slice
- no bulk inclusion of entire markdown artifacts unless explicitly justified
- compare no more than `2` runs or run sets in one step unless a higher-level summary artifact already exists
- prefer summary artifacts before underlying raw runs, then drill down only when needed
- keep tool descriptions short and specific
- never pass binary artifact contents to the model; pass metadata and file paths instead

### Locked Differentiation Note

`KVScope Investigator` is not meant to compete on generic feature count with LangSmith, Phoenix, Braintrust, HoneyHive, Helicone, or Weave.

Those systems already cover broad tracing, dataset, eval, and agent-observability use cases well.

`KVScope Investigator` is differentiated by:

- a domain-specific live-to-replay bridge for serving-cache questions
- explicit policy-surface reasoning over live-derived traces
- strong claim-boundary discipline between measured, replayed, and inferred evidence
- investigator questions that are specific to serving-cache behavior rather than generic trace summarization

The project should present itself as:

- a small, rigorous observability investigation system

The project should not present itself as:

- a general-purpose observability platform clone

### Locked Demo Sanitization Checklist

Before any external demo or walkthrough video:

- verify no secrets are present in manifests, screenshots, or shell history
- verify all cited artifact paths exist locally and open cleanly
- verify the demo uses a frozen artifact corpus rather than live-changing results
- verify every visible claim is labeled as `repeated`, `single-run`, or `exploratory`
- verify every visible result distinguishes measured, replayed, and inferred evidence
- verify the demo flow has no hidden setup step beyond documented environment variables
- verify screenshots do not expose unrelated services, hostnames, or tokens
- keep a prerecorded fallback for the investigator path if model latency or API issues arise during live capture

## Workstreams

### 1. Freeze `KVScope Core v1`

Goal:

- stop moving the evidence substrate while building the investigation layer

Tasks:

- repeat `locality-return` `2-3` more times before widening its crossover claim
- add one second `hotset`-style geometry if it creates a genuinely new replay surface
- classify all outward-facing findings as `repeated`, `single-run`, or `exploratory`
- publish one frozen summary artifact set that the investigator layer can rely on

Deliverables:

- frozen Phase 1, Phase 3, Phase 4, and Phase 6 summary set
- claim-class manifest or table
- documented corpus batches for `baseline` versus `exploratory`

Exit criteria:

- the investigator layer can point at a stable baseline corpus without chasing moving target docs

Risks:

- too much additional benchmarking delays the higher-signal product layer

### 2. Artifact Corpus And Index

Goal:

- turn `artifacts/` into a queryable local corpus

Build choice:

- `SQLite + FTS5`

Why:

- structured filters matter more than embedding similarity for the first slice
- exact citations and deterministic local reproducibility matter
- the corpus is small enough that operational simplicity wins

Core schema:

- `runs`
  - `run_id`
  - `family`
  - `phase`
  - `label`
  - `cache_mode`
  - `seed`
  - `batch_tag`
  - `family_claim_class`
  - `manifest_path`
  - `results_path`
- `run_metrics`
  - `run_id`
  - `ttft_p50_ms`
  - `prefill_mean_ms`
  - `throughput_tokens_per_s`
  - `live_prefix_queries`
  - `live_prefix_hits`
  - `live_prefix_hit_rate`
- `replay_summaries`
  - `artifact_id`
  - `run_id`
  - `policy`
  - `capacity_blocks`
  - `hit_rate`
  - `source_report_path`
- `capacity_curve_rows`
  - `family`
  - `policy`
  - `capacity_blocks`
  - `hit_rate`
  - `source_report_path`
- `findings`
  - `finding_id`
  - `family`
  - `claim_class`
  - `claim_kind`
  - `summary`
  - `source_path`
- `artifacts`
  - `artifact_id`
  - `run_id`
  - `artifact_type`
  - `corpus_scope`
  - `path`
  - `phase`
  - `created_at`
- `text_chunks`
  - `chunk_id`
  - `artifact_id`
  - `path`
  - `heading`
  - `text`

Planned modules:

- `analysis/schema.py`
- `analysis/index.py`
- `analysis/ingest.py`
- `analysis/search.py`
- `analysis/models.py`
- `tests/test_analysis_index.py`

Required behaviors:

- ingest manifests, results, `live_metrics.json`, replay reports, sweep reports, benchmark tables, and result-bundle markdown
- preserve exact source paths for every row
- support both structured queries and FTS-backed text search
- rebuild idempotently from the repo state

Exit criteria:

- the repo can answer structured questions like “show all cache-on runs with live hit rate > 0.3 and noisy TTFT caveats”

### 3. Corpus Expansion

Goal:

- make the investigation layer answer over a genuinely messy evidence set

Tasks:

- generate `100-300` additional runs across family, cache mode, capacity, and seed
- attach a `batch_tag` to every run
- keep clean baseline runs separate from exploratory runs
- record confounds explicitly:
  - cold start
  - warm start
  - cache mode
  - seed
  - model and runtime contract

Batch structure:

- `baseline-repeated`
- `policy-surface-expanded`
- `exploratory-stress`

Output:

- new run batches under `artifacts/runs/`
- ingestion manifest for the corpus builder

Exit criteria:

- the investigator no longer feels like it is answering over a tiny handcrafted artifact set

Risk:

- this can become a GPU burn pit if not hypothesis-driven

### 4. MCP Server

Goal:

- expose `KVScope` as an agent-usable observability system

Planned modules:

- `kvscope_mcp/server.py`
- `kvscope_mcp/catalog.py`
- `kvscope_mcp/models.py`
- `scripts/run_kvscope_mcp_server.py`
- `tests/test_kvscope_mcp.py`

Implementation note:

- use `kvscope_mcp/` instead of `mcp/` locally so the repo package does not shadow the official Python `mcp` SDK dependency

Initial tool contract:

- `search_runs`
  - filters by family, cache mode, claim class, metric threshold, and text query
- `get_run_manifest`
  - returns the manifest and artifact paths for one run
- `get_run_metrics`
  - returns serving and live cache metrics for one run
- `get_replay_summary`
  - returns replay results for one run or family at one capacity
- `get_capacity_curve`
  - returns family-policy curves across capacities
- `compare_runs`
  - returns a cited delta view between two runs or run sets
- `list_findings`
  - returns curated findings with claim class and source paths
- `read_artifact_text`
  - returns bounded text from one artifact with path and heading metadata

Resources:

- result bundle
- benchmark tables
- benchmark figures
- frozen summary manifests

Exit criteria:

- any MCP-capable client can inspect the `KVScope` corpus without repo-specific glue

### 5. Investigation Engine

Goal:

- answer bounded open-ended questions over the corpus with citations

Current status:

- first deterministic seeded-question investigator implemented over the MCP tool surface
- current implementation lives in:
  - `agent/answer_schema.py`
  - `agent/investigator.py`
  - `scripts/run_investigator.py`
  - `tests/test_investigator.py`
- direct Anthropic API reasoning is intentionally deferred until the eval harness is stable enough to grade it

Design:

- one investigator agent first
- one optional verifier pass second

Do not build first:

- a multi-agent orchestration tree
- autonomous run generation
- free-form long-horizon tool loops without evals

Planned modules:

- `agent/investigator.py`
- `agent/prompts.py`
- `agent/planner.py`
- `agent/verifier.py`
- `agent/answer_schema.py`
- `tests/test_investigator.py`

Answer contract:

- `question`
- `answer`
- `claims`
  - each claim has:
    - `type`: measured, replay, inferred, or caveat
    - `text`
    - `citations`
- `limitations`
- `suggested_followups`

Required behaviors:

- use MCP tools only, not ad hoc file access
- cite exact artifact paths and run IDs
- explicitly separate live evidence from replay evidence
- run an overclaim self-check before returning

Seed questions:

- why did cache-on help in `aligned-prefix` but not cleanly in `locality-shift`
- where does `lru` beat `fifo`
- where does `lfu` beat `lru`
- where do recency and frequency flip with capacity
- which findings are repeated enough to mention in a reviewer-facing demo

Exit criteria:

- the system can answer the seed questions with grounded citations and acceptable caveat quality

### 6. Evals

Goal:

- measure whether the investigation engine is useful and honest

Current status:

- seeded deterministic eval harness implemented over the locked seed-question set
- direct Anthropic-backed held-out eval harness implemented over the same MCP tool surface
- current implementation lives in:
  - `evals/tasks/seeded_investigator_tasks.yaml`
  - `evals/tasks/heldout_investigator_tasks.yaml`
  - `evals/runner.py`
  - `evals/graders.py`
  - `evals/reporting.py`
  - `scripts/run_investigator_evals.py`
  - `agent/anthropic_investigator.py`
  - `tests/test_eval_graders.py`
  - `tests/test_eval_runner.py`
  - `tests/test_anthropic_investigator.py`
- latest seeded eval artifact lives in:
  - `artifacts/evals/20260312-001938__investigator__seeded-evals/investigator-eval-report.json`
  - `artifacts/evals/20260312-001938__investigator__seeded-evals/investigator-eval-report.md`
- latest held-out Anthropic eval artifact lives in:
  - `artifacts/evals/20260312-031936__investigator__heldout-evals/investigator-eval-report.json`
  - `artifacts/evals/20260312-031936__investigator__heldout-evals/investigator-eval-report.md`
- current seeded eval slice scores the locked `5` deterministic tasks at `1.0` across:
  - factual correctness
  - citation correctness
  - tool selection quality
  - tool parameter correctness
  - omission rate
  - overclaim rate
  - claim-type labeling quality
  - task completion
- current held-out Anthropic slice scores the locked `15` held-out tasks at:
  - factual correctness `1.0`
  - citation correctness `1.0`
  - tool selection quality `1.0`
  - tool parameter correctness `1.0`
  - omission rate `0.0`
  - overclaim rate `0.0`
  - claim-type labeling quality `1.0`
  - task completion `1.0`

Planned modules:

- `evals/tasks/*.yaml`
- `evals/runner.py`
- `evals/graders.py`
- `evals/reporting.py`
- `tests/test_eval_graders.py`
- `tests/test_eval_runner.py`

Eval dimensions:

- factual correctness
- citation correctness
- omission rate
- overclaim rate
- task completion
- claim-type labeling quality

Dataset structure:

- `20-40` seeded tasks
- gold answer outline
- required citations
- acceptable caveats
- forbidden overclaims

Grader strategy:

- deterministic graders first:
  - citation paths exist
  - cited runs match claims
  - claim types present
- model grader only where deterministic grading is insufficient
- keep a held-out set for regression checks

Exit criteria:

- we can show a small eval dashboard with measurable answer quality and low overclaiming
- the next promotion gate after this clean held-out slice is demo hardening and broader held-out coverage, not immediate free-form agent broadening
- the first demo-hardening pass should keep the app narrow and guided, with `/demo` as the default reviewer path

### 7. Thin App

Goal:

- provide a user-facing interface without turning the project into frontend theatre

Framework:

- `FastAPI`
- server-rendered templates
- minimal JavaScript

Pages:

- run browser
- compare view
- workload family summary
- ask-the-investigator
- eval dashboard

Planned modules:

- `web/app.py`
- `web/routes/*.py`
- `web/templates/*.html`
- `web/static/*`
- `tests/test_web_app.py`

App rules:

- every answer card links to raw artifacts
- every chart is derived from source report JSONs
- the UI exposes claim class and evidence type

Exit criteria:

- a reviewer can navigate the system without reading the repo first

### 8. Standards Export

Goal:

- make the system legible to the current observability ecosystem without flattening its contribution

Planned modules:

- `interop/openinference_export.py`
- `interop/otel_export.py`
- `tests/test_interop_export.py`

Rules:

- export is adapter-only
- `kvtrace` remains the internal domain contract
- mark OTel GenAI export as provisional while the semantic conventions remain under development

Exit criteria:

- investigation traces and tool calls can be exported for interoperability demos

### 9. Comparative Integration

Goal:

- show ecosystem awareness without becoming a clone

Stretch path:

- export a bounded subset of runs into Phoenix or LangSmith
- document what generic tracing shows
- document what `KVScope` adds:
  - replay
  - claim boundaries
  - policy surface reasoning

Exit criteria:

- one honest comparison note, not an integration rabbit hole

## Recommended Execution Order

### Step 0

- lock the first `10` investigator questions
- lock the answer taxonomy and claim classes
- lock the MCP scope and security model
- lock the eval schema and grader types
- run the investigator harness tractability spike
- lock the context-budget rules
- lock the differentiation note
- lock the demo sanitization checklist

### Week 1

- freeze `KVScope Core v1`
- classify claims
- publish the frozen summary set

### Week 2

- build `analysis/` schema and index
- ingest the current corpus
- add CLI-level structured and text search

### Week 3

- add MCP server and tool contract
- add deterministic investigation queries over MCP
- seed `10-15` eval tasks in parallel

### Week 4

- build the bounded investigator
- add verifier pass
- run the first eval loop

### Week 5

- expand the eval set to `20-40`
- build the thin app
- add the eval dashboard

### Week 6+

- expand the corpus deliberately
- add interop export
- add one bounded comparative integration if it strengthens the demo

## Parallelization Plan

Run these streams in parallel after Week 0.

- Stream A:
  - freeze core
  - repeat the thinnest evidence families
  - expand baseline and exploratory batches
- Stream B:
  - build `analysis/`
  - build ingestion and search
- Stream C:
  - define investigation questions
  - build eval tasks and graders
- Stream D:
  - build MCP tools
  - integrate the investigator

Do not start Stream E, the app layer, until Streams B through D already produce useful output.

## Acceptance Gates

### Gate 1: Corpus Ready

- `analysis/` rebuilds the index from repo state
- structured search works
- FTS search works
- every row points back to a source artifact

### Gate 2: Tool Surface Ready

- MCP tools cover the seed investigation questions
- tool outputs are stable and test-backed

### Gate 3: Investigation Ready

- the investigator answers the seed questions with citations
- overclaim self-check is working

### Gate 4: Eval Ready

- seeded tasks run end to end
- graders produce stable scores
- regressions are detectable

### Gate 5: Demo Ready

- app or CLI can answer a real question live
- citations are visible
- eval dashboard exists
- demo does not depend on hidden manual setup

## Kill Conditions

- if `SQLite + FTS5` cannot answer the retrieval patterns cleanly, reevaluate storage before adding a vector DB
- if the investigator is mostly useful only because the prompts memorize repo language, harden the eval set and reduce prompt dependence
- if the app becomes the main source of complexity, demote it until the tool surface and evals are solid
- if corpus expansion stops being hypothesis-driven, cap it and redirect effort into evals and tooling

## Demo-Critical Path

The minimum reviewer-grade version is:

1. frozen core summary set
2. indexed artifact corpus
3. MCP tool surface
4. investigator answering `3-5` real questions with citations
5. seeded eval dashboard proving low overclaim and decent answer quality
6. thin app or CLI walkthrough showing the full loop

That is enough to show:

- production systems depth
- observability judgment
- agent/tool design
- eval discipline
- user-facing usefulness

without needing to build a much larger platform.
