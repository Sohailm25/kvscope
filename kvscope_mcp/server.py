from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from kvscope_mcp.catalog import Corpus
from kvscope_mcp.models import (
    ArtifactTextResult,
    CapacityCurveResult,
    CompareRunsResult,
    ListFindingsResult,
    ReplaySummaryResult,
    RunManifestResult,
    RunMetricsResult,
    SearchRunsResult,
)


def build_server(*, repo_root: Path) -> FastMCP:
    corpus = Corpus(repo_root=repo_root)
    server = FastMCP(
        "KVScope",
        instructions=(
            "Read-only AI observability corpus over live serving, replay, and claim artifacts. "
            "Prefer structured tool outputs, separate live evidence from replay evidence, and cite exact artifact paths."
        ),
        dependencies=("mcp==1.26.0",),
    )

    @server.tool(
        description="Search structured run records over the frozen KVScope corpus.",
        structured_output=True,
    )
    def search_runs(
        workload_family: str | None = None,
        cache_mode: str | None = None,
        family_claim_class: str | None = None,
        min_live_prefix_hit_rate: float | None = None,
        text_query: str | None = None,
        limit: int = 10,
    ) -> SearchRunsResult:
        return corpus.search_runs(
            workload_family=workload_family,
            cache_mode=cache_mode,
            family_claim_class=family_claim_class,
            min_live_prefix_hit_rate=min_live_prefix_hit_rate,
            text_query=text_query,
            limit=limit,
        )

    @server.tool(
        description="Return the manifest and artifact paths for one run.",
        structured_output=True,
    )
    def get_run_manifest(run_id: str) -> RunManifestResult:
        return corpus.get_run_manifest(run_id=run_id)

    @server.tool(
        description="Return serving and live cache metrics for one run.",
        structured_output=True,
    )
    def get_run_metrics(run_id: str) -> RunMetricsResult:
        return corpus.get_run_metrics(run_id=run_id)

    @server.tool(
        description="Return replay results for one run or one workload family at a chosen capacity.",
        structured_output=True,
    )
    def get_replay_summary(
        workload_family: str | None = None,
        run_id: str | None = None,
        capacity_blocks: int | None = None,
    ) -> ReplaySummaryResult:
        return corpus.get_replay_summary(
            workload_family=workload_family,
            run_id=run_id,
            capacity_blocks=capacity_blocks,
        )

    @server.tool(
        description="Return replay capacity curves for one workload family.",
        structured_output=True,
    )
    def get_capacity_curve(workload_family: str) -> CapacityCurveResult:
        return corpus.get_capacity_curve(workload_family=workload_family)

    @server.tool(
        description="Return a cited delta view between two run sets.",
        structured_output=True,
    )
    def compare_runs(
        left_run_ids: list[str],
        right_run_ids: list[str],
    ) -> CompareRunsResult:
        return corpus.compare_runs(
            left_run_ids=left_run_ids,
            right_run_ids=right_run_ids,
        )

    @server.tool(
        description="List bounded findings with claim class and source paths.",
        structured_output=True,
    )
    def list_findings(
        family: str | None = None,
        claim_class: str | None = None,
        claim_type: str | None = None,
        source_scope: str = "current-evidence",
        limit: int = 10,
    ) -> ListFindingsResult:
        return corpus.list_findings(
            family=family,
            claim_class=claim_class,
            claim_type=claim_type,
            source_scope=source_scope,
            limit=limit,
        )

    @server.tool(
        description="Read bounded text from one allowed artifact path.",
        structured_output=True,
    )
    def read_artifact_text(
        path: str,
        heading_query: str | None = None,
        max_sections: int = 3,
        max_chars: int = 1500,
    ) -> ArtifactTextResult:
        return corpus.read_artifact_text(
            path=path,
            heading_query=heading_query,
            max_sections=max_sections,
            max_chars=max_chars,
        )

    for resource_uri, resource_path in corpus.resource_uri_map().items():
        _register_text_resource(server=server, corpus=corpus, resource_uri=resource_uri, resource_path=resource_path)

    return server


def _register_text_resource(
    *,
    server: FastMCP,
    corpus: Corpus,
    resource_uri: str,
    resource_path: str,
) -> None:
    @server.resource(
        resource_uri,
        name=resource_path,
        description=f"Current KVScope resource for {resource_path}.",
    )
    def _resource() -> str:
        return corpus.resource_text(resource_name=resource_uri)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    build_server(repo_root=repo_root).run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
