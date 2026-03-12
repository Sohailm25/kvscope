# ABOUTME: Builds and queries the first SQLite-backed analysis index for KVScope.
# ABOUTME: This module keeps the investigator layer grounded in structured artifact retrieval before MCP or agent logic is added.

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from analysis.core_claims import build_core_v1_claim_manifest, render_core_v1_claim_manifest_markdown
from analysis.schema import apply_schema

_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "show",
    "shows",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def build_analysis_index(
    *,
    repo_root: Path,
    index_path: Path | None = None,
    claim_manifest: dict[str, Any] | None = None,
) -> Path:
    resolved_index_path = index_path or default_index_path(repo_root)
    resolved_index_path.parent.mkdir(parents=True, exist_ok=True)
    if resolved_index_path.exists():
        resolved_index_path.unlink()

    manifest = claim_manifest or build_core_v1_claim_manifest(repo_root=repo_root)
    current_evidence_paths = _current_evidence_paths(manifest)
    connection = sqlite3.connect(resolved_index_path)
    try:
        apply_schema(connection)
        _ingest_runs(
            connection=connection,
            repo_root=repo_root,
            claim_manifest=manifest,
        )
        _ingest_report_artifacts(
            connection=connection,
            repo_root=repo_root,
            claim_manifest=manifest,
            current_evidence_paths=current_evidence_paths,
        )
        _ingest_core_claim_manifest(
            connection=connection,
            manifest=manifest,
            current_evidence_paths=current_evidence_paths,
        )
        _ingest_markdown_sources(
            connection=connection,
            repo_root=repo_root,
            current_evidence_paths=current_evidence_paths,
        )
        connection.commit()
    finally:
        connection.close()

    return resolved_index_path


def default_index_path(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "analysis" / "kvscope-analysis.sqlite3"


def search_runs(
    *,
    index_path: Path,
    workload_family: str | None = None,
    prefix_caching_enabled: bool | None = None,
    family_claim_class: str | None = None,
    claim_class: str | None = None,
    min_live_prefix_hit_rate: float | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    connection = sqlite3.connect(index_path)
    connection.row_factory = sqlite3.Row
    try:
        where_clauses: list[str] = []
        parameters: list[Any] = []

        if workload_family is not None:
            where_clauses.append("runs.workload_family = ?")
            parameters.append(workload_family)
        if prefix_caching_enabled is not None:
            where_clauses.append("runs.prefix_caching_enabled = ?")
            parameters.append(1 if prefix_caching_enabled else 0)
        resolved_family_claim_class = family_claim_class or claim_class
        if resolved_family_claim_class is not None:
            where_clauses.append("runs.family_claim_class = ?")
            parameters.append(resolved_family_claim_class)
        if min_live_prefix_hit_rate is not None:
            where_clauses.append("COALESCE(run_metrics.live_prefix_hit_rate, 0.0) >= ?")
            parameters.append(min_live_prefix_hit_rate)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        parameters.append(limit)
        rows = connection.execute(
            f"""
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
            {where_sql}
            ORDER BY
                COALESCE(run_metrics.live_prefix_hit_rate, -1.0) DESC,
                COALESCE(run_metrics.ttft_p50_ms, 1e18) ASC,
                runs.run_id ASC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]


def search_text(
    *,
    index_path: Path,
    query: str,
    limit: int = 10,
    scope: str = "current-evidence",
) -> list[dict[str, Any]]:
    connection = sqlite3.connect(index_path)
    connection.row_factory = sqlite3.Row
    try:
        normalized_query = _normalize_text_query(query)
        resolved_scope = _normalize_scope(scope)
        if resolved_scope == "all":
            rows = connection.execute(
                """
                SELECT
                    text_chunks.path,
                    text_chunks.heading,
                    snippet(text_chunks, 2, '[', ']', '...', 12) AS snippet
                FROM text_chunks
                JOIN artifacts ON artifacts.path = text_chunks.path
                WHERE text_chunks MATCH ?
                ORDER BY bm25(text_chunks)
                LIMIT ?
                """,
                [normalized_query, limit],
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    text_chunks.path,
                    text_chunks.heading,
                    snippet(text_chunks, 2, '[', ']', '...', 12) AS snippet
                FROM text_chunks
                JOIN artifacts ON artifacts.path = text_chunks.path
                WHERE text_chunks MATCH ?
                  AND artifacts.corpus_scope = ?
                ORDER BY bm25(text_chunks)
                LIMIT ?
                """,
                [normalized_query, resolved_scope, limit],
            ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]


def _normalize_text_query(query: str) -> str:
    raw_tokens = [token for token in query.split() if token]
    tokens = [
        token
        for token in raw_tokens
        if token.lower().strip(".,:;!?()[]{}") not in _QUERY_STOPWORDS
    ]
    if not tokens:
        tokens = raw_tokens
    if not tokens:
        return '""'
    escaped_tokens = [token.replace('"', '""') for token in tokens]
    return " ".join(f'"{token}"' for token in escaped_tokens)


def _normalize_scope(scope: str) -> str:
    allowed_scopes = {
        "all",
        "current-evidence",
        "historical-evidence",
        "planning",
        "raw-evidence",
    }
    if scope not in allowed_scopes:
        raise ValueError(f"unsupported analysis search scope: {scope}")
    return scope


def _ingest_runs(
    *,
    connection: sqlite3.Connection,
    repo_root: Path,
    claim_manifest: dict[str, Any],
) -> None:
    family_claim_classes = claim_manifest["family_claim_classes"]
    runs_root = repo_root / "artifacts" / "runs"
    if not runs_root.exists():
        return

    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        manifest_path = run_dir / "manifest.json"
        results_path = run_dir / "results.json"
        if not manifest_path.exists() or not results_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text())
        results = json.loads(results_path.read_text())
        live_metrics_path = run_dir / "live_metrics.json"
        kvtrace_path = run_dir / "kvtrace.ndjson"

        run_id = manifest["run_id"]
        workload_family = manifest["workload_family"]
        family_claim_class = family_claim_classes.get(workload_family, "exploratory")

        connection.execute(
            """
            INSERT INTO runs (
                run_id,
                workload_family,
                prefix_caching_enabled,
                cold_start,
                family_claim_class,
                manifest_path,
                results_path,
                live_metrics_path,
                kvtrace_path,
                command
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                workload_family,
                1 if manifest["prefix_caching_enabled"] else 0,
                1 if manifest["cold_start"] else 0,
                family_claim_class,
                _relative_path(repo_root, manifest_path),
                _relative_path(repo_root, results_path),
                _relative_path(repo_root, live_metrics_path) if live_metrics_path.exists() else None,
                _relative_path(repo_root, kvtrace_path) if kvtrace_path.exists() else None,
                manifest["command"],
            ],
        )

        metrics = _extract_run_metrics(results=results, live_metrics_path=live_metrics_path)
        connection.execute(
            """
            INSERT INTO run_metrics (
                run_id,
                ttft_p50_ms,
                latency_p50_ms,
                live_prefix_queries,
                live_prefix_hits,
                live_prefix_hit_rate,
                request_prefill_mean_ms,
                request_queue_mean_ms,
                throughput_tokens_per_second
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                metrics["ttft_p50_ms"],
                metrics["latency_p50_ms"],
                metrics["live_prefix_queries"],
                metrics["live_prefix_hits"],
                metrics["live_prefix_hit_rate"],
                metrics["request_prefill_mean_ms"],
                metrics["request_queue_mean_ms"],
                metrics["throughput_tokens_per_second"],
            ],
        )

        for file_path in sorted(path for path in run_dir.iterdir() if path.is_file()):
            connection.execute(
                """
                INSERT INTO artifacts (path, artifact_type, run_id, family, schema_version, phase, corpus_scope)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    _relative_path(repo_root, file_path),
                    file_path.stem,
                    run_id,
                    workload_family,
                    _load_schema_version(file_path),
                    "run",
                    "raw-evidence",
                ],
            )


def _ingest_report_artifacts(
    *,
    connection: sqlite3.Connection,
    repo_root: Path,
    claim_manifest: dict[str, Any],
    current_evidence_paths: set[str],
) -> None:
    family_claim_classes = claim_manifest["family_claim_classes"]
    manifests_root = repo_root / "artifacts" / "manifests"
    if manifests_root.exists():
        for file_path in sorted(manifests_root.iterdir()):
            if not file_path.is_file():
                continue
            relative_path = _relative_path(repo_root, file_path)
            phase = _infer_phase_from_path(relative_path)
            if file_path.suffix == ".json":
                payload = json.loads(file_path.read_text())
                connection.execute(
                    """
                    INSERT INTO artifacts (path, artifact_type, run_id, family, schema_version, phase, corpus_scope)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        relative_path,
                        "manifest-report",
                        None,
                        None,
                        payload.get("schema_version"),
                        phase,
                        _artifact_corpus_scope(
                            relative_path=relative_path,
                            current_evidence_paths=current_evidence_paths,
                        ),
                    ],
                )
                for index, finding in enumerate(payload.get("findings", [])):
                    family = str(finding.get("evidence", {}).get("workload_family") or "")
                    connection.execute(
                        """
                        INSERT INTO findings (
                            finding_id,
                            family,
                            claim_class,
                            claim_type,
                            claim_kind,
                            summary,
                            source_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            f"{file_path.stem}::{index}",
                            family or None,
                            family_claim_classes.get(family, "exploratory"),
                            _infer_claim_type_from_path(relative_path),
                            finding["kind"],
                            finding["message"],
                            relative_path,
                        ],
                    )
                    _insert_text_chunk(
                        connection=connection,
                        path=relative_path,
                        heading=finding["kind"],
                        text=finding["message"],
                    )
            elif file_path.suffix == ".md":
                connection.execute(
                    """
                    INSERT INTO artifacts (path, artifact_type, run_id, family, schema_version, phase, corpus_scope)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        relative_path,
                        "markdown-report",
                        None,
                        None,
                        None,
                        phase,
                        _artifact_corpus_scope(
                            relative_path=relative_path,
                            current_evidence_paths=current_evidence_paths,
                        ),
                    ],
                )
                _ingest_markdown_file(
                    connection=connection,
                    relative_path=relative_path,
                    contents=file_path.read_text(),
                )


def _ingest_core_claim_manifest(
    *,
    connection: sqlite3.Connection,
    manifest: dict[str, Any],
    current_evidence_paths: set[str],
) -> None:
    json_path = "history/CORE-V1-CLAIMS.json"
    markdown_path = "history/CORE-V1-CLAIMS.md"
    markdown = render_core_v1_claim_manifest_markdown(manifest)

    connection.execute(
        """
        INSERT INTO artifacts (path, artifact_type, run_id, family, schema_version, phase, corpus_scope)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            json_path,
            "claim-manifest",
            None,
            None,
            manifest["schema_version"],
            "phase7",
            _artifact_corpus_scope(
                relative_path=json_path,
                current_evidence_paths=current_evidence_paths,
            ),
        ],
    )
    connection.execute(
        """
        INSERT INTO artifacts (path, artifact_type, run_id, family, schema_version, phase, corpus_scope)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            markdown_path,
            "claim-manifest-markdown",
            None,
            None,
            None,
            "phase7",
            _artifact_corpus_scope(
                relative_path=markdown_path,
                current_evidence_paths=current_evidence_paths,
            ),
        ],
    )

    for claim in manifest["claims"]:
        for family in claim["families"]:
            connection.execute(
                """
                INSERT INTO findings (
                    finding_id,
                    family,
                    claim_class,
                    claim_type,
                    claim_kind,
                    summary,
                    source_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    f"{claim['claim_id']}::{family}",
                    family,
                    claim["claim_class"],
                    claim["claim_type"],
                    "core-v1-claim",
                    claim["summary"],
                    json_path,
                ],
            )
        _insert_text_chunk(
            connection=connection,
            path=markdown_path,
            heading=claim["claim_id"],
            text="\n".join(
                [
                    f"Families: {', '.join(claim['families'])}",
                    f"Claim type: {claim['claim_type']}",
                    f"Claim class: {claim['claim_class']}",
                    f"Summary: {claim['summary']}",
                ]
            ),
        )

    _ingest_markdown_file(
        connection=connection,
        relative_path=markdown_path,
        contents=markdown,
    )


def _ingest_markdown_sources(
    *,
    connection: sqlite3.Connection,
    repo_root: Path,
    current_evidence_paths: set[str],
) -> None:
    for relative_path in (
        "docs/kvscope_result_bundle.md",
        "history/INVESTIGATOR-BUILD-SPEC.md",
    ):
        full_path = repo_root / relative_path
        if not full_path.exists():
            continue
        connection.execute(
            """
            INSERT OR IGNORE INTO artifacts (path, artifact_type, run_id, family, schema_version, phase, corpus_scope)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                relative_path,
                "markdown-doc",
                None,
                None,
                None,
                "doc",
                _artifact_corpus_scope(
                    relative_path=relative_path,
                    current_evidence_paths=current_evidence_paths,
                ),
            ],
        )
        _ingest_markdown_file(
            connection=connection,
            relative_path=relative_path,
            contents=full_path.read_text(),
        )


def _ingest_markdown_file(
    *,
    connection: sqlite3.Connection,
    relative_path: str,
    contents: str,
) -> None:
    heading = "Document"
    buffer: list[str] = []

    for line in contents.splitlines():
        if line.startswith("#"):
            if buffer:
                _insert_text_chunk(
                    connection=connection,
                    path=relative_path,
                    heading=heading,
                    text="\n".join(buffer).strip(),
                )
                buffer = []
            heading = line.lstrip("#").strip() or "Document"
        else:
            buffer.append(line)

    if buffer:
        _insert_text_chunk(
            connection=connection,
            path=relative_path,
            heading=heading,
            text="\n".join(buffer).strip(),
        )


def _insert_text_chunk(
    *,
    connection: sqlite3.Connection,
    path: str,
    heading: str,
    text: str,
) -> None:
    cleaned_text = text.strip()
    if not cleaned_text:
        return
    connection.execute(
        "INSERT INTO text_chunks (path, heading, text) VALUES (?, ?, ?)",
        [path, heading, cleaned_text],
    )


def _extract_run_metrics(*, results: dict[str, Any], live_metrics_path: Path) -> dict[str, float | None]:
    metrics = {
        "ttft_p50_ms": _optional_float(results.get("ttft_ms", {}).get("p50")),
        "latency_p50_ms": _optional_float(results.get("latency_ms", {}).get("p50")),
        "throughput_tokens_per_second": _optional_float(results.get("tokens_per_second")),
        "live_prefix_queries": None,
        "live_prefix_hits": None,
        "live_prefix_hit_rate": None,
        "request_prefill_mean_ms": None,
        "request_queue_mean_ms": None,
    }

    if live_metrics_path.exists():
        live_metrics = json.loads(live_metrics_path.read_text())
        delta = live_metrics.get("delta", {})
        counters = delta.get("counters", {})
        histograms = delta.get("histograms", {})
        derived = delta.get("derived", {})
        metrics.update(
            {
                "live_prefix_queries": _optional_float(counters.get("vllm:prefix_cache_queries")),
                "live_prefix_hits": _optional_float(counters.get("vllm:prefix_cache_hits")),
                "live_prefix_hit_rate": _optional_float(derived.get("prefix_cache_hit_rate")),
                "request_prefill_mean_ms": _optional_float(
                    histograms.get("vllm:request_prefill_time_seconds", {}).get("mean_ms")
                ),
                "request_queue_mean_ms": _optional_float(
                    histograms.get("vllm:request_queue_time_seconds", {}).get("mean_ms")
                ),
            }
        )

    return metrics


def _infer_phase_from_path(relative_path: str) -> str:
    parts = relative_path.split("__")
    if len(parts) >= 3:
        return parts[2]
    return "artifact"


def _infer_claim_type_from_path(relative_path: str) -> str:
    if "__kvtrace__" in relative_path:
        return "replay"
    return "measured"


def _load_schema_version(file_path: Path) -> str | None:
    if file_path.suffix != ".json":
        return None
    try:
        return json.loads(file_path.read_text()).get("schema_version")
    except json.JSONDecodeError:
        return None


def _relative_path(repo_root: Path, file_path: Path) -> str:
    return str(file_path.relative_to(repo_root))


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _current_evidence_paths(claim_manifest: dict[str, Any]) -> set[str]:
    current_paths = set(claim_manifest["source_reports"].values())
    current_paths.update(
        {
            "history/CORE-V1-CLAIMS.json",
            "history/CORE-V1-CLAIMS.md",
        }
    )
    return current_paths


def _artifact_corpus_scope(*, relative_path: str, current_evidence_paths: set[str]) -> str:
    if relative_path in current_evidence_paths:
        return "current-evidence"
    if relative_path == "history/INVESTIGATOR-BUILD-SPEC.md":
        return "planning"
    return "historical-evidence"
