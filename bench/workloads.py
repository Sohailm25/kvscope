from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


class TokenizerLike(Protocol):
    def encode(self, text: str) -> list[int] | list[str]:
        ...


@dataclass(frozen=True)
class WorkloadRequest:
    request_id: str
    prompt: str
    output_tokens_target: int
    shared_prefix_token_count: int
    arrival_offset_ms: int = 0


@dataclass(frozen=True)
class WorkloadArtifact:
    schema_version: str
    workload_id: str
    workload_family: str
    block_size_tokens: int
    requests: list[WorkloadRequest]


class SimpleWhitespaceTokenizer:
    def encode(self, text: str) -> list[str]:
        return text.split()


def build_aligned_prefix_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    num_requests: int,
    block_size_tokens: int,
    shared_prefix_blocks: int,
    unique_suffix_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    shared_prefix = [
        f"shared_block_{block_index}_token_{token_index}"
        for block_index in range(shared_prefix_blocks)
        for token_index in range(block_size_tokens)
    ]
    requests: list[WorkloadRequest] = []
    shared_prefix_token_count = len(shared_prefix)

    for request_number in range(1, num_requests + 1):
        suffix = [
            f"request_{request_number}_suffix_{token_index}"
            for token_index in range(unique_suffix_tokens)
        ]
        prompt_tokens = shared_prefix + suffix
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, shared_prefix_token_count + unique_suffix_tokens)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_number}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0 if request_number == 1 else shared_prefix_token_count,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="aligned-prefix",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_no_overlap_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    num_requests: int,
    prompt_tokens: int,
    output_tokens: int,
    block_size_tokens: int,
) -> WorkloadArtifact:
    requests: list[WorkloadRequest] = []

    for request_number in range(1, num_requests + 1):
        prompt_token_values = [
            f"request_{request_number}_token_{token_index}"
            for token_index in range(prompt_tokens)
        ]
        prompt = _tokens_to_prompt(prompt_token_values)
        _assert_token_length(tokenizer, prompt, prompt_tokens)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_number}",
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


def build_mixed_long_short_workload(
    *,
    tokenizer: TokenizerLike,
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

    long_prompt_token_values = [
        f"long_request_token_{token_index}" for token_index in range(long_prompt_tokens)
    ]
    short_prompt_token_values = [
        f"short_request_token_{token_index}" for token_index in range(short_prompt_tokens)
    ]

    long_prompt = _tokens_to_prompt(long_prompt_token_values)
    short_prompt = _tokens_to_prompt(short_prompt_token_values)
    _assert_token_length(tokenizer, long_prompt, long_prompt_tokens)
    _assert_token_length(tokenizer, short_prompt, short_prompt_tokens)

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


def build_bursty_arrivals_workload(
    *,
    tokenizer: TokenizerLike,
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

    shared_prefix = [
        f"shared_block_{block_index}_token_{token_index}"
        for block_index in range(shared_prefix_blocks)
        for token_index in range(block_size_tokens)
    ]
    requests: list[WorkloadRequest] = []
    shared_prefix_token_count = len(shared_prefix)
    first_burst_count = num_requests // 2

    for request_number in range(1, num_requests + 1):
        suffix = [
            f"request_{request_number}_suffix_{token_index}"
            for token_index in range(unique_suffix_tokens)
        ]
        prompt_tokens = shared_prefix + suffix
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, shared_prefix_token_count + unique_suffix_tokens)
        requests.append(
            WorkloadRequest(
                request_id=f"req-{request_number}",
                prompt=prompt,
                output_tokens_target=output_tokens,
                shared_prefix_token_count=0 if request_number == 1 else shared_prefix_token_count,
                arrival_offset_ms=0 if request_number <= first_burst_count else burst_gap_ms,
            )
        )

    return WorkloadArtifact(
        schema_version="kvscope-workload-v1",
        workload_id=workload_id,
        workload_family="bursty-arrivals",
        block_size_tokens=block_size_tokens,
        requests=requests,
    )


def build_eviction_ordering_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    hot_block = [f"hot_block_token_{token_index}" for token_index in range(block_size_tokens)]
    suffix_blocks = [
        [f"suffix_a_token_{token_index}" for token_index in range(block_size_tokens)],
        [f"suffix_b_token_{token_index}" for token_index in range(block_size_tokens)],
        [f"suffix_c_token_{token_index}" for token_index in range(block_size_tokens)],
    ]
    suffix_plan = [0, 1, 0, 2, 0, 1]
    requests: list[WorkloadRequest] = []

    for request_index, suffix_index in enumerate(suffix_plan, start=1):
        prompt_tokens = hot_block + suffix_blocks[suffix_index]
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, block_size_tokens * 2)
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


def build_hotset_scan_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
    workload_variant: str = "baseline",
) -> WorkloadArtifact:
    block_names = ("hot", "a", "b", "c", "d", "e", "f", "g")
    blocks = {
        block_name: [
            f"{block_name}_block_token_{token_index}"
            for token_index in range(block_size_tokens)
        ]
        for block_name in block_names
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
        prompt_tokens = blocks[prefix_block] + blocks[suffix_block]
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, block_size_tokens * 2)
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


def build_dual_hotset_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    block_names = ("hot", "pair", "scan", "spill", "return")
    blocks = {
        block_name: [
            f"{block_name}_block_token_{token_index}"
            for token_index in range(block_size_tokens)
        ]
        for block_name in block_names
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
        prompt_tokens = blocks[prefix_block] + blocks[suffix_block]
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, block_size_tokens * 2)
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


def build_locality_shift_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
) -> WorkloadArtifact:
    block_names = ("warm", "a", "b", "cool", "d", "e")
    blocks = {
        block_name: [
            f"{block_name}_block_token_{token_index}"
            for token_index in range(block_size_tokens)
        ]
        for block_name in block_names
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
        prompt_tokens = blocks[prefix_block] + blocks[suffix_block]
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, block_size_tokens * 2)
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


def build_locality_return_workload(
    *,
    tokenizer: TokenizerLike,
    workload_id: str,
    block_size_tokens: int,
    output_tokens: int,
    workload_variant: str = "baseline",
) -> WorkloadArtifact:
    block_names = ("warm", "a", "b", "cool", "d", "e")
    blocks = {
        block_name: [
            f"{block_name}_block_token_{token_index}"
            for token_index in range(block_size_tokens)
        ]
        for block_name in block_names
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
        prompt_tokens = blocks[prefix_block] + blocks[suffix_block]
        prompt = _tokens_to_prompt(prompt_tokens)
        _assert_token_length(tokenizer, prompt, block_size_tokens * 2)
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


def write_workload_artifact(path: Path, artifact: WorkloadArtifact) -> None:
    lines = [
        json.dumps(
            {
                "record_type": "metadata",
                "schema_version": artifact.schema_version,
                "workload_id": artifact.workload_id,
                "workload_family": artifact.workload_family,
                "block_size_tokens": artifact.block_size_tokens,
            }
        )
    ]
    lines.extend(
        json.dumps({"record_type": "request", **asdict(request)})
        for request in artifact.requests
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def load_workload_artifact(path: Path) -> WorkloadArtifact:
    metadata: dict[str, object] | None = None
    requests: list[WorkloadRequest] = []

    for raw_line in path.read_text().splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        if record["record_type"] == "metadata":
            metadata = record
            continue
        requests.append(
            WorkloadRequest(
                request_id=record["request_id"],
                prompt=record["prompt"],
                output_tokens_target=record["output_tokens_target"],
                shared_prefix_token_count=record["shared_prefix_token_count"],
                arrival_offset_ms=int(record.get("arrival_offset_ms", 0)),
            )
        )

    if metadata is None:
        raise ValueError(f"workload artifact {path} is missing metadata")

    return WorkloadArtifact(
        schema_version=str(metadata["schema_version"]),
        workload_id=str(metadata["workload_id"]),
        workload_family=str(metadata["workload_family"]),
        block_size_tokens=int(metadata["block_size_tokens"]),
        requests=requests,
    )


def _assert_token_length(tokenizer: TokenizerLike, prompt: str, expected_tokens: int) -> None:
    actual_tokens = tokenizer.encode(prompt)
    if len(actual_tokens) != expected_tokens:
        raise ValueError(
            f"prompt token length mismatch: expected {expected_tokens}, got {len(actual_tokens)}"
        )


def _tokens_to_prompt(tokens: list[str]) -> str:
    return " ".join(tokens)
