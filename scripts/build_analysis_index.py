from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.core_claims import build_core_v1_claim_manifest
from analysis.index import build_analysis_index, default_index_path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    claim_manifest = build_core_v1_claim_manifest(repo_root=repo_root)
    index_path = build_analysis_index(
        repo_root=repo_root,
        index_path=default_index_path(repo_root),
        claim_manifest=claim_manifest,
    )
    print(index_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
