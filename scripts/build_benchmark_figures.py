# ABOUTME: Builds a small reviewer-facing PNG figure bundle from existing KVScope summary reports.
# ABOUTME: This keeps figures reproducible and tied to report JSONs instead of becoming manual screenshots.

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from serve.benchmark_figures import (  # noqa: E402
    build_benchmark_figures_report,
    render_benchmark_figures_markdown,
    write_benchmark_figures_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-cache-report", required=True, help="Path to the Phase 3 summary JSON.")
    parser.add_argument(
        "--capacity-sweep-report",
        required=True,
        help="Path to the replay capacity-sweep summary JSON.",
    )
    parser.add_argument(
        "--report-slug",
        default="benchmark-figures",
        help="Slug to embed in the output artifact names.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_benchmark_figures_report(
        repo_root=REPO_ROOT,
        live_cache_report_path=(REPO_ROOT / args.live_cache_report).resolve(),
        capacity_sweep_report_path=(REPO_ROOT / args.capacity_sweep_report).resolve(),
        report_slug=args.report_slug,
    )
    markdown = render_benchmark_figures_markdown(report)
    json_path, markdown_path, figure_paths = write_benchmark_figures_report(
        repo_root=REPO_ROOT,
        report=report,
        markdown=markdown,
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    for figure_path in figure_paths:
        print(f"Figure: {figure_path}")


if __name__ == "__main__":
    main()
