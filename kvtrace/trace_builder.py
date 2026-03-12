# ABOUTME: Builds derived kvtrace events from benchmark workloads before deeper engine hooks exist.
# ABOUTME: The source_kind on these events must stay honest because they are derived from workload structure, not raw engine internals.

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any

from bench.workloads import TokenizerLike, WorkloadArtifact


def build_trace_events(
    *,
    workload: WorkloadArtifact,
    tokenizer: TokenizerLike,
    model_name: str,
    engine_name: str,
    run_id: str,
    cache_capacity_blocks: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cache: OrderedDict[str, None] = OrderedDict()
    pinned_blocks: set[str] = set()
    timestamp_ns = 1_000

    for request in workload.requests:
        prompt_tokens = list(tokenizer.encode(request.prompt))
        block_size = workload.block_size_tokens
        full_blocks = _chunk_full_blocks(prompt_tokens, block_size)

        prefix_hit_tokens = 0
        for block_index, block_tokens in enumerate(full_blocks):
            block_key = _block_key(block_tokens)
            if block_index * block_size != prefix_hit_tokens or block_key not in cache:
                break
            prefix_hit_tokens += block_size

        events.append(
            _event(
                run_id,
                timestamp_ns,
                engine_name,
                model_name,
                workload.workload_id,
                "request_arrival",
                request_id=request.request_id,
                prompt_tokens=len(prompt_tokens),
                output_tokens_target=request.output_tokens_target,
            )
        )
        timestamp_ns += 50
        events.append(
            _event(
                run_id,
                timestamp_ns,
                engine_name,
                model_name,
                workload.workload_id,
                "request_dispatch",
                request_id=request.request_id,
            )
        )
        timestamp_ns += 50
        events.append(
            _event(
                run_id,
                timestamp_ns,
                engine_name,
                model_name,
                workload.workload_id,
                "prefix_cache_query",
                request_id=request.request_id,
                shared_prefix_tokens=prefix_hit_tokens,
                block_size_tokens=block_size,
            )
        )
        timestamp_ns += 50

        blocks_used_this_request: list[str] = []

        for block_index, block_tokens in enumerate(full_blocks):
            block_key = _block_key(block_tokens)
            token_start = block_index * block_size
            token_end = token_start + block_size - 1

            events.append(
                _event(
                    run_id,
                    timestamp_ns,
                    engine_name,
                    model_name,
                    workload.workload_id,
                    "block_lookup",
                    request_id=request.request_id,
                    block_key=block_key,
                    block_index=block_index,
                    token_start=token_start,
                    token_end=token_end,
                    block_size_tokens=block_size,
                )
            )
            timestamp_ns += 50

            if block_key in cache:
                cache.move_to_end(block_key)
                events.append(
                    _event(
                        run_id,
                        timestamp_ns,
                        engine_name,
                        model_name,
                        workload.workload_id,
                        "block_hit",
                        source_kind="derived",
                        request_id=request.request_id,
                        block_key=block_key,
                        block_index=block_index,
                    )
                )
            else:
                cache[block_key] = None
                events.append(
                    _event(
                        run_id,
                        timestamp_ns,
                        engine_name,
                        model_name,
                        workload.workload_id,
                        "block_insert",
                        request_id=request.request_id,
                        block_key=block_key,
                        block_index=block_index,
                        token_start=token_start,
                        token_end=token_end,
                        block_size_tokens=block_size,
                    )
                )
            timestamp_ns += 50

            pinned_blocks.add(block_key)
            blocks_used_this_request.append(block_key)
            events.append(
                _event(
                    run_id,
                    timestamp_ns,
                    engine_name,
                    model_name,
                    workload.workload_id,
                    "block_pin",
                    request_id=request.request_id,
                    block_key=block_key,
                    active_sequence_count=1,
                )
            )
            timestamp_ns += 50

        for block_key in blocks_used_this_request:
            pinned_blocks.discard(block_key)
            events.append(
                _event(
                    run_id,
                    timestamp_ns,
                    engine_name,
                    model_name,
                    workload.workload_id,
                    "block_unpin",
                    request_id=request.request_id,
                    block_key=block_key,
                    active_sequence_count=0,
                )
            )
            timestamp_ns += 50

        while len(cache) > cache_capacity_blocks:
            oldest_block_key = next(iter(cache))
            if oldest_block_key in pinned_blocks:
                break
            cache.popitem(last=False)
            events.append(
                _event(
                    run_id,
                    timestamp_ns,
                    engine_name,
                    model_name,
                    workload.workload_id,
                    "block_evict",
                    source_kind="derived",
                    block_key=oldest_block_key,
                    eviction_reason="capacity",
                )
            )
            timestamp_ns += 50

        events.append(
            _event(
                run_id,
                timestamp_ns,
                engine_name,
                model_name,
                workload.workload_id,
                "request_complete",
                request_id=request.request_id,
                status="ok",
            )
        )
        timestamp_ns += 50

    return events


def _event(
    run_id: str,
    timestamp_ns: int,
    engine_name: str,
    model_name: str,
    workload_id: str,
    event_type: str,
    *,
    source_kind: str = "derived",
    **payload: Any,
) -> dict[str, Any]:
    return {
        "schema_version": "kvtrace-v2",
        "run_id": run_id,
        "event_type": event_type,
        "timestamp_ns": timestamp_ns,
        "source_kind": source_kind,
        "engine": engine_name,
        "model": model_name,
        "workload_id": workload_id,
        **payload,
    }


def _chunk_full_blocks(tokens: list[str] | list[int], block_size: int) -> list[list[str] | list[int]]:
    full_token_count = len(tokens) - (len(tokens) % block_size)
    return [
        tokens[index : index + block_size]
        for index in range(0, full_token_count, block_size)
    ]


def _block_key(block_tokens: list[str] | list[int]) -> str:
    encoded = "|".join(str(token) for token in block_tokens).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]
