# ADR-0005: Use Manifest-First Artifact Packaging

## Status

Accepted

## Context

The project’s main outputs are:

- measurements
- traces
- inferred phase artifacts
- figures

Without a manifest-first format, results become difficult to trust and difficult to revisit.

## Decision

Every meaningful run produces a manifest plus raw outputs.

Figures and summaries must point back to manifests.

## Rationale

- improves reviewer trust
- simplifies reruns
- supports negative-result retention

## Consequences

Positive:

- easier debugging
- clearer provenance

Negative:

- slightly more ceremony per run
