# ABOUTME: Builds the first live-to-replay bridge report from explicit KVScope run directories.
# ABOUTME: This script keeps replay evidence packaging reproducible and tied to raw run artifacts.

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kvtrace.bridge_report import (  # noqa: E402
    build_bridge_report,
    render_bridge_markdown,
    write_bridge_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        action="append",
        required=True,
        help="Path to a run directory under artifacts/runs/",
    )
    parser.add_argument(
        "--report-slug",
        default="bridge-baseline",
        help="Slug to embed in the output artifact names.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dirs = [(REPO_ROOT / run_dir).resolve() for run_dir in args.run_dir]

    report = build_bridge_report(
        repo_root=REPO_ROOT,
        run_dirs=run_dirs,
        report_slug=args.report_slug,
    )
    markdown = render_bridge_markdown(report)
    json_path, markdown_path = write_bridge_report(
        repo_root=REPO_ROOT,
        report=report,
        markdown=markdown,
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
