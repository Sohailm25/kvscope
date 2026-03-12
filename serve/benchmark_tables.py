from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_FAMILY_ORDER = {
    "aligned-prefix": 0,
    "near-aligned-prefix": 1,
    "mixed-long-short": 2,
    "bursty-arrivals": 3,
    "no-overlap-control": 4,
    "eviction-ordering": 5,
    "hotset-scan": 6,
    "locality-shift": 7,
    "locality-return": 8,
}


def build_benchmark_tables_report(
    *,
    repo_root: Path,
    phase1_report_path: Path,
    live_cache_report_path: Path,
    bridge_report_path: Path,
    report_slug: str,
) -> dict[str, Any]:
    phase1_report = json.loads(phase1_report_path.read_text())
    live_cache_report = json.loads(live_cache_report_path.read_text())
    bridge_report = json.loads(bridge_report_path.read_text())

    return {
        "schema_version": "benchmark-tables-v1",
        "report_slug": report_slug,
        "created_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "source_reports": {
            "phase1": str(phase1_report_path.relative_to(repo_root)),
            "live_cache": str(live_cache_report_path.relative_to(repo_root)),
            "bridge": str(bridge_report_path.relative_to(repo_root)),
        },
        "tables": {
            "serving_workloads": _build_serving_table(phase1_report),
            "live_cache": _build_live_cache_table(live_cache_report),
            "replay_policies": _build_replay_table(bridge_report),
        },
        "notes": [
            "These tables summarize the current artifact set and are strongest on qualitative ordering, direct cache-hit visibility, and replay-policy separation.",
            "They do not justify stable latency-envelope claims where repeated TTFT spread remains large.",
        ],
    }


def render_benchmark_tables_markdown(report: dict[str, Any]) -> str:
    lines = [
        "",
        f"# {report['report_slug']}",
        "",
        f"- Created: `{report['created_at_utc']}`",
        f"- Phase 1 source: `{report['source_reports']['phase1']}`",
        f"- Phase 3 source: `{report['source_reports']['live_cache']}`",
        f"- Replay source: `{report['source_reports']['bridge']}`",
        "",
        "## Serving Workloads",
        "",
        "| Family | Runs | TTFT p50 mean (ms) | TTFT p50 range (ms) | Block hits | Note |",
        "| --- | ---: | ---: | --- | ---: | --- |",
    ]

    for row in report["tables"]["serving_workloads"]:
        lines.append(
            "| {workload_family} | {run_count} | {ttft_p50_mean_ms} | {ttft_p50_min_ms}-{ttft_p50_max_ms} | {block_hit_count_total} | {note} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Live Cache",
            "",
            "| Family | On runs | Off runs | On hit rate | Off hit rate | On prefill mean (ms) | Off prefill mean (ms) | Note |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in report["tables"]["live_cache"]:
        lines.append(
            "| {workload_family} | {cache_on_run_count} | {cache_off_run_count} | {cache_on_hit_rate_mean} | {cache_off_hit_rate_mean} | {cache_on_prefill_mean_ms} | {cache_off_prefill_mean_ms} | {note} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Replay Policies",
            "",
            "| Family | Runs | FIFO hit rate | LRU hit rate | LFU hit rate | FIFO hits | LRU hits | LFU hits | Note |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in report["tables"]["replay_policies"]:
        lines.append(
            "| {workload_family} | {run_count} | {fifo_hit_rate_mean} | {lru_hit_rate_mean} | {lfu_hit_rate_mean} | {fifo_hits_total} | {lru_hits_total} | {lfu_hits_total} | {note} |".format(
                **row
            )
        )

    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


def write_benchmark_tables_report(
    *,
    repo_root: Path,
    report: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}__serve__phase6__{report['report_slug']}"
    output_dir = repo_root / "artifacts" / "manifests"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{base_name}.json"
    markdown_path = output_dir / f"{base_name}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(markdown)
    return json_path, markdown_path


def _build_serving_table(phase1_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for workload_family, summary in _sorted_items(phase1_report["families"]):
        ttft = summary["ttft_p50_ms"]
        rows.append(
            {
                "workload_family": workload_family,
                "run_count": int(summary["run_count"]),
                "ttft_p50_mean_ms": _round(ttft["mean"]),
                "ttft_p50_min_ms": _round(ttft["min"]),
                "ttft_p50_max_ms": _round(ttft["max"]),
                "block_hit_count_total": int(summary["block_hit_count_total"]),
                "note": _serving_note(workload_family),
            }
        )
    return rows


def _build_live_cache_table(live_cache_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for workload_family, summary in _sorted_items(live_cache_report["families"]):
        cache_on = summary["cache_on"]
        cache_off = summary["cache_off"]
        cache_on_ttft = _round(cache_on["ttft_p50_ms"]["mean"])
        cache_off_ttft = _round(cache_off["ttft_p50_ms"]["mean"])
        cache_on_prefill = _round(cache_on["request_prefill_mean_ms"]["mean"])
        cache_off_prefill = _round(cache_off["request_prefill_mean_ms"]["mean"])
        rows.append(
            {
                "workload_family": workload_family,
                "cache_on_run_count": int(cache_on["run_count"]),
                "cache_off_run_count": int(cache_off["run_count"]),
                "cache_on_hit_rate_mean": _round(cache_on["prefix_cache_hit_rate"]["mean"]),
                "cache_off_hit_rate_mean": _round(cache_off["prefix_cache_hit_rate"]["mean"]),
                "cache_on_prefill_mean_ms": cache_on_prefill,
                "cache_off_prefill_mean_ms": cache_off_prefill,
                "note": _live_cache_note(
                    cache_on_ttft_mean=cache_on_ttft,
                    cache_off_ttft_mean=cache_off_ttft,
                    cache_on_ttft_max=_round(cache_on["ttft_p50_ms"]["max"]),
                    cache_off_ttft_min=_round(cache_off["ttft_p50_ms"]["min"]),
                    cache_on_prefill=cache_on_prefill,
                    cache_off_prefill=cache_off_prefill,
                ),
            }
        )
    return rows


def _build_replay_table(bridge_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for workload_family, summary in _sorted_items(bridge_report["families"]):
        fifo = summary["policies"]["fifo"]
        lfu = summary["policies"].get("lfu", summary["policies"]["lru"])
        lru = summary["policies"]["lru"]
        rows.append(
            {
                "workload_family": workload_family,
                "run_count": int(summary["run_count"]),
                "fifo_hit_rate_mean": _round(fifo["hit_rate_mean"]),
                "lru_hit_rate_mean": _round(lru["hit_rate_mean"]),
                "lfu_hit_rate_mean": _round(lfu["hit_rate_mean"]),
                "fifo_hits_total": int(fifo["hits_total"]),
                "lru_hits_total": int(lru["hits_total"]),
                "lfu_hits_total": int(lfu["hits_total"]),
                "note": _replay_note(
                    workload_family=workload_family,
                    fifo_hit_rate=_round(fifo["hit_rate_mean"]),
                    lru_hit_rate=_round(lru["hit_rate_mean"]),
                    lfu_hit_rate=_round(lfu["hit_rate_mean"]),
                ),
            }
        )
    return rows


def _sorted_items(values: dict[str, Any]) -> list[tuple[str, Any]]:
    return sorted(values.items(), key=lambda item: (_FAMILY_ORDER.get(item[0], 999), item[0]))


def _serving_note(workload_family: str) -> str:
    notes = {
        "aligned-prefix": "positive reuse case",
        "near-aligned-prefix": "intermediate boundary-miss case",
        "mixed-long-short": "overlap and interference case",
        "bursty-arrivals": "reuse under burst pressure",
        "no-overlap-control": "negative control",
        "eviction-ordering": "policy-sensitive reuse case",
        "locality-return": "returning-locality crossover case",
    }
    return notes.get(workload_family, "current family summary")


def _live_cache_note(
    *,
    cache_on_ttft_mean: float,
    cache_off_ttft_mean: float,
    cache_on_ttft_max: float,
    cache_off_ttft_min: float,
    cache_on_prefill: float,
    cache_off_prefill: float,
) -> str:
    if (
        cache_on_prefill < cache_off_prefill
        and cache_on_ttft_mean < cache_off_ttft_mean
        and cache_on_ttft_max < cache_off_ttft_min
    ):
        return "Measured live cache hits with lower prefill and lower cache-on TTFT."
    if cache_on_prefill < cache_off_prefill:
        return "Measured live cache hits with lower prefill, but client-observed TTFT remained noisy."
    return "Measured live cache hits without a cleaner client-side latency story yet."


def _replay_note(
    *,
    workload_family: str,
    fifo_hit_rate: float,
    lru_hit_rate: float,
    lfu_hit_rate: float,
) -> str:
    if lfu_hit_rate > lru_hit_rate > fifo_hit_rate:
        return "Live-derived replay trace separates fifo from lru and leaves headroom above lru."
    if lfu_hit_rate > lru_hit_rate:
        return "Live-derived replay trace leaves headroom above lru."
    if lru_hit_rate > lfu_hit_rate:
        return "Live-derived replay trace shows recency beating stale frequency after locality shifts."
    if lru_hit_rate > fifo_hit_rate:
        return "Repeated live-derived trace separates lru from fifo."
    if lru_hit_rate > 0:
        return "Directional bridge only; current trace does not separate policies."
    if workload_family == "no-overlap-control":
        return "Negative control in replay."
    return "Current replay trace shows no policy separation."


def _round(value: float) -> float:
    return round(float(value), 3)
