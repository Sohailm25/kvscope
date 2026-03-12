# ABOUTME: Validates the first SQLite-backed analysis index for the KVScope investigator layer.
# ABOUTME: These tests ensure the repo can search structured run facts and text-backed findings without manual file scanning.

import tempfile
import unittest
from pathlib import Path

from analysis.core_claims import build_core_v1_claim_manifest
from analysis.index import build_analysis_index, search_runs, search_text


REPO_ROOT = Path(__file__).resolve().parents[1]


class AnalysisIndexTests(unittest.TestCase):
    def test_build_analysis_index_and_query_structured_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "kvscope-analysis.sqlite3"
            claim_manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)

            build_analysis_index(
                repo_root=REPO_ROOT,
                index_path=index_path,
                claim_manifest=claim_manifest,
            )

            results = search_runs(
                index_path=index_path,
                workload_family="locality-return",
                min_live_prefix_hit_rate=0.3,
            )

            self.assertTrue(index_path.exists())
            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0]["workload_family"], "locality-return")
            self.assertEqual(results[0]["family_claim_class"], "repeated")
            self.assertGreaterEqual(results[0]["live_prefix_hit_rate"], 0.3)

    def test_search_text_returns_cited_claims_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "kvscope-analysis.sqlite3"
            claim_manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)

            build_analysis_index(
                repo_root=REPO_ROOT,
                index_path=index_path,
                claim_manifest=claim_manifest,
            )

            results = search_text(
                index_path=index_path,
                query="replay-locality-return-crossover",
                limit=5,
            )

            self.assertGreaterEqual(len(results), 1)
            joined_paths = " ".join(row["path"] for row in results)
            self.assertIn("CORE-V1-CLAIMS.md", joined_paths)

    def test_search_text_defaults_to_current_evidence_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "kvscope-analysis.sqlite3"
            claim_manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)

            build_analysis_index(
                repo_root=REPO_ROOT,
                index_path=index_path,
                claim_manifest=claim_manifest,
            )

            results = search_text(
                index_path=index_path,
                query="cache policy ordering workload geometry capacity crossover",
                limit=5,
            )

            self.assertGreaterEqual(len(results), 1)
            self.assertNotIn(
                "history/INVESTIGATOR-BUILD-SPEC.md",
                {row["path"] for row in results},
            )
            self.assertTrue(
                any(
                    row["path"]
                    in {
                        "docs/kvscope_result_bundle.md",
                        "history/CORE-V1-CLAIMS.md",
                        "history/CLAIMS-AND-NON-CLAIMS.md",
                    }
                    for row in results
                )
            )

    def test_search_text_all_scope_can_return_planning_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "kvscope-analysis.sqlite3"
            claim_manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)

            build_analysis_index(
                repo_root=REPO_ROOT,
                index_path=index_path,
                claim_manifest=claim_manifest,
            )

            results = search_text(
                index_path=index_path,
                query="which workload families show direct live prefix-cache hits",
                limit=10,
                scope="all",
            )

            self.assertGreaterEqual(len(results), 1)
            self.assertIn(
                "history/INVESTIGATOR-BUILD-SPEC.md",
                {row["path"] for row in results},
            )

    def test_search_text_handles_hyphenated_natural_language_queries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "kvscope-analysis.sqlite3"
            claim_manifest = build_core_v1_claim_manifest(repo_root=REPO_ROOT)

            build_analysis_index(
                repo_root=REPO_ROOT,
                index_path=index_path,
                claim_manifest=claim_manifest,
            )

            results = search_text(
                index_path=index_path,
                query="locality-return direct live prefix-cache hits",
                limit=5,
            )

            self.assertGreaterEqual(len(results), 1)
