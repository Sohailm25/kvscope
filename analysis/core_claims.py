# ABOUTME: Frozen Core v1 claim registry for the current KVScope evidence surface.
# ABOUTME: This keeps the current outward-facing claims explicit, classified, and tied to source artifacts.

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_FAMILY_CLAIM_CLASSES = {
    "aligned-prefix": "repeated",
    "near-aligned-prefix": "repeated",
    "mixed-long-short": "repeated",
    "bursty-arrivals": "repeated",
    "no-overlap-control": "repeated",
    "eviction-ordering": "repeated",
    "hotset-scan": "repeated",
    "locality-shift": "repeated",
    "locality-return": "repeated",
}

_SOURCE_REPORTS = {
    "phase1": "artifacts/manifests/20260311-182034__serve__phase1__phase1-policy-surface-expanded.json",
    "phase3": "artifacts/manifests/20260311-200918__serve__phase3__live-cache-toggle-policy-surface-core-v1-refresh.json",
    "bridge": "artifacts/manifests/20260311-221444__kvtrace__bridge__bridge-policy-surface-core-v1-complete.json",
    "sweep": "artifacts/manifests/20260311-221459__kvtrace__sweep__replay-capacity-sweep-policy-surface-core-v1-complete.json",
    "tables": "artifacts/manifests/20260311-221503__serve__phase6__benchmark-tables-policy-surface-core-v1-complete.json",
    "figures": "artifacts/manifests/20260311-221511__serve__phase6__benchmark-figures-policy-surface-core-v1-complete.json",
    "bundle": "docs/kvscope_result_bundle.md",
}

_CLAIMS = [
    {
        "claim_id": "serving-aligned-prefix-reuse-signal",
        "claim_type": "measured",
        "claim_class": "repeated",
        "families": ["aligned-prefix"],
        "summary": "Aligned-prefix repeatedly shows derived reuse on the shared blocks and remains the clean positive-case family.",
        "source_paths": [
            _SOURCE_REPORTS["phase1"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "serving-near-aligned-intermediate-case",
        "claim_type": "measured",
        "claim_class": "repeated",
        "families": ["near-aligned-prefix"],
        "summary": "Near-aligned-prefix remains the repeated intermediate case between aligned reuse and the no-overlap control.",
        "source_paths": [
            _SOURCE_REPORTS["phase1"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "serving-no-overlap-negative-control",
        "claim_type": "measured",
        "claim_class": "repeated",
        "families": ["no-overlap-control"],
        "summary": "The no-overlap control remains flat at zero derived reuse and anchors the negative-control story.",
        "source_paths": [
            _SOURCE_REPORTS["phase1"],
            _SOURCE_REPORTS["sweep"],
        ],
    },
    {
        "claim_id": "live-cache-eviction-ordering-direct-hit-signal",
        "claim_type": "measured",
        "claim_class": "repeated",
        "families": ["eviction-ordering"],
        "summary": "Eviction-ordering repeatedly shows direct live prefix-cache hits in cache-on runs and none in the cache-off control.",
        "source_paths": [
            _SOURCE_REPORTS["phase3"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "live-cache-locality-shift-direct-hit-signal",
        "claim_type": "measured",
        "claim_class": "repeated",
        "families": ["locality-shift"],
        "summary": "Locality-shift repeatedly shows direct live cache-hit evidence even though the client-side latency story remains noisy.",
        "source_paths": [
            _SOURCE_REPORTS["phase3"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "live-cache-locality-return-direct-hit-signal",
        "claim_type": "measured",
        "claim_class": "repeated",
        "families": ["locality-return"],
        "summary": "Locality-return now repeatedly shows direct live prefix-cache hits and lower measured prefill than cache-off, but the client-side TTFT story remains mixed across the two observed pairs.",
        "source_paths": [
            _SOURCE_REPORTS["phase3"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "replay-eviction-ordering-lru-beats-fifo",
        "claim_type": "replay",
        "claim_class": "repeated",
        "families": ["eviction-ordering"],
        "summary": "Eviction-ordering repeatedly separates `lru` from `fifo` on live-derived replay traces at the native capacity.",
        "source_paths": [
            _SOURCE_REPORTS["bridge"],
            _SOURCE_REPORTS["sweep"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "replay-hotset-scan-lfu-headroom",
        "claim_type": "replay",
        "claim_class": "repeated",
        "families": ["hotset-scan"],
        "summary": "Hotset-scan now repeatedly shows `lfu > lru > fifo` replay headroom across the baseline and revisit workload geometries.",
        "source_paths": [
            _SOURCE_REPORTS["bridge"],
            _SOURCE_REPORTS["sweep"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "replay-locality-shift-recency-advantage",
        "claim_type": "replay",
        "claim_class": "repeated",
        "families": ["locality-shift"],
        "summary": "Locality-shift repeatedly shows a recency advantage where `lru` beats `lfu` on live-derived replay traces.",
        "source_paths": [
            _SOURCE_REPORTS["bridge"],
            _SOURCE_REPORTS["sweep"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
    {
        "claim_id": "replay-locality-return-crossover",
        "claim_type": "replay",
        "claim_class": "repeated",
        "families": ["locality-return"],
        "summary": "Locality-return now repeatedly shows a replay policy crossover: `lru` leads at lower capacities, then `lfu` gains headroom at a higher capacity across the baseline and concentrated geometries.",
        "source_paths": [
            _SOURCE_REPORTS["bridge"],
            _SOURCE_REPORTS["sweep"],
            _SOURCE_REPORTS["bundle"],
        ],
    },
]


def build_core_v1_claim_manifest(*, repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": "core-v1-claim-manifest-v1",
        "created_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "title": "Core v1 Claim Manifest",
        "family_claim_classes": dict(_FAMILY_CLAIM_CLASSES),
        "source_reports": {
            key: _require_relative_path(repo_root, relative_path)
            for key, relative_path in _SOURCE_REPORTS.items()
        },
        "claims": [
            {
                **claim,
                "source_paths": [
                    _require_relative_path(repo_root, relative_path)
                    for relative_path in claim["source_paths"]
                ],
            }
            for claim in _CLAIMS
        ],
    }


def render_core_v1_claim_manifest_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "ABOUTME: Frozen Core v1 claim surface for the current KVScope evidence set.",
        "ABOUTME: This file classifies which current claims are repeated, single-run, or exploratory before the investigator layer grows.",
        "",
        "# Core v1 Claim Manifest",
        "",
        f"- Created: `{manifest['created_at_utc']}`",
        "",
        "## Family Claim Classes",
        "",
        "| Family | Claim Class |",
        "| --- | --- |",
    ]

    for family, claim_class in sorted(manifest["family_claim_classes"].items()):
        lines.append(f"| `{family}` | `{claim_class}` |")

    lines.extend(["", "## Claims", ""])

    for claim in manifest["claims"]:
        family_list = ", ".join(f"`{family}`" for family in claim["families"])
        lines.extend(
            [
                f"### `{claim['claim_id']}`",
                "",
                f"- Claim type: `{claim['claim_type']}`",
                f"- Claim class: `{claim['claim_class']}`",
                f"- Families: {family_list}",
                f"- Summary: {claim['summary']}",
                "- Sources:",
            ]
        )
        for source_path in claim["source_paths"]:
            lines.append(f"  - `{source_path}`")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_core_v1_claim_manifest(
    *,
    repo_root: Path,
    manifest: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path]:
    output_dir = repo_root / "history"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "CORE-V1-CLAIMS.json"
    markdown_path = output_dir / "CORE-V1-CLAIMS.md"
    json_path.write_text(json.dumps(manifest, indent=2) + "\n")
    markdown_path.write_text(markdown)
    return json_path, markdown_path


def _require_relative_path(repo_root: Path, relative_path: str) -> str:
    full_path = repo_root / relative_path
    if not full_path.exists():
        raise FileNotFoundError(f"missing source artifact for core claim manifest: {relative_path}")
    return relative_path
