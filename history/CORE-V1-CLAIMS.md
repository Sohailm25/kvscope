# Core v1 Claim Manifest

- Created: `2026-03-11T22:38:16.676039Z`

## Family Claim Classes

| Family | Claim Class |
| --- | --- |
| `aligned-prefix` | `repeated` |
| `bursty-arrivals` | `repeated` |
| `eviction-ordering` | `repeated` |
| `hotset-scan` | `repeated` |
| `locality-return` | `repeated` |
| `locality-shift` | `repeated` |
| `mixed-long-short` | `repeated` |
| `near-aligned-prefix` | `repeated` |
| `no-overlap-control` | `repeated` |

## Claims

### `serving-aligned-prefix-reuse-signal`

- Claim type: `measured`
- Claim class: `repeated`
- Families: `aligned-prefix`
- Summary: Aligned-prefix repeatedly shows derived reuse on the shared blocks and remains the clean positive-case family.
- Sources:
  - `artifacts/manifests/20260311-182034__serve__phase1__phase1-policy-surface-expanded.json`
  - `docs/kvscope_result_bundle.md`

### `serving-near-aligned-intermediate-case`

- Claim type: `measured`
- Claim class: `repeated`
- Families: `near-aligned-prefix`
- Summary: Near-aligned-prefix remains the repeated intermediate case between aligned reuse and the no-overlap control.
- Sources:
  - `artifacts/manifests/20260311-182034__serve__phase1__phase1-policy-surface-expanded.json`
  - `docs/kvscope_result_bundle.md`

### `serving-no-overlap-negative-control`

- Claim type: `measured`
- Claim class: `repeated`
- Families: `no-overlap-control`
- Summary: The no-overlap control remains flat at zero derived reuse and anchors the negative-control story.
- Sources:
  - `artifacts/manifests/20260311-182034__serve__phase1__phase1-policy-surface-expanded.json`
  - `artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json`

### `live-cache-eviction-ordering-direct-hit-signal`

- Claim type: `measured`
- Claim class: `repeated`
- Families: `eviction-ordering`
- Summary: Eviction-ordering repeatedly shows direct live prefix-cache hits in cache-on runs and none in the cache-off control.
- Sources:
  - `artifacts/manifests/20260311-200918__serve__phase3__live-cache-toggle-policy-surface-core-v1-refresh.json`
  - `docs/kvscope_result_bundle.md`

### `live-cache-locality-shift-direct-hit-signal`

- Claim type: `measured`
- Claim class: `repeated`
- Families: `locality-shift`
- Summary: Locality-shift repeatedly shows direct live cache-hit evidence even though the client-side latency story remains noisy.
- Sources:
  - `artifacts/manifests/20260311-200918__serve__phase3__live-cache-toggle-policy-surface-core-v1-refresh.json`
  - `docs/kvscope_result_bundle.md`

### `live-cache-locality-return-direct-hit-signal`

- Claim type: `measured`
- Claim class: `repeated`
- Families: `locality-return`
- Summary: Locality-return now repeatedly shows direct live prefix-cache hits and lower measured prefill than cache-off, but the client-side TTFT story remains mixed across the two observed pairs.
- Sources:
  - `artifacts/manifests/20260311-200918__serve__phase3__live-cache-toggle-policy-surface-core-v1-refresh.json`
  - `docs/kvscope_result_bundle.md`

### `replay-eviction-ordering-lru-beats-fifo`

- Claim type: `replay`
- Claim class: `repeated`
- Families: `eviction-ordering`
- Summary: Eviction-ordering repeatedly shows policy separation between `lru` and `fifo` on live-derived replay traces at the native capacity.
- Sources:
  - `artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json`
  - `artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json`
  - `docs/kvscope_result_bundle.md`

### `replay-hotset-scan-lfu-headroom`

- Claim type: `replay`
- Claim class: `repeated`
- Families: `hotset-scan`
- Summary: Hotset-scan now repeatedly shows `lfu > lru > fifo` replay headroom across the baseline and revisit workload geometries.
- Sources:
  - `artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json`
  - `artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json`
  - `docs/kvscope_result_bundle.md`

### `replay-locality-shift-recency-advantage`

- Claim type: `replay`
- Claim class: `repeated`
- Families: `locality-shift`
- Summary: Locality-shift repeatedly shows a recency advantage where `lru` beats `lfu` on live-derived replay traces.
- Sources:
  - `artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json`
  - `artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json`
  - `docs/kvscope_result_bundle.md`

### `replay-locality-return-crossover`

- Claim type: `replay`
- Claim class: `repeated`
- Families: `locality-return`
- Summary: Locality-return now repeatedly shows a replay policy crossover: `lru` leads at lower capacities, then `lfu` gains headroom at a higher capacity across the baseline and concentrated geometries.
- Sources:
  - `artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json`
  - `artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json`
  - `docs/kvscope_result_bundle.md`
