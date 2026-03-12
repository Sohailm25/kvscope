from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any


@dataclass(frozen=True)
class RequestSlice:
    request_id: str
    prompt_tokens: int
    ttft_ms: float
    latency_ms: float
    arrival_offset_ms: float
    started_offset_ms: float
    completed_offset_ms: float


@dataclass(frozen=True)
class RunSlice:
    run_id: str
    workload_family: str
    engine: str
    model: str
    manifest_path: str
    results_path: str
    kvtrace_path: str
    request_count: int
    status_counts: dict[str, int]
    ttft_p50_ms: float
    latency_p50_ms: float
    tokens_per_second: float
    block_hit_count: int
    shared_prefix_token_counts: list[int]
    request_slices: list[RequestSlice]


def load_run_slice(*, repo_root: Path, run_dir: Path) -> RunSlice:
    manifest_path = run_dir / "manifest.json"
    results_path = run_dir / "results.json"
    kvtrace_path = run_dir / "kvtrace.ndjson"

    manifest = json.loads(manifest_path.read_text())
    results = json.loads(results_path.read_text())
    kvtrace_events = _load_kvtrace_events(kvtrace_path)

    return RunSlice(
        run_id=manifest["run_id"],
        workload_family=manifest["workload_family"],
        engine=manifest["engine"],
        model=manifest["model"],
        manifest_path=str(manifest_path.relative_to(repo_root)),
        results_path=str(results_path.relative_to(repo_root)),
        kvtrace_path=str(kvtrace_path.relative_to(repo_root)),
        request_count=int(results["request_count"]),
        status_counts=dict(results["status_counts"]),
        ttft_p50_ms=float(results["ttft_ms"]["p50"]),
        latency_p50_ms=float(results["latency_ms"]["p50"]),
        tokens_per_second=float(results["tokens_per_second"]),
        block_hit_count=sum(
            1 for event in kvtrace_events if event["event_type"] == "block_hit"
        ),
        shared_prefix_token_counts=[
            int(event["shared_prefix_tokens"])
            for event in kvtrace_events
            if event["event_type"] == "prefix_cache_query"
        ],
        request_slices=[
            RequestSlice(
                request_id=str(request["request_id"]),
                prompt_tokens=int(request["prompt_tokens"]),
                ttft_ms=float(request["ttft_ms"]),
                latency_ms=float(request["latency_ms"]),
                arrival_offset_ms=float(request.get("arrival_offset_ms", 0.0)),
                started_offset_ms=float(request.get("started_offset_ms", 0.0)),
                completed_offset_ms=float(request.get("completed_offset_ms", 0.0)),
            )
            for request in results.get("requests", [])
        ],
    )


def build_phase1_report(
    *,
    repo_root: Path,
    run_dirs: list[Path],
    report_slug: str,
) -> dict[str, Any]:
    run_slices = [
        load_run_slice(repo_root=repo_root, run_dir=run_dir)
        for run_dir in sorted(run_dirs)
    ]
    families = _group_by_family(run_slices)

    return {
        "schema_version": "phase1-report-v1",
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


def render_phase1_markdown(report: dict[str, Any]) -> str:
    lines = [
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
                f"- Run count: `{summary['run_count']}`",
                f"- Mean TTFT p50: `{summary['ttft_p50_ms']['mean']}` ms",
                f"- Mean latency p50: `{summary['latency_p50_ms']['mean']}` ms",
                f"- Mean tokens/sec: `{summary['tokens_per_second']['mean']}`",
                f"- Total derived block hits: `{summary['block_hit_count_total']}`",
                "- Referenced runs:",
            ]
        )
        for run in summary["runs"]:
            lines.append(
                f"  - `{run['run_id']}` via `{run['manifest_path']}` and `{run['kvtrace_path']}`"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_phase1_report(
    *,
    repo_root: Path,
    report: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}__serve__phase1__{report['report_slug']}"
    output_dir = repo_root / "artifacts" / "manifests"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{base_name}.json"
    markdown_path = output_dir / f"{base_name}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(markdown)
    return json_path, markdown_path


def _load_kvtrace_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _group_by_family(run_slices: list[RunSlice]) -> dict[str, list[RunSlice]]:
    grouped: dict[str, list[RunSlice]] = {}
    for run_slice in run_slices:
        grouped.setdefault(run_slice.workload_family, []).append(run_slice)
    return grouped


def _summarize_family(run_slices: list[RunSlice]) -> dict[str, Any]:
    return {
        "run_count": len(run_slices),
        "ttft_p50_ms": _metric_summary([run.ttft_p50_ms for run in run_slices]),
        "latency_p50_ms": _metric_summary([run.latency_p50_ms for run in run_slices]),
        "tokens_per_second": _metric_summary(
            [run.tokens_per_second for run in run_slices]
        ),
        "block_hit_count_total": sum(run.block_hit_count for run in run_slices),
        "shared_prefix_token_counts": [
            run.shared_prefix_token_counts for run in run_slices
        ],
        "runs": [asdict(run) for run in run_slices],
    }


def _metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(fmean(values), 3),
    }


def _build_findings(families: dict[str, list[RunSlice]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    aligned_runs = families.get("aligned-prefix", [])
    near_aligned_runs = families.get("near-aligned-prefix", [])
    control_runs = families.get("no-overlap-control", [])
    mixed_runs = families.get("mixed-long-short", [])
    bursty_runs = families.get("bursty-arrivals", [])

    if aligned_runs:
        findings.append(
            {
                "kind": "aligned-run-count",
                "message": (
                    f"Aligned-prefix family currently has {len(aligned_runs)} run(s) "
                    "referenced in this report."
                ),
                "evidence": {"run_count": len(aligned_runs)},
            }
        )

    aligned_block_hits = sum(run.block_hit_count for run in aligned_runs)
    near_aligned_block_hits = sum(run.block_hit_count for run in near_aligned_runs)
    control_block_hits = sum(run.block_hit_count for run in control_runs)
    if aligned_runs and control_runs and aligned_block_hits > control_block_hits:
        findings.append(
            {
                "kind": "derived-cache-separation",
                "message": (
                    "Aligned-prefix runs recorded derived block hits while the "
                    "no-overlap control did not."
                ),
                "evidence": {
                    "aligned_block_hits_total": aligned_block_hits,
                    "control_block_hits_total": control_block_hits,
                },
            }
        )

    if (
        aligned_runs
        and near_aligned_runs
        and control_runs
        and control_block_hits < near_aligned_block_hits < aligned_block_hits
    ):
        findings.append(
            {
                "kind": "near-aligned-intermediate-case",
                "message": (
                    "Near-aligned runs preserved some derived reuse, but fewer block "
                    "hits than the fully aligned family and more than the no-overlap control."
                ),
                "evidence": {
                    "aligned_block_hits_total": aligned_block_hits,
                    "near_aligned_block_hits_total": near_aligned_block_hits,
                    "control_block_hits_total": control_block_hits,
                },
            }
        )

    mixed_finding = _build_mixed_short_request_finding(mixed_runs)
    if mixed_finding is not None:
        findings.append(mixed_finding)

    bursty_finding = _build_bursty_overlap_pressure_finding(bursty_runs)
    if bursty_finding is not None:
        findings.append(bursty_finding)

    if len(aligned_runs) >= 2:
        aligned_ttft_values = [run.ttft_p50_ms for run in aligned_runs]
        ttft_min = min(aligned_ttft_values)
        ttft_max = max(aligned_ttft_values)
        if ttft_min > 0 and (ttft_max / ttft_min) >= 1.5:
            findings.append(
                {
                    "kind": "aligned-variance-caveat",
                    "message": (
                        "Aligned-prefix repeats show meaningful TTFT spread, so the "
                        "first slice demonstrates qualitative separation more strongly "
                        "than stable performance bounds."
                    ),
                    "evidence": {
                        "ttft_p50_min_ms": round(ttft_min, 3),
                        "ttft_p50_max_ms": round(ttft_max, 3),
                        "ttft_p50_ratio": round(ttft_max / ttft_min, 3),
                    },
                }
            )

    if len(aligned_runs) >= 3:
        findings.append(
            {
                "kind": "phase1-repetition-bar",
                "message": "The aligned-prefix family meets the three-run repetition bar.",
                "evidence": {"aligned_run_count": len(aligned_runs)},
            }
        )

    return findings


def _build_mixed_short_request_finding(
    mixed_runs: list[RunSlice],
) -> dict[str, Any] | None:
    for run in mixed_runs:
        if len(run.request_slices) < 2:
            continue

        shortest = min(run.request_slices, key=lambda request: request.prompt_tokens)
        longest = max(run.request_slices, key=lambda request: request.prompt_tokens)
        if shortest.prompt_tokens == longest.prompt_tokens:
            continue
        if shortest.arrival_offset_ms <= longest.arrival_offset_ms:
            continue
        if longest.ttft_ms <= 0 or longest.completed_offset_ms <= shortest.completed_offset_ms:
            continue
        if (
            shortest.prompt_tokens <= (longest.prompt_tokens / 4)
            and shortest.ttft_ms >= (0.35 * longest.ttft_ms)
        ):
            return {
                "kind": "mixed-short-request-pressure",
                "message": (
                    "In the mixed-long-short run, the much shorter request still paid "
                    "substantial TTFT while overlapping with the longer request, "
                    "which is consistent with queueing or prefill interference."
                ),
                "evidence": {
                    "run_id": run.run_id,
                    "long_prompt_tokens": longest.prompt_tokens,
                    "long_ttft_ms": round(longest.ttft_ms, 3),
                    "short_prompt_tokens": shortest.prompt_tokens,
                    "short_ttft_ms": round(shortest.ttft_ms, 3),
                    "short_arrival_offset_ms": round(shortest.arrival_offset_ms, 3),
                    "prompt_token_ratio": round(
                        shortest.prompt_tokens / longest.prompt_tokens, 3
                    ),
                    "ttft_ratio": round(shortest.ttft_ms / longest.ttft_ms, 3),
                },
            }
    return None


def _build_bursty_overlap_pressure_finding(
    bursty_runs: list[RunSlice],
) -> dict[str, Any] | None:
    for run in bursty_runs:
        if len(run.request_slices) < 4:
            continue

        requests_by_arrival: dict[float, list[RequestSlice]] = {}
        for request in run.request_slices:
            requests_by_arrival.setdefault(request.arrival_offset_ms, []).append(request)

        if len(requests_by_arrival) != 2:
            continue

        ordered_bursts = sorted(requests_by_arrival.items(), key=lambda item: item[0])
        first_arrival_offset, first_burst = ordered_bursts[0]
        second_arrival_offset, second_burst = ordered_bursts[1]
        if second_arrival_offset <= first_arrival_offset:
            continue
        if max(request.completed_offset_ms for request in first_burst) <= second_arrival_offset:
            continue
        if run.block_hit_count <= 0:
            continue

        first_burst_ttft_mean = fmean(request.ttft_ms for request in first_burst)
        second_burst_ttft_mean = fmean(request.ttft_ms for request in second_burst)
        if second_burst_ttft_mean < (0.75 * first_burst_ttft_mean):
            continue

        return {
            "kind": "bursty-overlap-pressure",
            "message": (
                "In the bursty-arrivals run, the later aligned burst arrived before "
                "the first burst drained and still paid substantial TTFT, which is "
                "consistent with burst pressure persisting alongside prefix reuse."
            ),
            "evidence": {
                "run_id": run.run_id,
                "burst_gap_ms": round(second_arrival_offset - first_arrival_offset, 3),
                "first_burst_request_count": len(first_burst),
                "second_burst_request_count": len(second_burst),
                "first_burst_ttft_mean_ms": round(first_burst_ttft_mean, 3),
                "second_burst_ttft_mean_ms": round(second_burst_ttft_mean, 3),
                "block_hit_count": run.block_hit_count,
            },
        }

    return None
