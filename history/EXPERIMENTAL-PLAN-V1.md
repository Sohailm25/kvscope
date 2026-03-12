ABOUTME: Master experimental plan consolidating all research, code reviews, and design direction for the KVScope project.
ABOUTME: This document is the single source of truth for the current session's findings. A third research source is pending.

# KVScope Experimental Plan — v1 (2026-03-12)

**Status:** DRAFT — awaiting third research source before finalizing
**Session:** Started 2026-03-12, pre-compaction snapshot

---

## Table of Contents

1. [Context and Goal](#1-context-and-goal)
2. [Code Review Findings (5 parallel reviews)](#2-code-review-findings)
3. [Decision: Strip the Investigator Layer](#3-decision-strip-the-investigator-layer)
4. [Removal Plan (Safe Cuts)](#4-removal-plan)
5. [README and Narrative Rewrite Plan](#5-readme-and-narrative-rewrite-plan)
6. [Research Knowledge System — The New Addition](#6-research-knowledge-system)
7. [Oracle Research Findings](#7-oracle-research-findings)
8. [X/Twitter Research Findings (6 Grok searches)](#8-x-twitter-research-findings)
9. [Second Research Source Findings](#9-second-research-source-findings)
10. [Reconciled Architecture](#10-reconciled-architecture)
11. [Open Questions](#11-open-questions)
12. [Next Steps](#12-next-steps)

---

## 1. Context and Goal

This repository contains KVScope — a cache-aware AI observability lab targeting research engineering depth.

**Original problem:** The project had an investigator + web app + eval harness layer that was over-engineered and looked "vibecoded." The goal shifted to:

1. Strip the weak layers (investigator, web app, evals)
2. Polish the strong core (workload design, serving, replay, claims)
3. Add a genuinely novel, high-signal component: a research knowledge extraction and sharing system
4. Present the whole thing as one coherent story

**What reviewers should see:**
- Understanding of how components work
- Ability to start simple and scale up to production
- Unique results with evidence backing them
- Intentional design choices, not over-complexity for no reason
- Good logic, reasoning, and setup
- NOT vibecoded

---

## 2. Code Review Findings

Five parallel critic agents reviewed every major component. Here are the verbatim findings.

### 2.1 Agent/Investigator Code (agent/)

**Overall Assessment:** Request Changes
**Critical Issues:** 3

**Critical Issue 1: The "Investigator" is a Switch Statement to Canned Answers**
- `investigator.py:22-67` routes questions via string matching to pre-written answer methods
- `if "aligned prefix" in normalized_question and "locality shift" in normalized_question:` → hardcoded routing
- `else: raise ValueError(f"unsupported investigator question: {question}")` — can only answer ~5 pre-programmed questions
- A reviewer will immediately see this is just a switch statement
- The tool calls in each `_answer_*` method are choreographed to support a pre-determined narrative

**Critical Issue 2: AnthropicInvestigator Routing is Just as Rigid**
- `anthropic_investigator.py:402-494` (`_route_for_question`) does string matching to pre-select tools, inject massive prompt guidance, and dictate what the answer should say
- `final_answer_guidance` literally tells the model what conclusions to draw (400+ characters)
- This isn't "tool use" — it's "template filling with extra steps"
- A reviewer will see this as not trusting the model to reason

**Critical Issue 3: Overclaim Detection is Security Theater**
- `runtime.py:59-106` (`run_overclaim_self_check`) is a regex-based keyword scanner
- `FORBIDDEN_OVERCLAIM_TERMS = ("prove", "proves", "always", "never", "global", "automatic")`
- Trivially bypassable: "This demonstrates" = fine, "This proves" = flagged. Same semantic meaning.
- Negation detection uses arbitrary 40-character prefix window
- Doesn't catch actual overclaims in the codebase (e.g., "Cache-on helps cleanly")

**Suggestions:**
- Tool call recording has no timing info, no error rate tracking
- Claim types are confusing: "caveat" is not a claim type — it's a hedge
- System prompt is too generic and vague
- `_enforce_route_boundaries` is bizarre — force-adds missing claims to Claude's output via regex
- Error handling is inconsistent (some errors swallowed, others crash)
- Transcript is low-information ("emitted structured JSON" is not informative)
- Heavy use of `dict[str, Any]` instead of typed models
- Missing type annotations (using `Any` defeats the purpose of type hints)

**Positives:**
- Excellent separation of concerns between answer schema, runtime, and investigator
- Thoughtful claim taxonomy (measured/replay/inferred)
- Good use of Pydantic for structured outputs
- Source path tracking for citations is clever

### 2.2 Serving and Benchmark Code (serve/, bench/)

**Overall Assessment:** Request Changes
**Critical Issues:** 3

**Critical Issue 1: Trace Events Are Derived Fiction, Not Real Observations**
- `kvtrace/trace_builder.py:22-50` uses local `OrderedDict` simulation
- Events marked `source_kind="derived"` but stored in same NDJSON as if real
- Timestamps are sequential integers (1_000, 1_050), not real nanoseconds
- No actual instrumentation of vLLM internals
- The ABOUTME comment proves the author knows this is questionable

**Critical Issue 2: No Statistical Rigor in Latency Claims**
- Reports p50/p95/p99 on 4-8 request workloads (p95 = p99 = max value with 4 requests)
- No confidence intervals, no warmup discarding, no stddev
- `warmup_requests_discarded: 0` in all manifests
- Each workload run exactly once per configuration
- Results could be entirely explained by Modal cold-start variance

**Critical Issue 3: Cache Policy Replay Doesn't Validate Correctness**
- `kvtrace/replay.py:49-67` assumes vLLM uses LRU but never validates this
- No cross-check between simulated hits and `vllm:prefix_cache_hits` from Prometheus
- vLLM uses PagedAttention with complex memory management — may not be pure LRU
- Block pinning during generation means unpinned blocks evict first

**Positives:**
- **Tokenizer round-trip handling is excellent** — `_find_stable_token_ids()` with round-trip check, preferring space-prefixed tokens
- **Prometheus metric scraping is production-grade** — version-aware aliases, correct histogram aggregation
- **Artifact provenance is excellent** — git SHA, exact reproduce commands, schema versioning
- **Workload diversity** — 10+ families show real thought about cache behavior
- **Modal deployment works** — correct use of volumes, GPU allocation

### 2.3 Test Coverage and Evals

**Overall Assessment:** Request Changes
**Critical Issues:** 3

**Critical Issue 1: "Held-Out" Evals Are Not Held-Out — Data Leakage**
- `_HeldoutInvestigatorStub` in `test_eval_runner.py:84-351` has memorized the exact answers to all "held-out" questions
- Helper functions `_citations_for_question()`, `_text_for_question()`, `_caveat_for_question()` are test oracle leakage
- The eval harness has never actually been tested on truly unseen questions

**Critical Issue 2: Perfect 1.0 Scores — Suspiciously Lenient Grading**
- Every metric scores 1.0 across all 15 held-out tasks
- Grading uses simple string matching with `_normalize_text()` (just lowercases and removes backticks)
- Citation matching only checks if string is present, not if it's relevant
- `_coverage_score` returns 1.0 automatically if `total == 0`
- No negative test cases proving graders catch failures

**Critical Issue 3: Tests Validate Mocks, Not Real Behavior**
- `test_live_benchmark.py` validates that `_FakeClient.close()` sets `self.closed = True`
- `test_anthropic_investigator.py` tests pre-canned fake responses, not real API integration
- No integration tests, no VCR/cassette recorded API responses

**Positives:**
- Excellent test documentation (ABOUTME headers)
- Structured eval tasks with rich metadata (intent, required_evidence, acceptable_caveats, forbidden_overclaims)
- Citation tracking in eval harness
- Workload generation tests are thorough (8 families)

### 2.4 KVTrace Replay System and MCP Server

**Overall Assessment:** Request Changes with strong positive notes
**Critical Issues:** 1

**Critical Issue: Trace Derivation vs. Live Modeling**
- Entire kvtrace system built on derived synthetic traces, not live vLLM internals
- ABOUTME line 2: "The source_kind on these events must stay honest because they are derived from workload structure, not raw engine internals"
- The "bridge" compares real vLLM latencies to simulated cache traces
- Block lifecycle model (lookup → hit/insert → pin → unpin → evict) assumes vLLM matches OrderedDict

**Positives (strong):**
- **Replay engine is correct** — textbook LRU/FIFO/LFU implementations
- **MCP server is well-designed** — bounded queries, structured outputs, provenance tracking, FTS5 indexing
- **Analysis corpus is well-designed** — explicit claim classification, structured artifact ingestion, proper relational schema
- **Workload design shows domain knowledge** — 10+ families testing specific hypotheses
- **"Honesty discipline" is noteworthy** — explicit non-claims, source tagging, negative controls
- **Every tool call logs provenance** (`source_paths` in all results)
- **SQLite FTS5 integration** for full-text search

### 2.5 Claims and Evidence Rigor

**Overall Assessment:** Approve with Discussion Points
**Critical Issues:** 0

**Key Concerns:**
- "LRU beats FIFO" claim may be too obvious — textbook cache theory
- Should reframe as "policy separation on live traces" not the directional result
- Perfect eval scores (15/15, all 1.0) are suspicious
- Claim hierarchy (repeated/single-run/exploratory) feels bureaucratic without justification

**The Interesting Results Are Buried:**
- LFU > LRU on hotset-scan (0.375 vs 0.271) — this is novel
- Capacity crossover in locality-return (LRU wins at cap 2-3, LFU wins at cap 4) — this is the surprise
- These should be the HERO narrative, not buried as claim #6

**Skeptic's First Three Questions:**
1. "Isn't LRU > FIFO just... obvious?"
2. "How do I know the investigator eval isn't tuned to the implementation?"
3. "What would falsify your claims?"

**Positive:**
- Evidence is real (JSON artifacts exist with specific numbers)
- Caveats are honest ("scraped vLLM TTFT ≠ client TTFT", "replay ≠ proof of live improvement")
- Negative control exists (no-overlap-control with 0 hits)
- Claim boundaries are explicit
- Narrative feels authentic, not AI-generated

---

## 3. Decision: Strip the Investigator Layer

**Rationale:** The investigator is the single biggest liability:

1. Deterministic investigator is a switch statement to canned answers
2. Anthropic investigator doesn't trust Claude (`_enforce_route_boundaries` injects claims post-hoc)
3. Eval scores (15/15, all 1.0) invite the wrong scrutiny
4. It's the most vibecoded-looking layer (~2000 lines of orchestration)
5. The web app is the wrong demo surface for this project
6. The MCP server is good — keep it as infrastructure

**What to keep:** MCP server (well-designed, shows tool surface thinking)
**What to cut:** investigator, web app, eval harness, demo script

---

## 4. Removal Plan

**The codebase has clean boundaries.** The investigator/eval/web layer sits entirely on top — zero reverse dependencies into the core.

### Files/Directories to Remove (19 items):

**Directories (4):**
1. `web/` — entire Flask app (app.py, templates/, static/)
2. `evals/` — entire eval harness (runner.py, graders.py, reporting.py, tasks/)
3. `agent/` — ALL 6 files (investigator.py, anthropic_investigator.py, runtime.py, answer_schema.py, prompts.py, __init__.py)
4. `artifacts/evals/` — eval output artifacts

**Scripts (3):**
1. `scripts/run_investigator.py` — imports agent.investigator
2. `scripts/run_investigator_evals.py` — imports evals.runner
3. `scripts/run_web_app.py` — imports web.app

**Tests (5-6):**
1. `tests/test_investigator.py`
2. `tests/test_anthropic_investigator.py`
3. `tests/test_agent_runtime.py` (if exists)
4. `tests/test_eval_graders.py`
5. `tests/test_eval_runner.py`
6. `tests/test_web_app.py`

**Docs (1):**
1. `docs/kvscope_demo_script.md`

**Dependencies (1):**
1. `anthropic==0.84.0` from requirements.txt (only used by removed code)

### What Stays Clean (zero modifications needed):
- `kvscope_mcp/` — no agent/ imports
- `analysis/` — no agent/ imports
- `serve/` — no agent/web/evals imports
- `bench/` — no agent/web/evals imports
- `kvtrace/` — no agent/web/evals imports
- All 11 remaining scripts (build_analysis_index.py, build_benchmark_figures.py, etc.)
- All remaining test files (test_analysis_index.py, test_benchmark_figures.py, test_core_claims.py, test_kvscope_mcp.py, etc.)

### README.md Requires Extensive Edits:
Lines referencing agent, investigator, web, evals, demo routes need removal/rewrite.

---

## 5. README and Narrative Rewrite Plan

### Current Problems (from README review):

1. **370 lines — far too long.** Target: 80-120 lines.
2. **"Current Status" section (lines 52-232)** is 180 lines of exhaustive artifact enumeration — reads like AI-generated documentation
3. **Defensive hedging everywhere:** "Current honest interpretation:", "Current caveat:", "so the direct claim is..."
4. **Artifact file listings add no value** — reviewers won't navigate timestamps like `20260311-182034__serve__phase1__...`
5. **"What This Is Not" section suggests insecurity** — defending against accusations no one made
6. **Reproduce section is 90 lines of noise** — 13 separate modal commands with no context
7. **Interesting results buried** — LFU > LRU on hotset, capacity crossover in locality-return, workload-policy interaction

### New README Structure (60-second version):

```
# KVScope

Cache-aware AI observability: can we explain serving regressions with measured facts?

## What I Found

**Cache policies separate on real workloads:**
- LRU > FIFO on eviction patterns (0.417 vs 0.25 hit rate)
- LFU > LRU on hotset-scan, but reverses on locality-shift
- Capacity crossover: locality-return shows policy ordering flip at cap=4

**Replay preserves live ordering** (aligned > near-aligned > no-overlap)
**Client TTFT is noisy** (2x variance), but replay methodology still useful

See [Result Bundle](docs/kvscope_result_bundle.md) for details.

## How It Works

- `serve/` — vLLM baseline on Modal, Prometheus metric scraping
- `bench/` — workload generators (10+ families)
- `kvtrace/` — trace builder + replay engine (LRU/FIFO/LFU)
- `analysis/` — SQLite corpus + claim registry
- `kvscope_mcp/` — MCP tool surface over corpus

## Try It

python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_repo_readiness.py

## Reproduce Key Results

./scripts/reproduce_key_results.sh

## Decision Docs

[Outline](history/FINAL-PROJECT-OUTLINE.md) | [Claims](history/CLAIMS-AND-NON-CLAIMS.md) | [Results](docs/kvscope_result_bundle.md)
```

### Result Bundle Rewrite (docs/kvscope_result_bundle.md):

**Problem:** Core insight buried. Opens with generic question, then 32 lines of file paths before any results.

**Fix:** Lead with the finding:
```
**Core Finding:** Cache policy effectiveness depends on workload geometry.
LFU wins on hotset-scan (0.375 vs 0.271 for LRU), but LRU wins on
locality-shift (0.375 vs 0.188 for LFU). Capacity crossovers exist
where the optimal policy flips at different cache sizes.
```

Then: workload-policy interactions → live serving evidence → replay-to-live bridge → caveats → artifact index (appendix).

### Claims Docs Updates:

1. Add trace derivation honesty to `CLAIMS-AND-NON-CLAIMS.md`:
   - "KVScope does not extract block-level events directly from vLLM internals"
   - "The kvtrace events are derived from workload structure and a simplified cache model"
   - "The bridge compares live serving latencies to replayed cache behavior on synthetic traces"

2. Reframe LRU>FIFO claim in `CORE-V1-CLAIMS.md`:
   - From: "replay-eviction-ordering-lru-beats-fifo"
   - To: "replay-eviction-ordering-policy-separation-on-live-traces"

3. Add "Falsification Criteria" section:
   - If no-overlap-control showed hits → alignment story breaks
   - If cache-off runs showed prefix-cache queries → toggle isn't working
   - If replay policies all converged → workload-policy interaction disappears

---

## 6. Research Knowledge System — The New Addition

### The Concept

An autonomous agent that reads any experiment directory, extracts structured findings, and pushes them to a central searchable archive. Key insight: **AI solves the adoption problem** — existing tools (W&B, MLflow) require researchers to change workflow; this reads what they already have.

### Four-Layer Architecture (from second research source):

**Layer 1: Capture** (Claude Code Skills + Hooks)
- `/publish-research` skill: interactive research card generator
  - Uses Cartographer pattern: parallel Sonnet subagents with 1M context windows
  - Outputs standardized research card (hypothesis, methodology, findings, open questions, contact, tags)
- `/retrospective` skill: captures the journey (failed approaches, debugging insights, parameter decisions)
  - Borrowed from Sionic AI pattern (1,000+ ML experiments/day)
  - Key insight: Claude writes while everything is still in context
- `Stop` hook: gentle nudge after sessions with findings ("Run /publish-research?")

**Layer 2: Review & Standardize** (Git + PR workflow)
- Skills output standardized markdown files
- Create branch, open PR to central GitHub repo
- Human review step ensures quality (solves "garbage in" problem)
- PR review adds context, teammate validates accuracy

**Layer 3: Index & Search** (RAG over repository)
- GitHub Action triggers indexing pipeline on merge
- Embeddings via text-embedding-3-large or self-hosted model
- Vector store: pgvector, LanceDB, or Chroma (self-hostable for security)
- MCP server that any Claude Code instance can connect to
- `/advise` skill queries the MCP server before starting new experiments

**Layer 4: Social Discovery** (browsable interface)
- Simple web UI on top of same index
- Browsable by tag, researcher, team, date
- Static site generated from GitHub repo with same embeddings for search

### Connection to KVScope

KVScope's claim taxonomy (measured/replay/inferred, repeated/single-run/exploratory) becomes the schema foundation for research cards. One coherent story:
- "I built a cache experiment with explicit claim boundaries"
- "I realized that claim structure is general-purpose for research findings"
- "So I designed a system to extract and share structured findings across a research org"

### Buildable Scope

| Deliverable | Effort | Signal |
|---|---|---|
| Clean KVScope + design doc | 1-2 days | "Can build AND think" |
| + working `/publish-research` skill on KVScope | 2-3 days | "Can build AND ship the concept" |
| + central repo + basic search | 4-5 days | Risky — lots of surface area |

---

## 7. Oracle Research Findings

### Research Report 1: Experiment Tracking Landscape (March 2026)

**Key Findings:**

1. **W&B** remains strongest standalone. Weave product bridges experiment tracking with LLM/agent workflows. Has some text extraction but for model *outputs*, not experiment *repos*.

2. **MLflow** (3.10.0, Feb 2026) pivoted to GenAI observability. Multi-workspace, no-code LLM judge eval, agent lifecycle tracking. 30M+ monthly downloads. Open-source standard.

3. **Neptune.ai is DEAD.** OpenAI acquired it (~$400M stock, Dec 2025). SaaS permanently shut down March 5, 2026. All data irreversibly deleted.

4. **ClearML** continues as solid open-source MLOps (1,300+ enterprise customers) but no AI extraction features.

5. **No new breakthrough tools** for experiment tracking. Market shifted to "AI observability" (production monitoring of LLM apps).

6. **Glean** is king of enterprise search. Can index GitHub repos (PRs, issues, code) with permissions. 1.9x preferred over ChatGPT in blind evals. But does NOT parse experiment structure or extract findings.

7. **Notion AI** has strong within-workspace search (10x scaling, 50-70ms latency). Cannot search across separate workspaces.

8. **THE BIGGEST GAP:** No tool reads experiment repos and extracts structured findings. Market has tools that track going forward (W&B, MLflow), search text (Glean), pack codebases (Repomix). Nothing bridges retrospective extraction.

9. **No productized "internal ArXiv" exists.** Labs use ELNs, Confluence/Notion, custom solutions.

10. **Claude Code building blocks are mature:**
    - Background agents (GA since v2.0.60)
    - Multi-pass analysis proven (Claude Code Security: 21.2 independent tool calls, multi-stage self-verification)
    - Subagent parallelism (3 subagents analyze 50K-line project in ~45 seconds)
    - Custom skills/commands: unified system with isolated subagents
    - Headless mode: full programmatic control
    - GitHub MCP Server (official): browse repos, manage issues/PRs
    - Repomix MCP Server: package repos for AI analysis

### Research Report 2: Autonomous Agent Patterns (March 2026)

**Key Findings:**

1. **Claude Code headless mode** (`-p` flag): pass prompt, reads codebase, outputs to stdout. `--output-format json`, `--session-id` + `--resume` for multi-turn.

2. **Claude Agent SDK** (Python v0.1.48, TypeScript v0.2.71): async iterator, custom tools via in-process MCP, cost limits (`max_cost_usd`), tool restrictions.

3. **Karpathy's AutoResearch** (March 8, 2026, 630 lines, 8k+ GitHub stars): ran 700 autonomous changes over 2 days, found ~20 additive improvements with 11% efficiency gain on GPT-2 training. Reads `program.md`, modifies `train.py`, runs 5-minute experiments, checks metrics, commits or reverts.

4. **OpenScholar** (Nature, Feb 2026): RAG over 45M papers. Experts preferred its responses over human-written answers 70% of the time. Open source.

5. **"Science Should Be Machine-Readable"** (Booeshaghi et al., bioRxiv Jan 2026): demonstrated automated extraction from entire eLife corpus. Results should be explicit machine-readable structures.

6. **ORKG Reborn** (Nature Scientific Data): pre-publication approach producing machine-readable findings using linked triples with provenance.

7. **Claude Code Review** (March 9, 2026): multiple specialized agents in parallel (security, performance, architecture, domain logic) → aggregator cross-validates, deduplicates, ranks by severity. 54% of PRs get substantive comments. <1% false positive rate. $15-25 per review.

8. **Custom multi-agent setups** straightforward with subagents. 100+ published subagent definitions (VoltAgent collection).

9. **No dominant standard for machine-readable research findings.** MLflow's schema (Experiment > Run > Parameters/Metrics/Artifacts/Tags) is most adopted. Practical recommendation: start with MLflow schema and extend with hypotheses, claims, confidence levels, code references.

10. **QMD** (Tobi Lutke): local CLI semantic search for markdown. **GitBook Agent**: learns from repos, generates documentation. **RAGFlow** (70k+ stars): enterprise knowledge base infra.

---

## 8. X/Twitter Research Findings (6 Grok Searches)

### Search 1: Anthropic Employees on Research Tooling

**Result:** Limited direct matches — Anthropic employees are discreet about internal tooling.

**@saffronhuang** (Societal Impacts researcher @AnthropicAI, Dec 4, 2025):
> "We built another tool - Anthropic Interviewer - that lets us interview people at scale by using Claude (obviously! we use Claude for everything!). See the piece for what we learned. This helps us expand the kind of research we can do which is exciiiiiitingggg -- it's is what we used for the internal qualitative interviews for the 'How AI is transforming work at Anthropic' study that dropped earlier this week."
- https://x.com/saffronhuang/status/1996632025412128957

**@saffronhuang** (Dec 2, 2025):
> "I'm so proud to have led this work... We decided to study how Anthropic engineers/researchers' jobs are changing... we thought: ok, AI is being used a lot in people's jobs... can we turn Anthropic into a living lab and study ourselves first?"
- https://x.com/saffronhuang/status/1995936052889223589

**@saffronhuang** (Feb 18, 2026):
> "New Societal Impacts research on studying how humans use and interact with AI agents (mostly coding agents)!"
- https://x.com/saffronhuang/status/2024224252803895599

**@AshPrabaker** (MTS @ Anthropic, Jan 12, 2026):
> "cowork has replaced my chat mode usage almost entirely and any product which changes behaviour for such a core surface is worth paying attention to hoping a lot more people get to feel the power of a good agentic harness outside of claude code."
- https://x.com/AshPrabaker/status/2010808437278638343

**@jackclarkSF** (Feb 2026 — THE MONEY QUOTE):
> "It's a fair question and something me and the team were discussing today. Our sense is we still have a ways to go on building the underlying tools and making them self-serve and once we've done that, we'll be well positioned to hire a range of social scientists."
- https://x.com/jackclarkSF/status/2024964364969935098

> "We've run this loop once already with the economics research team, though even there we've had to initially prioritize economists with coding experience because there's still some technical work required to interface with relevant tools, though this is improving over time."
- https://x.com/jackclarkSF/status/2024964608809918650

**@alexalbert__** (Anthropic, Mar 2026):
> "This has been a game changer for our internal eng and research teams. Rare to see a product get this much praise from some of the top engineers I know."
- https://x.com/alexalbert__/status/2031117564512981169

### Search 2: Claude Code Skills for Knowledge Management

**Edward Wu's Academic Research Skills** (@JeremyNguyenPhD, Mar 10, 2026, 700+ likes):
> "Claude Code skills for Academic Research: Edward Wu shares a suite of skills, complete with a 12-agent paper writing workflow, and a 13-agent research team."
- GitHub: https://github.com/Imbad0202/academic-research-skills
- https://x.com/JeremyNguyenPhD/status/2031314968675758452

**@limgangrui** (Jan 12, 2026) — PKM with Claude Code:
> Turned knowledge management system into repo using Obsidian as visualization layer and Claude Code as agent. Built 2 skills: (1) Clipper skill extracts content from links, creates Obsidian notes, auto-tags; (2) Dataview creator generates filtered views.
- https://x.com/limgangrui/status/2010724717901328790

**@aniketapanjwani** (PhD Economics, Jan 20, 2026) — Subagent lit review:
> Download 100 papers → define criteria in subagent → pdfgrep each paper → write findings to markdown → main agent compiles PDF with pandoc. "Easiest Claude Code win for academics."
- https://x.com/aniketapanjwani/status/2013410873717457230

**@avthar** (Jan 2026): Skills (load .md for specialized knowledge), Custom Subagents (isolated parallel processes), Slash Commands (user-invoked shortcuts).
- https://x.com/avthar/status/2013787939197591901

**@Noahhh1005**: Using Claude Code `/loop` for interactive observability in research vs. headless mode.
- https://x.com/Noahhh1005/status/2031208855724765314

**claude-scientific-skills**: 140+ domain-specific skills for bioinformatics, genomics, clinical data.
- https://x.com/ihtesham2005/status/2028073821232881675

### Search 3: ML Research Knowledge Loss Problem

**@YiTayML (DeepMind, May 8, 2025)** — DIRECT EVIDENCE OF DUPLICATED RESEARCH:
> "Sharing a pretty interesting story about how two research projects can end up with a very different outcome despite almost similar type of 'work' being done... there was another more low-key effort within Google that did almost all the same work but was pretty under-hyped... Despite so much parallel 'almost identical' work being done..."
- https://x.com/YiTayML/status/1920535379545108835

**@joburgai (Mar 6, 2026)** — Research findings as "historical artifacts":
> "This is worse than it looks. We annotate and red team for model behaviors, and by the time a paper gets published the model has updated 2-3x. The findings are historical artifacts before they're even out. Reproducibility is basically impossible in this space."
- https://x.com/joburgai/status/2029833803498127397

**@eigenron (Sep 12, 2025)** — ML research is ephemeral:
> "Coming from physics... most research ideas/approaches are just trial and error... researchers don't know why something works or how... paradigms change weekly."
- https://x.com/eigenron/status/1966522636998955395

**@aimodelsfyi (Mar 6, 2026)** — Duplicated experiments:
> "be me ML researcher watching 5 models train each one making the exact same mistakes model A figures something out after 100k examples model B right next to it learning nothing from A they're literally doing the same task both discovering identical insights independently"
- https://x.com/aimodelsfyi/status/2029740357139972513

**@cremieuxrecueil (May 2024)**: Analyzed 93 fMRI/statistics papers, only ~15% reproducible.
- https://x.com/cremieuxrecueil/status/1787257720271253545

### Search 4: MCP Research Tools and Knowledge Graphs

**Cartographer** (@KingBootoshi, Jan 13, 2026):
> Claude Code skill/plugin using parallel Sonnet subagents to analyze entire codebase, generate complete architecture doc/map. "YOU JUST NEVER GAVE IT A MAP"
- GitHub: https://github.com/kingbootoshi/cartographer
- https://x.com/KingBootoshi/status/2011205064724267245

**Mercator-AI** (@shihwesley, Feb 6, 2026):
> Open-source fork of Cartographer. Adds Merkle trees for SHA-256 hashing (O(1) staleness checks), auto-staleness prevention via post-commit hooks.
- GitHub: https://github.com/shihwesley/mercator-ai
- https://x.com/shihwesley/status/2019863624676753476

**DeepGraph MCP** (via @unwind_ai_, Sep 2025):
> Turns code repos into interactive knowledge graphs for semantic search, dependency analysis, and relationships. 100% open-source.
- https://x.com/unwind_ai_/status/1968512868544082377

**Claude Analysis** (@lihanc02, Mar 5, 2026):
> Visualizes Claude Code agent traces as explorable execution graphs/DAGs — like distributed tracing for observability.
- https://x.com/lihanc02/status/2029635557559804046

**GPT Researcher MCP Server** (@assaf_elovic, Mar 2025):
> All-in-one MCP server for web research (quick search to deep/multi-hop research).
- https://x.com/assaf_elovic/status/1906617401354915972

### Search 5: Specific Anthropic Employees

**@jackclarkSF** (Feb 2026) — Infrastructure for economics research:
> Mentioned infrastructure built for Anthropic Economic Index, Anthropic Interviewer, studying agents in the wild.
- https://x.com/jackclarkSF/status/2024581680921555129

**@karpathy** (Mar 2026) — Agent command center:
> "tmux grids are awesome, but i feel a need to have a proper 'agent command center' IDE for teams of them, which I could maximize per monitor. E.g. I want to see/hide toggle them, see if any are idle, pop open related tools (e.g. terminal), stats (usage), etc."
- https://x.com/karpathy/status/2031616709560610993

> "sadly the agents do not want to loop forever. My current solution is to set up 'watcher' scripts..."
- https://x.com/karpathy/status/2031621392609980754

**Anthropic official** (Nov 2025) — Long-running agent challenges:
> Blog post on context windows, memory, building "harness" inspired by human engineers (progress files, git, tests, initializer + coding agents).
- https://x.com/AnthropicAI/status/1993733817849303409

**Anthropic official** (Dec 2025) — Internal AI transformation study:
> Detailed summary of how Claude transforms engineering work — code generation, feedback loops, experimentation economics.
- https://x.com/AnthropicAI/status/1995933116717039664

**Observer** (@aakashgupta, Jan 2026):
> Anthropic using Claude for rapid prototyping, codebase search, PRs — "flipping the economics of experimentation."
- https://x.com/aakashgupta/status/2017421959018242173

### Search 6: AI-Assisted Research Workflows

**@sethlazar (Mar 5, 2026)** — CLOSEST DEPLOYED IMPLEMENTATION (40% of concept):
> "Here's my contribution on using agents to support academic research. I've got a pipeline going now with coding agents that checks arxiv, twitter, bluesky, philpapers, a bunch of journals, many RSS feeds and more, classifies it against a long statement of my lab's interests, shares it with me for further curation, then generates daily summaries for my lab, finds and ingests pdfs (and markdown files) of all articles mentioned, and incorporates them into a vector store with rich analysis and summaries for future searches. We can then call an agent in our slack who can do literature reviews, find papers, and just talk to our corpus of papers."
- https://x.com/sethlazar/status/2029549436280754205
- NOTE: This is for EXTERNAL papers, not extracting from own experiments

**"Rethinking the AI Scientist"** (via @rohanpaul_ai, Jan 25, 2026):
> 4 LLM agents run research loops with humans steering. They share a persistent world state. Key win: speed plus control. Papers behind paywalls and imperfect novelty checks create blind spots.
- https://x.com/rohanpaul_ai/status/2015363766691447238

**"Why LLMs Aren't Scientists Yet"** (via @rohanpaul_ai, Jan 19, 2026, arxiv:2601.03315):
> 4 autonomous research runs, 3 broke. Failures: defaulted to familiar tools, changed spec under pressure, forgot context, overpraised bad outputs. Needs: gradual detail, strict verification, explicit recovery, obsessive logging.
- https://x.com/rohanpaul_ai/status/2013170062010822756

**Adaptive multi-agent coordination** (@omarsar0, Dec 21, 2025, former Meta AI):
> Static pipelines break. Introduces: (1) dynamic routing, (2) bidirectional feedback (downstream agents issue revision requests upstream), (3) parallel evaluation. Shared memory and feedback loops as most critical — removing either caused 20%+ drop in coverage/coherence.
- https://x.com/omarsar0/status/2002760233656217751

**Knowledge graphs for experiment tracking** (@BranaRakic, Mar 2026):
> Referencing Karpathy's autoresearch, suggests knowledge graphs with peer-to-peer signed triples and SPARQL queries for agent coordination without central repos.
- https://x.com/BranaRakic/status/2031100089091985417

**Practitioner consensus on what works:**
- Persistent/shared state or memory
- Human steering in short loops
- Dynamic routing + bidirectional feedback
- Strict verification/logging
- High-quality curated examples over scale
- Vector stores + agents for corpus search

**What doesn't work:**
- Long fire-and-forget batches
- Static role pipelines
- Context drift over long projects
- Imperfect novelty checks
- Lack of recovery mechanisms

---

## 9. Second Research Source Findings

(Sohail provided this research from another session. Key findings verbatim.)

### Sionic AI Case Study (Dec 2025, Hugging Face)

Built a system where at end of any Claude Code experiment session, researcher types `/retrospective`, Claude reads conversation, extracts important parts, writes it up as a "skill," skill goes into shared registry via pull request. Next time anyone asks about related topic, Claude already knows what teammate discovered.

- Run 1,000+ ML experiments/day with it
- Example: teammate spent 3 days on ColBERT parameter experiments, found longer text chunks made FDE outperform MaxSim. Initially lived in Slack thread until system captured it.
- Built `/advise` which checks registry before new experiment, tells you what teammates already learned including warnings about approaches that didn't work.
- Key insight on WHY it works: "Claude writes the skill while everything is still in context. It watched you debug the tensor mismatch, saw which approaches failed and why, and all of that goes into the file without you reconstructing it from memory two days later."

### Hedgineer Pattern (Dec 2025)

Built company-wide knowledge layer using Claude Skills. Key insight: skills are model-invoked, not user-invoked — Claude reads description and decides when relevant. Engineers don't need to know what skills exist.

- Organized into 4 domains (AI, Data, Infra, UI), each owned by closest team
- Result: expertise travels. Front-end dev working on financial charts applies data pipeline thinking from skills written by data team.
- Five characteristics of effective skills: precise triggers, progressive detail, strong directives, validation checkpoints, bundled resources.

### Anthropic's Own Data

- November 2025 internal study: 50% productivity increase but declining peer collaboration
- Junior engineers prefer asking Claude over talking to senior colleagues
- Engineers use Claude in ~60% of daily tasks
- "AI has been deeply integrated into daily development at Anthropic"
- "Engineers report reduced peer collaboration, which is a concerning trend given that code review, pair programming, and collaborative problem-solving are cornerstones of quality development"

### Objection Handling (from second source)

**"We already use W&B / MLflow"**
W&B tracks structured experiment metadata (hyperparameters, metrics, loss curves). This system captures unstructured research knowledge (why someone chose an approach, what failed and why, unexpected insights, dead ends to avoid). Complementary, not competing.

**"This is just documentation, and researchers don't write docs"**
Cite Sionic: "People started explaining their reasoning more clearly during sessions, knowing Claude would read it at the end." System changes the incentive structure. Not "write docs after the fact" — "your normal Claude Code session becomes the docs."

**"We already use Notion like OpenAI does"**
OpenAI uses Notion as centralized hub (pull-based — researchers must remember to check). This is push-based: Claude proactively surfaces relevant prior work via `/advise`. Knowledge comes to you.

**"The collaboration decline isn't that serious"**
Hit them with their own data (50% productivity but declining collaboration). System creates asynchronous knowledge exchange mediated by Claude, not forcing old-style collaboration.

**"Won't scale / maintenance burden too high"**
Hedgineer evidence: each domain team runs continuous feedback loop. Far cheaper than watching knowledge drift. Skills = markdown in git with version control.

### Refined Pitch Structure (from second source)

1. Open with Anthropic's own finding: "Your Nov 2025 study showed 50% productivity increase but declining peer collaboration."
2. Name prior art immediately: Sionic AI, Hedgineer. Published late 2025.
3. Explain what makes Anthropic's version different: heterogeneous research, pre-publication sensitivity, cross-team discovery (Alignment/Interpretability/Pretraining/Infrastructure), self-hosted infrastructure.
4. Show 4-layer architecture with specific technical choices.
5. Propose pilot: 4-week, one team (Interpretability ideal), ship `/publish-research` + `/advise`, single GitHub repo.
6. Close with meta-argument: Anthropic positions as laboratory for responsible workplace transition. This system is that experiment.

### Remaining Gaps (from second source)

- What experiment tracking Anthropic actually uses internally
- Whether Skills infrastructure works on Claude.ai or just Claude Code
- Anthropic's internal GitHub/GitLab setup and compliance requirements
- Whether Anthropic Fellows rotation creates particular knowledge-loss problem

---

## 10. Third Research Source — The Skeptical Counterweight

Received 2026-03-12. This source stress-tested the pitch from a skeptical engineer's perspective and fundamentally corrected the framing.

### Core Thesis

"Real problem, wrong source of truth." The pitch should NOT be an autonomous agent that publishes to a central GitHub arXiv. The pitch should be a **permission-aware research metadata layer** that captures lightweight, reviewable experiment cards from messy local work.

### Seven Objections Raised (All Valid)

1. **Target state too broad.** "Any researcher can access any other researcher's work" is wrong goal. Right goal: any researcher can *discover* relevant work, understand relevance, get path to contact/request access. Existing enterprise search (Glean, Sourcegraph) already enforce inherited permissions.

2. **Central archive = second source of truth.** Backstage/Port/Compass push metadata to live with code. W&B/MLflow keep runs in experiment systems. A separate archive storing "real" summaries will drift from source repos and trackers.

3. **"Any arbitrary experiment directory" sounds magical, not credible.** Every mature system expects structured foothold: metadata YAML in catalogs, explicit runs/artifacts in trackers. Promise **progressive automation over minimal structure**, not zero-config universal understanding.

4. **Pushing to central GitHub is wrong write path.** GitHub has 100MB single-object limits, 2GB push limits, warns about repo health as repos grow. Safer pattern: create branch + draft PR, keep human review and merge in GitHub.

5. **Semantic search over summaries is not enough.** Researchers need code-aware navigation, not just generated prose. Copilot uses repo indexing, Glean Code Search reasons over connected repos, Sourcegraph follows symbols across repos. "Searchable markdown" is not a moat.

6. **"Tag employee ID" is too naive.** CODEOWNERS, Backstage `ownedBy`, Glean expertise profiles already exist. Derive contact/ownership from existing systems.

7. **Social layer can feel like surveillance.** Silently harvesting side experiments kills adoption on trust. Must be opt-in with visibility scoping.

### What Already Exists (Partly Redundant)

| Category | Existing Tools |
|---|---|
| Search & discovery | Glean GitHub connector, GitHub Copilot repo indexing, Sourcegraph cross-repo navigation |
| Ownership & cataloging | Backstage, Port, Compass, CODEOWNERS |
| Experiment lineage | W&B Artifacts (versioned inputs/outputs), MLflow datasets, OpenTelemetry-compatible tracing |
| LLM observability | Langfuse, Phoenix, Braintrust, LangSmith |
| Claude-native automation | Skills, subagents, hooks, Agent SDK |

### The Actually Novel Wedge

> Capture the messy long tail of research work that never makes it cleanly into a tracker or catalog — half-finished branches, ad hoc notebooks, odd directory layouts, exploratory scripts — and turn that into small, reviewable, permission-aware metadata with provenance.

Existing tools mostly assume the project is already registered somewhere structured. The gap is specifically about work that falls below the threshold of formal tracking.

### Recommended Architecture (Source 3)

1. **Lightweight descriptors only.** Code stays in repos. Runs stay in W&B/MLflow. New system stores only descriptors, links, provenance, freshness.
2. **Tiny schema.** `research-card.yaml` with minimal fields, not 20+ field specification. Borrow entity ideas from software catalogs (experiment, run, dataset, artifact, owner, source repo, commit, status, visibility, last verified).
3. **Three-pass Claude extraction.** Pass 1: read-only repo-mapper discovers structure. Pass 2: extractor drafts card. Pass 3: verifier checks every claim against files/commits, marks missing fields instead of guessing.
4. **Start with Claude Code skill + subagents, not MCP.** Reserve MCP for narrow external system integration later.
5. **Publish by PR, not silent push.** Draft PR → human review → merge. Owner can fix summaries, redact sensitive details, approve visibility.
6. **Let existing search do heavy lifting.** Index research cards. Results show title, owner, status, freshness, links to repo/PR/runs, related experiments. Complement existing search, don't compete.
7. **Freshness and provenance first-class.** Every claim points to file paths, commit SHAs, or tracker/run IDs. `last_verified_at`, confidence, stale badge. Otherwise archive turns into plausible fiction.

### Corrected Pitch (Source 3)

DO NOT say: "We're building an internal arXiv where Claude understands every project and anyone can access everything."

SAY: "We're building a Claude-assisted, permission-aware metadata layer for research. It captures lightweight, reviewable experiment cards from messy local work, links every claim back to source code and run artifacts, inherits existing ownership and access controls, and plugs into the search systems we already have."

---

## 11. Reconciled Architecture (All Three Sources)

### Where All Three Sources Converge (High Confidence)

1. **Problem is real.** Yi Tay duplicated research, Anthropic declining collaboration, Sionic running 1000+ experiments/day — all confirm knowledge siloing.
2. **Sionic is valid prior art.** `/retrospective` + `/advise` is proven, not speculative.
3. **Timing advantage is genuinely novel.** Capturing while Claude has full context — not reconstructed days later — is the one insight no existing tool replicates.
4. **Claude Code building blocks are mature enough.** Skills, subagents, hooks, Agent SDK.
5. **PR-based publishing is the right write path.** Never silently push generated content.

### Where Source 3 Correctly Overrides Sources 1 and 2

| Source 1/2 Claim | Source 3 Correction | Resolution |
|---|---|---|
| "No tool does retrospective extraction" | Gap is narrower — only the messy long tail below formal tracking threshold | Accept correction |
| "Internal arXiv" framing | "Permission-aware research metadata layer" — no second source of truth | Accept correction |
| "Any arbitrary experiment directory" | "Progressive automation over minimal structure" | Accept correction |
| Build full search service (Layer 4) | Let Glean/Copilot/Sourcegraph handle search | Accept correction |
| Tag employee ID from scratch | Derive from CODEOWNERS, Backstage, Glean profiles | Accept correction |

### Where Source 3 Goes Too Far (For Demo Purposes)

1. **research-card.yaml with 20+ fields** — over-specified for a demo. Keep minimal. **DECISION: Minimal card format for demo.**
2. **OpenLineage as conceptual anchor** — adds unnecessary complexity for first iteration. **DECISION: Sionic pattern (markdown skill + PR) first. OpenLineage as appendix "future direction."**
3. **"Don't start with MCP"** — correct for knowledge system, but KVScope's existing MCP server is a different thing (observability over frozen corpus). **DECISION: KVScope MCP stays.**

### Final Architecture for Demo

**Two deliverables, one narrative:**

1. **KVScope** (core engineering signal) — stripped to strong core: replay engine, trace builder, live metrics bridge, MCP server, benchmark workloads. Shows understanding of systems, cache behavior, experimental methodology.

2. **`/publish-research` skill** (product thinking signal) — runs on KVScope as proof of concept. Generates lightweight research card with provenance. Three-pass extraction. Accompanied by design doc showing broader vision.

**The narrative ties them together:** "I built an observability experiment that found interesting things about cache policy behavior. Then I built a tool that captures exactly this kind of messy research into a standardized, reviewable format — because at research org scale, this kind of knowledge currently gets lost."

---

## 12. Resolved Decisions

| Question | Decision |
|---|---|
| One project or two? | One narrative: KVScope + knowledge system tied together |
| Build scope? | Both: working `/publish-research` skill + design doc |
| Schema? | Minimal card format (Sionic pattern), not 20+ field YAML |
| OpenLineage? | Appendix item for "future direction" |
| MCP server role? | KVScope MCP stays as-is; knowledge system uses skill+subagents |
| Statistical rigor? | Reframe claims as "directional" with honest N-size disclosure |
| Reproduce script? | Yes |
| Design rationale doc? | Yes |

---

## 13. Execution Plan

### Completed
- [x] 5 parallel code reviews
- [x] 2 oracle research reports
- [x] 6 X/Twitter searches via Grok
- [x] Second research source integrated
- [x] Third research source integrated
- [x] Full reconciliation across all three sources
- [x] Experimental plan document written and updated

### Execution Order
1. **Strip KVScope** — remove agent/, web/, evals/, associated scripts/tests (mechanical, safe, zero dependencies)
2. **Rewrite README.md** — ~80 lines, lead with results
3. **Rewrite result bundle** — lead with capacity crossover finding
4. **Update claims docs** — trace derivation honesty, falsification criteria
5. **Write design rationale doc** — "why I made these choices"
6. **Write knowledge system design doc** — permission-aware metadata layer, prior art, minimal card format, pilot proposal, OpenLineage appendix
7. **Build `/publish-research` skill** — run on KVScope as proof of concept
8. **Final review pass** — every remaining file earns its place

---

*Last updated: 2026-03-12*
*Status: FINALIZED — all three sources integrated, executing*
*Next action: Strip KVScope weak layers*
