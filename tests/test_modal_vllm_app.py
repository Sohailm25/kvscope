import unittest

from serve.modal_vllm_app import FUNCTION_KWARGS, build_invocation_command, build_workload


class _FakeTokenizer:
    def __init__(self) -> None:
        self.all_special_ids = {0}
        self.vocab_size = 64
        self._id_to_token = {index: f"tok{index}" for index in range(1, self.vocab_size)}
        self._token_to_id = {token: index for index, token in self._id_to_token.items()}

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        del add_special_tokens
        return [self._token_to_id[token] for token in text.split()]

    def decode(
        self, token_ids: list[int], clean_up_tokenization_spaces: bool = False
    ) -> str:
        del clean_up_tokenization_spaces
        return " ".join(self._id_to_token[token_id] for token_id in token_ids)


class ModalVllmAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tokenizer = _FakeTokenizer()

    def test_modal_function_defaults_do_not_prewarm_both_cache_modes(self) -> None:
        self.assertEqual(FUNCTION_KWARGS["min_containers"], 0)

    def test_build_workload_supports_near_aligned_prefix(self) -> None:
        workload = build_workload(
            workload_family="near-aligned-prefix",
            tokenizer=self.tokenizer,
            num_requests=2,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "near-aligned-prefix")
        self.assertEqual(workload.requests[1].shared_prefix_token_count, 7)

    def test_build_workload_supports_bursty_arrivals(self) -> None:
        workload = build_workload(
            workload_family="bursty-arrivals",
            tokenizer=self.tokenizer,
            num_requests=4,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "bursty-arrivals")
        self.assertEqual(
            [request.arrival_offset_ms for request in workload.requests],
            [0, 0, 120, 120],
        )

    def test_build_workload_supports_eviction_ordering(self) -> None:
        workload = build_workload(
            workload_family="eviction-ordering",
            tokenizer=self.tokenizer,
            num_requests=6,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "eviction-ordering")
        self.assertEqual(len(workload.requests), 6)
        self.assertEqual(workload.requests[5].shared_prefix_token_count, 4)

    def test_build_workload_supports_hotset_scan(self) -> None:
        workload = build_workload(
            workload_family="hotset-scan",
            tokenizer=self.tokenizer,
            num_requests=8,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "hotset-scan")
        self.assertEqual(len(workload.requests), 8)
        self.assertEqual(workload.requests[7].shared_prefix_token_count, 4)

    def test_build_workload_supports_locality_shift(self) -> None:
        workload = build_workload(
            workload_family="locality-shift",
            tokenizer=self.tokenizer,
            num_requests=8,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "locality-shift")
        self.assertEqual(len(workload.requests), 8)
        self.assertEqual(
            [request.shared_prefix_token_count for request in workload.requests],
            [0, 4, 4, 4, 0, 4, 4, 4],
        )

    def test_build_workload_supports_locality_return(self) -> None:
        workload = build_workload(
            workload_family="locality-return",
            tokenizer=self.tokenizer,
            num_requests=8,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "locality-return")
        self.assertEqual(len(workload.requests), 8)
        self.assertEqual(
            [request.shared_prefix_token_count for request in workload.requests],
            [0, 4, 4, 0, 4, 4, 0, 4],
        )

    def test_build_workload_supports_dual_hotset(self) -> None:
        workload = build_workload(
            workload_family="dual-hotset",
            tokenizer=self.tokenizer,
            num_requests=8,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "dual-hotset")
        self.assertEqual(len(workload.requests), 8)
        self.assertEqual(
            [request.shared_prefix_token_count for request in workload.requests],
            [0, 4, 4, 0, 0, 4, 4, 4],
        )

    def test_build_workload_supports_hotset_revisit_variant(self) -> None:
        workload = build_workload(
            workload_family="hotset-scan",
            tokenizer=self.tokenizer,
            workload_variant="revisit",
            num_requests=8,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "hotset-scan")
        self.assertEqual(
            [request.shared_prefix_token_count for request in workload.requests],
            [0, 4, 4, 0, 4, 4, 4, 4],
        )

    def test_build_workload_supports_locality_return_concentrated_variant(self) -> None:
        workload = build_workload(
            workload_family="locality-return",
            tokenizer=self.tokenizer,
            workload_variant="concentrated",
            num_requests=8,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            prompt_tokens=12,
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=16,
        )

        self.assertEqual(workload.workload_family, "locality-return")
        self.assertEqual(
            [request.shared_prefix_token_count for request in workload.requests],
            [0, 4, 4, 0, 4, 4, 0, 4],
        )

    def test_build_workload_rejects_unknown_family(self) -> None:
        with self.assertRaises(ValueError):
            build_workload(
                workload_family="bad-family",
                tokenizer=self.tokenizer,
                num_requests=2,
                block_size_tokens=4,
                shared_prefix_blocks=2,
                prefix_miss_tokens=1,
                unique_suffix_tokens=3,
                prompt_tokens=12,
                long_prompt_tokens=12,
                short_prompt_tokens=4,
                short_arrival_offset_ms=25,
                burst_gap_ms=120,
                prefix_caching_mode="on",
                output_tokens=16,
            )

    def test_build_invocation_command_includes_workload_geometry(self) -> None:
        command = build_invocation_command(
            workload_family="near-aligned-prefix",
            workload_variant="baseline",
            num_requests=2,
            block_size_tokens=16,
            shared_prefix_blocks=4,
            prefix_miss_tokens=3,
            unique_suffix_tokens=8,
            prompt_tokens=72,
            long_prompt_tokens=160,
            short_prompt_tokens=24,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="off",
            output_tokens=8,
            run_slug="smoke-near-aligned",
            cache_capacity_blocks=16,
        )

        self.assertIn("--workload-family near-aligned-prefix", command)
        self.assertIn("--shared-prefix-blocks 4", command)
        self.assertIn("--prefix-miss-tokens 3", command)
        self.assertIn("--prompt-tokens 72", command)
        self.assertIn("--long-prompt-tokens 160", command)
        self.assertIn("--short-arrival-offset-ms 25", command)
        self.assertIn("--burst-gap-ms 120", command)
        self.assertIn("--prefix-caching-mode off", command)
        self.assertIn("--run-slug smoke-near-aligned", command)

    def test_build_invocation_command_records_workload_variant(self) -> None:
        command = build_invocation_command(
            workload_family="locality-return",
            workload_variant="concentrated",
            num_requests=8,
            block_size_tokens=16,
            shared_prefix_blocks=8,
            prefix_miss_tokens=3,
            unique_suffix_tokens=16,
            prompt_tokens=96,
            long_prompt_tokens=160,
            short_prompt_tokens=24,
            short_arrival_offset_ms=25,
            burst_gap_ms=120,
            prefix_caching_mode="on",
            output_tokens=24,
            run_slug="smoke-locality-return-concentrated",
            cache_capacity_blocks=2,
        )

        self.assertIn("--workload-variant concentrated", command)
