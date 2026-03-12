ABOUTME: Defines the bridge experiment connecting live serving behavior to offline kvtrace replay.
ABOUTME: This is a high-signal upgrade because it answers the obvious criticism that replay is detached from reality.

# Live-To-Replay Bridge

## Purpose

Show that offline replay is meaningfully connected to live behavior rather than being a free-floating simulator.

## Core bridge question

When a workload changes live cache behavior in a measurable way, does replay preserve the same directional story?

## Experiment design

### Live side

Run the same serving engine with:

- prefix caching enabled
- prefix caching disabled if the engine exposes such a knob, or
- a live configuration change that materially changes reuse

Collect:

- TTFT percentiles
- ITL percentiles
- goodput
- exposed cache metrics

### Replay side

From the same live runs, extract:

- reuse-relevant events
- block-alignment details
- workload labels

Replay:

- LRU baseline
- one alternative policy

Collect:

- miss ratio
- eviction behavior
- policy ranking by workload

## Success condition

At least one workload family should show:

- live behavior indicating stronger reuse benefit
- replay behavior indicating a more favorable miss-ratio story

This does not prove causal equivalence.

It does prove the replay is not detached from reality.

## Failure condition

If replay and live behavior diverge badly with no explanation, the replay story must be weakened or redesigned.
