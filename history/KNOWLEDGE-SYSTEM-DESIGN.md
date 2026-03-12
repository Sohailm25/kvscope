# Research Knowledge System — Design Document

## Problem Statement

AI research labs face a specific knowledge-sharing failure mode: as AI tools increase individual productivity, peer collaboration declines, and research insights get siloed in individual experiment directories, Slack threads, and local notebooks.

**Evidence:**
- Anthropic's November 2025 internal study found 50% productivity increase but declining peer collaboration. Junior engineers prefer asking Claude over talking to senior colleagues.
- Yi Tay (DeepMind, May 2025) documented "almost identical" parallel research efforts within Google that didn't know about each other.
- @joburgai (March 2026): "We annotate and red team for model behaviors, and by the time a paper gets published the model has updated 2-3x. The findings are historical artifacts before they're even out."

The problem isn't lack of tools. W&B tracks runs. MLflow tracks datasets. Glean indexes repos. The problem is the **messy long tail** — half-finished branches, ad hoc notebooks, odd directory layouts, exploratory scripts that never make it into any structured tracker.

## What This Is Not

This is NOT:
- An internal arXiv (storing full documents creates a second source of truth that drifts)
- A replacement for W&B, MLflow, or existing experiment trackers
- A replacement for Glean, Copilot, or existing code search
- A magic system that understands any arbitrary experiment directory

## What This Is

A **permission-aware research metadata layer** that captures lightweight, reviewable experiment cards from messy local work, links every claim back to source code and run artifacts, inherits existing ownership and access controls, and plugs into existing search infrastructure.

## Prior Art

### Sionic AI (December 2025, Hugging Face)

Built `/retrospective` and `/advise` slash commands for Claude Code. At session end, `/retrospective` extracts insights into a "skill" file, pushed to a shared registry via PR. `/advise` checks the registry before new experiments. They run 1,000+ ML experiments/day with it.

**Key insight:** Claude writes the skill while everything is still in context — not reconstructed from memory days later. This timing advantage is the core differentiator.

**Limitation:** Captures session insights (what happened during a Claude conversation), not structured experiment metadata (what the code does, what results it produced, what traces it generated).

### Hedgineer (December 2025)

Built a company-wide knowledge layer using Claude Skills. Skills are model-invoked, not user-invoked — Claude reads the description and decides when it's relevant.

**Key insight:** Engineers don't need to know what skills exist. Knowledge flows automatically to whoever needs it.

**Limitation:** Designed for operational knowledge (error handling patterns, data pipeline conventions), not research findings.

### Existing Infrastructure

| Category | Tools | What They Cover |
|---|---|---|
| Experiment tracking | W&B, MLflow | Structured metrics, hyperparameters, loss curves, versioned artifacts |
| Code search | Glean, GitHub Copilot, Sourcegraph | Code-aware navigation with inherited permissions |
| Catalogs | Backstage, Port, Compass | Metadata YAML living with code, ownership, service discovery |
| LLM observability | Langfuse, Phoenix, Braintrust | Traces, datasets, evaluation flows |

**The gap:** None of these capture *why* a researcher chose their approach, what failed, what unexpected insight emerged, or which dead ends to avoid. None handle the messy long tail of work that never gets formally registered anywhere.

## Architecture

### Layer 1: Capture (Claude Code Skill)

A `/publish-research` skill that a researcher runs voluntarily in their experiment directory. Claude performs three passes:

1. **Map:** Read-only scan of the directory. Discover entry points, scripts, result files, configuration, tests. Build a structural understanding.
2. **Extract:** Draft a lightweight research card with provenance — linking every claim to specific files, commit SHAs, or run IDs.
3. **Verify:** Check every claim in the draft against actual files. Mark missing or uncertain fields rather than guessing.

The skill outputs a research card in a minimal schema:

```yaml
title: "Cache policy crossover in locality-return workloads"
status: exploring | active | paused | archived
visibility: private | team | org
owners: ["sohail"]
source_repo: "github.com/org/kvscope"
source_commit: "abc123"
entrypoints:
  - serve/modal_vllm_app.py
  - kvtrace/replay.py
summary: |
  Replay of live-derived traces through LRU/FIFO/LFU shows that the
  optimal eviction policy depends on cache capacity. LRU > LFU at
  capacities 2-3, LFU > LRU at capacity 4 on locality-return workloads.
key_results:
  - "Capacity crossover: LRU→LFU flip at capacity 4 (N=4 traces)"
  - "Hotset-scan: LFU > LRU > FIFO consistently across capacities 2-5"
open_questions:
  - "Does the crossover hold at larger N?"
  - "Does vLLM's internal eviction match derived trace predictions?"
evidence:
  - path: artifacts/manifests/replay-capacity-sweep*.json
    note: "Capacity sweep data"
  - path: docs/kvscope_result_bundle.md
    note: "Reviewer-facing summary"
tracker_links: []
confidence: medium
last_verified_at: "2026-03-12"
```

### Layer 2: Review (Git + PR)

The skill creates a branch and opens a draft PR — either in the source repo or in a thin index repo. The researcher reviews, fixes bad summaries, redacts sensitive details, and approves visibility. This solves the "garbage in" problem: human review ensures quality without putting the writing burden entirely on the researcher.

### Layer 3: Index

Once merged, a CI pipeline embeds the card and pushes to a vector store (pgvector, LanceDB, or similar self-hosted solution). The index stores only the lightweight cards plus their links back to source repos.

### Layer 4: Discover

An `/advise` skill (borrowed from Sionic) queries the index before a new experiment starts. Claude surfaces semantically related research cards with researcher contact info. Existing search infrastructure (Glean, Copilot) can also index the cards.

**The search itself is NOT the moat.** Glean, Copilot, and Sourcegraph already do code-aware search better than a custom solution. The moat is capture quality, provenance, and freshness.

## Design Principles

1. **Lightweight metadata, not full documents.** Code stays in repos. Runs stay in experiment trackers. The new system stores only descriptors, links, provenance, and freshness status.

2. **Progressive automation over minimal structure.** The skill helps fill in the card, but doesn't claim to magically understand any arbitrary directory. Researchers provide the structured foothold; Claude reduces the writing burden.

3. **Opt-in with visibility scoping.** Exploratory work should never be silently harvested. The researcher explicitly runs `/publish-research` and chooses visibility (private/team/org).

4. **Provenance and freshness are first-class.** Every claim points to file paths, commit SHAs, or tracker/run IDs. Cards include `last_verified_at`, `confidence`, and staleness detection.

5. **Derive ownership from existing systems.** Use CODEOWNERS, Backstage `ownedBy`, Glean expertise profiles where they exist, rather than inventing a new ownership model.

6. **PR-based publishing, not silent push.** Generated content is always reviewed before merging. Matches the pattern in agentic GitHub tooling (Glean Code Writer, etc.).

## Pilot Proposal

**Scope:** 4-week pilot with one team. Interpretability is ideal — their work is highly exploratory and would benefit most from cross-pollination.

**Deliverables:**
1. `/publish-research` skill (capture layer)
2. `/advise` skill (discover layer)
3. Thin GitHub index repo
4. pgvector index + simple query interface

**Success criteria:**
- Do researchers actually use `/publish-research`?
- Does `/advise` surface genuinely relevant prior work?
- Does the review step catch errors without creating friction?

## Appendix: Future Directions

### OpenLineage Integration

OpenLineage's job/run/dataset model provides a mature conceptual framework for representing experiment lineage. A future version could map research cards to OpenLineage facets, enabling interoperability with existing lineage tools (Marquez, Atlan, DataHub). This was explicitly deferred for the first iteration to avoid unnecessary complexity.

### Bidirectional Tracker Links

Future cards could link directly to W&B runs, MLflow experiments, or Langfuse traces, enabling a researcher to jump from a research card to the exact training run or eval that produced a finding. This requires integration with each tracker's API.

### Automated Staleness Detection

A GitHub Action could periodically check whether the source commit referenced in a card still exists, whether the linked files have changed significantly, and whether the `last_verified_at` date is too old. Stale cards get flagged for review or archival.

### Local Hybrid Search via QMD

QMD (github.com/tobi/qmd, 14.5k stars, MIT) is a fully local markdown search engine combining BM25 full-text search, semantic vector search (local embeddings via embeddinggemma-300M), and LLM re-ranking — all running on-device with no cloud dependency. It exposes an MCP server and a TypeScript SDK.

For the discover layer, QMD is a strong candidate: research cards are markdown files, QMD's hybrid search handles both exact parameter matches (BM25) and conceptual similarity (vector), and the MCP integration means Claude Code skills could call it directly. The `context` annotation feature maps well to experiment metadata ("this collection contains fine-tuning experiment cards").

**Deferred for first iteration** because adding ~2GB of local models and a third-party dependency to a pilot complicates deployment. But for a self-hosted, privacy-preserving search layer that avoids cloud embedding APIs, QMD is the most mature option available (March 2026).

### Knowledge Graph View

Research cards naturally form a graph (related_work links, shared tags, same-team ownership). A graph view could surface clusters of related research and identify gaps — teams working on similar problems without knowing about each other. BranaRakic (March 2026) proposed knowledge graphs with peer-to-peer signed triples for agent coordination without central repos.

## References

- Sionic AI case study (Dec 2025, Hugging Face): `/retrospective` + `/advise` pattern
- Hedgineer knowledge layer (Dec 2025): model-invoked skills as company-wide knowledge
- Anthropic internal study (Nov 2025): 50% productivity increase, declining collaboration
- Yi Tay (DeepMind, May 2025): duplicated research within Google
- @sethlazar (Mar 2026): deployed external paper ingestion pipeline
- OpenLineage: job/run/dataset model for experiment lineage
- Backstage/Port/Compass: software catalog patterns
