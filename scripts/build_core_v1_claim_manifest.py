from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.core_claims import (
    build_core_v1_claim_manifest,
    render_core_v1_claim_manifest_markdown,
    write_core_v1_claim_manifest,
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_core_v1_claim_manifest(repo_root=repo_root)
    markdown = render_core_v1_claim_manifest_markdown(manifest)
    json_path, markdown_path = write_core_v1_claim_manifest(
        repo_root=repo_root,
        manifest=manifest,
        markdown=markdown,
    )
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
