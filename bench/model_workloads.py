from __future__ import annotations

from typing import Protocol

from bench.workloads import WorkloadArtifact, WorkloadRequest


class RoundTripTokenizerLike(Protocol):
    all_special_ids: set[int] | list[int]
    vocab_size: int

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ...

    def decode(
        self, token_ids: list[int], clean_up_tokenization_spaces: bool = False
    ) -> str:
        ...


def build_model_aligned_prefix_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    num_requests: int,
    block_size_tokens: int,
    shared_prefix_blocks: int,
    unique_suffix_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(
        tokenizer,
        shared_prefix_blocks * block_size_tokens + num_requests * unique_suffix_tokens + 16,
    )
    shared_prefix_token_ids = stable_token_ids[: shared_prefix_blocks * block_size_tokens]
    requests: list[WorkloadRequest] = []

    offset = len(shared_prefix_token_ids)
    for request_index in range(num_requests):
        suffix_start = offset + request_index * unique_suffix_tokens
        suffix_end = suffix_start + unique_suffix_tokens
        prompt_token_ids = shared_prefix_token_ids + stable_token_ids[suffix_start:suffix_end]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)

        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index + 1}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0
                if request_index == 0
                else len(shared_prefix_token_ids),
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="aligned-prefix",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_near_aligned_prefix_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    num_requests: int,
    block_size_tokens: int,
    shared_prefix_blocks: int,
    prefix_miss_tokens: int,
    unique_suffix_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    if prefix_miss_tokens <= 0 or prefix_miss_tokens >= block_size_tokens:
        raise ValueError(
            "prefix_miss_tokens must be greater than 0 and less than block_size_tokens"
        )

    shared_prefix_token_count = shared_prefix_blocks * block_size_tokens - prefix_miss_tokens
    if shared_prefix_token_count <= 0:
        raise ValueError("near-aligned workload must retain at least one shared token")

    stable_token_ids = _find_stable_token_ids(
        tokenizer,
        shared_prefix_token_count + num_requests * unique_suffix_tokens + 16,
    )
    shared_prefix_token_ids = stable_token_ids[:shared_prefix_token_count]
    requests: list[WorkloadRequest] = []

    offset = len(shared_prefix_token_ids)
    for request_index in range(num_requests):
        suffix_start = offset + request_index * unique_suffix_tokens
        suffix_end = suffix_start + unique_suffix_tokens
        prompt_token_ids = shared_prefix_token_ids + stable_token_ids[suffix_start:suffix_end]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)

        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index + 1}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0
                if request_index == 0
                else len(shared_prefix_token_ids),
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="near-aligned-prefix",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_no_overlap_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    num_requests: int,
    prompt_tokens: int,
    output_tokens: int,
    block_size_tokens: int,
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(
        tokenizer, num_requests * prompt_tokens + 16
    )
    requests: list[WorkloadRequest] = []

    for request_index in range(num_requests):
        start = request_index * prompt_tokens
        end = start + prompt_tokens
        prompt_token_ids = stable_token_ids[start:end]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)

        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index + 1}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="no-overlap-control",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_mixed_long_short_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    long_prompt_tokens: int,
    short_prompt_tokens: int,
    short_arrival_offset_ms: int,
    output_tokens: int,
    block_size_tokens: int,
) -> WorkloadArtifact:
    if short_arrival_offset_ms < 0:
        raise ValueError("short_arrival_offset_ms must be non-negative")
    if short_prompt_tokens >= long_prompt_tokens:
        raise ValueError("short_prompt_tokens must be less than long_prompt_tokens")

    stable_token_ids = _find_stable_token_ids(
        tokenizer, long_prompt_tokens + short_prompt_tokens + 16
    )
    long_prompt = _materialize_prompt(tokenizer, stable_token_ids[:long_prompt_tokens])
    short_prompt = _materialize_prompt(
        tokenizer,
        stable_token_ids[long_prompt_tokens : long_prompt_tokens + short_prompt_tokens],
    )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="mixed-long-short",
        block_size_tokens=block_size_tokens,
        requests=[
            WorkloadRequest(
                request_id="req-1",
                prompt=long_prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0,
                arrival_offset_ms=0,
            ),
            WorkloadRequest(
                request_id="req-2",
                prompt=short_prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0,
                arrival_offset_ms=short_arrival_offset_ms,
            ),
        ],
    )


def build_model_bursty_arrivals_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    num_requests: int,
    block_size_tokens: int,
    shared_prefix_blocks: int,
    unique_suffix_tokens: int,
    burst_gap_ms: int,
    output_tokens: int,
) -> WorkloadArtifact:
    if num_requests < 2 or num_requests % 2 != 0:
        raise ValueError("num_requests must be an even number greater than or equal to 2")
    if burst_gap_ms < 0:
        raise ValueError("burst_gap_ms must be non-negative")

    stable_token_ids = _find_stable_token_ids(
        tokenizer,
        shared_prefix_blocks * block_size_tokens + num_requests * unique_suffix_tokens + 16,
    )
    shared_prefix_token_ids = stable_token_ids[: shared_prefix_blocks * block_size_tokens]
    requests: list[WorkloadRequest] = []
    offset = len(shared_prefix_token_ids)
    first_burst_count = num_requests // 2

    for request_index in range(num_requests):
        suffix_start = offset + request_index * unique_suffix_tokens
        suffix_end = suffix_start + unique_suffix_tokens
        prompt_token_ids = shared_prefix_token_ids + stable_token_ids[suffix_start:suffix_end]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)

        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index + 1}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0
                if request_index == 0
                else len(shared_prefix_token_ids),
                arrival_offset_ms=0
                if request_index < first_burst_count
                else burst_gap_ms,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="bursty-arrivals",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_eviction_ordering_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(tokenizer, block_size_tokens * 4 + 16)
    hot_block = stable_token_ids[:block_size_tokens]
    suffix_blocks = [
        stable_token_ids[block_size_tokens : block_size_tokens * 2],
        stable_token_ids[block_size_tokens * 2 : block_size_tokens * 3],
        stable_token_ids[block_size_tokens * 3 : block_size_tokens * 4],
    ]
    suffix_plan = [0, 1, 0, 2, 0, 1]
    requests: list[WorkloadRequest] = []

    for request_index, suffix_index in enumerate(suffix_plan, start=1):
        prompt_token_ids = hot_block + suffix_blocks[suffix_index]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0 if request_index == 1 else block_size_tokens,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="eviction-ordering",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_hotset_scan_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
    workload_variant: str = "baseline",
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(tokenizer, block_size_tokens * 8 + 16)
    block_names = ("hot", "a", "b", "c", "d", "e", "f", "g")
    blocks = {
        block_name: stable_token_ids[index * block_size_tokens : (index + 1) * block_size_tokens]
        for index, block_name in enumerate(block_names)
    }
    if workload_variant == "baseline":
        block_plan = [
            ("hot", "a"),
            ("hot", "b"),
            ("hot", "c"),
            ("hot", "a"),
            ("d", "e"),
            ("f", "g"),
            ("hot", "a"),
            ("hot", "b"),
        ]
        cold_request_indexes = {1, 5, 6}
    elif workload_variant == "revisit":
        block_plan = [
            ("hot", "a"),
            ("hot", "b"),
            ("hot", "c"),
            ("d", "e"),
            ("hot", "a"),
            ("hot", "b"),
            ("hot", "c"),
            ("hot", "a"),
        ]
        cold_request_indexes = {1, 4}
    else:
        raise ValueError(f"unsupported hotset-scan workload variant: {workload_variant}")
    requests: list[WorkloadRequest] = []

    for request_index, (prefix_block, suffix_block) in enumerate(block_plan, start=1):
        prompt_token_ids = blocks[prefix_block] + blocks[suffix_block]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0
                if request_index in cold_request_indexes
                else block_size_tokens,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="hotset-scan",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_dual_hotset_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(tokenizer, block_size_tokens * 5 + 16)
    block_names = ("hot", "pair", "scan", "spill", "return")
    blocks = {
        block_name: stable_token_ids[index * block_size_tokens : (index + 1) * block_size_tokens]
        for index, block_name in enumerate(block_names)
    }
    block_plan = [
        ("hot", "pair"),
        ("hot", "pair"),
        ("hot", "pair"),
        ("scan", "spill"),
        ("pair", "return"),
        ("hot", "pair"),
        ("hot", "return"),
        ("hot", "pair"),
    ]
    requests: list[WorkloadRequest] = []

    for request_index, (prefix_block, suffix_block) in enumerate(block_plan, start=1):
        prompt_token_ids = blocks[prefix_block] + blocks[suffix_block]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0
                if request_index in {1, 4, 5}
                else block_size_tokens,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="dual-hotset",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_locality_shift_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(tokenizer, block_size_tokens * 6 + 16)
    block_names = ("warm", "a", "b", "cool", "d", "e")
    blocks = {
        block_name: stable_token_ids[index * block_size_tokens : (index + 1) * block_size_tokens]
        for index, block_name in enumerate(block_names)
    }
    block_plan = [
        ("warm", "a"),
        ("warm", "b"),
        ("warm", "a"),
        ("warm", "b"),
        ("cool", "d"),
        ("cool", "e"),
        ("cool", "d"),
        ("cool", "e"),
    ]
    requests: list[WorkloadRequest] = []

    for request_index, (prefix_block, suffix_block) in enumerate(block_plan, start=1):
        prompt_token_ids = blocks[prefix_block] + blocks[suffix_block]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0 if request_index in {1, 5} else block_size_tokens,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="locality-shift",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_model_locality_return_workload(
    *,
    tokenizer: RoundTripTokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
    workload_variant: str = "baseline",
) -> WorkloadArtifact:
    stable_token_ids = _find_stable_token_ids(tokenizer, block_size_tokens * 6 + 16)
    block_names = ("warm", "a", "b", "cool", "d", "e")
    blocks = {
        block_name: stable_token_ids[index * block_size_tokens : (index + 1) * block_size_tokens]
        for index, block_name in enumerate(block_names)
    }
    if workload_variant == "baseline":
        block_plan = [
            ("warm", "a"),
            ("warm", "b"),
            ("warm", "a"),
            ("cool", "d"),
            ("cool", "e"),
            ("cool", "d"),
            ("warm", "a"),
            ("warm", "b"),
        ]
    elif workload_variant == "concentrated":
        block_plan = [
            ("warm", "a"),
            ("warm", "b"),
            ("warm", "a"),
            ("cool", "d"),
            ("cool", "e"),
            ("cool", "d"),
            ("warm", "a"),
            ("warm", "a"),
        ]
    else:
        raise ValueError(f"unsupported locality-return workload variant: {workload_variant}")
    requests: list[WorkloadRequest] = []

    for request_index, (prefix_block, suffix_block) in enumerate(block_plan, start=1):
        prompt_token_ids = blocks[prefix_block] + blocks[suffix_block]
        prompt = _materialize_prompt(tokenizer, prompt_token_ids)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_index}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0 if request_index in {1, 4, 7} else block_size_tokens,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="locality-return",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def _find_stable_token_ids(
    tokenizer: RoundTripTokenizerLike, minimum_count: int
) -> list[int]:
    special_ids = set(tokenizer.all_special_ids)
    preferred_ids: list[int] = []
    fallback_ids: list[int] = []

    for token_id in range(tokenizer.vocab_size):
        if token_id in special_ids:
            continue
        text = tokenizer.decode([token_id], clean_up_tokenization_spaces=False)
        if not text.strip():
            continue
        if tokenizer.encode(text, add_special_tokens=False) == [token_id]:
            if text.startswith(" "):
                preferred_ids.append(token_id)
            else:
                fallback_ids.append(token_id)
        if len(preferred_ids) >= minimum_count:
            return preferred_ids

    combined_ids = preferred_ids + fallback_ids
    if len(combined_ids) >= minimum_count:
        return combined_ids[:minimum_count]

    raise ValueError(
        f"tokenizer only exposed {len(combined_ids)} stable token ids; need {minimum_count}"
    )


def _materialize_prompt(
    tokenizer: RoundTripTokenizerLike, token_ids: list[int]
) -> str:
    candidates = [
        "".join(
            tokenizer.decode([token_id], clean_up_tokenization_spaces=False)
            for token_id in token_ids
        ),
        tokenizer.decode(token_ids, clean_up_tokenization_spaces=False),
    ]

    seen_candidates: set[str] = set()
    for candidate in candidates:
        if candidate in seen_candidates:
            continue
        seen_candidates.add(candidate)
        try:
            encoded = tokenizer.encode(candidate, add_special_tokens=False)
        except Exception:  # noqa: BLE001
            continue
        if encoded == token_ids:
            return candidate

    raise ValueError("tokenizer did not round-trip prompt")
