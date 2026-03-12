# ABOUTME: Validates the frozen Core v1 claim manifest used by the investigator layer.
# ABOUTME: These tests keep the current claim surface explicit and machine-checkable.

import tempfile
import unittest
from pathlib import Path

from analysis.core_claims import (
    build_core_v1_claim_manifest,
    render_core_v1_claim_manifest_markdown,
    write_core_v1_claim_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CoreClaimManifestTests(unittest.TestCase):
    def test_build_core_v1_claim_manifest_captures_claim_classes(self) -> None:
        manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)

        self.assertEqual(manifest["schema_version"], "core-v1-claim-manifest-v1")
        self.assertEqual(manifest["family_claim_classes"]["hotset-scan"], "repeated")
        self.assertEqual(manifest["family_claim_classes"]["locality-shift"], "repeated")
        self.assertEqual(manifest["family_claim_classes"]["locality-return"], "repeated")
        self.assertGreaterEqual(len(manifest["claims"]), 8)

        claim_ids = {claim["claim_id"] for claim in manifest["claims"]}
        claim_classes = {
            claim["claim_id"]: claim["claim_class"] for claim in manifest["claims"]
        }
        self.assertIn("live-cache-locality-return-direct-hit-signal", claim_ids)
        self.assertEqual(claim_classes["replay-hotset-scan-lfu-headroom"], "repeated")
        self.assertIn("replay-locality-return-crossover", claim_ids)
        self.assertEqual(claim_classes["replay-locality-return-crossover"], "repeated")

    def test_render_and_write_core_v1_claim_manifest(self) -> None:
        manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)
        markdown = render_core_v1_claim_manifest_markdown(manifest)

        self.assertIn("# Core v1 Claim Manifest", markdown)
        self.assertIn("`locality-return`", markdown)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            json_path, markdown_path = write_core_v1_claim_manifest(
                repo_root=repo_root,
                manifest=manifest,
                markdown=markdown,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertEqual(json_path.name, "CORE-V1-CLAIMS.json")
            self.assertEqual(markdown_path.name, "CORE-V1-CLAIMS.md")
