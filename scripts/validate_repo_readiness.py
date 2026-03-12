# ABOUTME: Command-line entrypoint for implementation-readiness validation.
# ABOUTME: This script is designed for local use, pre-commit hooks, and future automation.

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.shared.repo_readiness import collect_readiness_errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors = collect_readiness_errors(repo_root)

    if errors:
        print("Repository readiness checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository readiness checks passed.")
    print("Validated docs, example fixtures, and contract invariants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
