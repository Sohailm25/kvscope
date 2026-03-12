import unittest

from bench.workloads import (
    SimpleWhitespaceTokenizer,
    WorkloadArtifact,
    WorkloadRequest,
    build_aligned_prefix_workload,
    build_eviction_ordering_workload,
    build_no_overlap_workload,
)
from kvtrace.replay import replay_block_sequence
from kvtrace.trace_builder import build_trace_events


class TraceBuilderTests(unittest.TestCase):
    def test_trace_builder_emits_hits_for_reused_blocks(self) -> None:
        tokenizer = SimpleWhitespaceTokenizer()
        workload = build_aligned_prefix_workload(
            tokenizer=tokenizer,
            workload_id="aligned-demo",
            num_requests=2,
            block_size_tokens=4,
            shared_prefix_blocks=2,
            unique_suffix_tokens=3,
            output_tokens=32,
        )

        events = build_trace_events(
            workload=workload,
            tokenizer=tokenizer,
            model_name="test-model",
            engine_name="derived-test-engine",
            run_id="trace-run",
            cache_capacity_blocks=2,
        )

        hit_events = [
            event
            for event in events
            if event["event_type"] == "block_hit" and event["request_id"] == "req-2"
        ]

        self.assertTrue(hit_events)
        self.assertTrue(all(event["schema_version"] == "kvtrace-v2" for event in events))

    def test_trace_builder_emits_evictions_under_tight_capacity(self) -> None:
        tokenizer = SimpleWhitespaceTokenizer()
        workload = build_no_overlap_workload(
            tokenizer=tokenizer,
            workload_id="no-overlap-demo",
            num_requests=3,
            prompt_tokens=8,
            output_tokens=16,
            block_size_tokens=4,
        )

        events = build_trace_events(
            workload=workload,
            tokenizer=tokenizer,
            model_name="test-model",
            engine_name="derived-test-engine",
            run_id="trace-run",
            cache_capacity_blocks=2,
        )

        eviction_events = [event for event in events if event["event_type"] == "block_evict"]

        self.assertTrue(eviction_events)

    def test_trace_builder_reuses_only_full_blocks_for_near_aligned_prefix(self) -> None:
        tokenizer = SimpleWhitespaceTokenizer()
        workload = WorkloadArtifact(
            schema_version="kvscope-workload-v1",
            workload_id="near-aligned-demo",
            workload_family="near-aligned-prefix",
            block_size_tokens=4,
            requests=[
                WorkloadRequest(
                    request_id="req-1",
                    prompt="a1 a2 a3 a4 a5 a6 a7 x1 x2 x3",
                    output_tokens_target=16,
                    shared_prefix_token_count=0,
                ),
                WorkloadRequest(
                    request_id="req-2",
                    prompt="a1 a2 a3 a4 a5 a6 a7 y1 y2 y3",
                    output_tokens_target=16,
                    shared_prefix_token_count=7,
                ),
            ],
        )

        events = build_trace_events(
            workload=workload,
            tokenizer=tokenizer,
            model_name="test-model",
            engine_name="derived-test-engine",
            run_id="trace-run",
            cache_capacity_blocks=4,
        )

        query_event = next(
            event
            for event in events
            if event["event_type"] == "prefix_cache_query"
            and event["request_id"] == "req-2"
        )
        hit_events = [
            event
            for event in events
            if event["event_type"] == "block_hit" and event["request_id"] == "req-2"
        ]

        self.assertEqual(query_event["shared_prefix_tokens"], 4)
        self.assertEqual(len(hit_events), 1)

    def test_trace_builder_emits_lookup_sequence_that_separates_fifo_and_lru(self) -> None:
        tokenizer = SimpleWhitespaceTokenizer()
        workload = build_eviction_ordering_workload(
            tokenizer=tokenizer,
            workload_id="eviction-demo",
            block_size_tokens=4,
            output_tokens=16,
        )

        events = build_trace_events(
            workload=workload,
            tokenizer=tokenizer,
            model_name="test-model",
            engine_name="derived-test-engine",
            run_id="trace-run",
            cache_capacity_blocks=2,
        )

        block_lookup_keys = [
            event["block_key"] for event in events if event["event_type"] == "block_lookup"
        ]
        lru = replay_block_sequence(
            policy_name="lru",
            capacity_blocks=2,
            block_keys=block_lookup_keys,
        )
        fifo = replay_block_sequence(
            policy_name="fifo",
            capacity_blocks=2,
            block_keys=block_lookup_keys,
        )

        self.assertGreater(lru["hits"], fifo["hits"])
