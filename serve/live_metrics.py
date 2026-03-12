# ABOUTME: Scrapes and normalizes the subset of vLLM Prometheus metrics used by KVScope.
# ABOUTME: This keeps live cache-observability evidence machine-checkable instead of buried in raw text logs.

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests


COUNTER_ALIASES = {
    "vllm:prefix_cache_queries": (
        "vllm:prefix_cache_queries",
        "vllm:gpu_prefix_cache_queries",
    ),
    "vllm:prefix_cache_hits": (
        "vllm:prefix_cache_hits",
        "vllm:gpu_prefix_cache_hits",
    ),
    "vllm:prompt_tokens_total": ("vllm:prompt_tokens_total",),
    "vllm:generation_tokens_total": ("vllm:generation_tokens_total",),
}

GAUGE_ALIASES = {
    "vllm:gpu_cache_usage_perc": ("vllm:gpu_cache_usage_perc",),
    "vllm:num_requests_running": ("vllm:num_requests_running",),
    "vllm:num_requests_waiting": ("vllm:num_requests_waiting",),
}

HISTOGRAM_ALIASES = {
    "vllm:request_queue_time_seconds": ("vllm:request_queue_time_seconds",),
    "vllm:request_prefill_time_seconds": ("vllm:request_prefill_time_seconds",),
    "vllm:time_to_first_token_seconds": ("vllm:time_to_first_token_seconds",),
}

_COUNTER_LOOKUP = {
    alias: canonical
    for canonical, aliases in COUNTER_ALIASES.items()
    for alias in aliases
}
_GAUGE_LOOKUP = {
    alias: canonical for canonical, aliases in GAUGE_ALIASES.items() for alias in aliases
}
_HISTOGRAM_LOOKUP = {
    alias: canonical
    for canonical, aliases in HISTOGRAM_ALIASES.items()
    for alias in aliases
}


def scrape_metrics_snapshot(*, base_url: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
    response = requests.get(f"{base_url}/metrics", timeout=timeout_seconds)
    response.raise_for_status()
    return parse_metrics_snapshot(response.text)


def parse_metrics_snapshot(metrics_text: str) -> dict[str, Any]:
    gauges: dict[str, float] = {}
    counters: dict[str, float] = {}
    histograms: dict[str, dict[str, float]] = {}

    for raw_line in metrics_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        sample_name, value = _parse_metric_line(line)
        base_name = sample_name.split("{", 1)[0]
        canonical_counter = _COUNTER_LOOKUP.get(base_name.removesuffix("_total"))
        if canonical_counter is not None:
            counters[canonical_counter] = counters.get(canonical_counter, 0.0) + value
            continue

        canonical_gauge = _GAUGE_LOOKUP.get(base_name)
        if canonical_gauge is not None:
            gauges[canonical_gauge] = value
            continue

        if base_name.endswith("_sum"):
            canonical_histogram = _HISTOGRAM_LOOKUP.get(base_name.removesuffix("_sum"))
            if canonical_histogram is not None:
                histograms.setdefault(
                    canonical_histogram, {"sum": 0.0, "count": 0.0}
                )["sum"] += value
                continue

        if base_name.endswith("_count"):
            canonical_histogram = _HISTOGRAM_LOOKUP.get(base_name.removesuffix("_count"))
            if canonical_histogram is not None:
                histograms.setdefault(
                    canonical_histogram, {"sum": 0.0, "count": 0.0}
                )["count"] += value

    return {
        "gauges": gauges,
        "counters": counters,
        "histograms": histograms,
    }


def build_live_metrics_artifact(
    *, before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    counter_delta = {
        metric_name: round(
            float(after["counters"].get(metric_name, 0.0))
            - float(before["counters"].get(metric_name, 0.0)),
            3,
        )
        for metric_name in sorted(set(before["counters"]) | set(after["counters"]))
    }
    histogram_delta = {
        metric_name: _build_histogram_delta(
            before=before["histograms"].get(metric_name, {"sum": 0.0, "count": 0.0}),
            after=after["histograms"].get(metric_name, {"sum": 0.0, "count": 0.0}),
        )
        for metric_name in sorted(set(before["histograms"]) | set(after["histograms"]))
    }
    gauge_delta = {
        metric_name: {
            "before": round(float(before["gauges"].get(metric_name, 0.0)), 3),
            "after": round(float(after["gauges"].get(metric_name, 0.0)), 3),
        }
        for metric_name in sorted(set(before["gauges"]) | set(after["gauges"]))
    }

    prefix_cache_queries = counter_delta.get("vllm:prefix_cache_queries", 0.0)
    prefix_cache_hits = counter_delta.get("vllm:prefix_cache_hits", 0.0)
    derived: dict[str, float | None] = {
        "prefix_cache_hit_rate": None
        if prefix_cache_queries <= 0
        else round(prefix_cache_hits / prefix_cache_queries, 3)
    }

    return {
        "schema_version": "live-metrics-v1",
        "created_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "before": before,
        "after": after,
        "delta": {
            "gauges": gauge_delta,
            "counters": counter_delta,
            "histograms": histogram_delta,
            "derived": derived,
        },
    }


def _build_histogram_delta(*, before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    sum_delta = round(float(after.get("sum", 0.0)) - float(before.get("sum", 0.0)), 6)
    count_delta = round(
        float(after.get("count", 0.0)) - float(before.get("count", 0.0)),
        3,
    )
    mean_ms = 0.0 if count_delta <= 0 else round((sum_delta / count_delta) * 1000.0, 3)
    return {
        "sum_delta": sum_delta,
        "count_delta": count_delta,
        "mean_ms": mean_ms,
    }


def _parse_metric_line(line: str) -> tuple[str, float]:
    sample_name, raw_value = line.rsplit(maxsplit=1)
    return sample_name, float(raw_value)
