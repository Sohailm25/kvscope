import json
import tempfile
import unittest
from pathlib import Path

from serve.benchmark_tables import (
    build_benchmark_tables_report,
    render_benchmark_tables_markdown,
    write_benchmark_tables_report,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


class BenchmarkTablesTests(unittest.TestCase):
    def test_build_benchmark_tables_report_combines_three_summary_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            phase1_report = _write_json(
                repo_root / "artifacts" / "manifests" / "phase1.json",
                {
                    "schema_version": "phase1-report-v1",
                    "report_slug": "phase1-repeated-families-slice",
                    "families": {
                        "aligned-prefix": {
                            "run_count": 3,
                            "ttft_p50_ms": {"min": 328.199, "max": 614.805, "mean": 427.52},
                            "block_hit_count_total": 12,
                        },
                        "near-aligned-prefix": {
                            "run_count": 3,
                            "ttft_p50_ms": {"min": 402.04, "max": 891.925, "mean": 616.775},
                            "block_hit_count_total": 9,
                        },
                        "no-overlap-control": {
                            "run_count": 2,
                            "ttft_p50_ms": {"min": 356.895, "max": 622.419, "mean": 489.657},
                            "block_hit_count_total": 0,
                        },
                    },
                },
            )
            live_cache_report = _write_json(
                repo_root / "artifacts" / "manifests" / "live-cache.json",
                {
                    "schema_version": "live-cache-report-v1",
                    "report_slug": "live-cache-toggle-expanded",
                    "families": {
                        "aligned-prefix": {
                            "cache_on": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 834.289, "max": 834.289, "mean": 834.289},
                                "prefix_cache_hit_rate": {"min": 0.5, "max": 0.5, "mean": 0.5},
                                "request_prefill_mean_ms": {"min": 35.191, "max": 35.191, "mean": 35.191},
                            },
                            "cache_off": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 2312.512, "max": 2312.512, "mean": 2312.512},
                                "prefix_cache_hit_rate": {"min": 0.0, "max": 0.0, "mean": 0.0},
                                "request_prefill_mean_ms": {"min": 43.572, "max": 43.572, "mean": 43.572},
                            },
                        },
                        "eviction-ordering": {
                            "cache_on": {
                                "run_count": 3,
                                "ttft_p50_ms": {"min": 594.689, "max": 1768.586, "mean": 1038.598},
                                "prefix_cache_hit_rate": {"min": 0.417, "max": 0.417, "mean": 0.417},
                                "request_prefill_mean_ms": {"min": 15.975, "max": 22.701, "mean": 18.229},
                            },
                            "cache_off": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 769.642, "max": 769.642, "mean": 769.642},
                                "prefix_cache_hit_rate": {"min": 0.0, "max": 0.0, "mean": 0.0},
                                "request_prefill_mean_ms": {"min": 24.259, "max": 24.259, "mean": 24.259},
                            },
                        },
                        "locality-shift": {
                            "cache_on": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 2535.439, "max": 2535.439, "mean": 2535.439},
                                "prefix_cache_hit_rate": {"min": 0.375, "max": 0.375, "mean": 0.375},
                                "request_prefill_mean_ms": {"min": 15.244, "max": 15.244, "mean": 15.244},
                            },
                            "cache_off": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 1730.403, "max": 1730.403, "mean": 1730.403},
                                "prefix_cache_hit_rate": {"min": 0.0, "max": 0.0, "mean": 0.0},
                                "request_prefill_mean_ms": {"min": 13.713, "max": 13.713, "mean": 13.713},
                            },
                        },
                        "locality-return": {
                            "cache_on": {
                                "run_count": 2,
                                "ttft_p50_ms": {"min": 1127.069, "max": 2499.845, "mean": 1813.457},
                                "prefix_cache_hit_rate": {"min": 0.375, "max": 0.375, "mean": 0.375},
                                "request_prefill_mean_ms": {"min": 12.659, "max": 15.993, "mean": 14.326},
                            },
                            "cache_off": {
                                "run_count": 2,
                                "ttft_p50_ms": {"min": 966.882, "max": 2793.383, "mean": 1880.133},
                                "prefix_cache_hit_rate": {"min": 0.0, "max": 0.0, "mean": 0.0},
                                "request_prefill_mean_ms": {"min": 12.88, "max": 17.972, "mean": 15.426},
                            },
                        },
                    },
                },
            )
            bridge_report = _write_json(
                repo_root / "artifacts" / "manifests" / "bridge.json",
                {
                    "schema_version": "kvtrace-bridge-report-v1",
                    "report_slug": "bridge-policy-headroom-expanded",
                    "families": {
                        "aligned-prefix": {
                            "run_count": 3,
                            "policies": {
                                "fifo": {"hit_rate_mean": 0.5, "hits_total": 12},
                                "lfu": {"hit_rate_mean": 0.5, "hits_total": 12},
                                "lru": {"hit_rate_mean": 0.5, "hits_total": 12},
                            },
                        },
                        "eviction-ordering": {
                            "run_count": 3,
                            "policies": {
                                "fifo": {"hit_rate_mean": 0.25, "hits_total": 9},
                                "lfu": {"hit_rate_mean": 0.417, "hits_total": 15},
                                "lru": {"hit_rate_mean": 0.417, "hits_total": 15},
                            },
                        },
                        "hotset-scan": {
                            "run_count": 1,
                            "policies": {
                                "fifo": {"hit_rate_mean": 0.188, "hits_total": 3},
                                "lfu": {"hit_rate_mean": 0.375, "hits_total": 6},
                                "lru": {"hit_rate_mean": 0.25, "hits_total": 4},
                            },
                        },
                        "locality-shift": {
                            "run_count": 1,
                            "policies": {
                                "fifo": {"hit_rate_mean": 0.25, "hits_total": 4},
                                "lfu": {"hit_rate_mean": 0.188, "hits_total": 3},
                                "lru": {"hit_rate_mean": 0.375, "hits_total": 6},
                            },
                        },
                    },
                },
            )

            report = build_benchmark_tables_report(
                repo_root=repo_root,
                phase1_report_path=phase1_report,
                live_cache_report_path=live_cache_report,
                bridge_report_path=bridge_report,
                report_slug="benchmark-tables",
            )

            self.assertEqual(report["schema_version"], "benchmark-tables-v1")
            self.assertEqual(len(report["tables"]["serving_workloads"]), 3)
            self.assertEqual(len(report["tables"]["live_cache"]), 4)
            self.assertEqual(len(report["tables"]["replay_policies"]), 4)
            eviction_cache_row = next(
                row
                for row in report["tables"]["live_cache"]
                if row["workload_family"] == "eviction-ordering"
            )
            self.assertIn("TTFT remained noisy", eviction_cache_row["note"])
            locality_return_row = next(
                row
                for row in report["tables"]["live_cache"]
                if row["workload_family"] == "locality-return"
            )
            self.assertIn("TTFT remained noisy", locality_return_row["note"])
            hotset_row = next(
                row
                for row in report["tables"]["replay_policies"]
                if row["workload_family"] == "hotset-scan"
            )
            self.assertEqual(hotset_row["lfu_hit_rate_mean"], 0.375)
            self.assertIn("headroom above lru", hotset_row["note"])
            locality_shift_row = next(
                row
                for row in report["tables"]["replay_policies"]
                if row["workload_family"] == "locality-shift"
            )
            self.assertEqual(locality_shift_row["lru_hit_rate_mean"], 0.375)
            self.assertIn("recency", locality_shift_row["note"])

    def test_render_and_write_benchmark_tables_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            phase1_report = _write_json(
                repo_root / "artifacts" / "manifests" / "phase1.json",
                {
                    "schema_version": "phase1-report-v1",
                    "report_slug": "phase1-repeated-families-slice",
                    "families": {
                        "aligned-prefix": {
                            "run_count": 3,
                            "ttft_p50_ms": {"min": 328.199, "max": 614.805, "mean": 427.52},
                            "block_hit_count_total": 12,
                        }
                    },
                },
            )
            live_cache_report = _write_json(
                repo_root / "artifacts" / "manifests" / "live-cache.json",
                {
                    "schema_version": "live-cache-report-v1",
                    "report_slug": "live-cache-toggle-expanded",
                    "families": {
                        "aligned-prefix": {
                            "cache_on": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 834.289, "max": 834.289, "mean": 834.289},
                                "prefix_cache_hit_rate": {"min": 0.5, "max": 0.5, "mean": 0.5},
                                "request_prefill_mean_ms": {"min": 35.191, "max": 35.191, "mean": 35.191},
                            },
                            "cache_off": {
                                "run_count": 1,
                                "ttft_p50_ms": {"min": 2312.512, "max": 2312.512, "mean": 2312.512},
                                "prefix_cache_hit_rate": {"min": 0.0, "max": 0.0, "mean": 0.0},
                                "request_prefill_mean_ms": {"min": 43.572, "max": 43.572, "mean": 43.572},
                            },
                        }
                    },
                },
            )
            bridge_report = _write_json(
                repo_root / "artifacts" / "manifests" / "bridge.json",
                {
                    "schema_version": "kvtrace-bridge-report-v1",
                    "report_slug": "bridge-policy-headroom-expanded",
                    "families": {
                        "aligned-prefix": {
                            "run_count": 3,
                            "policies": {
                                "fifo": {"hit_rate_mean": 0.5, "hits_total": 12},
                                "lfu": {"hit_rate_mean": 0.5, "hits_total": 12},
                                "lru": {"hit_rate_mean": 0.5, "hits_total": 12},
                            },
                        }
                    },
                },
            )

            report = build_benchmark_tables_report(
                repo_root=repo_root,
                phase1_report_path=phase1_report,
                live_cache_report_path=live_cache_report,
                bridge_report_path=bridge_report,
                report_slug="benchmark-tables",
            )
            markdown = render_benchmark_tables_markdown(report)
            json_path, markdown_path = write_benchmark_tables_report(
                repo_root=repo_root,
                report=report,
                markdown=markdown,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("| Family | Runs |", markdown)
            self.assertIn("LFU hit rate", markdown)
            self.assertIn("benchmark-tables", markdown_path.name)
