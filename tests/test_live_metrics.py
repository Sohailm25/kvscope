import unittest

from serve.live_metrics import build_live_metrics_artifact, parse_metrics_snapshot


class LiveMetricsTests(unittest.TestCase):
    def test_build_live_metrics_artifact_derives_prefix_hit_rate_and_histogram_means(
        self,
    ) -> None:
        before_text = """
# HELP vllm:gpu_cache_usage_perc GPU KV-cache usage.
vllm:gpu_cache_usage_perc{model_name="demo"} 0.0
vllm:prefix_cache_queries_total{model_name="demo"} 0
vllm:prefix_cache_hits_total{model_name="demo"} 0
vllm:prompt_tokens_total{model_name="demo"} 0
vllm:generation_tokens_total{model_name="demo"} 0
vllm:request_prefill_time_seconds_sum{model_name="demo"} 0
vllm:request_prefill_time_seconds_count{model_name="demo"} 0
vllm:request_queue_time_seconds_sum{model_name="demo"} 0
vllm:request_queue_time_seconds_count{model_name="demo"} 0
vllm:time_to_first_token_seconds_sum{model_name="demo"} 0
vllm:time_to_first_token_seconds_count{model_name="demo"} 0
"""
        after_text = """
# HELP vllm:gpu_cache_usage_perc GPU KV-cache usage.
vllm:gpu_cache_usage_perc{model_name="demo"} 0.5
vllm:prefix_cache_queries_total{model_name="demo"} 128
vllm:prefix_cache_hits_total{model_name="demo"} 96
vllm:prompt_tokens_total{model_name="demo"} 144
vllm:generation_tokens_total{model_name="demo"} 16
vllm:request_prefill_time_seconds_sum{model_name="demo"} 1.2
vllm:request_prefill_time_seconds_count{model_name="demo"} 2
vllm:request_queue_time_seconds_sum{model_name="demo"} 0.2
vllm:request_queue_time_seconds_count{model_name="demo"} 2
vllm:time_to_first_token_seconds_sum{model_name="demo"} 1.8
vllm:time_to_first_token_seconds_count{model_name="demo"} 2
"""

        artifact = build_live_metrics_artifact(
            before=parse_metrics_snapshot(before_text),
            after=parse_metrics_snapshot(after_text),
        )

        self.assertEqual(
            artifact["delta"]["counters"]["vllm:prefix_cache_queries"],
            128.0,
        )
        self.assertEqual(
            artifact["delta"]["counters"]["vllm:prefix_cache_hits"],
            96.0,
        )
        self.assertEqual(
            artifact["delta"]["derived"]["prefix_cache_hit_rate"],
            0.75,
        )
        self.assertEqual(
            artifact["delta"]["histograms"]["vllm:request_prefill_time_seconds"][
                "mean_ms"
            ],
            600.0,
        )
        self.assertEqual(
            artifact["delta"]["gauges"]["vllm:gpu_cache_usage_perc"]["after"],
            0.5,
        )

    def test_parse_metrics_snapshot_ignores_unselected_metrics(self) -> None:
        snapshot = parse_metrics_snapshot(
            """
unrelated_metric 9
vllm:prefix_cache_queries_total{model_name="demo"} 10
vllm:prefix_cache_hits_total{model_name="demo"} 8
"""
        )

        self.assertNotIn("unrelated_metric", snapshot["counters"])
        self.assertEqual(snapshot["counters"]["vllm:prefix_cache_queries"], 10.0)

