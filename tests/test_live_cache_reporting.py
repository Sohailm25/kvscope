import json
import tempfile
import unittest
from pathlib import Path

from serve.live_cache_reporting import (
    build_live_cache_report,
    render_live_cache_markdown,
)


def _write_cache_run(
    root: Path,
    run_id: str,
    *,
    workload_family: str = "aligned-prefix",
    prefix_caching_enabled: bool,
    ttft_p50: float,
    prefill_mean_ms: float,
    prefix_cache_queries: float,
    prefix_cache_hits: float,
) -> Path:
    run_dir = root / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "run-manifest-v1",
                "run_id": run_id,
                "module": "serve",
                "engine": "vllm",
                "engine_version": "0.8.3",
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "gpu_type": "A10G",
                "workload_id": f"{workload_family}-demo",
                "workload_family": workload_family,
                "prefix_caching_enabled": prefix_caching_enabled,
                "cold_start": True,
                "warmup_requests_discarded": 0,
                "commit": "81409c9",
                "created_at_utc": "2026-03-11T14:00:00Z",
                "command": f"modal run serve/modal_vllm_app.py --workload-family {workload_family}",
            },
            indent=2,
        )
        + "\n"
    )
    (run_dir / "results.json").write_text(
        json.dumps(
            {
                "request_count": 2,
                "status_counts": {"ok": 2},
                "ttft_ms": {"p50": ttft_p50, "p95": ttft_p50, "p99": ttft_p50, "mean": ttft_p50},
                "latency_ms": {"p50": ttft_p50 + 100, "p95": ttft_p50 + 100, "p99": ttft_p50 + 100, "mean": ttft_p50 + 100},
                "itl_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0},
                "total_output_tokens": 16,
                "tokens_per_second": 10.0,
                "requests": [],
            },
            indent=2,
        )
        + "\n"
    )
    (run_dir / "live_metrics.json").write_text(
        json.dumps(
            {
                "schema_version": "live-metrics-v1",
                "before": {"gauges": {"vllm:gpu_cache_usage_perc": 0.0}, "counters": {}, "histograms": {}},
                "after": {"gauges": {"vllm:gpu_cache_usage_perc": 0.5}, "counters": {}, "histograms": {}},
                "delta": {
                    "gauges": {
                        "vllm:gpu_cache_usage_perc": {"before": 0.0, "after": 0.5}
                    },
                    "counters": {
                        "vllm:prefix_cache_queries": prefix_cache_queries,
                        "vllm:prefix_cache_hits": prefix_cache_hits,
                        "vllm:prompt_tokens_total": 144.0,
                        "vllm:generation_tokens_total": 16.0,
                    },
                    "histograms": {
                        "vllm:request_prefill_time_seconds": {
                            "sum_delta": round(prefill_mean_ms / 1000.0 * 2, 6),
                            "count_delta": 2.0,
                            "mean_ms": prefill_mean_ms,
                        },
                        "vllm:request_queue_time_seconds": {
                            "sum_delta": 0.1,
                            "count_delta": 2.0,
                            "mean_ms": 50.0,
                        },
                        "vllm:time_to_first_token_seconds": {
                            "sum_delta": round(ttft_p50 / 1000.0 * 2, 6),
                            "count_delta": 2.0,
                            "mean_ms": ttft_p50,
                        },
                    },
                    "derived": {
                        "prefix_cache_hit_rate": 0.0
                        if prefix_cache_queries == 0
                        else round(prefix_cache_hits / prefix_cache_queries, 3)
                    },
                },
            },
            indent=2,
        )
        + "\n"
    )
    return run_dir


class LiveCacheReportingTests(unittest.TestCase):
    def test_build_live_cache_report_finds_cache_toggle_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            cache_on = _write_cache_run(
                repo_root,
                "20260311-140000__serve__aligned-prefix__cache-on",
                prefix_caching_enabled=True,
                ttft_p50=340.0,
                prefill_mean_ms=250.0,
                prefix_cache_queries=128.0,
                prefix_cache_hits=96.0,
            )
            cache_off = _write_cache_run(
                repo_root,
                "20260311-140100__serve__aligned-prefix__cache-off",
                prefix_caching_enabled=False,
                ttft_p50=610.0,
                prefill_mean_ms=520.0,
                prefix_cache_queries=0.0,
                prefix_cache_hits=0.0,
            )

            report = build_live_cache_report(
                repo_root=repo_root,
                run_dirs=[cache_on, cache_off],
                report_slug="aligned-cache-toggle",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("live-prefix-cache-hit-signal", findings)
            self.assertIn("cache-on-prefill-improvement", findings)
            self.assertEqual(
                findings["live-prefix-cache-hit-signal"]["evidence"][
                    "cache_on_prefix_cache_hit_rate"
                ],
                0.75,
            )
            self.assertEqual(
                report["families"]["aligned-prefix"]["cache_on"]["run_count"],
                1,
            )
            self.assertIn(
                "aligned-cache-toggle",
                render_live_cache_markdown(report),
            )

    def test_build_live_cache_report_flags_noisy_ttft_when_prefill_improves(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            cache_on = _write_cache_run(
                repo_root,
                "20260311-163000__serve__eviction-ordering__cache-on",
                workload_family="eviction-ordering",
                prefix_caching_enabled=True,
                ttft_p50=1038.598,
                prefill_mean_ms=18.229,
                prefix_cache_queries=12.0,
                prefix_cache_hits=5.0,
            )
            cache_off = _write_cache_run(
                repo_root,
                "20260311-163100__serve__eviction-ordering__cache-off",
                workload_family="eviction-ordering",
                prefix_caching_enabled=False,
                ttft_p50=769.642,
                prefill_mean_ms=24.259,
                prefix_cache_queries=0.0,
                prefix_cache_hits=0.0,
            )

            report = build_live_cache_report(
                repo_root=repo_root,
                run_dirs=[cache_on, cache_off],
                report_slug="eviction-cache-toggle",
            )

            finding = next(
                candidate
                for candidate in report["findings"]
                if candidate["kind"] == "cache-on-prefill-improvement"
            )
            self.assertIn("client-observed TTFT remained noisy", finding["message"])

    def test_build_live_cache_report_keeps_ttft_noisy_when_ranges_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dirs = [
                _write_cache_run(
                    repo_root,
                    "20260311-181625__serve__locality-return__cache-on-1",
                    workload_family="locality-return",
                    prefix_caching_enabled=True,
                    ttft_p50=1127.069,
                    prefill_mean_ms=15.993,
                    prefix_cache_queries=16.0,
                    prefix_cache_hits=6.0,
                ),
                _write_cache_run(
                    repo_root,
                    "20260311-200421__serve__locality-return__cache-on-2",
                    workload_family="locality-return",
                    prefix_caching_enabled=True,
                    ttft_p50=2499.845,
                    prefill_mean_ms=12.659,
                    prefix_cache_queries=16.0,
                    prefix_cache_hits=6.0,
                ),
                _write_cache_run(
                    repo_root,
                    "20260311-181906__serve__locality-return__cache-off-1",
                    workload_family="locality-return",
                    prefix_caching_enabled=False,
                    ttft_p50=2793.383,
                    prefill_mean_ms=17.972,
                    prefix_cache_queries=0.0,
                    prefix_cache_hits=0.0,
                ),
                _write_cache_run(
                    repo_root,
                    "20260311-200419__serve__locality-return__cache-off-2",
                    workload_family="locality-return",
                    prefix_caching_enabled=False,
                    ttft_p50=966.882,
                    prefill_mean_ms=12.88,
                    prefix_cache_queries=0.0,
                    prefix_cache_hits=0.0,
                ),
            ]

            report = build_live_cache_report(
                repo_root=repo_root,
                run_dirs=run_dirs,
                report_slug="locality-return-cache-toggle",
            )

            finding = next(
                candidate
                for candidate in report["findings"]
                if candidate["kind"] == "cache-on-prefill-improvement"
            )
            self.assertIn("client-observed TTFT remained noisy", finding["message"])
