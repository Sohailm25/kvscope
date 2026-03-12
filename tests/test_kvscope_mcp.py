# ABOUTME: Validates the first local-only MCP server for KVScope.
# ABOUTME: These tests keep the MCP slice grounded in the frozen current-evidence corpus and structured tool outputs.

import unittest
from pathlib import Path

from kvscope_mcp.server import build_server


REPO_ROOT = Path(__file__).resolve().parents[1]


class KVScopeMCPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.server = build_server(repo_root=REPO_ROOT)

    async def test_server_lists_expected_tools(self) -> None:
        tools = await self.server.list_tools()
        tool_names = {tool.name for tool in tools}

        self.assertEqual(
            tool_names,
            {
                "search_runs",
                "get_run_manifest",
                "get_run_metrics",
                "get_replay_summary",
                "get_capacity_curve",
                "compare_runs",
                "list_findings",
                "read_artifact_text",
            },
        )

    async def test_search_runs_returns_family_claim_class(self) -> None:
        _, structured = await self.server.call_tool(
            "search_runs",
            {
                "workload_family": "locality-return",
                "min_live_prefix_hit_rate": 0.3,
                "limit": 2,
            },
        )

        self.assertGreaterEqual(len(structured["runs"]), 1)
        self.assertEqual(structured["runs"][0]["workload_family"], "locality-return")
        self.assertEqual(structured["runs"][0]["family_claim_class"], "repeated")

    async def test_get_run_manifest_returns_artifact_paths(self) -> None:
        _, structured = await self.server.call_tool(
            "get_run_manifest",
            {"run_id": "20260311-181625__serve__locality-return__smoke-locality-return-clean"},
        )

        self.assertEqual(
            structured["manifest"]["run_id"],
            "20260311-181625__serve__locality-return__smoke-locality-return-clean",
        )
        self.assertTrue(structured["artifact_paths"]["results_path"].endswith("results.json"))

    async def test_get_run_metrics_returns_live_cache_metrics(self) -> None:
        _, structured = await self.server.call_tool(
            "get_run_metrics",
            {"run_id": "20260311-181625__serve__locality-return__smoke-locality-return-clean"},
        )

        self.assertEqual(structured["workload_family"], "locality-return")
        self.assertGreater(structured["metrics"]["live_prefix_hit_rate"], 0.0)
        self.assertIn("delta", structured["live_metrics"])

    async def test_list_findings_defaults_to_current_evidence(self) -> None:
        _, structured = await self.server.call_tool(
            "list_findings",
            {
                "family": "locality-return",
                "limit": 5,
            },
        )

        self.assertGreaterEqual(len(structured["findings"]), 1)
        self.assertNotIn(
            "history/INVESTIGATOR-BUILD-SPEC.md",
            {finding["source_path"] for finding in structured["findings"]},
        )

    async def test_get_replay_summary_supports_family_capacity_queries(self) -> None:
        _, structured = await self.server.call_tool(
            "get_replay_summary",
            {
                "workload_family": "locality-return",
                "capacity_blocks": 4,
            },
        )

        self.assertEqual(structured["mode"], "family-capacity")
        self.assertEqual(structured["workload_family"], "locality-return")
        self.assertEqual(structured["capacity_blocks"], 4)
        self.assertGreater(
            structured["policies"]["lfu"]["hit_rate_mean"],
            structured["policies"]["lru"]["hit_rate_mean"],
        )

    async def test_get_capacity_curve_returns_multiple_capacities(self) -> None:
        _, structured = await self.server.call_tool(
            "get_capacity_curve",
            {"workload_family": "locality-return"},
        )

        capacities = [row["capacity_blocks"] for row in structured["capacities"]]
        self.assertIn(2, capacities)
        self.assertIn(4, capacities)

    async def test_compare_runs_returns_metric_deltas(self) -> None:
        _, structured = await self.server.call_tool(
            "compare_runs",
            {
                "left_run_ids": [
                    "20260311-181625__serve__locality-return__smoke-locality-return-clean"
                ],
                "right_run_ids": [
                    "20260311-181906__serve__locality-return__smoke-locality-return-cache-off-clean"
                ],
            },
        )

        self.assertGreater(structured["left_metrics"]["live_prefix_hit_rate"], 0.0)
        self.assertIsNone(structured["right_metrics"]["live_prefix_hit_rate"])
        self.assertIsNone(structured["metric_deltas"]["live_prefix_hit_rate"])

    async def test_read_artifact_text_returns_bounded_sections(self) -> None:
        _, structured = await self.server.call_tool(
            "read_artifact_text",
            {
                "path": "docs/kvscope_result_bundle.md",
                "max_sections": 1,
                "max_chars": 400,
            },
        )

        self.assertEqual(structured["path"], "docs/kvscope_result_bundle.md")
        self.assertEqual(len(structured["sections"]), 1)
        self.assertLessEqual(len(structured["sections"][0]["text"]), 400)

    async def test_server_exposes_current_resources(self) -> None:
        resources = await self.server.list_resources()
        resource_uris = {str(resource.uri) for resource in resources}

        self.assertIn("kvscope://result-bundle/current", resource_uris)
        self.assertIn("kvscope://benchmark-tables/current", resource_uris)

        contents = await self.server.read_resource("kvscope://result-bundle/current")
        self.assertGreaterEqual(len(contents), 1)
        self.assertIn("The Headline Finding", contents[0].content)
