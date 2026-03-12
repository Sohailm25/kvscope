from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RequestObservation:
    request_id: str
    prompt_tokens: int
    output_tokens: int
    ttft_ms: float
    latency_ms: float
    inter_token_latencies_ms: list[float]
    status: str
    arrival_offset_ms: float = 0.0
    started_offset_ms: float = 0.0
    completed_offset_ms: float = 0.0


def create_run_directory(
    *,
    artifacts_root: Path,
    module: str,
    workload_family: str,
    slug: str,
    timestamp_override: str | None = None,
) -> Path:
    timestamp = timestamp_override or "19700101-000000"
    run_id = f"{timestamp}__{module}__{workload_family}__{slug}"
    run_dir = artifacts_root / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_run_manifest(
    *,
    run_id: str,
    module: str,
    engine: str,
    engine_version: str,
    model: str,
    gpu_type: str,
    workload_id: str,
    workload_family: str,
    prefix_caching_enabled: bool,
    cold_start: bool,
    warmup_requests_discarded: int,
    commit: str,
    created_at_utc: str,
    command: str,
) -> dict[str, Any]:
    return {
        "schema_version": "run-manifest-v1",
        "run_id": run_id,
        "module": module,
        "engine": engine,
        "engine_version": engine_version,
        "model": model,
        "gpu_type": gpu_type,
        "workload_id": workload_id,
        "workload_family": workload_family,
        "prefix_caching_enabled": prefix_caching_enabled,
        "cold_start": cold_start,
        "warmup_requests_discarded": warmup_requests_discarded,
        "commit": commit,
        "created_at_utc": created_at_utc,
        "command": command,
    }


def summarize_observations(observations: list[RequestObservation]) -> dict[str, Any]:
    ttft_values = [observation.ttft_ms for observation in observations]
    latency_values = [observation.latency_ms for observation in observations]
    itl_values = [
        latency
        for observation in observations
        for latency in observation.inter_token_latencies_ms
    ]
    total_output_tokens = sum(observation.output_tokens for observation in observations)
    total_latency_ms = sum(observation.latency_ms for observation in observations)

    return {
        "request_count": len(observations),
        "status_counts": _status_counts(observations),
        "ttft_ms": _percentiles(ttft_values),
        "latency_ms": _percentiles(latency_values),
        "itl_ms": _percentiles(itl_values),
        "total_output_tokens": total_output_tokens,
        "tokens_per_second": 0.0
        if total_latency_ms == 0
        else round(total_output_tokens / (total_latency_ms / 1000.0), 3),
        "requests": [asdict(observation) for observation in observations],
    }


def write_run_bundle(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    results: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
    kvtrace_events: list[dict[str, Any]],
    live_metrics: dict[str, Any] | None = None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (run_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    (run_dir / "stdout.log").write_text(stdout_text)
    (run_dir / "stderr.log").write_text(stderr_text)
    if live_metrics is not None:
        (run_dir / "live_metrics.json").write_text(json.dumps(live_metrics, indent=2) + "\n")

    if kvtrace_events:
        (run_dir / "kvtrace.ndjson").write_text(
            "".join(json.dumps(event) + "\n" for event in kvtrace_events)
        )


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}

    ordered = sorted(values)
    return {
        "p50": round(_percentile(ordered, 50), 3),
        "p95": round(_percentile(ordered, 95), 3),
        "p99": round(_percentile(ordered, 99), 3),
        "mean": round(statistics.fmean(ordered), 3),
    }


def _percentile(ordered_values: list[float], percentile: int) -> float:
    if len(ordered_values) == 1:
        return ordered_values[0]

    rank = (percentile / 100) * (len(ordered_values) - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered_values) - 1)
    weight = rank - lower_index
    lower_value = ordered_values[lower_index]
    upper_value = ordered_values[upper_index]
    return lower_value + (upper_value - lower_value) * weight


def _status_counts(observations: list[RequestObservation]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for observation in observations:
        counts[observation.status] = counts.get(observation.status, 0) + 1
    return counts
