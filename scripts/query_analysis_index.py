from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.index import default_index_path, search_runs, search_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    runs_parser = subparsers.add_parser("runs")
    runs_parser.add_argument("--family")
    runs_parser.add_argument("--cache-mode", choices=("on", "off"))
    runs_parser.add_argument("--family-claim-class")
    runs_parser.add_argument("--claim-class")
    runs_parser.add_argument("--min-live-prefix-hit-rate", type=float)
    runs_parser.add_argument("--limit", type=int, default=20)

    text_parser = subparsers.add_parser("text")
    text_parser.add_argument("query")
    text_parser.add_argument("--limit", type=int, default=10)
    text_parser.add_argument(
        "--scope",
        choices=("current-evidence", "historical-evidence", "planning", "raw-evidence", "all"),
        default="current-evidence",
    )

    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    index_path = default_index_path(repo_root)

    if args.command == "runs":
        results = search_runs(
            index_path=index_path,
            workload_family=args.family,
            prefix_caching_enabled=None
            if args.cache_mode is None
            else args.cache_mode == "on",
            family_claim_class=args.family_claim_class,
            claim_class=args.claim_class,
            min_live_prefix_hit_rate=args.min_live_prefix_hit_rate,
            limit=args.limit,
        )
    else:
        results = search_text(
            index_path=index_path,
            query=args.query,
            limit=args.limit,
            scope=args.scope,
        )

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
