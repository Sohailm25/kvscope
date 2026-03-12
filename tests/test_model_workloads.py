import unittest

from bench.model_workloads import (
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


class FakeRoundTripTokenizer:
    def __init__(self) -> None:
        self.all_special_ids = {0}
        self.vocab_size = 64
        self._id_to_token = {index: f"tok{index}" for index in range(1, self.vocab_size)}
        self._token_to_id = {token: index for index, token in self._id_to_token.items()}

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return [self._token_to_id[token] for token in text.split()]

    def decode(
        self, token_ids: list[int], clean_up_tokenization_spaces: bool = False
    ) -> str:
        return " ".join(self._id_to_token[token_id] for token_id in token_ids)


class ModelAwareWorkloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tokenizer = FakeRoundTripTokenizer()

    def test_model_aligned_prefix_workload_uses_real_tokenizer_counts(self) -> None:
        artifact = build_model_aligned_prefix_workload(
            tokenizer=self.tokenizer,
            workload_id="aligned-model-demo",
            num_requests=2,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            unique_suffix_tokens=3,
            output_tokens=16,
        )

        first_prompt_tokens = self.tokenizer.encode(artifact.requests[0].prompt)
        second_prompt_tokens = self.tokenizer.encode(artifact.requests[1].prompt)

        self.assertEqual(first_prompt_tokens[:8], second_prompt_tokens[:8])
        self.assertNotEqual(first_prompt_tokens[8:], second_prompt_tokens[8:])
        self.assertEqual(artifact.requests[1].shared_prefix_token_count, 8)

    def test_model_no_overlap_workload_keeps_unique_prefixes(self) -> None:
        artifact = build_model_no_overlap_workload(
            tokenizer=self.tokenizer,
            workload_id="no-overlap-model-demo",
            num_requests=3,
            prompt_tokens=8,
            output_tokens=16,
            block_size_tokens=4,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "no-overlap-control")
        self.assertNotEqual(prompts[0][:4], prompts[1][:4])

    def test_model_near_aligned_workload_misses_next_full_block_boundary(self) -> None:
        artifact = build_model_near_aligned_prefix_workload(
            tokenizer=self.tokenizer,
            workload_id="near-aligned-model-demo",
            num_requests=2,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            prefix_miss_tokens=1,
            unique_suffix_tokens=3,
            output_tokens=16,
        )

        first_prompt_tokens = self.tokenizer.encode(artifact.requests[0].prompt)
        second_prompt_tokens = self.tokenizer.encode(artifact.requests[1].prompt)

        self.assertEqual(artifact.workload_family, "near-aligned-prefix")
        self.assertEqual(first_prompt_tokens[:7], second_prompt_tokens[:7])
        self.assertNotEqual(first_prompt_tokens[7:], second_prompt_tokens[7:])
        self.assertEqual(artifact.requests[1].shared_prefix_token_count, 7)

    def test_model_mixed_long_short_workload_respects_prompt_sizes_and_arrival(self) -> None:
        artifact = build_model_mixed_long_short_workload(
            tokenizer=self.tokenizer,
            workload_id="mixed-model-demo",
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            output_tokens=8,
            block_size_tokens=4,
        )

        self.assertEqual(artifact.workload_family, "mixed-long-short")
        self.assertEqual(
            len(self.tokenizer.encode(artifact.requests[0].prompt)),
            12,
        )
        self.assertEqual(
            len(self.tokenizer.encode(artifact.requests[1].prompt)),
            4,
        )
        self.assertEqual(
            [request.arrival_offset_ms for request in artifact.requests],
            [0, 25],
        )

    def test_model_bursty_arrivals_workload_preserves_shared_prefix_and_bursts(self) -> None:
        artifact = build_model_bursty_arrivals_workload(
            tokenizer=self.tokenizer,
            workload_id="bursty-model-demo",
            num_requests=4,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            unique_suffix_tokens=3,
            burst_gap_ms=120,
            output_tokens=16,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "bursty-arrivals")
        self.assertEqual(prompts[0][:8], prompts[3][:8])
        self.assertEqual(
            [request.arrival_offset_ms for request in artifact.requests],
            [0, 0, 120, 120],
        )
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 8, 8, 8],
        )

    def test_model_eviction_ordering_workload_preserves_hot_prefix_pattern(self) -> None:
        artifact = build_model_eviction_ordering_workload(
            tokenizer=self.tokenizer,
            workload_id="eviction-model-demo",
            block_size_tokens=4,
            output_tokens=16,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "eviction-ordering")
        self.assertEqual(len(artifact.requests), 6)
        self.assertTrue(all(prompt[:4] == prompts[0][:4] for prompt in prompts[1:]))
        self.assertEqual(prompts[0][4:8], prompts[2][4:8])
        self.assertEqual(prompts[0][4:8], prompts[4][4:8])
        self.assertEqual(prompts[1][4:8], prompts[5][4:8])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 4, 4, 4],
        )

    def test_model_hotset_scan_workload_preserves_hot_prefix_and_scan_tail(self) -> None:
        artifact = build_model_hotset_scan_workload(
            tokenizer=self.tokenizer,
            workload_id="hotset-scan-model-demo",
            block_size_tokens=4,
            output_tokens=16,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "hotset-scan")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[1][:4])
        self.assertEqual(prompts[0][:4], prompts[3][:4])
        self.assertNotEqual(prompts[4][:4], prompts[0][:4])
        self.assertEqual(prompts[6][:4], prompts[0][:4])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 4, 0, 0, 4, 4],
        )

    def test_model_locality_shift_workload_switches_to_a_new_hot_prefix(self) -> None:
        artifact = build_model_locality_shift_workload(
            tokenizer=self.tokenizer,
            workload_id="locality-shift-model-demo",
            block_size_tokens=4,
            output_tokens=16,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "locality-shift")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[1][:4])
        self.assertEqual(prompts[0][:4], prompts[3][:4])
        self.assertNotEqual(prompts[0][:4], prompts[4][:4])
        self.assertEqual(prompts[4][:4], prompts[7][:4])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 4, 0, 4, 4, 4],
        )

    def test_model_hotset_scan_workload_supports_revisit_variant(self) -> None:
        artifact = build_model_hotset_scan_workload(
            tokenizer=self.tokenizer,
            workload_id="hotset-scan-revisit-model-demo",
            block_size_tokens=4,
            output_tokens=16,
            workload_variant="revisit",
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "hotset-scan")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[4][:4], prompts[0][:4])
        self.assertEqual(prompts[7][:4], prompts[0][:4])
        self.assertEqual(prompts[4][4:8], prompts[0][4:8])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 0, 4, 4, 4, 4],
        )

    def test_model_locality_return_workload_returns_to_original_prefix_after_shift(self) -> None:
        artifact = build_model_locality_return_workload(
            tokenizer=self.tokenizer,
            workload_id="locality-return-model-demo",
            block_size_tokens=4,
            output_tokens=16,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "locality-return")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[1][:4])
        self.assertEqual(prompts[0][:4], prompts[2][:4])
        self.assertNotEqual(prompts[0][:4], prompts[3][:4])
        self.assertEqual(prompts[3][:4], prompts[4][:4])
        self.assertEqual(prompts[0][:4], prompts[6][:4])
        self.assertEqual(prompts[0][:4], prompts[7][:4])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 0, 4, 4, 0, 4],
        )

    def test_model_dual_hotset_workload_keeps_frequency_biased_blocks_under_scan_pressure(self) -> None:
        artifact = build_model_dual_hotset_workload(
            tokenizer=self.tokenizer,
            workload_id="dual-hotset-model-demo",
            block_size_tokens=4,
            output_tokens=16,
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "dual-hotset")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[1][:4])
        self.assertEqual(prompts[0][:4], prompts[2][:4])
        self.assertNotEqual(prompts[0][:4], prompts[3][:4])
        self.assertNotEqual(prompts[0][:4], prompts[4][:4])
        self.assertEqual(prompts[0][:4], prompts[5][:4])
        self.assertEqual(prompts[0][:4], prompts[7][:4])
        self.assertEqual(prompts[0][4:], prompts[1][4:])
        self.assertEqual(prompts[0][4:], prompts[2][4:])
        self.assertEqual(prompts[0][4:], prompts[5][4:])
        self.assertEqual(prompts[0][4:], prompts[7][4:])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 0, 0, 4, 4, 4],
        )

    def test_model_locality_return_workload_supports_concentrated_variant(self) -> None:
        artifact = build_model_locality_return_workload(
            tokenizer=self.tokenizer,
            workload_id="locality-return-concentrated-model-demo",
            block_size_tokens=4,
            output_tokens=16,
            workload_variant="concentrated",
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "locality-return")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[6][:4])
        self.assertEqual(prompts[0][:4], prompts[7][:4])
        self.assertEqual(prompts[0][4:8], prompts[6][4:8])
        self.assertEqual(prompts[0][4:8], prompts[7][4:8])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 0, 4, 4, 0, 4],
        )
