from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

from openai import OpenAI

from bench.workloads import WorkloadArtifact, WorkloadRequest, write_workload_artifact
from kvtrace.trace_builder import build_trace_events
from serve.artifacts import (
    RequestObservation,
    build_run_manifest,
    create_run_directory,
    summarize_observations,
    write_run_bundle,
)


class TokenizerLike(Protocol):
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ...


class OpenAIClientLike(Protocol):
    models: object
    completions: object

    def close(self) -> None:
        ...


def wait_for_model(
    *,
    base_url: str,
    api_key: str,
    timeout_seconds: int,
    client_factory: Callable[..., OpenAIClientLike] = OpenAI,
) -> None:
    client = client_factory(base_url=f"{base_url}/v1", api_key=api_key)
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    try:
        while time.monotonic() < deadline:
            try:
                response = client.models.list()
                if response.data:
                    return
            except Exception as error:  # noqa: BLE001
                last_error = error
            time.sleep(2)
    finally:
        client.close()

    raise TimeoutError("vLLM endpoint did not become ready in time") from last_error


def run_workload(
    *,
    base_url: str,
    api_key: str,
    model_name: str,
    workload: WorkloadArtifact,
    tokenizer: TokenizerLike,
    client_factory: Callable[..., OpenAIClientLike] = OpenAI,
) -> list[RequestObservation]:
    run_started_at = time.monotonic()
    observations_by_index: dict[int, RequestObservation] = {}

    with ThreadPoolExecutor(max_workers=max(1, len(workload.requests))) as executor:
        futures = [
            (
                request_index,
                executor.submit(
                    _run_scheduled_request,
                    base_url=base_url,
                    api_key=api_key,
                    model_name=model_name,
                    tokenizer=tokenizer,
                    request=request,
                    run_started_at=run_started_at,
                    client_factory=client_factory,
                ),
            )
            for request_index, request in enumerate(workload.requests)
        ]

        for request_index, future in futures:
            observations_by_index[request_index] = future.result()

    return [observations_by_index[index] for index in range(len(workload.requests))]


def persist_run(
    *,
    repo_root: Path,
    workload: WorkloadArtifact,
    tokenizer: TokenizerLike,
    observations: list[RequestObservation],
    engine_name: str,
    engine_version: str,
    model_name: str,
    gpu_type: str,
    prefix_caching_enabled: bool,
    cold_start: bool,
    warmup_requests_discarded: int,
    run_slug: str,
    command: str,
    stdout_text: str,
    stderr_text: str,
    cache_capacity_blocks: int,
    live_metrics: dict[str, object] | None = None,
) -> Path:
    timestamp_for_run = datetime.now(tz=UTC)
    run_timestamp = timestamp_for_run.strftime("%Y%m%d-%H%M%S")
    run_dir = create_run_directory(
        artifacts_root=repo_root,
        module="serve",
        workload_family=workload.workload_family,
        slug=run_slug,
        timestamp_override=run_timestamp,
    )
    write_workload_artifact(run_dir / "workload.jsonl", workload)

    run_id = run_dir.name
    kvtrace_events = build_trace_events(
        workload=workload,
        tokenizer=tokenizer,
        model_name=model_name,
        engine_name=engine_name,
        run_id=run_id,
        cache_capacity_blocks=cache_capacity_blocks,
    )
    manifest = build_run_manifest(
        run_id=run_id,
        module="serve",
        engine=engine_name,
        engine_version=engine_version,
        model=model_name,
        gpu_type=gpu_type,
        workload_id=workload.workload_id,
        workload_family=workload.workload_family,
        prefix_caching_enabled=prefix_caching_enabled,
        cold_start=cold_start,
        warmup_requests_discarded=warmup_requests_discarded,
        commit=_git_short_sha(repo_root),
        created_at_utc=timestamp_for_run.isoformat().replace("+00:00", "Z"),
        command=command,
    )
    results = summarize_observations(observations)
    write_run_bundle(
        run_dir=run_dir,
        manifest=manifest,
        results=results,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        kvtrace_events=kvtrace_events,
        live_metrics=live_metrics,
    )
    return run_dir


def _run_request(
    *,
    client: OpenAIClientLike,
    model_name: str,
    tokenizer: TokenizerLike,
    request: WorkloadRequest,
    run_started_at: float,
    started_offset_ms: float,
) -> RequestObservation:
    started_at = time.perf_counter()
    first_token_at: float | None = None
    last_token_at: float | None = None
    inter_token_latencies_ms: list[float] = []
    output_chunks: list[str] = []

    stream = client.completions.create(
        model=model_name,
        prompt=request.prompt,
        max_tokens=request.output_tokens_target,
        stream=True,
        temperature=0.0,
    )

    for event in stream:
        choices = getattr(event, "choices", [])
        if not choices:
            continue
        token_text = choices[0].text or ""
        if not token_text:
            continue

        now = time.perf_counter()
        if first_token_at is None:
            first_token_at = now
        elif last_token_at is not None:
            inter_token_latencies_ms.append((now - last_token_at) * 1000.0)

        last_token_at = now
        output_chunks.append(token_text)

    completed_at = time.perf_counter()
    output_text = "".join(output_chunks)
    output_tokens = len(tokenizer.encode(output_text, add_special_tokens=False))
    ttft_ms = 0.0 if first_token_at is None else (first_token_at - started_at) * 1000.0
    latency_ms = (completed_at - started_at) * 1000.0
    prompt_tokens = len(tokenizer.encode(request.prompt, add_special_tokens=False))

    return RequestObservation(
        request_id=request.request_id,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        ttft_ms=ttft_ms,
        latency_ms=latency_ms,
        inter_token_latencies_ms=inter_token_latencies_ms,
        status="ok",
        arrival_offset_ms=float(request.arrival_offset_ms),
        started_offset_ms=started_offset_ms,
        completed_offset_ms=(completed_at - run_started_at) * 1000.0,
    )


def _run_scheduled_request(
    *,
    base_url: str,
    api_key: str,
    model_name: str,
    tokenizer: TokenizerLike,
    request: WorkloadRequest,
    run_started_at: float,
    client_factory: Callable[..., OpenAIClientLike],
) -> RequestObservation:
    _sleep_until(run_started_at + (request.arrival_offset_ms / 1000.0))
    started_offset_ms = (time.monotonic() - run_started_at) * 1000.0
    client = client_factory(base_url=f"{base_url}/v1", api_key=api_key)

    try:
        return _run_request(
            client=client,
            model_name=model_name,
            tokenizer=tokenizer,
            request=request,
            run_started_at=run_started_at,
            started_offset_ms=started_offset_ms,
        )
    finally:
        client.close()


def _sleep_until(target_time: float) -> None:
    remaining = target_time - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)


def _git_short_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    candidate = result.stdout.strip()
    return candidate if candidate else "0000000"
