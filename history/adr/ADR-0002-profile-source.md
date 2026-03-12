ABOUTME: Architecture decision record for sampled-profile input selection.
ABOUTME: The project needs time-preserving profile data; this ADR locks the primary path.

# ADR-0002: Use Linux perf As The Primary Profile Source

## Status

Accepted

## Context

KVScope needs sampled profiles with time ordering suitable for approximate phase inference.

Aggregate-only profile dumps are not enough.

Candidate paths:

- Linux `perf`
- async-profiler / JFR
- mixed path

## Decision

Use Linux `perf` as the primary profile source.

Treat JFR or async-profiler as secondary or local-development alternatives if needed.

## Rationale

- natural fit for Linux-based serving environments
- time-preserving sample stream
- good compatibility with Perfetto-oriented validation workflows
- avoids tying the project too early to JVM-specific tooling

## Consequences

Positive:

- simpler cross-language story
- stronger alignment with the serving environment

Negative:

- profile collection ergonomics may be rougher than higher-level tools
- local development on non-Linux systems may need adaptation

## Revisit conditions

- if collection friction blocks progress
- if a JFR-based path yields materially better validation with less risk
