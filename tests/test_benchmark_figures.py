# ABOUTME: Validates the generated benchmark-figure bundle for KVScope.
# ABOUTME: These tests keep reviewer-facing figures tied to source reports and run provenance instead of becoming ad hoc screenshots.

import json
import tempfile
import unittest
from pathlib import Path

from serve.benchmark_figures import (
    build_benchmark_figures_report,
    render_benchmark_figures_markdown,
    write_benchmark_figures_report,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


class BenchmarkFiguresTests(unittest.TestCase):
    def test_build_benchmark_figures_report_collects_two_figure_specs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            live_cache_report = _write_json(
                repo_root / "artifacts" / "manifests" / "live-cache.json",
                {
                    "schema_version": "live-cache-report-v1",
                    "report_slug": "live-cache-toggle-tradeoffs-expanded",
                    "run_ids": ["a-on", "a-off", "e-on", "e-off", "h-on", "h-off", "l-on", "l-off"],
                    "families": {
                        "aligned-prefix": {
                            "cache_on": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.5},
                                "request_prefill_mean_ms": {"mean": 35.191},
                                "runs": [{"run_id": "a-on", "manifest_path": "artifacts/runs/a-on/manifest.json"}],
                            },
                            "cache_off": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.0},
                                "request_prefill_mean_ms": {"mean": 43.572},
                                "runs": [{"run_id": "a-off", "manifest_path": "artifacts/runs/a-off/manifest.json"}],
                            },
                        },
                        "eviction-ordering": {
                            "cache_on": {
                                "run_count": 2,
                                "prefix_cache_hit_rate": {"mean": 0.417},
                                "request_prefill_mean_ms": {"mean": 18.229},
                                "runs": [{"run_id": "e-on", "manifest_path": "artifacts/runs/e-on/manifest.json"}],
                            },
                            "cache_off": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.0},
                                "request_prefill_mean_ms": {"mean": 24.259},
                                "runs": [{"run_id": "e-off", "manifest_path": "artifacts/runs/e-off/manifest.json"}],
                            },
                        },
                        "hotset-scan": {
                            "cache_on": {
                                "run_count": 2,
                                "prefix_cache_hit_rate": {"mean": 0.312},
                                "request_prefill_mean_ms": {"mean": 13.946},
                                "runs": [{"run_id": "h-on", "manifest_path": "artifacts/runs/h-on/manifest.json"}],
                            },
                            "cache_off": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.0},
                                "request_prefill_mean_ms": {"mean": 16.914},
                                "runs": [{"run_id": "h-off", "manifest_path": "artifacts/runs/h-off/manifest.json"}],
                            },
                        },
                        "locality-shift": {
                            "cache_on": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.375},
                                "request_prefill_mean_ms": {"mean": 15.244},
                                "runs": [{"run_id": "l-on", "manifest_path": "artifacts/runs/l-on/manifest.json"}],
                            },
                            "cache_off": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.0},
                                "request_prefill_mean_ms": {"mean": 13.713},
                                "runs": [{"run_id": "l-off", "manifest_path": "artifacts/runs/l-off/manifest.json"}],
                            },
                        },
                    },
                },
            )
            capacity_sweep_report = _write_json(
                repo_root / "artifacts" / "manifests" / "capacity-sweep.json",
                {
                    "schema_version": "kvtrace-capacity-sweep-v1",
                    "report_slug": "replay-capacity-sweep-tradeoffs-expanded",
                    "run_ids": ["e-on", "h-on", "l-on"],
                    "capacities": [1, 2, 3, 4],
                    "families": {
                        "eviction-ordering": {
                            "runs": [{"run_id": "e-on", "manifest_path": "artifacts/runs/e-on/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.25}, "lru": {"hit_rate_mean": 0.417}, "lfu": {"hit_rate_mean": 0.417}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.417}, "lru": {"hit_rate_mean": 0.583}, "lfu": {"hit_rate_mean": 0.583}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.667}, "lru": {"hit_rate_mean": 0.667}, "lfu": {"hit_rate_mean": 0.667}}},
                            },
                        },
                        "hotset-scan": {
                            "runs": [{"run_id": "h-on", "manifest_path": "artifacts/runs/h-on/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.188}, "lru": {"hit_rate_mean": 0.25}, "lfu": {"hit_rate_mean": 0.312}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.188}, "lru": {"hit_rate_mean": 0.25}, "lfu": {"hit_rate_mean": 0.375}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.312}, "lru": {"hit_rate_mean": 0.312}, "lfu": {"hit_rate_mean": 0.438}}},
                            },
                        },
                        "locality-shift": {
                            "runs": [{"run_id": "l-on", "manifest_path": "artifacts/runs/l-on/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.25}, "lru": {"hit_rate_mean": 0.375}, "lfu": {"hit_rate_mean": 0.188}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.625}, "lru": {"hit_rate_mean": 0.625}, "lfu": {"hit_rate_mean": 0.438}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.625}, "lru": {"hit_rate_mean": 0.625}, "lfu": {"hit_rate_mean": 0.438}}},
                            },
                        },
                    },
                },
            )

            report = build_benchmark_figures_report(
                repo_root=repo_root,
                live_cache_report_path=live_cache_report,
                capacity_sweep_report_path=capacity_sweep_report,
                report_slug="benchmark-figures-tradeoffs",
            )

            self.assertEqual(report["schema_version"], "benchmark-figures-v1")
            self.assertEqual(len(report["figures"]), 2)
            figure_paths = [figure["figure_path"] for figure in report["figures"]]
            self.assertIn(
                "artifacts/figures/live-cache-toggle__vllm__cross-family__hit-rate-and-prefill.png",
                figure_paths,
            )
            self.assertIn(
                "artifacts/figures/policy-tradeoffs__vllm__cross-family__hit-rate-by-capacity.png",
                figure_paths,
            )
            replay_figure = next(
                figure
                for figure in report["figures"]
                if figure["kind"] == "policy-tradeoffs"
            )
            self.assertEqual(replay_figure["workload_families"], ["eviction-ordering", "hotset-scan", "locality-shift"])
            self.assertIn("l-on", replay_figure["referenced_run_ids"])

    def test_write_benchmark_figures_report_persists_pngs_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            live_cache_report = _write_json(
                repo_root / "artifacts" / "manifests" / "live-cache.json",
                {
                    "schema_version": "live-cache-report-v1",
                    "report_slug": "live-cache-toggle-tradeoffs-expanded",
                    "run_ids": ["a-on", "a-off"],
                    "families": {
                        "aligned-prefix": {
                            "cache_on": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.5},
                                "request_prefill_mean_ms": {"mean": 35.191},
                                "runs": [{"run_id": "a-on", "manifest_path": "artifacts/runs/a-on/manifest.json"}],
                            },
                            "cache_off": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.0},
                                "request_prefill_mean_ms": {"mean": 43.572},
                                "runs": [{"run_id": "a-off", "manifest_path": "artifacts/runs/a-off/manifest.json"}],
                            },
                        }
                    },
                },
            )
            capacity_sweep_report = _write_json(
                repo_root / "artifacts" / "manifests" / "capacity-sweep.json",
                {
                    "schema_version": "kvtrace-capacity-sweep-v1",
                    "report_slug": "replay-capacity-sweep-tradeoffs-expanded",
                    "run_ids": ["a-on"],
                    "capacities": [1, 2],
                    "families": {
                        "eviction-ordering": {
                            "runs": [{"run_id": "a-on", "manifest_path": "artifacts/runs/a-on/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.25}, "lru": {"hit_rate_mean": 0.417}, "lfu": {"hit_rate_mean": 0.417}}},
                            },
                        }
                    },
                },
            )

            report = build_benchmark_figures_report(
                repo_root=repo_root,
                live_cache_report_path=live_cache_report,
                capacity_sweep_report_path=capacity_sweep_report,
                report_slug="benchmark-figures-tradeoffs",
            )
            markdown = render_benchmark_figures_markdown(report)
            json_path, markdown_path, figure_paths = write_benchmark_figures_report(
                repo_root=repo_root,
                report=report,
                markdown=markdown,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("benchmark-figures-tradeoffs", markdown)
            self.assertEqual(len(figure_paths), 2)
            for figure_path in figure_paths:
                self.assertTrue(figure_path.exists())
                self.assertEqual(figure_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_build_benchmark_figures_report_includes_locality_return_panel_when_present(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            live_cache_report = _write_json(
                repo_root / "artifacts" / "manifests" / "live-cache.json",
                {
                    "schema_version": "live-cache-report-v1",
                    "report_slug": "live-cache-toggle-tradeoffs-repeated",
                    "run_ids": ["return-on", "return-off"],
                    "families": {
                        "locality-return": {
                            "cache_on": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.375},
                                "request_prefill_mean_ms": {"mean": 14.0},
                                "runs": [{"run_id": "return-on", "manifest_path": "artifacts/runs/return-on/manifest.json"}],
                            },
                            "cache_off": {
                                "run_count": 1,
                                "prefix_cache_hit_rate": {"mean": 0.0},
                                "request_prefill_mean_ms": {"mean": 13.5},
                                "runs": [{"run_id": "return-off", "manifest_path": "artifacts/runs/return-off/manifest.json"}],
                            },
                        }
                    },
                },
            )
            capacity_sweep_report = _write_json(
                repo_root / "artifacts" / "manifests" / "capacity-sweep.json",
                {
                    "schema_version": "kvtrace-capacity-sweep-v1",
                    "report_slug": "replay-capacity-sweep-tradeoffs-repeated",
                    "run_ids": ["evict", "hotset", "shift", "return"],
                    "capacities": [1, 2, 3, 4, 5],
                    "families": {
                        "eviction-ordering": {
                            "runs": [{"run_id": "evict", "manifest_path": "artifacts/runs/evict/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.25}, "lru": {"hit_rate_mean": 0.417}, "lfu": {"hit_rate_mean": 0.417}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.417}, "lru": {"hit_rate_mean": 0.583}, "lfu": {"hit_rate_mean": 0.583}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.667}, "lru": {"hit_rate_mean": 0.667}, "lfu": {"hit_rate_mean": 0.667}}},
                                "5": {"policies": {"fifo": {"hit_rate_mean": 0.667}, "lru": {"hit_rate_mean": 0.667}, "lfu": {"hit_rate_mean": 0.667}}},
                            },
                        },
                        "hotset-scan": {
                            "runs": [{"run_id": "hotset", "manifest_path": "artifacts/runs/hotset/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.188}, "lru": {"hit_rate_mean": 0.25}, "lfu": {"hit_rate_mean": 0.312}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.188}, "lru": {"hit_rate_mean": 0.25}, "lfu": {"hit_rate_mean": 0.375}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.312}, "lru": {"hit_rate_mean": 0.312}, "lfu": {"hit_rate_mean": 0.438}}},
                                "5": {"policies": {"fifo": {"hit_rate_mean": 0.312}, "lru": {"hit_rate_mean": 0.312}, "lfu": {"hit_rate_mean": 0.438}}},
                            },
                        },
                        "locality-shift": {
                            "runs": [{"run_id": "shift", "manifest_path": "artifacts/runs/shift/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.25}, "lru": {"hit_rate_mean": 0.375}, "lfu": {"hit_rate_mean": 0.188}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.625}, "lru": {"hit_rate_mean": 0.625}, "lfu": {"hit_rate_mean": 0.438}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.625}, "lru": {"hit_rate_mean": 0.625}, "lfu": {"hit_rate_mean": 0.438}}},
                                "5": {"policies": {"fifo": {"hit_rate_mean": 0.625}, "lru": {"hit_rate_mean": 0.625}, "lfu": {"hit_rate_mean": 0.5}}},
                            },
                        },
                        "locality-return": {
                            "runs": [{"run_id": "return", "manifest_path": "artifacts/runs/return/manifest.json"}],
                            "capacities": {
                                "1": {"policies": {"fifo": {"hit_rate_mean": 0.0}, "lru": {"hit_rate_mean": 0.0}, "lfu": {"hit_rate_mean": 0.0}}},
                                "2": {"policies": {"fifo": {"hit_rate_mean": 0.188}, "lru": {"hit_rate_mean": 0.312}, "lfu": {"hit_rate_mean": 0.188}}},
                                "3": {"policies": {"fifo": {"hit_rate_mean": 0.438}, "lru": {"hit_rate_mean": 0.438}, "lfu": {"hit_rate_mean": 0.375}}},
                                "4": {"policies": {"fifo": {"hit_rate_mean": 0.438}, "lru": {"hit_rate_mean": 0.438}, "lfu": {"hit_rate_mean": 0.5}}},
                                "5": {"policies": {"fifo": {"hit_rate_mean": 0.438}, "lru": {"hit_rate_mean": 0.562}, "lfu": {"hit_rate_mean": 0.562}}},
                            },
                        },
                    },
                },
            )

            report = build_benchmark_figures_report(
                repo_root=repo_root,
                live_cache_report_path=live_cache_report,
                capacity_sweep_report_path=capacity_sweep_report,
                report_slug="benchmark-figures-tradeoffs",
            )

            replay_figure = next(
                figure
                for figure in report["figures"]
                if figure["kind"] == "policy-tradeoffs"
            )
            self.assertEqual(
                replay_figure["workload_families"],
                ["eviction-ordering", "hotset-scan", "locality-shift", "locality-return"],
            )
