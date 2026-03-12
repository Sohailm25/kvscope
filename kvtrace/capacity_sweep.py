# ABOUTME: Builds replay-capacity sweep reports from live-derived KVScope traces.
# ABOUTME: A capacity sweep is useful because policy differences can appear, disappear, or reverse as cache budget changes.

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from kvtrace.replay import (
    infer_capacity_blocks_from_command,
    load_block_lookup_keys,
    replay_block_sequence,
)


@dataclass(frozen=True)
class ReplayCapacityRunSlice:
    run_id: str
    workload_family: str
    manifest_path: str
    results_path: str
    kvtrace_path: str
    live_ttft_p50_ms: float
    native_capacity_blocks: int
    lookup_keys: list[str]


def build_replay_capacity_sweep_report(
    *,
    repo_root: Path,
    run_dirs: list[Path],
    capacities: list[int],
    report_slug: str,
) -> dict[str, Any]:
    normalized_capacities = _normalize_capacities(capacities)
    run_slices = [
        _load_run_slice(repo_root=repo_root, run_dir=run_dir)
        for run_dir in sorted(run_dirs)
    ]
    families = _group_by_family(run_slices)
    family_summaries = {
        family: _summarize_family(run_slices=group, capacities=normalized_capacities)
        for family, group in sorted(families.items())
    }

    return {
        "schema_version": "kvtrace-capacity-sweep-v1",
        "report_slug": report_slug,
        "created_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "run_count": len(run_slices),
        "run_ids": [run_slice.run_id for run_slice in run_slices],
        "capacities": normalized_capacities,
        "families": family_summaries,
        "findings": _build_findings(
            family_summaries=family_summaries,
            capacities=normalized_capacities,
        ),
    }


def render_replay_capacity_sweep_markdown(report: dict[str, Any]) -> str:
    lines = [
        "ABOUTME: Reviewer-facing replay-capacity sweep for KVScope.",
        "ABOUTME: This report shows where replay policies separate, collapse, or first become useful as cache budget changes.",
        "",
        f"# {report['report_slug']}",
        "",
        f"- Created: `{report['created_at_utc']}`",
        f"- Runs summarized: `{report['run_count']}`",
        f"- Capacities swept: `{', '.join(str(capacity) for capacity in report['capacities'])}`",
        "",
        "## Findings",
        "",
    ]

    for finding in report["findings"]:
        lines.append(f"- `{finding['kind']}`: {finding['message']}")

    lines.extend(["", "## Families", ""])

    for family, summary in sorted(report["families"].items()):
        native_capacities = ", ".join(
            str(capacity) for capacity in summary["native_capacity_blocks_observed"]
        )
        lines.extend(
            [
                f"### `{family}`",
                "",
                f"- Run count: `{summary['run_count']}`",
                f"- Mean live TTFT p50: `{summary['live_ttft_p50_ms']['mean']}` ms",
                f"- Native capacities observed in manifests: `{native_capacities}`",
                "",
                "| Capacity | FIFO hit rate | LRU hit rate | LFU hit rate |",
                "| ---: | ---: | ---: | ---: |",
            ]
        )

        for capacity in report["capacities"]:
            capacity_summary = summary["capacities"][str(capacity)]["policies"]
            lines.append(
                "| {capacity} | {fifo} | {lru} | {lfu} |".format(
                    capacity=capacity,
                    fifo=capacity_summary["fifo"]["hit_rate_mean"],
                    lru=capacity_summary["lru"]["hit_rate_mean"],
                    lfu=capacity_summary["lfu"]["hit_rate_mean"],
                )
            )

        lines.append("")
        lines.append("- Referenced runs:")
        for run in summary["runs"]:
            lines.append(
                f"  - `{run['run_id']}` via `{run['manifest_path']}` and `{run['kvtrace_path']}`"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_replay_capacity_sweep_report(
    *,
    repo_root: Path,
    report: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}__kvtrace__sweep__{report['report_slug']}"
    output_dir = repo_root / "artifacts" / "manifests"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{base_name}.json"
    markdown_path = output_dir / f"{base_name}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(markdown)
    return json_path, markdown_path


def _load_run_slice(*, repo_root: Path, run_dir: Path) -> ReplayCapacityRunSlice:
    manifest_path = run_dir / "manifest.json"
    results_path = run_dir / "results.json"
    kvtrace_path = run_dir / "kvtrace.ndjson"

    manifest = json.loads(manifest_path.read_text())
    results = json.loads(results_path.read_text())

    return ReplayCapacityRunSlice(
        run_id=manifest["run_id"],
        workload_family=manifest["workload_family"],
        manifest_path=str(manifest_path.relative_to(repo_root)),
        results_path=str(results_path.relative_to(repo_root)),
        kvtrace_path=str(kvtrace_path.relative_to(repo_root)),
        live_ttft_p50_ms=float(results["ttft_ms"]["p50"]),
        native_capacity_blocks=infer_capacity_blocks_from_command(manifest["command"]),
        lookup_keys=load_block_lookup_keys(kvtrace_path),
    )


def _group_by_family(
    run_slices: list[ReplayCapacityRunSlice],
) -> dict[str, list[ReplayCapacityRunSlice]]:
    grouped: dict[str, list[ReplayCapacityRunSlice]] = {}
    for run_slice in run_slices:
        grouped.setdefault(run_slice.workload_family, []).append(run_slice)
    return grouped


def _summarize_family(
    *, run_slices: list[ReplayCapacityRunSlice], capacities: list[int]
) -> dict[str, Any]:
    return {
        "run_count": len(run_slices),
        "live_ttft_p50_ms": _metric_summary([run.live_ttft_p50_ms for run in run_slices]),
        "native_capacity_blocks_observed": sorted(
            {run.native_capacity_blocks for run in run_slices}
        ),
        "capacities": {
            str(capacity): {
                "policies": {
                    policy_name: _summarize_policy(
                        run_slices=run_slices,
                        capacity_blocks=capacity,
                        policy_name=policy_name,
                    )
                    for policy_name in ("fifo", "lru", "lfu")
                }
            }
            for capacity in capacities
        },
        "runs": [_serialize_run_slice(run_slice) for run_slice in run_slices],
    }


def _summarize_policy(
    *,
    run_slices: list[ReplayCapacityRunSlice],
    capacity_blocks: int,
    policy_name: str,
) -> dict[str, float | int]:
    summaries = [
        replay_block_sequence(
            policy_name=policy_name,
            capacity_blocks=capacity_blocks,
            block_keys=run_slice.lookup_keys,
        )
        for run_slice in run_slices
    ]
    return {
        "hits_total": sum(int(summary["hits"]) for summary in summaries),
        "misses_total": sum(int(summary["misses"]) for summary in summaries),
        "hit_rate_mean": round(fmean(float(summary["hit_rate"]) for summary in summaries), 3),
    }


def _serialize_run_slice(run_slice: ReplayCapacityRunSlice) -> dict[str, Any]:
    return {
        "run_id": run_slice.run_id,
        "workload_family": run_slice.workload_family,
        "manifest_path": run_slice.manifest_path,
        "results_path": run_slice.results_path,
        "kvtrace_path": run_slice.kvtrace_path,
        "live_ttft_p50_ms": run_slice.live_ttft_p50_ms,
        "native_capacity_blocks": run_slice.native_capacity_blocks,
        "lookup_count": len(run_slice.lookup_keys),
    }


def _build_findings(
    *,
    family_summaries: dict[str, dict[str, Any]],
    capacities: list[int],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for workload_family, summary in sorted(family_summaries.items()):
        capacities_summary = summary["capacities"]

        first_reuse_capacity = next(
            (
                capacity
                for capacity in capacities
                if capacities_summary[str(capacity)]["policies"]["lru"]["hit_rate_mean"] > 0
            ),
            None,
        )
        if first_reuse_capacity is not None and first_reuse_capacity > capacities[0]:
            findings.append(
                {
                    "kind": "capacity-reuse-threshold",
                    "message": (
                        f"For `{workload_family}`, replay reuse first appears once cache "
                        f"capacity reaches `{first_reuse_capacity}` blocks."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "first_reuse_capacity_blocks": first_reuse_capacity,
                    },
                }
            )

        divergence_capacities = [
            capacity
            for capacity in capacities
            if capacities_summary[str(capacity)]["policies"]["lru"]["hit_rate_mean"]
            > capacities_summary[str(capacity)]["policies"]["fifo"]["hit_rate_mean"]
        ]
        if divergence_capacities:
            findings.append(
                {
                    "kind": "capacity-policy-divergence-band",
                    "message": (
                        f"For `{workload_family}`, `lru` beats `fifo` at capacities "
                        f"`{', '.join(str(capacity) for capacity in divergence_capacities)}`."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "capacity_blocks": divergence_capacities,
                    },
                }
            )

        headroom_capacities = [
            capacity
            for capacity in capacities
            if capacities_summary[str(capacity)]["policies"]["lfu"]["hit_rate_mean"]
            > capacities_summary[str(capacity)]["policies"]["lru"]["hit_rate_mean"]
        ]
        if headroom_capacities:
            findings.append(
                {
                    "kind": "capacity-policy-headroom-band",
                    "message": (
                        f"For `{workload_family}`, `lfu` leaves headroom above `lru` at "
                        f"capacities `{', '.join(str(capacity) for capacity in headroom_capacities)}`."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "capacity_blocks": headroom_capacities,
                    },
                }
            )

        recency_advantage_capacities = [
            capacity
            for capacity in capacities
            if capacities_summary[str(capacity)]["policies"]["lru"]["hit_rate_mean"]
            > capacities_summary[str(capacity)]["policies"]["lfu"]["hit_rate_mean"]
        ]
        if recency_advantage_capacities:
            findings.append(
                {
                    "kind": "capacity-recency-advantage-band",
                    "message": (
                        f"For `{workload_family}`, `lru` beats `lfu` at capacities "
                        f"`{', '.join(str(capacity) for capacity in recency_advantage_capacities)}`."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "capacity_blocks": recency_advantage_capacities,
                    },
                }
            )
        if headroom_capacities and recency_advantage_capacities:
            findings.append(
                {
                    "kind": "capacity-policy-crossover",
                    "message": (
                        f"For `{workload_family}`, the `lru` versus `lfu` preference flips "
                        "as cache capacity changes."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "lru_advantage_capacity_blocks": recency_advantage_capacities,
                        "lfu_advantage_capacity_blocks": headroom_capacities,
                    },
                }
            )

        if _all_zero_family(summary, capacities):
            findings.append(
                {
                    "kind": "capacity-negative-control",
                    "message": (
                        f"For `{workload_family}`, replay stays flat at zero across the "
                        "entire capacity sweep."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "capacity_blocks": capacities,
                    },
                }
            )

    return findings


def _all_zero_family(summary: dict[str, Any], capacities: list[int]) -> bool:
    for capacity in capacities:
        policies = summary["capacities"][str(capacity)]["policies"]
        if any(policies[policy_name]["hit_rate_mean"] > 0 for policy_name in ("fifo", "lru", "lfu")):
            return False
    return True


def _metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(fmean(values), 3),
    }


def _normalize_capacities(capacities: list[int]) -> list[int]:
    normalized = sorted(set(int(capacity) for capacity in capacities))
    if not normalized:
        raise ValueError("at least one capacity is required")
    if any(capacity <= 0 for capacity in normalized):
        raise ValueError("capacities must be positive")
    return normalized
