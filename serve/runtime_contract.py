from __future__ import annotations


VLLM_VERSION = "0.8.3"
TRANSFORMERS_VERSION = "4.51.3"
OPENAI_VERSION = "2.26.0"
REQUESTS_VERSION = "2.32.5"
HF_CACHE_PATH = "/root/.cache/huggingface"


def runtime_packages() -> tuple[str, ...]:
    return (
        f"vllm=={VLLM_VERSION}",
        f"transformers=={TRANSFORMERS_VERSION}",
        f"openai=={OPENAI_VERSION}",
        f"requests=={REQUESTS_VERSION}",
    )


def modal_environment() -> dict[str, str]:
    return {
        "HF_HOME": HF_CACHE_PATH,
        "HUGGINGFACE_HUB_CACHE": HF_CACHE_PATH,
        "TOKENIZERS_PARALLELISM": "false",
    }
