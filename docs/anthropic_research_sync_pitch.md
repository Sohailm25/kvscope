# Narration Script

> *Deliver this conversationally. Not memorized — internalize the beats and talk through them. Pause where marked.*

---

**[OPEN — The Problem]**

So here's something I kept thinking about while building this project.

Anthropic published an internal study last November — 132 engineers and researchers. The headline was a 50% productivity increase from Claude. Great. But buried in the findings was something more interesting: peer collaboration was declining. Junior engineers were increasingly going to Claude instead of talking to senior colleagues.

That's a tradeoff most people aren't talking about. The tool that makes individuals faster is quietly eroding the thing that makes the *organization* smarter — which is people learning from each other's work.

And it's not just Anthropic. Yi Tay at DeepMind documented nearly identical research efforts happening in parallel at Google — teams that didn't know about each other. This is a structural problem that hits every research org past a certain size.

**[TRANSITION — The Gap]**

Now, Anthropic has great tools. W&B for experiment tracking. Glean for code search. MLflow, Copilot — all excellent at what they do. The gap isn't in any of those categories.

The gap is the messy long tail. The half-finished branch. The notebook with a surprising result that never got written up. The experiment directory where you tried three approaches, one of them was interesting, and then you moved on. That work — the exploratory stuff — is exactly what matters most for cross-pollination, and it's exactly what none of these tools capture.

*(pause)*

**[LAYER 1 — What I Built]**

So I built two things.

First: KVScope. It's a cache-aware observability lab that studies how KV cache eviction policies behave on vLLM serving workloads. Nine workload families, live instrumentation on Modal with Prometheus scraping, derived trace replay through LRU, FIFO, and LFU simulators. Thirty-eight runs, forty-six manifests, seven verified findings with full provenance.

The headline result is a capacity crossover: on locality-return workloads, LRU beats LFU at small cache capacities, then LFU overtakes at capacity four. The optimal policy flips depending on your cache budget. No single policy wins everywhere.

I want to be clear about the limitations — these are directional findings on small N. Two to four runs per family. The traces are derived from request structure, not vLLM kernel instrumentation. This is a structured exploration, not a production benchmark.

*(pause)*

Second: while building KVScope, I noticed I was creating exactly the kind of knowledge that gets lost. Findings spread across manifests, scripts, result bundles — invisible to anyone who doesn't read every file. So I built a proof of concept for capturing it.

It's a Claude Code skill called `/publish-research`. Three passes: map the directory structure, extract a lightweight research card with provenance — every claim linked to a specific file — then a verify pass that re-reads the evidence and confirms numbers match. It actually caught a discrepancy where my result bundle said N equals four but the manifest showed three.

The output is a YAML research card. Structured, verifiable, lightweight. Not a paper. Not a wiki page. A card with claims, evidence links, confidence levels, and caveats.

**[LAYER 2 — What the Demo Shows]**

I want to be explicit about what this demo does and doesn't cover.

It proves the hardest first step: that Claude can extract structured metadata with real provenance from a messy experiment directory, while the context is fresh. That timing advantage — capturing at session end when everything is still in memory — is the key insight. Sionic AI demonstrated this at scale with their retrospective pattern on HuggingFace.

What the demo does not show is the full loop. There's no PR automation, no vector index, no `/advise` command querying prior cards. That's all proposed. I'm not going to pretend those pieces are built when they're not. The plumbing — PRs, embeddings, search — is standard infrastructure. The hard part is capture quality, and that's what the demo proves.

**[LAYER 3 — The Vision]**

If the capture step works — and the demo suggests it can — the rest is a four-week pilot.

Week one and two: harden the capture skill. Token-bounded cards, auto-fill from git, PR-based review so a human always approves before anything is published. Add a `/retrospective` command for end-of-session capture — reasoning and journey, not just final state.

Week two and three: lightweight index. CI pipeline embeds cards on merge, pushes to pgvector. The index stores cards and links. Code stays in repos. Runs stay in trackers. No second source of truth.

Week three and four: an `/advise` skill. Before starting a new experiment, query the index. Surface related prior work with who ran it and what they found. The knowledge finds you instead of you searching for it.

I'd run this with one team. Interpretability is ideal — highly exploratory, benefits most from cross-pollination. Measure adoption, relevance of results, and whether the review step creates friction or catches errors.

*(pause)*

**[CLOSE — Honesty and the Ask]**

I want to close with what I don't know. I don't know what Anthropic uses internally for experiment tracking. I don't know if the gap I identified from public evidence matches what people actually experience day to day. I don't know how researchers would respond to capture friction in practice.

What I do know is that the problem is real — Anthropic's own data says so. The existing tools don't cover the messy long tail. And the novel wedge here isn't search — search infrastructure exists. The novel wedge is provenance-first capture of the work that currently disappears. Claude writing the card while context is fresh makes that possible at low friction.

The cost is near-zero marginal. A few hundred tokens per capture. The value compounds — every card makes future queries more useful. It's a flywheel.

If this resonates with what you're seeing internally, I'd love to explore it further. If I'm wrong about the gap, I'd want to understand why. Either way, the systems work in KVScope stands on its own.

---

*[End of narration script. Detailed pitch document follows.]*

---

# Research Knowledge Capture: A Proposal

## The 30-Second Hook

Anthropic has grown from 240 employees in 2023 to likely over 1,500-3,000+ today. Hundreds of those are research engineers and researchers. Since 2021, those researchers have collectively explored tens of thousands of ideas — hypotheses tested, approaches tried and abandoned, parameter spaces searched, dead ends discovered. The vast majority of that knowledge lives nowhere searchable. It's in local directories, abandoned branches, Slack threads, and individual memory.

**Anthropic's own November 2025 internal study found a 50% productivity increase from Claude — but declining peer collaboration.** Junior engineers increasingly prefer asking Claude over talking to senior colleagues. The tool that makes individuals faster is quietly eroding the knowledge-sharing that makes the organization smarter.

---

## The Problem

AI research labs face a specific knowledge-sharing failure mode: as AI tools increase individual productivity, peer collaboration declines, and research insights get siloed in local directories, Slack threads, and experiment notebooks.

**Evidence:**

- **Anthropic's own data (November 2025):** An internal study of 132 engineers and researchers found a 50% productivity increase from Claude usage — but declining peer collaboration. Junior engineers increasingly prefer asking Claude over talking to senior colleagues.
- **Yi Tay, DeepMind (May 2025):** Documented "almost identical" parallel research efforts within Google that didn't know about each other.
- **@joburgai (March 2026):** "We annotate and red team for model behaviors, and by the time a paper gets published the model has updated 2-3x. The findings are historical artifacts before they're even out."

The problem isn't lack of tools. W&B tracks runs. MLflow tracks datasets. Glean indexes repos. The problem is the **messy long tail** — half-finished branches, ad hoc notebooks, odd directory layouts, exploratory scripts that never make it into any structured tracker. This is the work that matters most for cross-pollination, and it's the work that's hardest to capture.

---

## Layer 1: What Exists Today

### KVScope — The Systems Work

I built KVScope as a cache-aware AI observability lab studying KV cache policy behavior on vLLM serving workloads. It demonstrates the kind of messy, exploratory research work that is exactly what gets lost:

- **9 workload families** designed to stress different cache behaviors (prefix sharing, frequency bias, locality shifts, capacity pressure)
- **Live instrumentation** via Modal + Prometheus metric scraping (cache-on vs cache-off toggles)
- **Derived trace replay** through textbook LRU/FIFO/LFU simulators at varying cache capacities
- **38 runs, 46 manifests, 7 verified findings** with provenance back to source artifacts

**The headline finding:** On locality-return workloads, LRU beats LFU at cache capacities 2-3, then LFU overtakes LRU at capacity 4. The optimal eviction policy flips with cache budget. No single policy wins everywhere — it depends on workload geometry and cache capacity together.

All claims are directional on small N (2-4 runs per family). Traces are derived from request structure, not vLLM kernel instrumentation. This is honest about what it is: a structured exploration, not a production benchmark.

### The Research Card — Proof of Concept for Capture

While building KVScope, I noticed the exact problem described above: my own experiment directory was accumulating findings that would be invisible to anyone who didn't read every manifest and script. So I built a proof of concept for capture.

**What exists:**
- `.claude/commands/publish-research.md` — A Claude Code skill that performs three passes over an experiment directory:
  1. **Map:** Read-only scan to discover entry points, configs, results, tests
  2. **Extract:** Draft a lightweight YAML research card with provenance (every claim links to source files and commit SHAs)
  3. **Verify:** Re-read every referenced evidence file, confirm numbers match, mark anything unverified
- `research-card.yaml` — The output: a 197-line card with 7 verified key results, actual numbers from manifests, open questions, caveats, and a confidence scale. It even caught a discrepancy where the result bundle claimed N=4 but the manifest showed N=3 for locality-return.

**What this demonstrates:** Claude can extract structured, verifiable metadata from messy experiment directories *while the context is fresh*. The timing advantage is the key insight from Sionic AI's work — writing happens at session end when everything is still in context, not reconstructed days later.

### The Design Document

`history/KNOWLEDGE-SYSTEM-DESIGN.md` lays out:
- Problem framing (with evidence from Anthropic, DeepMind, and practitioners)
- Why this is NOT an internal arXiv or a replacement for existing trackers
- Prior art analysis (Sionic AI's `/retrospective` + `/advise` pattern, Hedgineer's model-invoked skills)
- A 4-layer architecture sketch: Capture → Review → Index → Discover
- Design principles (lightweight metadata, opt-in with visibility scoping, provenance-first, PR-based publishing)
- A pilot proposal

---

## Layer 2: What the Demo Simulates

Running `/publish-research` in the KVScope directory simulates the capture step of a broader workflow. Here's what it does and doesn't cover:

| Aspect | Demo shows | Demo does not show |
|--------|-----------|-------------------|
| **Capture** | Three-pass extraction producing a verified YAML card | Automatic triggering or integration with session end |
| **Provenance** | Every claim links to specific artifact files | Linking to commit SHAs or tracker run IDs automatically |
| **Quality control** | Verify pass catches number mismatches | PR review workflow or teammate approval |
| **Card schema** | Minimal structure: title, status, summary, key results, evidence, caveats | Full card lifecycle (draft → review → merge → stale → archived) |
| **Output** | Local YAML file | Branch creation, PR opening, or index updates |

The demo is intentionally narrow. It proves the hardest first step: that Claude can produce research cards with real provenance from messy directories. The plumbing (PRs, indexing, search) is standard infrastructure that doesn't need proving.

---

## Layer 3: What a Pilot Would Build

*Everything below is proposed, not implemented. Labels are explicit.*

### Proposed Pilot: 4 Weeks, One Team

Interpretability is ideal — highly exploratory work that benefits most from cross-pollination.

### Capture (Week 1-2): Two Modes

#### Mode A: Ongoing Capture (Prevent Future Loss)

**`/publish-research`** — Harden the existing proof of concept:
- Token-bounded cards (max 200 lines / ~2000 tokens to prevent index bloat)
- Auto-fill `source_commit` from git HEAD, `owners` from git config
- Create a branch and open a draft PR — researcher reviews, redacts sensitive details, approves visibility (private / team / org)

**`/retrospective`** — End-of-session capture (borrowed from Sionic AI's proven pattern). Claude reads the full conversation, extracts key decisions, failed approaches, and insights, writes them as a skill/card. Especially powerful because it captures the *reasoning* and *journey*, not just the final state.

**CLAUDE.md passive awareness** — Add a single line to research engineers' project-level CLAUDE.md:

```
When this session involves running experiments, testing hypotheses,
or evaluating results, keep a running internal note of key findings.
At natural stopping points, suggest running /publish-research.
```

This costs ~50 tokens of context. Claude already reads CLAUDE.md. The nudge is passive — it doesn't force anything.

#### Mode B: Backfill (Recover What Already Exists)

**`/backfill-research`** — Researcher points it at their local experiment directory. Claude scans the directory tree, groups experiments by apparent project/hypothesis, and generates draft research cards with:
- Inferred hypothesis (flagged as "inferred — please verify")
- Directory structure summary, key files and their apparent purpose
- Any results/metrics found in logs or outputs
- Status: active / abandoned / completed (inferred)

All cards are presented to the researcher for review before any commit.

**Honest caveat:** Backfill will produce noisy, imperfect cards. Many will be for experiments the researcher barely remembers. That's fine. The goal isn't perfection — it's creating a searchable starting point. A noisy card that says "Researcher X tried approach Y in October 2024 and abandoned it" is more useful than nothing.

### Index (Week 2-3): Pilot Search Architecture

```
Researcher runs /publish-research or /retrospective
        ↓
Research card (standardized YAML) committed to branch
        ↓
PR opened → teammate or lightweight review → merge
        ↓
CI pipeline triggers on merge:
  1. Embed the card (text-embedding-3-large or local model)
  2. Push embedding to vector store (pgvector / LanceDB)
  3. Update tag index and researcher directory
        ↓
Query via /advise (MCP server) or existing search (Glean, Copilot)
```

The index stores only lightweight cards plus links back to source repos. Code stays in repos. Runs stay in experiment trackers. Ownership is inherited from existing systems (CODEOWNERS, Backstage) rather than inventing a new model.

### Discover (Week 3-4): The `/advise` Command

Before starting a new experiment, researcher types `/advise pruning transformer attention heads`.

Claude queries the index, retrieves semantically similar cards, and returns:

- **Related prior experiments** with summaries
- **Who ran them** and how to reach them
- **What worked and what didn't**
- **Suggested starting point** based on collective findings

This is push-based knowledge delivery. The knowledge finds *you* instead of you searching for it. Existing search infrastructure (Glean, Copilot) can also index the cards — search itself is not the moat.

### Merge Strategy

| Strategy | When to merge | Trade-off |
|----------|--------------|-----------|
| **On completion** | Researcher marks experiment as done | Cleanest cards, but in-progress work stays invisible |
| **Chronological batches** | Weekly auto-merge of all pending cards | Regular cadence, but some cards will be rough |
| **Immediate with "draft" tag** | Merge immediately, flagged as draft | Maximum discoverability, but noise in the index |

**Recommendation:** Merge immediately with a `status: in-progress` tag. Someone searching for "attention head pruning" needs to find that a colleague is *currently* exploring it, not discover it three weeks later.

### What the Pilot Measures

- Do researchers actually use `/publish-research`?
- Does `/advise` surface genuinely relevant prior work?
- Does the review step catch errors without creating friction?
- How many cards does it take before the index is useful?

---

## Why This Matters

### The Narrow Argument

1. **The problem is real.** Anthropic's own research documented declining peer collaboration. Yi Tay documented parallel efforts at Google. Every growing research org faces this.

2. **Existing tools don't cover the gap.** W&B, MLflow, Glean, Copilot — all excellent at their domains. None capture *why* a researcher chose an approach, what failed, what unexpected insight emerged, or which dead ends to avoid. None handle work that never gets formally registered anywhere.

3. **The novel wedge is capture, not search.** Search infrastructure exists. What doesn't exist is a way to capture lightweight, reviewable metadata from the messy long tail of research work — with provenance, freshness tracking, and respect for ownership. Claude writing the card while context is fresh is the timing advantage that makes low-friction capture possible.

4. **The cost is near-zero marginal.** A few hundred tokens per capture. A PR review per card. The value compounds with participation: every card makes future `/advise` queries more useful. Every surfaced prior result saves a researcher from re-exploring a dead end.

### The Compounding Argument

Every research card added to the index makes every future `/advise` query more useful. Every `/advise` query that saves a researcher from re-exploring a dead end frees up a cycle for novel work. Every novel insight produced gets captured and added back to the index.

**This is a flywheel.** The more it's used, the more valuable it becomes. The cost is near-zero marginal (a few hundred tokens per capture). The value compounds with participation.

Anthropic's own research showed that Claude is making engineers more full-stack but reducing peer collaboration. This system doesn't fight that trend — it works *with* it. Researchers keep working with Claude as their primary partner. But now Claude has access to the collective memory of every researcher who came before.

**The pitch in one sentence:** "Give Claude the team's memory so that every researcher starts from the frontier of collective knowledge, not from zero."

---

## Honest Caveats (Say These Out Loud)

1. **"I ran an experiment, it got published as a card, and now someone's asking me about something I barely remember."** This will happen. It's a feature, not a bug. Even saying "I don't remember the details but here's the directory" is more useful than that person spending a week rediscovering the same approach. The card is a pointer, not a commitment.

2. **"The backfill will be noisy."** Yes. 60% of backfilled cards might be low-value. But 40% of recovered knowledge across hundreds of researchers is thousands of insights that would otherwise be permanently lost. The noise decreases over time as ongoing capture produces higher-quality cards.

3. **"Researchers won't use it."** The Sionic AI evidence directly counters this: when the capture mechanism is embedded in the tool researchers already use (Claude Code), and when the effort is a single command at natural stopping points, adoption is real. Sionic found that researchers actually started narrating their thinking more clearly *because they knew it would be captured*.

4. **"This is just documentation."** No. Documentation is pull-based and written after the fact. This is push-based and captured in real-time by the tool that watched you do the work. Claude writes the card while the context is still in the conversation. You review and approve. The effort delta vs. traditional documentation is 10x lower.

5. **"Security concerns with a centralized research index."** Valid. Implement role-based access. Some experiments (capability evals, red-teaming) may need restricted visibility. The system should support `visibility: team-only | org-wide | restricted` tags on each card. This is a configuration decision, not an architectural blocker.

**What I don't know:**
- What tools Anthropic actually uses internally for experiment tracking and knowledge management
- Whether the gap I've identified from public evidence matches internal reality
- How researchers would actually respond to capture friction in practice

**What I'd want to learn first:**
- What does the internal experiment workflow look like today?
- Where do researchers currently lose track of prior work?
- What existing systems would this need to integrate with?
- What are the security and access control requirements for research metadata?

---

## Demo Plan (5 Minutes Max)

### Minute 0-1: The Problem
Anthropic's own finding on declining collaboration. Thousands of experiments across hundreds of researchers since 2021. The messy long tail of work that never gets captured anywhere. One slide. Don't overstate — the audience will respect honesty more than precision theater.

### Minute 1-2: The Solution in 30 Seconds
Live demo: open a terminal. Navigate to KVScope. Run `/publish-research`. Watch Claude scan the directory, extract findings, verify numbers against manifests, produce a research card. 60 seconds.

### Minute 2-3: The Payoff
Show the research card output. Walk through provenance: every claim links to a specific manifest file. Show where the verify pass caught a discrepancy (N=4 claim vs N=3 reality). Show the confidence scale and caveats. This is what low-friction capture with real provenance looks like.

### Minute 3-4: The Broader Vision
Walk through the proposed pilot architecture. Capture → Review (PR) → Index → Discover (`/advise`). Label clearly: "This is what I'd build next, not what exists today." Show the design document.

### Minute 4-5: The Ask
Propose a 4-week pilot with one team (Interpretability or Alignment). Ship two skills (`/publish-research`, `/advise`). One GitHub repo. Measure: cards created, queries made, connections formed, duplicate work avoided. If it works, expand. If it doesn't, you've lost four weeks and gained data.

---

## Appendix A: Back-of-Napkin Math

*These estimates are illustrative, not precise. All assumptions are flagged.*

### Experiment Velocity

A research engineer at a frontier lab doesn't run one clean experiment at a time:

- **Active experiment threads per week:** 2-5 (some long-running, some quick probes)
- **Quick probes / failed ideas per week:** 3-10 (spin up, test hypothesis, abandon in hours)
- **"Interesting but not pursued" discoveries per month:** 2-5 per researcher

These estimates are informed by the Sionic AI case study (1,000+ experiments/day across their team) and general ML research patterns. They have not been verified against Anthropic's actual practices.

### Conservative Cumulative Estimate

| Metric | Low Estimate | High Estimate | Confidence |
|--------|-------------|---------------|------------|
| Researcher-years since founding (cumulative) | ~400 | ~800 | Medium |
| Failed/abandoned experiments per researcher-year | ~100 | ~300 | Low (assumed) |
| **Total lost experimental knowledge** | **~40,000** | **~240,000** | Low |
| High-signal "someone should know this" insights | ~5-10% | ~5-10% | Low (assumed) |
| **Recoverable high-value insights** | **~2,000** | **~24,000** | Low |

The honest framing: we don't know the exact number. But the *order of magnitude* is almost certainly in the thousands to tens of thousands. Even at the very bottom of this range — 2,000 lost insights — that represents enormous knowledge that could be compounding instead of decaying.

### The Duplication Tax

If even 5% of current experiment time is spent re-exploring paths a colleague already tried:

- ~300 researchers (mid-estimate) x 2,080 work hours/year x 5% = **~31,000 hours/year**
- **More important than the dollar figure: ~31,000 hours of frontier research capacity redirected from novel work**

*The 5% duplication rate is an assumption. It could be 2% or 10%. The point isn't precision — it's that any non-trivial duplication rate, applied across hundreds of researchers over years, represents a significant opportunity cost. Anthropic's own finding of declining peer collaboration makes duplication more likely, not less.*

---

## Appendix B: The Strategic Argument

### Boyd's OODA Loop Applied to Frontier Research

Colonel John Boyd's OODA loop (Observe → Orient → Decide → Act) was designed for competitive environments where the entity that cycles faster gains a compounding advantage.

| OODA Phase | Without Knowledge Capture | With Knowledge Capture |
|-----------|--------------------------|----------------------|
| **Observe** | Researcher sees a problem. Checks papers, asks 1-2 colleagues | Researcher sees a problem. `/advise` surfaces prior internal attempts |
| **Orient** | Spends days exploring approaches, some already tried by colleagues | Orients in hours because dead ends and promising directions are indexed |
| **Decide** | Decides based on incomplete internal context | Decides with organizational context — knows what's been tried, who to talk to |
| **Act** | Runs experiment. If it fails, the failure stays local | Runs experiment. `/publish-research` captures the result. Next researcher starts from here |

The key insight: competitive advantage comes not from cycling faster on one loop, but from *each loop starting from a higher baseline* because the previous loop's output is preserved and accessible. That's compounding.

---

## Appendix C: Source Verification & Confidence Levels

### Verified Claims (High Confidence)

| Claim | Source | Status |
|-------|--------|--------|
| Anthropic founded 2021 | Wikipedia, multiple sources | Verified |
| 192 employees in 2022 | Multiple sources agree | Verified |
| 240 employees in 2023 | Multiple sources agree | Verified |
| ~1,035 employees in 2024 | Multiple sources cite this snapshot | Verified |
| Anthropic surveyed 132 engineers/researchers (Aug 2025) | Anthropic's published research | Verified |
| Engineers report reduced peer collaboration | Anthropic's published research | Verified |
| Junior employees prefer asking Claude over colleagues | Reporting on Anthropic's research | Verified (secondary source) |
| Claude used in ~60% of daily tasks at Anthropic | Reporting on Anthropic's research | Verified (secondary source) |
| Sionic AI built /retrospective and /advise with Claude Code | HuggingFace blog, Dec 2025 | Verified |
| Claude Code supports skills, hooks, and subagents | Anthropic official docs | Verified |

### Uncertain Claims (Medium Confidence)

| Claim | Source | Issue |
|-------|--------|-------|
| Current headcount 1,500-3,000+ | Multiple conflicting sources | Tracxn says 4,585. TrueUp says 3,000. Others vary. |
| 200-500 research engineers | Estimate based on % of headcount | No direct source for researcher count |

### Speculative Claims (Low Confidence — Flagged in Appendix A)

| Claim | Basis | Risk |
|-------|-------|------|
| 2,000-24,000 recoverable insights | Back-of-napkin estimation | Depends on assumed researcher count and experiment rate |
| 5% duplication rate | Assumption | No data source. Could be 1% or 15%. |
| ~31,000 hours/year wasted | Derived from above | Cascading uncertainty |
| 100-300 failed experiments per researcher-year | General ML norms | Not verified against Anthropic |

### Claims We Explicitly Do NOT Make

- We do not claim to know what tools Anthropic uses internally for experiment tracking
- We do not claim the exact number of research engineers at Anthropic
- We do not claim this system will directly increase revenue
- We do not claim the full system is built — the demo proves the capture step; the rest is proposed

---

## References

- Anthropic internal study (November 2025): 50% productivity increase, declining peer collaboration
- Yi Tay, DeepMind (May 2025): duplicated parallel research within Google
- Sionic AI (December 2025, Hugging Face): `/retrospective` + `/advise` pattern for Claude Code
- Hedgineer (December 2025): model-invoked skills as company-wide knowledge layer
- Design document: `history/KNOWLEDGE-SYSTEM-DESIGN.md`
- Research card output: `research-card.yaml`
- Frozen claims: `history/CORE-V1-CLAIMS.md`
