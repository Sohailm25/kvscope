from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    run_id: str
    workload_family: str
    prefix_caching_enabled: bool
    family_claim_class: str
    manifest_path: str
    results_path: str
    live_metrics_path: str | None = None
    kvtrace_path: str | None = None
    ttft_p50_ms: float | None = None
    latency_p50_ms: float | None = None
    live_prefix_hit_rate: float | None = None
    live_prefix_hits: float | None = None
    live_prefix_queries: float | None = None
    request_prefill_mean_ms: float | None = None


class SearchRunsResult(BaseModel):
    applied_filters: dict[str, Any]
    matched_source_paths: list[str] = Field(default_factory=list)
    runs: list[RunSummary] = Field(default_factory=list)


class RunManifestResult(BaseModel):
    run_id: str
    workload_family: str
    prefix_caching_enabled: bool
    family_claim_class: str
    manifest: dict[str, Any]
    artifact_paths: dict[str, str | None]


class RunMetricsResult(BaseModel):
    run_id: str
    workload_family: str
    prefix_caching_enabled: bool
    family_claim_class: str
    metrics: dict[str, float | None]
    live_metrics: dict[str, Any] | None = None
    source_paths: list[str]


class ReplaySummaryResult(BaseModel):
    mode: str
    workload_family: str
    capacity_blocks: int
    run_id: str | None = None
    policies: dict[str, dict[str, Any]]
    source_paths: list[str]
    supporting_run_ids: list[str] = Field(default_factory=list)


class CapacityCurveResult(BaseModel):
    workload_family: str
    capacities: list[dict[str, Any]]
    source_paths: list[str]


class CompareRunsResult(BaseModel):
    left_run_ids: list[str]
    right_run_ids: list[str]
    left_metrics: dict[str, float | None]
    right_metrics: dict[str, float | None]
    metric_deltas: dict[str, float | None]
    source_paths: list[str]


class FindingRecord(BaseModel):
    finding_id: str
    family: str | None = None
    claim_class: str
    claim_type: str
    claim_kind: str
    summary: str
    source_path: str


class ListFindingsResult(BaseModel):
    source_scope: str
    findings: list[FindingRecord] = Field(default_factory=list)


class ArtifactSection(BaseModel):
    heading: str
    text: str


class ArtifactTextResult(BaseModel):
    path: str
    source_scope: str | None = None
    sections: list[ArtifactSection] = Field(default_factory=list)
