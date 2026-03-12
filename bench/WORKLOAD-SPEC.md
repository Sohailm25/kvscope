# Workload Spec

## Families

### `sharegpt-baseline`

Purpose:

- realistic chat-like baseline

### `no-overlap-control`

Purpose:

- verify reuse benefits collapse when shared prefixes disappear

### `aligned-prefix`

Purpose:

- expose best-case full-block prefix reuse

### `near-aligned-prefix`

Purpose:

- expose the cost of missing a full block boundary

### `mixed-long-short`

Purpose:

- expose prefill/decode interference and fairness issues

### `bursty-arrivals`

Purpose:

- expose queueing and infrastructure warm/cold confounds

### `scan-adversarial`

Purpose:

- stress cache pollution behavior

## Required labels

Each workload artifact should declare:

- `workload_id`
- `source_kind`
- `expected_reuse_class`
- `prompt_length_class`
- `arrival_pattern`

## Rule

No benchmark result should be published without a declared workload family.
