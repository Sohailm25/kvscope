from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from serve.benchmark_tables import (  # noqa: E402
    build_benchmark_tables_report,
    render_benchmark_tables_markdown,
    write_benchmark_tables_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1-report", required=True, help="Path to the Phase 1 summary JSON.")
    parser.add_argument("--live-cache-report", required=True, help="Path to the Phase 3 summary JSON.")
    parser.add_argument("--bridge-report", required=True, help="Path to the bridge summary JSON.")
    parser.add_argument(
        "--report-slug",
        default="benchmark-tables",
        help="Slug to embed in the output artifact names.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_benchmark_tables_report(
        repo_root=REPO_ROOT,
        phase1_report_path=(REPO_ROOT / args.phase1_report).resolve(),
        live_cache_report_path=(REPO_ROOT / args.live_cache_report).resolve(),
        bridge_report_path=(REPO_ROOT / args.bridge_report).resolve(),
        report_slug=args.report_slug,
    )
    markdown = render_benchmark_tables_markdown(report)
    json_path, markdown_path = write_benchmark_tables_report(
        repo_root=REPO_ROOT,
        report=report,
        markdown=markdown,
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
