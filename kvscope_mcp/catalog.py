from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from analysis.core_claims import build_core_v1_claim_manifest
from analysis.index import default_index_path, search_runs as index_search_runs, search_text

from kvscope_mcp.models import (
    ArtifactSection,
    ArtifactTextResult,
    CapacityCurveResult,
    CompareRunsResult,
    FindingRecord,
    ListFindingsResult,
    ReplaySummaryResult,
    RunManifestResult,
    RunMetricsResult,
    RunSummary,
    SearchRunsResult,
)


class Corpus:
    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.index_path = default_index_path(repo_root)
        if not self.index_path.exists():
            raise FileNotFoundError(
                "analysis index is missing; build artifacts/analysis/kvscope-analysis.sqlite3 first"
            )
        self.claim_manifest = build_core_v1_claim_manifest(repo_root=repo_root)
        self.source_reports = self.claim_manifest["source_reports"]
        self.logger = logging.getLogger("kvscope_mcp")

    def search_runs(
        self,
        *,
        workload_family: str | None = None,
        cache_mode: str | None = None,
        family_claim_class: str | None = None,
        min_live_prefix_hit_rate: float | None = None,
        text_query: str | None = None,
        limit: int = 10,
    ) -> SearchRunsResult:
        matched_source_paths: list[str] = []
        if text_query:
            matched_source_paths = [
                row["path"]
                for row in search_text(
                    index_path=self.index_path,
                    query=text_query,
                    limit=max(limit, 10),
                )
            ]

        rows = index_search_runs(
            index_path=self.index_path,
            workload_family=workload_family,
            prefix_caching_enabled=None if cache_mode is None else cache_mode == "on",
            family_claim_class=family_claim_class,
            min_live_prefix_hit_rate=min_live_prefix_hit_rate,
            limit=limit,
        )

        result = SearchRunsResult(
            applied_filters={
                "workload_family": workload_family,
                "cache_mode": cache_mode,
                "family_claim_class": family_claim_class,
                "min_live_prefix_hit_rate": min_live_prefix_hit_rate,
                "text_query": text_query,
                "limit": limit,
            },
            matched_source_paths=matched_source_paths,
            runs=[RunSummary.model_validate(row) for row in rows],
        )
        self._log_tool_call(
            tool_name="search_runs",
            parameters=result.applied_filters,
            source_paths=matched_source_paths
            + [run.manifest_path for run in result.runs]
            + [run.results_path for run in result.runs],
        )
        return result

    def get_run_manifest(self, *, run_id: str) -> RunManifestResult:
        row = self._run_row(run_id)
        manifest = self._load_json(row["manifest_path"])
        result = RunManifestResult(
            run_id=run_id,
            workload_family=row["workload_family"],
            prefix_caching_enabled=bool(row["prefix_caching_enabled"]),
            family_claim_class=row["family_claim_class"],
            manifest=manifest,
            artifact_paths={
                "manifest_path": row["manifest_path"],
                "results_path": row["results_path"],
                "live_metrics_path": row["live_metrics_path"],
                "kvtrace_path": row["kvtrace_path"],
            },
        )
        self._log_tool_call(
            tool_name="get_run_manifest",
            parameters={"run_id": run_id},
            source_paths=[path for path in result.artifact_paths.values() if path is not None],
        )
        return result

    def get_run_metrics(self, *, run_id: str) -> RunMetricsResult:
        row = self._run_row(run_id)
        live_metrics = (
            self._load_json(row["live_metrics_path"])
            if row["live_metrics_path"] is not None
            else None
        )
        result = RunMetricsResult(
            run_id=run_id,
            workload_family=row["workload_family"],
            prefix_caching_enabled=bool(row["prefix_caching_enabled"]),
            family_claim_class=row["family_claim_class"],
            metrics={
                "ttft_p50_ms": row["ttft_p50_ms"],
                "latency_p50_ms": row["latency_p50_ms"],
                "live_prefix_hit_rate": row["live_prefix_hit_rate"],
                "live_prefix_hits": row["live_prefix_hits"],
                "live_prefix_queries": row["live_prefix_queries"],
                "request_prefill_mean_ms": row["request_prefill_mean_ms"],
            },
            live_metrics=live_metrics,
            source_paths=[
                row["results_path"],
                row["live_metrics_path"],
            ]
            if row["live_metrics_path"] is not None
            else [row["results_path"]],
        )
        self._log_tool_call(
            tool_name="get_run_metrics",
            parameters={"run_id": run_id},
            source_paths=result.source_paths,
        )
        return result

    def get_replay_summary(
        self,
        *,
        workload_family: str | None = None,
        run_id: str | None = None,
        capacity_blocks: int | None = None,
    ) -> ReplaySummaryResult:
        if run_id is not None:
            bridge_report = self._bridge_report()
            for family_name, summary in bridge_report["families"].items():
                for run in summary["runs"]:
                    if run["run_id"] != run_id:
                        continue
                    result = ReplaySummaryResult(
                        mode="run",
                        workload_family=family_name,
                        run_id=run_id,
                        capacity_blocks=int(run["capacity_blocks"]),
                        policies=run["policies"],
                        source_paths=[self.source_reports["bridge"], run["kvtrace_path"]],
                        supporting_run_ids=[run_id],
                    )
                    self._log_tool_call(
                        tool_name="get_replay_summary",
                        parameters={"run_id": run_id},
                        source_paths=result.source_paths,
                    )
                    return result
            raise ValueError(f"unknown run id for replay summary: {run_id}")

        if workload_family is None or capacity_blocks is None:
            raise ValueError("workload_family and capacity_blocks are required when run_id is omitted")

        sweep_report = self._sweep_report()
        family = sweep_report["families"].get(workload_family)
        if family is None:
            raise ValueError(f"unknown workload family for replay summary: {workload_family}")
        capacity = family["capacities"].get(str(capacity_blocks))
        if capacity is None:
            raise ValueError(
                f"unknown replay capacity {capacity_blocks} for workload family {workload_family}"
            )

        result = ReplaySummaryResult(
            mode="family-capacity",
            workload_family=workload_family,
            capacity_blocks=capacity_blocks,
            policies=capacity["policies"],
            source_paths=[self.source_reports["sweep"]],
            supporting_run_ids=[run["run_id"] for run in family["runs"]],
        )
        self._log_tool_call(
            tool_name="get_replay_summary",
            parameters={
                "workload_family": workload_family,
                "capacity_blocks": capacity_blocks,
            },
            source_paths=result.source_paths,
        )
        return result

    def get_capacity_curve(self, *, workload_family: str) -> CapacityCurveResult:
        sweep_report = self._sweep_report()
        family = sweep_report["families"].get(workload_family)
        if family is None:
            raise ValueError(f"unknown workload family for capacity curve: {workload_family}")

        result = CapacityCurveResult(
            workload_family=workload_family,
            capacities=[
                {
                    "capacity_blocks": int(capacity_blocks),
                    "policies": summary["policies"],
                }
                for capacity_blocks, summary in sorted(
                    family["capacities"].items(),
                    key=lambda item: int(item[0]),
                )
            ],
            source_paths=[self.source_reports["sweep"]],
        )
        self._log_tool_call(
            tool_name="get_capacity_curve",
            parameters={"workload_family": workload_family},
            source_paths=result.source_paths,
        )
        return result

    def compare_runs(
        self,
        *,
        left_run_ids: list[str],
        right_run_ids: list[str],
    ) -> CompareRunsResult:
        left_rows = [self._run_row(run_id) for run_id in left_run_ids]
        right_rows = [self._run_row(run_id) for run_id in right_run_ids]

        left_metrics = self._aggregate_run_metrics(left_rows)
        right_metrics = self._aggregate_run_metrics(right_rows)
        metric_deltas = {
            metric_name: self._optional_delta(
                left_metrics.get(metric_name),
                right_metrics.get(metric_name),
            )
            for metric_name in left_metrics
        }

        source_paths = sorted(
            {
                row["manifest_path"]
                for row in left_rows + right_rows
            }
            | {
                row["results_path"]
                for row in left_rows + right_rows
            }
            | {
                row["live_metrics_path"]
                for row in left_rows + right_rows
                if row["live_metrics_path"] is not None
            }
        )
        result = CompareRunsResult(
            left_run_ids=left_run_ids,
            right_run_ids=right_run_ids,
            left_metrics=left_metrics,
            right_metrics=right_metrics,
            metric_deltas=metric_deltas,
            source_paths=source_paths,
        )
        self._log_tool_call(
            tool_name="compare_runs",
            parameters={"left_run_ids": left_run_ids, "right_run_ids": right_run_ids},
            source_paths=source_paths,
        )
        return result

    def list_findings(
        self,
        *,
        family: str | None = None,
        claim_class: str | None = None,
        claim_type: str | None = None,
        source_scope: str = "current-evidence",
        limit: int = 10,
    ) -> ListFindingsResult:
        where_clauses = ["artifacts.path = findings.source_path"]
        parameters: list[Any] = []
        if family is not None:
            where_clauses.append("findings.family = ?")
            parameters.append(family)
        if claim_class is not None:
            where_clauses.append("findings.claim_class = ?")
            parameters.append(claim_class)
        if claim_type is not None:
            where_clauses.append("findings.claim_type = ?")
            parameters.append(claim_type)
        if source_scope != "all":
            where_clauses.append("artifacts.corpus_scope = ?")
            parameters.append(source_scope)

        parameters.append(limit)
        query = """
            SELECT
                findings.finding_id,
                findings.family,
                findings.claim_class,
                findings.claim_type,
                findings.claim_kind,
                findings.summary,
                findings.source_path
            FROM findings
            JOIN artifacts ON artifacts.path = findings.source_path
            WHERE {where_sql}
            ORDER BY findings.finding_id ASC
            LIMIT ?
        """.format(where_sql=" AND ".join(where_clauses))
        rows = self._query_rows(query, parameters)
        result = ListFindingsResult(
            source_scope=source_scope,
            findings=[FindingRecord.model_validate(row) for row in rows],
        )
        self._log_tool_call(
            tool_name="list_findings",
            parameters={
                "family": family,
                "claim_class": claim_class,
                "claim_type": claim_type,
                "source_scope": source_scope,
                "limit": limit,
            },
            source_paths=[finding.source_path for finding in result.findings],
        )
        return result

    def read_artifact_text(
        self,
        *,
        path: str,
        heading_query: str | None = None,
        max_sections: int = 3,
        max_chars: int = 1500,
    ) -> ArtifactTextResult:
        bounded_sections = max(1, min(max_sections, 5))
        bounded_chars = max(200, min(max_chars, 4000))
        resolved_path = self._resolve_allowed_path(path)

        where_clauses = ["path = ?"]
        parameters: list[Any] = [path]
        if heading_query is not None:
            where_clauses.append("LOWER(heading) LIKE ?")
            parameters.append(f"%{heading_query.lower()}%")
        parameters.append(bounded_sections)

        rows = self._query_rows(
            """
            SELECT heading, text
            FROM text_chunks
            WHERE {where_sql}
            LIMIT ?
            """.format(where_sql=" AND ".join(where_clauses)),
            parameters,
        )

        sections = [
            ArtifactSection(heading=row["heading"], text=row["text"][:bounded_chars])
            for row in rows
        ]
        if not sections:
            sections = [
                ArtifactSection(
                    heading="Document",
                    text=resolved_path.read_text()[:bounded_chars],
                )
            ]

        result = ArtifactTextResult(
            path=path,
            source_scope=self._artifact_scope(path),
            sections=sections,
        )
        self._log_tool_call(
            tool_name="read_artifact_text",
            parameters={
                "path": path,
                "heading_query": heading_query,
                "max_sections": bounded_sections,
                "max_chars": bounded_chars,
            },
            source_paths=[path],
        )
        return result

    def resource_text(self, *, resource_name: str) -> str:
        path = self._resource_path(resource_name)
        return self._resolve_allowed_path(path).read_text()

    def resource_uri_map(self) -> dict[str, str]:
        return {
            "kvscope://result-bundle/current": "docs/kvscope_result_bundle.md",
            "kvscope://core-v1-claims/current": "history/CORE-V1-CLAIMS.md",
            "kvscope://benchmark-tables/current": self._markdown_companion(
                self.source_reports["tables"]
            ),
            "kvscope://benchmark-figures/current": self._markdown_companion(
                self.source_reports["figures"]
            ),
        }

    def _resource_path(self, resource_name: str) -> str:
        resource_path = self.resource_uri_map().get(resource_name)
        if resource_path is None:
            raise ValueError(f"unknown resource: {resource_name}")
        return resource_path

    def _bridge_report(self) -> dict[str, Any]:
        return self._load_json(self.source_reports["bridge"])

    def _sweep_report(self) -> dict[str, Any]:
        return self._load_json(self.source_reports["sweep"])

    def _run_row(self, run_id: str) -> dict[str, Any]:
        rows = self._query_rows(
            """
            SELECT
                runs.run_id,
                runs.workload_family,
                runs.prefix_caching_enabled,
                runs.family_claim_class,
                runs.manifest_path,
                runs.results_path,
                runs.live_metrics_path,
                runs.kvtrace_path,
                run_metrics.ttft_p50_ms,
                run_metrics.latency_p50_ms,
                run_metrics.live_prefix_hit_rate,
                run_metrics.live_prefix_hits,
                run_metrics.live_prefix_queries,
                run_metrics.request_prefill_mean_ms
            FROM runs
            LEFT JOIN run_metrics ON run_metrics.run_id = runs.run_id
            WHERE runs.run_id = ?
            """,
            [run_id],
        )
        if not rows:
            raise ValueError(f"unknown run id: {run_id}")
        return rows[0]

    def _aggregate_run_metrics(self, rows: list[dict[str, Any]]) -> dict[str, float | None]:
        return {
            "ttft_p50_ms": self._mean([row["ttft_p50_ms"] for row in rows]),
            "latency_p50_ms": self._mean([row["latency_p50_ms"] for row in rows]),
            "live_prefix_hit_rate": self._mean([row["live_prefix_hit_rate"] for row in rows]),
            "request_prefill_mean_ms": self._mean(
                [row["request_prefill_mean_ms"] for row in rows]
            ),
        }

    def _query_rows(self, query: str, parameters: list[Any]) -> list[dict[str, Any]]:
        connection = sqlite3.connect(self.index_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(query, parameters).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

    def _load_json(self, relative_path: str) -> dict[str, Any]:
        return json.loads(self._resolve_allowed_path(relative_path).read_text())

    def _resolve_allowed_path(self, relative_path: str) -> Path:
        if not any(
            relative_path == allowed or relative_path.startswith(f"{allowed}/")
            for allowed in ("artifacts", "docs", "history")
        ):
            raise ValueError(f"path is outside the allowed read roots: {relative_path}")
        full_path = (self.repo_root / relative_path).resolve()
        repo_root = self.repo_root.resolve()
        if not str(full_path).startswith(str(repo_root)):
            raise ValueError(f"path escapes repo root: {relative_path}")
        if not full_path.exists():
            raise FileNotFoundError(f"artifact path does not exist: {relative_path}")
        return full_path

    def _artifact_scope(self, relative_path: str) -> str | None:
        rows = self._query_rows(
            "SELECT corpus_scope FROM artifacts WHERE path = ?",
            [relative_path],
        )
        if not rows:
            return None
        return rows[0]["corpus_scope"]

    def _markdown_companion(self, relative_path: str) -> str:
        if relative_path.endswith(".json"):
            companion = relative_path[:-5] + ".md"
            if (self.repo_root / companion).exists():
                return companion
        return relative_path

    def _mean(self, values: list[float | None]) -> float | None:
        present_values = [float(value) for value in values if value is not None]
        if not present_values:
            return None
        return round(sum(present_values) / len(present_values), 3)

    def _optional_delta(self, left: float | None, right: float | None) -> float | None:
        if left is None or right is None:
            return None
        return round(left - right, 3)

    def _log_tool_call(
        self,
        *,
        tool_name: str,
        parameters: dict[str, Any],
        source_paths: list[str],
    ) -> None:
        self.logger.debug(
            "tool=%s parameters=%s source_paths=%s",
            tool_name,
            parameters,
            sorted({path for path in source_paths if path}),
        )
