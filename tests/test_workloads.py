import json
import tempfile
import unittest
from pathlib import Path

from bench.workloads import (
    SimpleWhitespaceTokenizer,
    build_aligned_prefix_workload,
    build_bursty_arrivals_workload,
    build_dual_hotset_workload,
    build_eviction_ordering_workload,
    build_hotset_scan_workload,
    build_locality_return_workload,
    build_locality_shift_workload,
    build_mixed_long_short_workload,
    build_no_overlap_workload,
    load_workload_artifact,
    write_workload_artifact,
)


class WorkloadGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tokenizer = SimpleWhitespaceTokenizer()

    def test_aligned_prefix_workload_preserves_full_block_prefix(self) -> None:
        artifact = build_aligned_prefix_workload(
            tokenizer=self.tokenizer,
            workload_id="aligned-demo",
            num_requests=3,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            unique_suffix_tokens=3,
            output_tokens=32,
        )

        self.assertEqual(artifact.workload_family, "aligned-prefix")
        self.assertEqual(len(artifact.requests), 3)

        first_tokens = self.tokenizer.encode(artifact.requests[0].prompt)
        second_tokens = self.tokenizer.encode(artifact.requests[1].prompt)

        self.assertEqual(first_tokens[:8], second_tokens[:8])
        self.assertNotEqual(first_tokens[8:], second_tokens[8:])
        self.assertEqual(artifact.requests[1].shared_prefix_token_count, 8)

    def test_no_overlap_workload_has_no_shared_prefix_blocks(self) -> None:
        artifact = build_no_overlap_workload(
            tokenizer=self.tokenizer,
            workload_id="no-overlap-demo",
            num_requests=3,
            prompt_tokens=10,
            output_tokens=24,
            block_size_tokens=4,
        )

        self.assertEqual(artifact.workload_family, "no-overlap-control")
        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]
        self.assertNotEqual(prompts[0][:4], prompts[1][:4])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 0, 0],
        )

    def test_mixed_long_short_workload_marks_short_arrival_offset(self) -> None:
        artifact = build_mixed_long_short_workload(
            tokenizer=self.tokenizer,
            workload_id="mixed-demo",
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            output_tokens=8,
            block_size_tokens=4,
        )

        self.assertEqual(artifact.workload_family, "mixed-long-short")
        self.assertEqual(len(artifact.requests), 2)
        self.assertEqual(len(self.tokenizer.encode(artifact.requests[0].prompt)), 12)
        self.assertEqual(len(self.tokenizer.encode(artifact.requests[1].prompt)), 4)
        self.assertEqual(
            [request.arrival_offset_ms for request in artifact.requests],
            [0, 25],
        )
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 0],
        )

    def test_bursty_arrivals_workload_splits_requests_into_two_aligned_bursts(self) -> None:
        artifact = build_bursty_arrivals_workload(
            tokenizer=self.tokenizer,
            workload_id="bursty-demo",
            num_requests=4,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            unique_suffix_tokens=3,
            burst_gap_ms=120,
            output_tokens=16,
        )

        self.assertEqual(artifact.workload_family, "bursty-arrivals")
        self.assertEqual(len(artifact.requests), 4)
        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]
        self.assertEqual(prompts[0][:8], prompts[1][:8])
        self.assertEqual(prompts[0][:8], prompts[2][:8])
        self.assertEqual(
            [request.arrival_offset_ms for request in artifact.requests],
            [0, 0, 120, 120],
        )
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 8, 8, 8],
        )

    def test_eviction_ordering_workload_reuses_hot_block_under_capacity_pressure(self) -> None:
        artifact = build_eviction_ordering_workload(
            tokenizer=self.tokenizer,
            workload_id="eviction-demo",
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
        self.assertNotEqual(prompts[0][4:8], prompts[1][4:8])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 4, 4, 4],
        )

    def test_hotset_scan_workload_creates_frequency_then_scan_pattern(self) -> None:
        artifact = build_hotset_scan_workload(
            tokenizer=self.tokenizer,
            workload_id="hotset-scan-demo",
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

    def test_hotset_scan_workload_supports_revisit_variant(self) -> None:
        artifact = build_hotset_scan_workload(
            tokenizer=self.tokenizer,
            workload_id="hotset-scan-revisit-demo",
            block_size_tokens=4,
            output_tokens=16,
            workload_variant="revisit",
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "hotset-scan")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[1][:4])
        self.assertNotEqual(prompts[3][:4], prompts[0][:4])
        self.assertEqual(prompts[4][:4], prompts[0][:4])
        self.assertEqual(prompts[7][:4], prompts[0][:4])
        self.assertEqual(prompts[4][4:8], prompts[0][4:8])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 0, 4, 4, 4, 4],
        )

    def test_locality_shift_workload_switches_to_a_new_hot_prefix(self) -> None:
        artifact = build_locality_shift_workload(
            tokenizer=self.tokenizer,
            workload_id="locality-shift-demo",
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

    def test_locality_return_workload_returns_to_original_prefix_after_shift(self) -> None:
        artifact = build_locality_return_workload(
            tokenizer=self.tokenizer,
            workload_id="locality-return-demo",
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

    def test_dual_hotset_workload_keeps_two_frequency_biased_blocks_under_scan_pressure(self) -> None:
        artifact = build_dual_hotset_workload(
            tokenizer=self.tokenizer,
            workload_id="dual-hotset-demo",
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

    def test_locality_return_workload_supports_concentrated_variant(self) -> None:
        artifact = build_locality_return_workload(
            tokenizer=self.tokenizer,
            workload_id="locality-return-concentrated-demo",
            block_size_tokens=4,
            output_tokens=16,
            workload_variant="concentrated",
        )

        prompts = [self.tokenizer.encode(request.prompt) for request in artifact.requests]

        self.assertEqual(artifact.workload_family, "locality-return")
        self.assertEqual(len(artifact.requests), 8)
        self.assertEqual(prompts[0][:4], prompts[1][:4])
        self.assertNotEqual(prompts[0][:4], prompts[3][:4])
        self.assertEqual(prompts[0][:4], prompts[6][:4])
        self.assertEqual(prompts[0][:4], prompts[7][:4])
        self.assertEqual(prompts[0][4:8], prompts[6][4:8])
        self.assertEqual(prompts[0][4:8], prompts[7][4:8])
        self.assertEqual(
            [request.shared_prefix_token_count for request in artifact.requests],
            [0, 4, 4, 0, 4, 4, 0, 4],
        )

    def test_workload_artifact_round_trips_to_jsonl(self) -> None:
        artifact = build_mixed_long_short_workload(
            tokenizer=self.tokenizer,
            workload_id="mixed-demo",
            long_prompt_tokens=12,
            short_prompt_tokens=4,
            short_arrival_offset_ms=25,
            output_tokens=16,
            block_size_tokens=4,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "workload.jsonl"
            write_workload_artifact(path, artifact)
            loaded = load_workload_artifact(path)

        self.assertEqual(loaded.workload_id, artifact.workload_id)
        self.assertEqual(loaded.workload_family, artifact.workload_family)
        self.assertEqual(
            [request.arrival_offset_ms for request in loaded.requests],
            [0, 25],
        )
        self.assertEqual(
            json.loads(path.read_text().splitlines()[0])["workload_family"]
            if path.exists()
            else artifact.workload_family,
            artifact.workload_family,
        )
