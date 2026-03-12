from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


RUN_MANIFEST_REQUIRED_FIELDS = {
    "schema_version": str,
    "run_id": str,
    "module": str,
    "engine": str,
    "engine_version": str,
    "model": str,
    "gpu_type": str,
    "workload_id": str,
    "workload_family": str,
    "prefix_caching_enabled": bool,
    "cold_start": bool,
    "warmup_requests_discarded": int,
    "commit": str,
    "created_at_utc": str,
    "command": str,
}

VALID_MODULES = {"serve", "bench", "kvtrace", "analysis", "kvscope_mcp"}
VALID_WORKLOAD_FAMILIES = {
    "aligned-prefix",
    "near-aligned-prefix",
    "no-overlap-control",
    "mixed-long-short",
    "bursty-arrivals",
    "eviction-ordering",
    "hotset-scan",
    "locality-shift",
    "locality-return",
}
VALID_SOURCE_KINDS = {"measured", "inferred", "derived"}
VALID_REQUEST_STATUSES = {"ok", "error", "cancelled"}

KVTRACE_COMMON_FIELDS = {
    "schema_version": str,
    "run_id": str,
    "event_type": str,
    "timestamp_ns": int,
    "source_kind": str,
    "engine": str,
    "model": str,
    "workload_id": str,
}

KVTRACE_EVENT_FIELDS = {
    "request_arrival": {
        "request_id": str,
        "prompt_tokens": int,
        "output_tokens_target": int,
    },
    "request_dispatch": {
        "request_id": str,
    },
    "prefix_cache_query": {
        "request_id": str,
        "shared_prefix_tokens": int,
        "block_size_tokens": int,
    },
    "block_lookup": {
        "request_id": str,
        "block_key": str,
        "block_index": int,
        "token_start": int,
        "token_end": int,
        "block_size_tokens": int,
    },
    "block_hit": {
        "request_id": str,
        "block_key": str,
        "block_index": int,
    },
    "block_insert": {
        "request_id": str,
        "block_key": str,
        "block_index": int,
        "token_start": int,
        "token_end": int,
        "block_size_tokens": int,
    },
    "block_pin": {
        "request_id": str,
        "block_key": str,
        "active_sequence_count": int,
    },
    "block_unpin": {
        "request_id": str,
        "block_key": str,
        "active_sequence_count": int,
    },
    "block_evict": {
        "block_key": str,
        "eviction_reason": str,
    },
    "request_complete": {
        "request_id": str,
        "status": str,
    },
}

REQUIRED_READINESS_FILES = [
    Path("README.md"),
    Path("requirements.txt"),
    Path("requirements-dev.txt"),
    Path("history/FINAL-PROJECT-OUTLINE.md"),
    Path("history/IMPLEMENTATION.md"),
    Path("history/EXECUTION-READINESS.md"),
    Path("history/INVESTIGATOR-BUILD-SPEC.md"),
    Path("history/CORE-V1-CLAIMS.json"),
    Path("history/CORE-V1-CLAIMS.md"),
    Path("history/adr/ADR-0006-modal-baseline.md"),
    Path("artifacts/examples/run-manifest-v1.example.json"),
    Path("artifacts/examples/kvtrace-v2.example.ndjson"),
]

STALE_PHRASES = {
    Path("README.md"): [
        "strong preparation vehicle for Anthropic-style systems questions",
    ],
    Path("history/FINAL-PROJECT-OUTLINE.md"): [
        "vLLM or SGLang, chosen by tractability spike",
    ],
    Path("history/IMPLEMENTATION.md"): [
        "choose vLLM or SGLang",
    ],
    Path("history/EXECUTION-READINESS.md"): [
        "Engine choice is still unresolved",
        "The trace contract is not yet defined",
        "The profile input path is not locked",
        "Corpus and workload sources are not locked",
        "Result artifact conventions are not defined",
    ],
}

REQUIRED_SECTION_HEADINGS = {
    Path("history/INVESTIGATOR-BUILD-SPEC.md"): [
        "## Current State",
        "## Goal State",
        "## Step 0: Pre-Execution Lock",
        "### Locked Investigator Questions",
        "### Locked Answer Taxonomy",
        "### Locked MCP Scope Model",
        "### Locked Eval Schema",
        "### Locked Harness Decision",
        "### Locked Context-Budget Rules",
        "### Locked Differentiation Note",
        "### Locked Demo Sanitization Checklist",
    ],
    Path("history/CORE-V1-CLAIMS.md"): [
        "## Family Claim Classes",
        "## Claims",
    ],
    Path("history/IMPLEMENTATION.md"): [
        "## Phase 7: Investigator Layer",
        "## Immediate Next Slice",
    ],
    Path("history/EXECUTION-READINESS.md"): [
        "## Immediate Build Order",
    ],
}


def load_run_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_kvtrace_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def validate_run_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for field_name, expected_type in RUN_MANIFEST_REQUIRED_FIELDS.items():
        if field_name not in manifest:
            errors.append(f"run manifest is missing required field '{field_name}'")
            continue
        if not isinstance(manifest[field_name], expected_type):
            errors.append(
                f"run manifest field '{field_name}' must be {expected_type.__name__}"
            )

    if errors:
        return errors

    if manifest["schema_version"] != "run-manifest-v1":
        errors.append("run manifest schema_version must be 'run-manifest-v1'")

    if manifest["module"] not in VALID_MODULES:
        errors.append("run manifest module must be one of the documented modules")

    if manifest["workload_family"] not in VALID_WORKLOAD_FAMILIES:
        errors.append("run manifest workload_family must be a documented workload family")

    if manifest["warmup_requests_discarded"] < 0:
        errors.append("run manifest warmup_requests_discarded must be >= 0")

    if not re.fullmatch(
        r"\d{8}-\d{6}__[a-z]+__[a-z0-9-]+__[a-z0-9-]+", manifest["run_id"]
    ):
        errors.append("run manifest run_id must follow the documented naming convention")

    if not re.fullmatch(r"[0-9a-f]{7,40}", manifest["commit"]):
        errors.append("run manifest commit must look like a git sha")

    if not _looks_like_iso8601_utc(manifest["created_at_utc"]):
        errors.append("run manifest created_at_utc must be an ISO-8601 UTC timestamp")

    if not manifest["engine"].strip():
        errors.append("run manifest engine must be non-empty")
    if not manifest["engine_version"].strip():
        errors.append("run manifest engine_version must be non-empty")
    if not manifest["model"].strip():
        errors.append("run manifest model must be non-empty")
    if not manifest["gpu_type"].strip():
        errors.append("run manifest gpu_type must be non-empty")
    if not manifest["workload_id"].strip():
        errors.append("run manifest workload_id must be non-empty")
    if not manifest["command"].strip():
        errors.append("run manifest command must be non-empty")

    return errors


def validate_kvtrace_events(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not events:
        return ["kvtrace fixture must contain at least one event"]

    previous_timestamp = -1
    seen_lookups: set[tuple[str, str, int]] = set()
    active_pins: dict[str, int] = {}
    seen_arrivals: set[str] = set()
    seen_completions: set[str] = set()

    for index, event in enumerate(events):
        prefix = f"kvtrace event {index}"

        for field_name, expected_type in KVTRACE_COMMON_FIELDS.items():
            if field_name not in event:
                errors.append(f"{prefix} is missing required field '{field_name}'")
                continue
            if not isinstance(event[field_name], expected_type):
                errors.append(f"{prefix} field '{field_name}' must be {expected_type.__name__}")

        if errors:
            continue

        event_type = event["event_type"]
        if event["schema_version"] != "kvtrace-v2":
            errors.append(f"{prefix} must use schema_version 'kvtrace-v2'")
            continue

        if event["source_kind"] not in VALID_SOURCE_KINDS:
            errors.append(f"{prefix} has invalid source_kind '{event['source_kind']}'")

        if event["timestamp_ns"] < previous_timestamp:
            errors.append(f"{prefix} timestamps must be monotonic")
        previous_timestamp = event["timestamp_ns"]

        required_fields = KVTRACE_EVENT_FIELDS.get(event_type)
        if required_fields is None:
            errors.append(f"{prefix} has unknown event_type '{event_type}'")
            continue

        for field_name, expected_type in required_fields.items():
            if field_name not in event:
                errors.append(f"{prefix} is missing required field '{field_name}'")
                continue
            if not isinstance(event[field_name], expected_type):
                errors.append(f"{prefix} field '{field_name}' must be {expected_type.__name__}")

        if event_type == "request_arrival":
            seen_arrivals.add(event["request_id"])
        elif event_type == "block_lookup":
            seen_lookups.add(
                (event["request_id"], event["block_key"], event["block_index"])
            )
        elif event_type == "block_hit":
            lookup_key = (event["request_id"], event["block_key"], event["block_index"])
            if lookup_key not in seen_lookups:
                errors.append(f"{prefix} must follow a matching block_lookup event")
        elif event_type == "block_pin":
            block_key = event["block_key"]
            active_count = event["active_sequence_count"]
            if active_count <= 0:
                errors.append(f"{prefix} active_sequence_count must be > 0")
            active_pins[block_key] = active_count
        elif event_type == "block_unpin":
            block_key = event["block_key"]
            active_count = event["active_sequence_count"]
            previous_count = active_pins.get(block_key)
            if previous_count is None:
                errors.append(f"{prefix} must follow a block_pin for the same block_key")
            elif active_count < 0 or active_count >= previous_count:
                errors.append(
                    f"{prefix} active_sequence_count must decrease after block_pin"
                )
            active_pins[block_key] = active_count
        elif event_type == "block_evict":
            block_key = event["block_key"]
            if active_pins.get(block_key, 0) > 0:
                errors.append(f"{prefix} cannot evict a block while it is pinned")
        elif event_type == "request_complete":
            if event["request_id"] not in seen_arrivals:
                errors.append(f"{prefix} must follow request_arrival for the same request")
            if event["status"] not in VALID_REQUEST_STATUSES:
                errors.append(f"{prefix} has invalid request status '{event['status']}'")
            seen_completions.add(event["request_id"])

    missing_completions = sorted(seen_arrivals - seen_completions)
    if missing_completions:
        errors.append(
            "kvtrace fixture is missing request_complete for: "
            + ", ".join(missing_completions)
        )

    return errors


def collect_readiness_errors(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for relative_path in REQUIRED_READINESS_FILES:
        full_path = repo_root / relative_path
        if not full_path.exists():
            errors.append(f"missing required readiness file: {relative_path}")

    if errors:
        return errors

    errors.extend(validate_docs_consistency(repo_root))
    errors.extend(validate_required_section_headings(repo_root))
    errors.extend(
        validate_run_manifest(
            load_run_manifest(repo_root / "artifacts/examples/run-manifest-v1.example.json")
        )
    )
    errors.extend(
        validate_kvtrace_events(
            load_kvtrace_events(repo_root / "artifacts/examples/kvtrace-v2.example.ndjson")
        )
    )

    return errors


def validate_docs_consistency(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for relative_path, stale_phrases in STALE_PHRASES.items():
        contents = (repo_root / relative_path).read_text()
        for stale_phrase in stale_phrases:
            if stale_phrase in contents:
                errors.append(
                    f"{relative_path} still contains stale wording: '{stale_phrase}'"
                )

    return errors


def validate_required_section_headings(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for relative_path, headings in REQUIRED_SECTION_HEADINGS.items():
        contents = (repo_root / relative_path).read_text()
        for heading in headings:
            if heading not in contents:
                errors.append(f"{relative_path} is missing required section heading '{heading}'")

    return errors


def _looks_like_iso8601_utc(value: str) -> bool:
    if not value.endswith("Z"):
        return False

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False

    return True
