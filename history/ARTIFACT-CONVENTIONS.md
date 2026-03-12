ABOUTME: Artifact and result-layout conventions for KVScope.
ABOUTME: The repo should produce reproducible outputs, not remembered numbers or screenshots without provenance.

# Artifact Conventions

## Root Layout

- `artifacts/runs/`
- `artifacts/figures/`
- `artifacts/examples/`
- `artifacts/manifests/`

## Run Directory Naming

Format:

`YYYYMMDD-HHMMSS__module__workload__slug`

Example:

`20260311-011500__serve__aligned-prefix__warm-run-01`

## Required Files Per Run

- `manifest.json`
- `stdout.log`
- `stderr.log`
- `results.json`
- `workload.jsonl`
- `kvtrace.ndjson` for `serve/` runs that emit replayable traces
- optional `live_metrics.json` when the engine exposes scrapeable runtime metrics
- optional `notes.md`

## Required Manifest Fields

Every run manifest must include:

- `schema_version`
- `run_id`
- `module`
- `engine`
- `engine_version`
- `model`
- `gpu_type`
- `workload_id`
- `workload_family`
- `prefix_caching_enabled`
- `cold_start`
- `warmup_requests_discarded`
- `commit`
- `created_at_utc`
- `command`

See:

- [run-manifest-v1.example.json](artifacts/examples/run-manifest-v1.example.json)

The `command` field should encode the workload geometry needed to reproduce the run, not just the workload family name.

When a run records `cache_capacity_blocks` in the command, that value is currently a replay-budget parameter for derived `kvtrace` and offline policy comparison. It is not, by itself, a live `vLLM` cache-capacity control.

When present, `live_metrics.json` should use the `live-metrics-v1` schema and keep measured engine metrics separate from inferred or replayed values.

## Figure Naming

Format:

`<topic>__<engine>__<workload>__<metric>.png`

Example:

`cache-alignment__vllm__aligned-prefix__ttft-p99.png`

## Trace Fixture Reference

Replay-capable traces should follow:

- [kvtrace-v2.example.ndjson](artifacts/examples/kvtrace-v2.example.ndjson)

## Manifest Rule

Every figure and summary table must reference one or more run manifests.

When a workload depends on staggered or overlapping requests, `results.json` request entries should preserve the per-request arrival and timing fields needed to interpret the run:

- `arrival_offset_ms`
- `started_offset_ms`
- `completed_offset_ms`

## Multi-Run Summary Artifacts

Cross-run summaries live under `artifacts/manifests/`.

Format:

`YYYYMMDD-HHMMSS__serve__phase1__<slug>.json`

and the reviewer-facing markdown note with the same basename:

`YYYYMMDD-HHMMSS__serve__phase1__<slug>.md`

Example:

- [phase1-clean-baseline.json](artifacts/manifests/20260311-012300__serve__phase1__phase1-clean-baseline.json)
- [phase1-clean-baseline.md](artifacts/manifests/20260311-012300__serve__phase1__phase1-clean-baseline.md)
- [phase1-expanded-slice.json](artifacts/manifests/20260311-023401__serve__phase1__phase1-expanded-slice.json)
- [phase1-expanded-slice.md](artifacts/manifests/20260311-023401__serve__phase1__phase1-expanded-slice.md)
- [phase1-observability-slice.json](artifacts/manifests/20260311-025009__serve__phase1__phase1-observability-slice.json)
- [phase1-observability-slice.md](artifacts/manifests/20260311-025009__serve__phase1__phase1-observability-slice.md)
- [phase1-bursty-observability-slice.json](artifacts/manifests/20260311-132801__serve__phase1__phase1-bursty-observability-slice.json)
- [phase1-bursty-observability-slice.md](artifacts/manifests/20260311-132801__serve__phase1__phase1-bursty-observability-slice.md)
- [phase1-repeated-families-slice.json](artifacts/manifests/20260311-142406__serve__phase1__phase1-repeated-families-slice.json)
- [phase1-repeated-families-slice.md](artifacts/manifests/20260311-142406__serve__phase1__phase1-repeated-families-slice.md)

Replay bridge summaries follow:

`YYYYMMDD-HHMMSS__kvtrace__bridge__<slug>.json`

and the reviewer-facing markdown note with the same basename:

`YYYYMMDD-HHMMSS__kvtrace__bridge__<slug>.md`

Example:

- [bridge-cache-ordering.json](artifacts/manifests/20260311-025649__kvtrace__bridge__bridge-cache-ordering.json)
- [bridge-cache-ordering.md](artifacts/manifests/20260311-025649__kvtrace__bridge__bridge-cache-ordering.md)
- [bridge-cache-ordering-bursty.json](artifacts/manifests/20260311-132801__kvtrace__bridge__bridge-cache-ordering-bursty.json)
- [bridge-cache-ordering-bursty.md](artifacts/manifests/20260311-132801__kvtrace__bridge__bridge-cache-ordering-bursty.md)
- [bridge-cache-ordering-divergence.json](artifacts/manifests/20260311-143006__kvtrace__bridge__bridge-cache-ordering-divergence.json)
- [bridge-cache-ordering-divergence.md](artifacts/manifests/20260311-143006__kvtrace__bridge__bridge-cache-ordering-divergence.md)
- [bridge-cache-ordering-divergence-repeated.json](artifacts/manifests/20260311-163320__kvtrace__bridge__bridge-cache-ordering-divergence-repeated.json)
- [bridge-cache-ordering-divergence-repeated.md](artifacts/manifests/20260311-163320__kvtrace__bridge__bridge-cache-ordering-divergence-repeated.md)
- [bridge-policy-headroom-expanded.json](artifacts/manifests/20260311-170559__kvtrace__bridge__bridge-policy-headroom-expanded.json)
- [bridge-policy-headroom-expanded.md](artifacts/manifests/20260311-170559__kvtrace__bridge__bridge-policy-headroom-expanded.md)
- [bridge-policy-tradeoffs-expanded.json](artifacts/manifests/20260311-173634__kvtrace__bridge__bridge-policy-tradeoffs-expanded.json)
- [bridge-policy-tradeoffs-expanded.md](artifacts/manifests/20260311-173634__kvtrace__bridge__bridge-policy-tradeoffs-expanded.md)
- [bridge-policy-tradeoffs-repeated.json](artifacts/manifests/20260311-175734__kvtrace__bridge__bridge-policy-tradeoffs-repeated.json)
- [bridge-policy-tradeoffs-repeated.md](artifacts/manifests/20260311-175734__kvtrace__bridge__bridge-policy-tradeoffs-repeated.md)

Replay capacity-sweep summaries follow:

`YYYYMMDD-HHMMSS__kvtrace__sweep__<slug>.json`

and the reviewer-facing markdown note with the same basename:

`YYYYMMDD-HHMMSS__kvtrace__sweep__<slug>.md`

Example:

- [replay-capacity-sweep-expanded.json](artifacts/manifests/20260311-172909__kvtrace__sweep__replay-capacity-sweep-expanded.json)
- [replay-capacity-sweep-expanded.md](artifacts/manifests/20260311-172909__kvtrace__sweep__replay-capacity-sweep-expanded.md)
- [replay-capacity-sweep-tradeoffs-expanded.json](artifacts/manifests/20260311-173634__kvtrace__sweep__replay-capacity-sweep-tradeoffs-expanded.json)
- [replay-capacity-sweep-tradeoffs-expanded.md](artifacts/manifests/20260311-173634__kvtrace__sweep__replay-capacity-sweep-tradeoffs-expanded.md)
- [replay-capacity-sweep-tradeoffs-repeated.json](artifacts/manifests/20260311-175734__kvtrace__sweep__replay-capacity-sweep-tradeoffs-repeated.json)
- [replay-capacity-sweep-tradeoffs-repeated.md](artifacts/manifests/20260311-175734__kvtrace__sweep__replay-capacity-sweep-tradeoffs-repeated.md)
- [replay-capacity-sweep-policy-surface-expanded.json](artifacts/manifests/20260311-182034__kvtrace__sweep__replay-capacity-sweep-policy-surface-expanded.json)
- [replay-capacity-sweep-policy-surface-expanded.md](artifacts/manifests/20260311-182034__kvtrace__sweep__replay-capacity-sweep-policy-surface-expanded.md)

Live cache-toggle summaries follow:

`YYYYMMDD-HHMMSS__serve__phase3__<slug>.json`

and the reviewer-facing markdown note with the same basename:

`YYYYMMDD-HHMMSS__serve__phase3__<slug>.md`

Example:

- [aligned-live-cache-toggle.json](artifacts/manifests/20260311-140423__serve__phase3__aligned-live-cache-toggle.json)
- [aligned-live-cache-toggle.md](artifacts/manifests/20260311-140423__serve__phase3__aligned-live-cache-toggle.md)
- [live-cache-toggle-expanded.json](artifacts/manifests/20260311-163728__serve__phase3__live-cache-toggle-expanded.json)
- [live-cache-toggle-expanded.md](artifacts/manifests/20260311-163728__serve__phase3__live-cache-toggle-expanded.md)
- [live-cache-toggle-hotset-expanded.json](artifacts/manifests/20260311-171756__serve__phase3__live-cache-toggle-hotset-expanded.json)
- [live-cache-toggle-hotset-expanded.md](artifacts/manifests/20260311-171756__serve__phase3__live-cache-toggle-hotset-expanded.md)
- [live-cache-toggle-tradeoffs-expanded.json](artifacts/manifests/20260311-173634__serve__phase3__live-cache-toggle-tradeoffs-expanded.json)
- [live-cache-toggle-tradeoffs-expanded.md](artifacts/manifests/20260311-173634__serve__phase3__live-cache-toggle-tradeoffs-expanded.md)
- [live-cache-toggle-tradeoffs-repeated.json](artifacts/manifests/20260311-175734__serve__phase3__live-cache-toggle-tradeoffs-repeated.json)
- [live-cache-toggle-tradeoffs-repeated.md](artifacts/manifests/20260311-175734__serve__phase3__live-cache-toggle-tradeoffs-repeated.md)
- [live-cache-toggle-policy-surface-expanded.json](artifacts/manifests/20260311-182034__serve__phase3__live-cache-toggle-policy-surface-expanded.json)
- [live-cache-toggle-policy-surface-expanded.md](artifacts/manifests/20260311-182034__serve__phase3__live-cache-toggle-policy-surface-expanded.md)

Phase 6 result-table summaries follow:

`YYYYMMDD-HHMMSS__serve__phase6__<slug>.json`

and the reviewer-facing markdown note with the same basename:

`YYYYMMDD-HHMMSS__serve__phase6__<slug>.md`

Example:

- [benchmark-tables.json](artifacts/manifests/20260311-165220__serve__phase6__benchmark-tables.json)
- [benchmark-tables.md](artifacts/manifests/20260311-165220__serve__phase6__benchmark-tables.md)
- [benchmark-tables-expanded.json](artifacts/manifests/20260311-170722__serve__phase6__benchmark-tables-expanded.json)
- [benchmark-tables-expanded.md](artifacts/manifests/20260311-170722__serve__phase6__benchmark-tables-expanded.md)
- [benchmark-tables-hotset-expanded.json](artifacts/manifests/20260311-171800__serve__phase6__benchmark-tables-hotset-expanded.json)
- [benchmark-tables-hotset-expanded.md](artifacts/manifests/20260311-171800__serve__phase6__benchmark-tables-hotset-expanded.md)
- [benchmark-tables-tradeoffs-expanded.json](artifacts/manifests/20260311-173725__serve__phase6__benchmark-tables-tradeoffs-expanded.json)
- [benchmark-tables-tradeoffs-expanded.md](artifacts/manifests/20260311-173725__serve__phase6__benchmark-tables-tradeoffs-expanded.md)
- [benchmark-tables-tradeoffs-repeated.json](artifacts/manifests/20260311-175741__serve__phase6__benchmark-tables-tradeoffs-repeated.json)
- [benchmark-tables-tradeoffs-repeated.md](artifacts/manifests/20260311-175741__serve__phase6__benchmark-tables-tradeoffs-repeated.md)
- [benchmark-tables-policy-surface-expanded.json](artifacts/manifests/20260311-182054__serve__phase6__benchmark-tables-policy-surface-expanded.json)
- [benchmark-tables-policy-surface-expanded.md](artifacts/manifests/20260311-182054__serve__phase6__benchmark-tables-policy-surface-expanded.md)

Phase 6 figure summaries follow the same manifest pattern:

`YYYYMMDD-HHMMSS__serve__phase6__<slug>.json`

and the reviewer-facing markdown note with the same basename:

`YYYYMMDD-HHMMSS__serve__phase6__<slug>.md`

Example:

- [benchmark-figures-tradeoffs-repeated.json](artifacts/manifests/20260311-175741__serve__phase6__benchmark-figures-tradeoffs-repeated.json)
- [benchmark-figures-tradeoffs-repeated.md](artifacts/manifests/20260311-175741__serve__phase6__benchmark-figures-tradeoffs-repeated.md)
- [benchmark-figures-policy-surface-expanded.json](artifacts/manifests/20260311-182136__serve__phase6__benchmark-figures-policy-surface-expanded.json)
- [benchmark-figures-policy-surface-expanded.md](artifacts/manifests/20260311-182136__serve__phase6__benchmark-figures-policy-surface-expanded.md)
- [live-cache-toggle__vllm__cross-family__hit-rate-and-prefill.png](artifacts/figures/live-cache-toggle__vllm__cross-family__hit-rate-and-prefill.png)
- [policy-tradeoffs__vllm__cross-family__hit-rate-by-capacity.png](artifacts/figures/policy-tradeoffs__vllm__cross-family__hit-rate-by-capacity.png)

Reviewer-facing bundle docs live under `docs/`.

Example:

- [kvscope_result_bundle.md](docs/kvscope_result_bundle.md)

## Retention Rule

Do not delete failed or negative-result artifacts unless they are provably invalid.
