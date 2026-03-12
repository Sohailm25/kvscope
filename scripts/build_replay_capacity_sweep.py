from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kvtrace.capacity_sweep import (  # noqa: E402
    build_replay_capacity_sweep_report,
    render_replay_capacity_sweep_markdown,
    write_replay_capacity_sweep_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        action="append",
        required=True,
        help="Path to a run directory under artifacts/runs/.",
    )
    parser.add_argument(
        "--capacity",
        action="append",
        type=int,
        help="Replay capacity to include. Defaults to 1 through 6.",
    )
    parser.add_argument(
        "--report-slug",
        default="replay-capacity-sweep",
        help="Slug to embed in the output artifact names.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dirs = [(REPO_ROOT / run_dir).resolve() for run_dir in args.run_dir]
    capacities = args.capacity or [1, 2, 3, 4, 5, 6]

    report = build_replay_capacity_sweep_report(
        repo_root=REPO_ROOT,
        run_dirs=run_dirs,
        capacities=capacities,
        report_slug=args.report_slug,
    )
    markdown = render_replay_capacity_sweep_markdown(report)
    json_path, markdown_path = write_replay_capacity_sweep_report(
        repo_root=REPO_ROOT,
        report=report,
        markdown=markdown,
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
