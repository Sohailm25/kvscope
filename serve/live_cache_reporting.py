# ABOUTME: Summarizes cache-on versus cache-off serving runs using measured live metrics.
# ABOUTME: This report keeps engine-side evidence separate from derived traces and replay conclusions.

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any


@dataclass(frozen=True)
class LiveCacheRunSlice:
    run_id: str
    workload_family: str
    prefix_caching_enabled: bool
    manifest_path: str
    results_path: str
    live_metrics_path: str
    ttft_p50_ms: float
    latency_p50_ms: float
    prefix_cache_queries: float
    prefix_cache_hits: float
    prefix_cache_hit_rate: float
    request_prefill_mean_ms: float
    request_queue_mean_ms: float
    metric_ttft_mean_ms: float
    gpu_cache_usage_after: float


def build_live_cache_report(
    *,
    repo_root: Path,
    run_dirs: list[Path],
    report_slug: str,
) -> dict[str, Any]:
    run_slices = [
        load_live_cache_run_slice(repo_root=repo_root, run_dir=run_dir)
        for run_dir in sorted(run_dirs)
    ]
    families = _group_by_family(run_slices)

    return {
        "schema_version": "live-cache-report-v1",
        "report_slug": report_slug,
        "created_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "run_count": len(run_slices),
        "run_ids": [run_slice.run_id for run_slice in run_slices],
        "families": {
            family: _summarize_family(group)
            for family, group in sorted(families.items())
        },
        "findings": _build_findings(families),
    }


def render_live_cache_markdown(report: dict[str, Any]) -> str:
    lines = [
        "ABOUTME: Reviewer-facing cache-on versus cache-off summary for KVScope.",
        "ABOUTME: This report only makes claims grounded in measured live metrics and explicit runtime toggles.",
        "",
        f"# {report['report_slug']}",
        "",
        f"- Created: `{report['created_at_utc']}`",
        f"- Runs summarized: `{report['run_count']}`",
        "",
        "## Findings",
        "",
    ]

    for finding in report["findings"]:
        lines.append(f"- `{finding['kind']}`: {finding['message']}")

    lines.extend(["", "## Families", ""])

    for family, summary in sorted(report["families"].items()):
        lines.extend(
            [
                f"### `{family}`",
                "",
                f"- Cache-on runs: `{summary['cache_on']['run_count']}`",
                f"- Cache-off runs: `{summary['cache_off']['run_count']}`",
                f"- Cache-on mean TTFT p50: `{summary['cache_on']['ttft_p50_ms']['mean']}` ms",
                f"- Cache-off mean TTFT p50: `{summary['cache_off']['ttft_p50_ms']['mean']}` ms",
                f"- Cache-on live prefix-cache hit rate mean: `{summary['cache_on']['prefix_cache_hit_rate']['mean']}`",
                f"- Cache-off live prefix-cache hit rate mean: `{summary['cache_off']['prefix_cache_hit_rate']['mean']}`",
                "- Referenced runs:",
            ]
        )
        for mode_name in ("cache_on", "cache_off"):
            for run in summary[mode_name]["runs"]:
                lines.append(
                    f"  - `{run['run_id']}` via `{run['manifest_path']}` and `{run['live_metrics_path']}`"
                )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_live_cache_report(
    *,
    repo_root: Path,
    report: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}__serve__phase3__{report['report_slug']}"
    output_dir = repo_root / "artifacts" / "manifests"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{base_name}.json"
    markdown_path = output_dir / f"{base_name}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(markdown)
    return json_path, markdown_path


def load_live_cache_run_slice(*, repo_root: Path, run_dir: Path) -> LiveCacheRunSlice:
    manifest_path = run_dir / "manifest.json"
    results_path = run_dir / "results.json"
    live_metrics_path = run_dir / "live_metrics.json"

    manifest = json.loads(manifest_path.read_text())
    results = json.loads(results_path.read_text())
    live_metrics = json.loads(live_metrics_path.read_text())
    delta = live_metrics.get("delta", {})

    return LiveCacheRunSlice(
        run_id=manifest["run_id"],
        workload_family=manifest["workload_family"],
        prefix_caching_enabled=bool(manifest["prefix_caching_enabled"]),
        manifest_path=str(manifest_path.relative_to(repo_root)),
        results_path=str(results_path.relative_to(repo_root)),
        live_metrics_path=str(live_metrics_path.relative_to(repo_root)),
        ttft_p50_ms=float(results["ttft_ms"]["p50"]),
        latency_p50_ms=float(results["latency_ms"]["p50"]),
        prefix_cache_queries=float(delta.get("counters", {}).get("vllm:prefix_cache_queries", 0.0)),
        prefix_cache_hits=float(delta.get("counters", {}).get("vllm:prefix_cache_hits", 0.0)),
        prefix_cache_hit_rate=float(
            delta.get("derived", {}).get("prefix_cache_hit_rate") or 0.0
        ),
        request_prefill_mean_ms=float(
            delta.get("histograms", {})
            .get("vllm:request_prefill_time_seconds", {})
            .get("mean_ms", 0.0)
        ),
        request_queue_mean_ms=float(
            delta.get("histograms", {})
            .get("vllm:request_queue_time_seconds", {})
            .get("mean_ms", 0.0)
        ),
        metric_ttft_mean_ms=float(
            delta.get("histograms", {})
            .get("vllm:time_to_first_token_seconds", {})
            .get("mean_ms", 0.0)
        ),
        gpu_cache_usage_after=float(
            delta.get("gauges", {})
            .get("vllm:gpu_cache_usage_perc", {})
            .get("after", 0.0)
        ),
    )


def _group_by_family(run_slices: list[LiveCacheRunSlice]) -> dict[str, list[LiveCacheRunSlice]]:
    grouped: dict[str, list[LiveCacheRunSlice]] = {}
    for run_slice in run_slices:
        grouped.setdefault(run_slice.workload_family, []).append(run_slice)
    return grouped


def _summarize_family(run_slices: list[LiveCacheRunSlice]) -> dict[str, Any]:
    cache_on_runs = [run for run in run_slices if run.prefix_caching_enabled]
    cache_off_runs = [run for run in run_slices if not run.prefix_caching_enabled]
    return {
        "cache_on": _summarize_mode(cache_on_runs),
        "cache_off": _summarize_mode(cache_off_runs),
    }


def _summarize_mode(run_slices: list[LiveCacheRunSlice]) -> dict[str, Any]:
    if not run_slices:
        return {
            "run_count": 0,
            "ttft_p50_ms": _empty_metric_summary(),
            "latency_p50_ms": _empty_metric_summary(),
            "prefix_cache_queries": _empty_metric_summary(),
            "prefix_cache_hits": _empty_metric_summary(),
            "prefix_cache_hit_rate": _empty_metric_summary(),
            "request_prefill_mean_ms": _empty_metric_summary(),
            "request_queue_mean_ms": _empty_metric_summary(),
            "metric_ttft_mean_ms": _empty_metric_summary(),
            "gpu_cache_usage_after": _empty_metric_summary(),
            "runs": [],
        }

    return {
        "run_count": len(run_slices),
        "ttft_p50_ms": _metric_summary([run.ttft_p50_ms for run in run_slices]),
        "latency_p50_ms": _metric_summary([run.latency_p50_ms for run in run_slices]),
        "prefix_cache_queries": _metric_summary(
            [run.prefix_cache_queries for run in run_slices]
        ),
        "prefix_cache_hits": _metric_summary(
            [run.prefix_cache_hits for run in run_slices]
        ),
        "prefix_cache_hit_rate": _metric_summary(
            [run.prefix_cache_hit_rate for run in run_slices]
        ),
        "request_prefill_mean_ms": _metric_summary(
            [run.request_prefill_mean_ms for run in run_slices]
        ),
        "request_queue_mean_ms": _metric_summary(
            [run.request_queue_mean_ms for run in run_slices]
        ),
        "metric_ttft_mean_ms": _metric_summary(
            [run.metric_ttft_mean_ms for run in run_slices]
        ),
        "gpu_cache_usage_after": _metric_summary(
            [run.gpu_cache_usage_after for run in run_slices]
        ),
        "runs": [asdict(run) for run in run_slices],
    }


def _build_findings(
    families: dict[str, list[LiveCacheRunSlice]]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for workload_family, run_slices in sorted(families.items()):
        cache_on_runs = [run for run in run_slices if run.prefix_caching_enabled]
        cache_off_runs = [run for run in run_slices if not run.prefix_caching_enabled]
        if not cache_on_runs or not cache_off_runs:
            continue

        cache_on_hit_rate = round(fmean(run.prefix_cache_hit_rate for run in cache_on_runs), 3)
        cache_off_hit_rate = round(
            fmean(run.prefix_cache_hit_rate for run in cache_off_runs), 3
        )
        if cache_on_hit_rate > cache_off_hit_rate:
            findings.append(
                {
                    "kind": "live-prefix-cache-hit-signal",
                    "message": (
                        f"For `{workload_family}`, the cache-on run exposed live prefix-cache "
                        "hits while the cache-off run did not."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "cache_on_prefix_cache_queries": round(
                            fmean(run.prefix_cache_queries for run in cache_on_runs), 3
                        ),
                        "cache_on_prefix_cache_hits": round(
                            fmean(run.prefix_cache_hits for run in cache_on_runs), 3
                        ),
                        "cache_on_prefix_cache_hit_rate": cache_on_hit_rate,
                        "cache_off_prefix_cache_hit_rate": cache_off_hit_rate,
                    },
                }
            )

        cache_on_prefill = round(
            fmean(run.request_prefill_mean_ms for run in cache_on_runs), 3
        )
        cache_off_prefill = round(
            fmean(run.request_prefill_mean_ms for run in cache_off_runs), 3
        )
        cache_on_ttft = round(fmean(run.ttft_p50_ms for run in cache_on_runs), 3)
        cache_off_ttft = round(fmean(run.ttft_p50_ms for run in cache_off_runs), 3)
        if cache_on_prefill > 0 and cache_off_prefill > cache_on_prefill:
            if _has_clean_ttft_improvement(cache_on_runs, cache_off_runs):
                message = (
                    f"For `{workload_family}`, cache-on reduced measured live prefill time "
                    "relative to cache-off, which is consistent with the lower cache-on TTFT."
                )
            else:
                message = (
                    f"For `{workload_family}`, cache-on reduced measured live prefill time "
                    "relative to cache-off, but client-observed TTFT remained noisy."
                )
            findings.append(
                {
                    "kind": "cache-on-prefill-improvement",
                    "message": message,
                    "evidence": {
                        "workload_family": workload_family,
                        "cache_on_request_prefill_mean_ms": cache_on_prefill,
                        "cache_off_request_prefill_mean_ms": cache_off_prefill,
                        "cache_on_ttft_p50_ms": cache_on_ttft,
                        "cache_off_ttft_p50_ms": cache_off_ttft,
                    },
                }
            )

    return findings


def _has_clean_ttft_improvement(
    cache_on_runs: list[LiveCacheRunSlice],
    cache_off_runs: list[LiveCacheRunSlice],
) -> bool:
    cache_on_mean = fmean(run.ttft_p50_ms for run in cache_on_runs)
    cache_off_mean = fmean(run.ttft_p50_ms for run in cache_off_runs)
    if cache_on_mean >= cache_off_mean:
        return False

    cache_on_max = max(run.ttft_p50_ms for run in cache_on_runs)
    cache_off_min = min(run.ttft_p50_ms for run in cache_off_runs)
    return cache_on_max < cache_off_min


def _metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(fmean(values), 3),
    }


def _empty_metric_summary() -> dict[str, float]:
    return {"min": 0.0, "max": 0.0, "mean": 0.0}
