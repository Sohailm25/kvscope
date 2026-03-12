ABOUTME: External research note for the KVScope investigator-layer plan.
ABOUTME: This captures the current role and ecosystem signals that justify shifting from benchmark-only depth to an investigation system.

# KVScope Investigator Research Note

## Purpose

Capture the external grounding for the post-core `KVScope` plan as of March 11, 2026.

## Primary Sources

### Anthropic

- AI Observability, Research Engineer role:
  - https://job-boards.greenhouse.io/anthropic/jobs/5125083008
- Careers:
  - https://www.anthropic.com/careers
- Engineering:
  - https://www.anthropic.com/engineering
- How we built our multi-agent research system:
  - https://www.anthropic.com/engineering/built-multi-agent-research-system
- Demystifying evals for AI agents:
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Writing tools for agents:
  - https://www.anthropic.com/engineering/writing-tools-for-agents
- Effective context engineering for AI agents:
  - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Code execution with MCP:
  - https://www.anthropic.com/engineering/code-execution-with-mcp
- AI-resistant technical evaluations:
  - https://www.anthropic.com/engineering/AI-resistant-technical-evaluations

### Observability And Evaluation Tooling

- LangSmith observability:
  - https://docs.langchain.com/langsmith/observability
- Phoenix user guide:
  - https://arize.com/docs/phoenix/user-guide
- Braintrust:
  - https://www.braintrust.dev/
- HoneyHive:
  - https://docs.honeyhive.ai/introduction/what-is-hhai
- Helicone AI agents guide:
  - https://docs.helicone.ai/guides/cookbooks/ai-agents

### Standards And Interop

- Model Context Protocol architecture:
  - https://modelcontextprotocol.io/docs/concepts/architecture
- OpenInference traces:
  - https://arize-ai.github.io/openinference/spec/traces.html
- OpenTelemetry GenAI semantic conventions:
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/

## Findings

### 1. The role is broader than inference benchmarking

The official role emphasizes:

- AI-based monitoring systems
- deriving structured insight from large unstructured datasets
- agentic integrations
- user-facing tools and interfaces
- converting messy evidence into trustworthy structured signals

### 2. Anthropic’s current engineering style favors bounded agent systems

The recent engineering material repeatedly emphasizes:

- tool quality before autonomy
- eval-driven iteration
- careful context management
- strong transcripts and traces
- simple systems that can be audited

### 3. The market already covers generic traces and evals

Current platforms converge on:

- tracing
- evals
- datasets
- feedback and annotation
- agent/session views
- AI assistant layers

That means a new project should not try to win by feature-count parity alone.

### 4. Interop matters, but replacement is a bad bet

MCP is already the right agent/tooling surface.

OpenInference is useful for export and interoperability.

OpenTelemetry GenAI semantic conventions are still under active development, so a domain-specific internal contract can still be the right internal choice.

### 5. The repo’s best gap is the investigation layer

`KVScope` already has a strong evidence substrate:

- live runs
- replay
- bridge reports
- capacity sweeps
- tables and figures
- disciplined claim boundaries

The largest role-shaped gap is:

- no artifact index
- no tool surface
- no investigation loop
- no answer-quality evals
- no user-facing interface

## Conclusion

The highest-signal continuation is not another pure benchmark pass.

It is a grounded AI observability investigation system built on top of the current `KVScope` artifact corpus.
