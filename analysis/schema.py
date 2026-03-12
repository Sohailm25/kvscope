# ABOUTME: SQLite schema for the first KVScope investigator corpus index.
# ABOUTME: The schema is intentionally small and biased toward structured retrieval plus FTS-backed text search.

from __future__ import annotations


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        workload_family TEXT NOT NULL,
        prefix_caching_enabled INTEGER NOT NULL,
        cold_start INTEGER NOT NULL,
        family_claim_class TEXT NOT NULL,
        manifest_path TEXT NOT NULL,
        results_path TEXT NOT NULL,
        live_metrics_path TEXT,
        kvtrace_path TEXT,
        command TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_metrics (
        run_id TEXT PRIMARY KEY,
        ttft_p50_ms REAL,
        latency_p50_ms REAL,
        live_prefix_queries REAL,
        live_prefix_hits REAL,
        live_prefix_hit_rate REAL,
        request_prefill_mean_ms REAL,
        request_queue_mean_ms REAL,
        throughput_tokens_per_second REAL,
        FOREIGN KEY(run_id) REFERENCES runs(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS findings (
        finding_id TEXT PRIMARY KEY,
        family TEXT,
        claim_class TEXT NOT NULL,
        claim_type TEXT NOT NULL,
        claim_kind TEXT NOT NULL,
        summary TEXT NOT NULL,
        source_path TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        path TEXT PRIMARY KEY,
        artifact_type TEXT NOT NULL,
        run_id TEXT,
        family TEXT,
        schema_version TEXT,
        phase TEXT,
        corpus_scope TEXT NOT NULL
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS text_chunks
    USING fts5(path UNINDEXED, heading, text)
    """,
]


def apply_schema(connection) -> None:
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
