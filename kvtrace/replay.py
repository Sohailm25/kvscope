from __future__ import annotations

import json
import re
from collections import OrderedDict, deque
from pathlib import Path
from typing import Iterable


def replay_block_sequence(
    *,
    policy_name: str,
    capacity_blocks: int,
    block_keys: Iterable[str],
) -> dict[str, float | int | str]:
    if capacity_blocks <= 0:
        raise ValueError("capacity_blocks must be positive")

    policy = policy_name.lower()
    if policy not in {"lru", "fifo", "lfu"}:
        raise ValueError(f"unsupported policy: {policy_name}")

    block_key_list = list(block_keys)
    if policy == "lru":
        return _replay_lru(capacity_blocks=capacity_blocks, block_keys=block_key_list)
    if policy == "lfu":
        return _replay_lfu(capacity_blocks=capacity_blocks, block_keys=block_key_list)
    return _replay_fifo(capacity_blocks=capacity_blocks, block_keys=block_key_list)


def load_block_lookup_keys(path: Path) -> list[str]:
    return [
        event["block_key"]
        for event in _load_trace_events(path)
        if event["event_type"] == "block_lookup"
    ]


def infer_capacity_blocks_from_command(command: str) -> int:
    match = re.search(r"--cache-capacity-blocks\s+(\d+)", command)
    if match is None:
        return 16
    return int(match.group(1))


def _replay_lru(
    *, capacity_blocks: int, block_keys: list[str]
) -> dict[str, float | int | str]:
    cache: OrderedDict[str, None] = OrderedDict()
    hits = 0
    misses = 0

    for block_key in block_keys:
        if block_key in cache:
            hits += 1
            cache.move_to_end(block_key)
            continue

        misses += 1
        if len(cache) >= capacity_blocks:
            cache.popitem(last=False)
        cache[block_key] = None

    return _build_summary("lru", hits=hits, misses=misses)


def _replay_fifo(
    *, capacity_blocks: int, block_keys: list[str]
) -> dict[str, float | int | str]:
    cache: set[str] = set()
    insertion_order: deque[str] = deque()
    hits = 0
    misses = 0

    for block_key in block_keys:
        if block_key in cache:
            hits += 1
            continue

        misses += 1
        if len(cache) >= capacity_blocks:
            evicted = insertion_order.popleft()
            cache.remove(evicted)
        cache.add(block_key)
        insertion_order.append(block_key)

    return _build_summary("fifo", hits=hits, misses=misses)


def _replay_lfu(
    *, capacity_blocks: int, block_keys: list[str]
) -> dict[str, float | int | str]:
    cache: dict[str, tuple[int, int]] = {}
    observed_frequency: dict[str, int] = {}
    hits = 0
    misses = 0

    for access_index, block_key in enumerate(block_keys):
        observed_frequency[block_key] = observed_frequency.get(block_key, 0) + 1
        if block_key in cache:
            hits += 1
            cache[block_key] = (observed_frequency[block_key], access_index)
            continue

        misses += 1
        if len(cache) >= capacity_blocks:
            evicted_key = min(
                cache.items(),
                key=lambda item: (item[1][0], item[1][1]),
            )[0]
            del cache[evicted_key]

        cache[block_key] = (observed_frequency[block_key], access_index)

    return _build_summary("lfu", hits=hits, misses=misses)


def _build_summary(policy_name: str, *, hits: int, misses: int) -> dict[str, float | int | str]:
    total = hits + misses
    return {
        "policy": policy_name,
        "hits": hits,
        "misses": misses,
        "hit_rate": 0.0 if total == 0 else round(hits / total, 3),
        "miss_rate": 0.0 if total == 0 else round(misses / total, 3),
        "lookup_count": total,
    }


def _load_trace_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
