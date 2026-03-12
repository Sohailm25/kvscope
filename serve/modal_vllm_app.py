# ABOUTME: Launches a single vLLM baseline on Modal and drives the first benchmark slice locally.
# ABOUTME: This file is the execution entrypoint for moving KVScope from planning into real serving artifacts.

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Protocol

import modal

from bench.model_workloads import (
    RoundTripTokenizerLike,
    build_model_aligned_prefix_workload,
    build_model_bursty_arrivals_workload,
    build_model_dual_hotset_workload,
    build_model_eviction_ordering_workload,
    build_model_hotset_scan_workload,
    build_model_locality_return_workload,
    build_model_locality_shift_workload,
    build_model_mixed_long_short_workload,
    build_model_near_aligned_prefix_workload,
    build_model_no_overlap_workload,
)
from serve.live_benchmark import persist_run, run_workload, wait_for_model
from serve.live_metrics import build_live_metrics_artifact, scrape_metrics_snapshot
from serve.runtime_contract import (
    HF_CACHE_PATH,
    VLLM_VERSION,
    modal_environment,
    runtime_packages,
)


APP_NAME = "kvscope-vllm"
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
GPU_TYPE = "A10G"
VLLM_API_KEY = "kvscope-local-api-key"

app = modal.App(APP_NAME)
hf_cache = modal.Volume.from_name("kvscope-hf-cache", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    *runtime_packages()
).add_local_python_source("bench", "kvtrace", "serve")
FUNCTION_KWARGS = {
    "image": image,
    "gpu": GPU_TYPE,
    "timeout": 60 * 30,
    "startup_timeout": 60 * 20,
    "scaledown_window": 60 * 10,
    "min_containers": 0,
    "volumes": {HF_CACHE_PATH: hf_cache},
    "env": modal_environment(),
}


def _launch_vllm(*, prefix_caching_enabled: bool) -> None:
    command = [
        "vllm",
        "serve",
        MODEL_NAME,
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--api-key",
        VLLM_API_KEY,
        "--dtype",
        "auto",
        "--gpu-memory-utilization",
        "0.85",
        "--max-model-len",
        "4096",
    ]
    command.append(
        "--enable-prefix-caching" if prefix_caching_enabled else "--no-enable-prefix-caching"
    )
    subprocess.Popen(command)


@app.function(**FUNCTION_KWARGS)
@modal.web_server(8000, startup_timeout=60 * 20)
def serve_vllm_prefix_on() -> None:
    _launch_vllm(prefix_caching_enabled=True)


@app.function(**FUNCTION_KWARGS)
@modal.web_server(8000, startup_timeout=60 * 20)
def serve_vllm_prefix_off() -> None:
    _launch_vllm(prefix_caching_enabled=False)


class WorkloadTokenizerLike(Protocol):
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ...

    def decode(
        self, token_ids: list[int], clean_up_tokenization_spaces: bool = False
    ) -> str:
        ...


def build_workload(
    *,
    workload_family: str,
    workload_variant: str = "baseline",
    tokenizer: RoundTripTokenizerLike | WorkloadTokenizerLike,
    num_requests: int,
    block_size_tokens: int,
    shared_prefix_blocks: int,
    prefix_miss_tokens: int,
    unique_suffix_tokens: int,
    prompt_tokens: int,
    long_prompt_tokens: int,
    short_prompt_tokens: int,
    short_arrival_offset_ms: int,
    burst_gap_ms: int,
    prefix_caching_mode: str,
    output_tokens: int,
):
    del prefix_caching_mode
    if workload_family not in {"hotset-scan", "locality-return"} and workload_variant != "baseline":
        raise ValueError(
            f"workload family `{workload_family}` does not support variant `{workload_variant}`"
        )
    if workload_family == "aligned-prefix":
        return build_model_aligned_prefix_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            num_requests=num_requests,
            block_size_tokens=block_size_tokens,
            shared_prefix_blocks=shared_prefix_blocks,
            unique_suffix_tokens=unique_suffix_tokens,
            output_tokens=output_tokens,
        )
    if workload_family == "near-aligned-prefix":
        return build_model_near_aligned_prefix_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            num_requests=num_requests,
            block_size_tokens=block_size_tokens,
            shared_prefix_blocks=shared_prefix_blocks,
            prefix_miss_tokens=prefix_miss_tokens,
            unique_suffix_tokens=unique_suffix_tokens,
            output_tokens=output_tokens,
        )
    if workload_family == "no-overlap-control":
        return build_model_no_overlap_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            num_requests=num_requests,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            block_size_tokens=block_size_tokens,
        )
    if workload_family == "mixed-long-short":
        return build_model_mixed_long_short_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            long_prompt_tokens=long_prompt_tokens,
            short_prompt_tokens=short_prompt_tokens,
            short_arrival_offset_ms=short_arrival_offset_ms,
            output_tokens=output_tokens,
            block_size_tokens=block_size_tokens,
        )
    if workload_family == "bursty-arrivals":
        return build_model_bursty_arrivals_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            num_requests=num_requests,
            block_size_tokens=block_size_tokens,
            shared_prefix_blocks=shared_prefix_blocks,
            unique_suffix_tokens=unique_suffix_tokens,
            burst_gap_ms=burst_gap_ms,
            output_tokens=output_tokens,
        )
    if workload_family == "eviction-ordering":
        if num_requests != 6:
            raise ValueError("eviction-ordering workload requires num_requests=6")
        return build_model_eviction_ordering_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            block_size_tokens=block_size_tokens,
            output_tokens=output_tokens,
        )
    if workload_family == "hotset-scan":
        if num_requests != 8:
            raise ValueError("hotset-scan workload requires num_requests=8")
        return build_model_hotset_scan_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            block_size_tokens=block_size_tokens,
            output_tokens=output_tokens,
            workload_variant=workload_variant,
        )
    if workload_family == "dual-hotset":
        if num_requests != 8:
            raise ValueError("dual-hotset workload requires num_requests=8")
        return build_model_dual_hotset_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            block_size_tokens=block_size_tokens,
            output_tokens=output_tokens,
        )
    if workload_family == "locality-shift":
        if num_requests != 8:
            raise ValueError("locality-shift workload requires num_requests=8")
        return build_model_locality_shift_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            block_size_tokens=block_size_tokens,
            output_tokens=output_tokens,
        )
    if workload_family == "locality-return":
        if num_requests != 8:
            raise ValueError("locality-return workload requires num_requests=8")
        return build_model_locality_return_workload(
            tokenizer=tokenizer,
            workload_id=_workload_id(workload_family, workload_variant),
            block_size_tokens=block_size_tokens,
            output_tokens=output_tokens,
            workload_variant=workload_variant,
        )
    raise ValueError(
        "workload_family must be 'aligned-prefix', 'near-aligned-prefix', 'no-overlap-control', 'mixed-long-short', 'bursty-arrivals', 'eviction-ordering', 'hotset-scan', 'dual-hotset', 'locality-shift', or 'locality-return'"
    )


def build_invocation_command(
    *,
    workload_family: str,
    workload_variant: str,
    num_requests: int,
    block_size_tokens: int,
    shared_prefix_blocks: int,
    prefix_miss_tokens: int,
    unique_suffix_tokens: int,
    prompt_tokens: int,
    long_prompt_tokens: int,
    short_prompt_tokens: int,
    short_arrival_offset_ms: int,
    burst_gap_ms: int,
    prefix_caching_mode: str,
    output_tokens: int,
    run_slug: str,
    cache_capacity_blocks: int,
) -> str:
    return (
        "modal run serve/modal_vllm_app.py "
        f"--workload-family {workload_family} "
        f"--workload-variant {workload_variant} "
        f"--num-requests {num_requests} "
        f"--block-size-tokens {block_size_tokens} "
        f"--shared-prefix-blocks {shared_prefix_blocks} "
        f"--prefix-miss-tokens {prefix_miss_tokens} "
        f"--unique-suffix-tokens {unique_suffix_tokens} "
        f"--prompt-tokens {prompt_tokens} "
        f"--long-prompt-tokens {long_prompt_tokens} "
        f"--short-prompt-tokens {short_prompt_tokens} "
        f"--short-arrival-offset-ms {short_arrival_offset_ms} "
        f"--burst-gap-ms {burst_gap_ms} "
        f"--prefix-caching-mode {prefix_caching_mode} "
        f"--output-tokens {output_tokens} "
        f"--run-slug {run_slug} "
        f"--cache-capacity-blocks {cache_capacity_blocks}"
    )


@app.local_entrypoint()
def main(
    workload_family: str = "aligned-prefix",
    workload_variant: str = "baseline",
    num_requests: int = 4,
    block_size_tokens: int = 16,
    shared_prefix_blocks: int = 8,
    prefix_miss_tokens: int = 3,
    unique_suffix_tokens: int = 16,
    prompt_tokens: int = 96,
    long_prompt_tokens: int = 160,
    short_prompt_tokens: int = 24,
    short_arrival_offset_ms: int = 25,
    burst_gap_ms: int = 120,
    prefix_caching_mode: str = "on",
    output_tokens: int = 24,
    run_slug: str = "first-slice",
    cache_capacity_blocks: int = 16,
) -> None:
    from transformers import AutoTokenizer

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    repo_root = Path(__file__).resolve().parents[1]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    workload = build_workload(
        workload_family=workload_family,
        workload_variant=workload_variant,
        tokenizer=tokenizer,
        num_requests=num_requests,
        block_size_tokens=block_size_tokens,
        shared_prefix_blocks=shared_prefix_blocks,
        prefix_miss_tokens=prefix_miss_tokens,
        unique_suffix_tokens=unique_suffix_tokens,
        prompt_tokens=prompt_tokens,
        long_prompt_tokens=long_prompt_tokens,
        short_prompt_tokens=short_prompt_tokens,
        short_arrival_offset_ms=short_arrival_offset_ms,
        burst_gap_ms=burst_gap_ms,
        prefix_caching_mode=prefix_caching_mode,
        output_tokens=output_tokens,
    )

    prefix_caching_enabled = _resolve_prefix_caching_mode(prefix_caching_mode)
    base_url = (
        serve_vllm_prefix_on.get_web_url()
        if prefix_caching_enabled
        else serve_vllm_prefix_off.get_web_url()
    )
    if base_url is None:
        raise RuntimeError("Modal did not provide a web URL for the vLLM endpoint")

    wait_for_model(base_url=base_url, api_key=VLLM_API_KEY, timeout_seconds=60 * 20)
    live_metrics_before = scrape_metrics_snapshot(base_url=base_url)
    observations = run_workload(
        base_url=base_url,
        api_key=VLLM_API_KEY,
        model_name=MODEL_NAME,
        workload=workload,
        tokenizer=tokenizer,
    )
    live_metrics_after = scrape_metrics_snapshot(base_url=base_url)
    run_dir = persist_run(
        repo_root=repo_root,
        workload=workload,
        tokenizer=tokenizer,
        observations=observations,
        engine_name="vllm",
        engine_version=VLLM_VERSION,
        model_name=MODEL_NAME,
        gpu_type=GPU_TYPE,
        prefix_caching_enabled=prefix_caching_enabled,
        cold_start=True,
        warmup_requests_discarded=0,
        run_slug=run_slug,
        command=build_invocation_command(
            workload_family=workload_family,
            workload_variant=workload_variant,
            num_requests=num_requests,
            block_size_tokens=block_size_tokens,
            shared_prefix_blocks=shared_prefix_blocks,
            prefix_miss_tokens=prefix_miss_tokens,
            unique_suffix_tokens=unique_suffix_tokens,
            prompt_tokens=prompt_tokens,
            long_prompt_tokens=long_prompt_tokens,
            short_prompt_tokens=short_prompt_tokens,
            short_arrival_offset_ms=short_arrival_offset_ms,
            burst_gap_ms=burst_gap_ms,
            prefix_caching_mode=prefix_caching_mode,
            output_tokens=output_tokens,
            run_slug=run_slug,
            cache_capacity_blocks=cache_capacity_blocks,
        ),
        stdout_text=(
            f"base_url={base_url}\n"
            f"workload_family={workload.workload_family}\n"
            f"workload_variant={workload_variant}\n"
            f"num_requests={len(workload.requests)}\n"
            f"prefix_caching_enabled={prefix_caching_enabled}\n"
        ),
        stderr_text="",
        cache_capacity_blocks=cache_capacity_blocks,
        live_metrics=build_live_metrics_artifact(
            before=live_metrics_before,
            after=live_metrics_after,
        ),
    )
    print(f"Run directory: {run_dir}")


def _resolve_prefix_caching_mode(prefix_caching_mode: str) -> bool:
    normalized = prefix_caching_mode.strip().lower()
    if normalized == "on":
        return True
    if normalized == "off":
        return False
    raise ValueError("prefix_caching_mode must be 'on' or 'off'")


def _workload_id(workload_family: str, workload_variant: str) -> str:
    if workload_variant == "baseline":
        return f"{workload_family}-demo"
    return f"{workload_family}-{workload_variant}-demo"
