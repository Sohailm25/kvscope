from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kvscope_mcp.server import build_server


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    build_server(repo_root=repo_root).run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
