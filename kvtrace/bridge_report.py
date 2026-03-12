# ABOUTME: Builds the first live-to-replay bridge report for KVScope.
# ABOUTME: The bridge report compares live workload families to offline replay without claiming causal equivalence.

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
class ReplayRunSlice:
    run_id: str
    workload_family: str
    manifest_path: str
    results_path: str
    kvtrace_path: str
    live_ttft_p50_ms: float
    capacity_blocks: int
    policies: dict[str, dict[str, float | int | str]]


def build_bridge_report(
    *,
    repo_root: Path,
    run_dirs: list[Path],
    report_slug: str,
) -> dict[str, Any]:
    run_slices = [
        _load_run_slice(repo_root=repo_root, run_dir=run_dir)
        for run_dir in sorted(run_dirs)
    ]
    families = _group_by_family(run_slices)

    return {
        "schema_version": "kvtrace-bridge-report-v1",
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


def render_bridge_markdown(report: dict[str, Any]) -> str:
    lines = [
        "ABOUTME: Reviewer-facing bridge between live serving artifacts and offline kvtrace replay.",
        "ABOUTME: This report compares directional stories and keeps replay narrower than live claims.",
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
                f"- Mean live TTFT p50: `{summary['live_ttft_p50_ms']['mean']}` ms",
            ]
        )
        for policy_name, policy_summary in sorted(summary["policies"].items()):
            lines.append(
                f"- `{policy_name}` replay hit rate mean: `{policy_summary['hit_rate_mean']}`"
            )
        lines.append("- Referenced runs:")
        for run in summary["runs"]:
            lines.append(
                f"  - `{run['run_id']}` via `{run['manifest_path']}` and `{run['kvtrace_path']}`"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_bridge_report(
    *,
    repo_root: Path,
    report: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}__kvtrace__bridge__{report['report_slug']}"
    output_dir = repo_root / "artifacts" / "manifests"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{base_name}.json"
    markdown_path = output_dir / f"{base_name}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(markdown)
    return json_path, markdown_path


def _load_run_slice(*, repo_root: Path, run_dir: Path) -> ReplayRunSlice:
    manifest_path = run_dir / "manifest.json"
    results_path = run_dir / "results.json"
    kvtrace_path = run_dir / "kvtrace.ndjson"

    manifest = json.loads(manifest_path.read_text())
    results = json.loads(results_path.read_text())
    capacity_blocks = infer_capacity_blocks_from_command(manifest["command"])
    lookup_keys = load_block_lookup_keys(kvtrace_path)

    return ReplayRunSlice(
        run_id=manifest["run_id"],
        workload_family=manifest["workload_family"],
        manifest_path=str(manifest_path.relative_to(repo_root)),
        results_path=str(results_path.relative_to(repo_root)),
        kvtrace_path=str(kvtrace_path.relative_to(repo_root)),
        live_ttft_p50_ms=float(results["ttft_ms"]["p50"]),
        capacity_blocks=capacity_blocks,
        policies={
            policy_name: replay_block_sequence(
                policy_name=policy_name,
                capacity_blocks=capacity_blocks,
                block_keys=lookup_keys,
            )
            for policy_name in ("fifo", "lru", "lfu")
        },
    )


def _group_by_family(run_slices: list[ReplayRunSlice]) -> dict[str, list[ReplayRunSlice]]:
    grouped: dict[str, list[ReplayRunSlice]] = {}
    for run_slice in run_slices:
        grouped.setdefault(run_slice.workload_family, []).append(run_slice)
    return grouped


def _summarize_family(run_slices: list[ReplayRunSlice]) -> dict[str, Any]:
    policy_names = sorted(run_slices[0].policies)
    return {
        "run_count": len(run_slices),
        "live_ttft_p50_ms": _metric_summary([run.live_ttft_p50_ms for run in run_slices]),
        "policies": {
            policy_name: {
                "hits_total": sum(int(run.policies[policy_name]["hits"]) for run in run_slices),
                "misses_total": sum(
                    int(run.policies[policy_name]["misses"]) for run in run_slices
                ),
                "hit_rate_mean": round(
                    fmean(float(run.policies[policy_name]["hit_rate"]) for run in run_slices),
                    3,
                ),
            }
            for policy_name in policy_names
        },
        "runs": [asdict(run) for run in run_slices],
    }


def _metric_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(fmean(values), 3),
    }


def _build_findings(families: dict[str, list[ReplayRunSlice]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    aligned_runs = families.get("aligned-prefix", [])
    near_aligned_runs = families.get("near-aligned-prefix", [])
    control_runs = families.get("no-overlap-control", [])

    if aligned_runs and control_runs:
        aligned_hit_rate = _mean_policy_hit_rate(aligned_runs, "lru")
        control_hit_rate = _mean_policy_hit_rate(control_runs, "lru")
        if aligned_hit_rate > control_hit_rate:
            findings.append(
                {
                    "kind": "directional-live-to-replay-alignment",
                    "message": (
                        "The aligned-prefix family shows both stronger live behavior "
                        "and a better LRU replay hit rate than the no-overlap control."
                    ),
                    "evidence": {
                        "aligned_live_ttft_p50_mean_ms": round(
                            fmean(run.live_ttft_p50_ms for run in aligned_runs), 3
                        ),
                        "control_live_ttft_p50_mean_ms": round(
                            fmean(run.live_ttft_p50_ms for run in control_runs), 3
                        ),
                        "aligned_lru_hit_rate_mean": aligned_hit_rate,
                        "control_lru_hit_rate_mean": control_hit_rate,
                    },
                }
            )

    if aligned_runs and near_aligned_runs and control_runs:
        aligned_hit_rate = _mean_policy_hit_rate(aligned_runs, "lru")
        near_hit_rate = _mean_policy_hit_rate(near_aligned_runs, "lru")
        control_hit_rate = _mean_policy_hit_rate(control_runs, "lru")
        if control_hit_rate < near_hit_rate < aligned_hit_rate:
            findings.append(
                {
                    "kind": "replay-near-aligned-intermediate-case",
                    "message": (
                        "Replay preserves the same intermediate ordering for the "
                        "near-aligned family that the live slice shows qualitatively."
                    ),
                    "evidence": {
                        "aligned_lru_hit_rate_mean": aligned_hit_rate,
                        "near_aligned_lru_hit_rate_mean": near_hit_rate,
                        "control_lru_hit_rate_mean": control_hit_rate,
                    },
                }
            )

    for workload_family, run_slices in sorted(families.items()):
        fifo_hit_rate = _mean_policy_hit_rate(run_slices, "fifo")
        lru_hit_rate = _mean_policy_hit_rate(run_slices, "lru")
        lfu_hit_rate = _mean_policy_hit_rate(run_slices, "lfu")
        if lru_hit_rate > fifo_hit_rate:
            findings.append(
                {
                    "kind": "replay-policy-divergence",
                    "message": (
                        f"For `{workload_family}`, the replay trace separates `lru` from "
                        "`fifo` under the configured cache capacity."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "fifo_hit_rate_mean": fifo_hit_rate,
                        "lru_hit_rate_mean": lru_hit_rate,
                    },
                }
            )
        if lfu_hit_rate > lru_hit_rate:
            findings.append(
                {
                    "kind": "replay-policy-headroom",
                    "message": (
                        f"For `{workload_family}`, the replay trace leaves headroom above "
                        "`lru` under an `lfu` policy."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "lru_hit_rate_mean": lru_hit_rate,
                        "lfu_hit_rate_mean": lfu_hit_rate,
                    },
                }
            )
        if lru_hit_rate > lfu_hit_rate:
            findings.append(
                {
                    "kind": "replay-policy-adaptation",
                    "message": (
                        f"For `{workload_family}`, the replay trace shows `lru` adapting "
                        "better than `lfu` once locality shifts."
                    ),
                    "evidence": {
                        "workload_family": workload_family,
                        "lru_hit_rate_mean": lru_hit_rate,
                        "lfu_hit_rate_mean": lfu_hit_rate,
                    },
                }
            )

    return findings


def _mean_policy_hit_rate(run_slices: list[ReplayRunSlice], policy_name: str) -> float:
    return round(
        fmean(float(run.policies[policy_name]["hit_rate"]) for run in run_slices),
        3,
    )
