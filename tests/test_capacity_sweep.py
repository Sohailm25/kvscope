# ABOUTME: Validates the replay-capacity sweep report for KVScope.
# ABOUTME: Capacity sweeps matter because one-capacity policy wins can hide where policies separate, collapse, or only win in a narrow band.

import json
import tempfile
import unittest
from pathlib import Path

from kvtrace.capacity_sweep import (
    build_replay_capacity_sweep_report,
    render_replay_capacity_sweep_markdown,
    write_replay_capacity_sweep_report,
)


def _write_run(
    root: Path,
    run_id: str,
    workload_family: str,
    *,
    ttft_p50: float,
    block_lookup_keys: list[str],
    native_capacity_blocks: int = 3,
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
                "prefix_caching_enabled": True,
                "cold_start": True,
                "warmup_requests_discarded": 0,
                "commit": "81409c9",
                "created_at_utc": "2026-03-11T03:00:00Z",
                "command": (
                    "modal run serve/modal_vllm_app.py "
                    f"--workload-family {workload_family} "
                    f"--cache-capacity-blocks {native_capacity_blocks}"
                ),
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
                "latency_ms": {"p50": 500.0, "p95": 500.0, "p99": 500.0, "mean": 500.0},
                "itl_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0},
                "total_output_tokens": 16,
                "tokens_per_second": 10.0,
                "requests": [],
            },
            indent=2,
        )
        + "\n"
    )

    events = []
    for index, block_key in enumerate(block_lookup_keys):
        events.append(
            {
                "schema_version": "kvtrace-v2",
                "run_id": run_id,
                "event_type": "block_lookup",
                "timestamp_ns": index + 1,
                "source_kind": "derived",
                "engine": "vllm",
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "workload_id": f"{workload_family}-demo",
                "request_id": f"req-{1 if index < 2 else 2}",
                "block_key": block_key,
                "block_index": index,
                "token_start": index * 16,
                "token_end": index * 16 + 15,
                "block_size_tokens": 16,
            }
        )
    (run_dir / "kvtrace.ndjson").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )
    return run_dir


class ReplayCapacitySweepTests(unittest.TestCase):
    def test_build_replay_capacity_sweep_report_surfaces_divergence_headroom_and_control(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hotset = _write_run(
                repo_root,
                "20260311-030300__serve__hotset-scan__rep-01",
                "hotset-scan",
                ttft_p50=900.0,
                block_lookup_keys=[
                    "H",
                    "A",
                    "H",
                    "B",
                    "H",
                    "C",
                    "H",
                    "A",
                    "D",
                    "E",
                    "F",
                    "G",
                    "H",
                    "A",
                    "H",
                    "B",
                ],
            )
            control = _write_run(
                repo_root,
                "20260311-030400__serve__no-overlap-control__rep-01",
                "no-overlap-control",
                ttft_p50=700.0,
                block_lookup_keys=["A", "B", "C", "D", "E", "F", "G", "H"],
            )

            report = build_replay_capacity_sweep_report(
                repo_root=repo_root,
                run_dirs=[hotset, control],
                capacities=[1, 2, 3, 4],
                report_slug="capacity-demo",
            )

            self.assertEqual(report["schema_version"], "kvtrace-capacity-sweep-v1")
            self.assertEqual(report["capacities"], [1, 2, 3, 4])
            self.assertEqual(
                report["families"]["hotset-scan"]["capacities"]["2"]["policies"]["lfu"][
                    "hit_rate_mean"
                ],
                0.312,
            )
            self.assertEqual(
                report["families"]["hotset-scan"]["capacities"]["3"]["policies"]["lfu"][
                    "hit_rate_mean"
                ],
                0.375,
            )

            findings = {
                (finding["kind"], finding["evidence"]["workload_family"]): finding
                for finding in report["findings"]
                if "workload_family" in finding.get("evidence", {})
            }
            self.assertEqual(
                findings[("capacity-policy-divergence-band", "hotset-scan")]["evidence"][
                    "capacity_blocks"
                ],
                [2, 3],
            )
            self.assertEqual(
                findings[("capacity-policy-headroom-band", "hotset-scan")]["evidence"][
                    "capacity_blocks"
                ],
                [2, 3, 4],
            )
            self.assertEqual(
                findings[("capacity-negative-control", "no-overlap-control")]["evidence"][
                    "capacity_blocks"
                ],
                [1, 2, 3, 4],
            )

    def test_build_replay_capacity_sweep_report_finds_first_reuse_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            aligned = _write_run(
                repo_root,
                "20260311-030000__serve__aligned-prefix__rep-01",
                "aligned-prefix",
                ttft_p50=340.0,
                block_lookup_keys=["A", "B", "C", "D", "A", "B", "C", "D"],
                native_capacity_blocks=16,
            )

            report = build_replay_capacity_sweep_report(
                repo_root=repo_root,
                run_dirs=[aligned],
                capacities=[1, 2, 3, 4],
                report_slug="capacity-threshold-demo",
            )

            threshold_finding = next(
                finding
                for finding in report["findings"]
                if finding["kind"] == "capacity-reuse-threshold"
            )
            self.assertEqual(
                threshold_finding["evidence"]["first_reuse_capacity_blocks"],
                4,
            )
            self.assertEqual(
                report["families"]["aligned-prefix"]["capacities"]["4"]["policies"]["lru"][
                    "hit_rate_mean"
                ],
                0.5,
            )

    def test_build_replay_capacity_sweep_report_flags_recency_advantage_band(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            locality_shift = _write_run(
                repo_root,
                "20260311-030500__serve__locality-shift__rep-01",
                "locality-shift",
                ttft_p50=850.0,
                block_lookup_keys=[
                    "A",
                    "B",
                    "A",
                    "C",
                    "A",
                    "B",
                    "A",
                    "C",
                    "D",
                    "E",
                    "D",
                    "F",
                    "D",
                    "E",
                    "D",
                    "F",
                ],
                native_capacity_blocks=2,
            )

            report = build_replay_capacity_sweep_report(
                repo_root=repo_root,
                run_dirs=[locality_shift],
                capacities=[1, 2, 3, 4],
                report_slug="capacity-recency-demo",
            )

            findings = {
                (finding["kind"], finding["evidence"]["workload_family"]): finding
                for finding in report["findings"]
                if "workload_family" in finding.get("evidence", {})
            }
            self.assertEqual(
                findings[("capacity-recency-advantage-band", "locality-shift")]["evidence"][
                    "capacity_blocks"
                ],
                [2, 3, 4],
            )

    def test_build_replay_capacity_sweep_report_flags_policy_crossover_band(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            locality_return = _write_run(
                repo_root,
                "20260311-030600__serve__locality-return__rep-01",
                "locality-return",
                ttft_p50=910.0,
                block_lookup_keys=[
                    "W",
                    "A",
                    "W",
                    "B",
                    "W",
                    "A",
                    "C",
                    "D",
                    "C",
                    "E",
                    "C",
                    "D",
                    "W",
                    "A",
                    "W",
                    "B",
                ],
                native_capacity_blocks=2,
            )

            report = build_replay_capacity_sweep_report(
                repo_root=repo_root,
                run_dirs=[locality_return],
                capacities=[1, 2, 3, 4, 5],
                report_slug="capacity-crossover-demo",
            )

            findings = {
                (finding["kind"], finding["evidence"]["workload_family"]): finding
                for finding in report["findings"]
                if "workload_family" in finding.get("evidence", {})
            }
            self.assertEqual(
                findings[("capacity-recency-advantage-band", "locality-return")]["evidence"][
                    "capacity_blocks"
                ],
                [2, 3],
            )
            self.assertEqual(
                findings[("capacity-policy-headroom-band", "locality-return")]["evidence"][
                    "capacity_blocks"
                ],
                [4],
            )
            self.assertEqual(
                findings[("capacity-policy-crossover", "locality-return")]["evidence"][
                    "lru_advantage_capacity_blocks"
                ],
                [2, 3],
            )
            self.assertEqual(
                findings[("capacity-policy-crossover", "locality-return")]["evidence"][
                    "lfu_advantage_capacity_blocks"
                ],
                [4],
            )

    def test_render_and_write_replay_capacity_sweep_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            hotset = _write_run(
                repo_root,
                "20260311-030300__serve__hotset-scan__rep-01",
                "hotset-scan",
                ttft_p50=900.0,
                block_lookup_keys=[
                    "H",
                    "A",
                    "H",
                    "B",
                    "H",
                    "C",
                    "H",
                    "A",
                    "D",
                    "E",
                    "F",
                    "G",
                    "H",
                    "A",
                    "H",
                    "B",
                ],
            )

            report = build_replay_capacity_sweep_report(
                repo_root=repo_root,
                run_dirs=[hotset],
                capacities=[1, 2, 3],
                report_slug="capacity-markdown-demo",
            )
            markdown = render_replay_capacity_sweep_markdown(report)
            json_path, markdown_path = write_replay_capacity_sweep_report(
                repo_root=repo_root,
                report=report,
                markdown=markdown,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("| Capacity | FIFO hit rate | LRU hit rate | LFU hit rate |", markdown)
            self.assertIn("capacity-markdown-demo", markdown_path.name)
