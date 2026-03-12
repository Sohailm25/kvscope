# ABOUTME: Validates the first-slice multi-run reporting path for KVScope.
# ABOUTME: The raw runs are only reviewer-legible if we can summarize them without hand-editing numbers.

import json
import tempfile
import unittest
from pathlib import Path

from serve.phase1_reporting import (
    build_phase1_report,
    load_run_slice,
    render_phase1_markdown,
    write_phase1_report,
)


def _write_run(
    root: Path,
    run_id: str,
    workload_family: str,
    *,
    ttft_p50: float,
    latency_p50: float,
    tokens_per_second: float,
    block_hits: int,
    shared_prefix_tokens: list[int],
    request_records: list[dict[str, object]] | None = None,
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
                "created_at_utc": "2026-03-11T01:00:00Z",
                "command": "modal run serve/modal_vllm_app.py",
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
                "latency_ms": {
                    "p50": latency_p50,
                    "p95": latency_p50,
                    "p99": latency_p50,
                    "mean": latency_p50,
                },
                "itl_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0},
                "total_output_tokens": 16,
                "tokens_per_second": tokens_per_second,
                "requests": request_records or [],
            },
            indent=2,
        )
        + "\n"
    )

    events = []
    for shared_prefix in shared_prefix_tokens:
        events.append(
            {
                "schema_version": "kvtrace-v2",
                "run_id": run_id,
                "event_type": "prefix_cache_query",
                "timestamp_ns": len(events) + 1,
                "source_kind": "derived",
                "engine": "vllm",
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "workload_id": f"{workload_family}-demo",
                "request_id": f"req-{len(events) + 1}",
                "shared_prefix_tokens": shared_prefix,
                "block_size_tokens": 16,
            }
        )
    for _ in range(block_hits):
        events.append(
            {
                "schema_version": "kvtrace-v2",
                "run_id": run_id,
                "event_type": "block_hit",
                "timestamp_ns": len(events) + 1,
                "source_kind": "derived",
                "engine": "vllm",
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "workload_id": f"{workload_family}-demo",
                "request_id": "req-2",
                "block_key": f"block-{len(events)}",
                "block_index": len(events),
            }
        )
    (run_dir / "kvtrace.ndjson").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )
    return run_dir


class Phase1ReportingTests(unittest.TestCase):
    def test_load_run_slice_extracts_trace_and_latency_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _write_run(
                repo_root,
                "20260311-010000__serve__aligned-prefix__rep-01",
                "aligned-prefix",
                ttft_p50=340.0,
                latency_p50=420.0,
                tokens_per_second=18.5,
                block_hits=4,
                shared_prefix_tokens=[0, 64],
            )

            summary = load_run_slice(repo_root=repo_root, run_dir=run_dir)

            self.assertEqual(summary.run_id, run_dir.name)
            self.assertEqual(summary.workload_family, "aligned-prefix")
            self.assertEqual(summary.block_hit_count, 4)
            self.assertEqual(summary.shared_prefix_token_counts, [0, 64])
            self.assertEqual(summary.ttft_p50_ms, 340.0)

    def test_build_phase1_report_groups_runs_and_derives_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            aligned_one = _write_run(
                repo_root,
                "20260311-010000__serve__aligned-prefix__rep-01",
                "aligned-prefix",
                ttft_p50=340.0,
                latency_p50=420.0,
                tokens_per_second=18.5,
                block_hits=4,
                shared_prefix_tokens=[0, 64],
            )
            aligned_two = _write_run(
                repo_root,
                "20260311-010100__serve__aligned-prefix__rep-02",
                "aligned-prefix",
                ttft_p50=360.0,
                latency_p50=430.0,
                tokens_per_second=18.0,
                block_hits=4,
                shared_prefix_tokens=[0, 64],
            )
            control = _write_run(
                repo_root,
                "20260311-010200__serve__no-overlap-control__rep-01",
                "no-overlap-control",
                ttft_p50=355.0,
                latency_p50=380.0,
                tokens_per_second=21.0,
                block_hits=0,
                shared_prefix_tokens=[0, 0],
            )

            report = build_phase1_report(
                repo_root=repo_root,
                run_dirs=[aligned_one, aligned_two, control],
                report_slug="phase1-baseline",
            )

            self.assertEqual(report["schema_version"], "phase1-report-v1")
            self.assertEqual(report["report_slug"], "phase1-baseline")
            self.assertEqual(report["families"]["aligned-prefix"]["run_count"], 2)
            self.assertEqual(
                report["families"]["aligned-prefix"]["block_hit_count_total"], 8
            )
            self.assertEqual(
                report["families"]["no-overlap-control"]["block_hit_count_total"], 0
            )
            finding_kinds = {finding["kind"] for finding in report["findings"]}
            self.assertIn("derived-cache-separation", finding_kinds)

    def test_write_phase1_report_emits_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _write_run(
                repo_root,
                "20260311-010000__serve__aligned-prefix__rep-01",
                "aligned-prefix",
                ttft_p50=340.0,
                latency_p50=420.0,
                tokens_per_second=18.5,
                block_hits=4,
                shared_prefix_tokens=[0, 64],
            )
            report = build_phase1_report(
                repo_root=repo_root,
                run_dirs=[run_dir],
                report_slug="phase1-baseline",
            )
            markdown = render_phase1_markdown(report)

            json_path, markdown_path = write_phase1_report(
                repo_root=repo_root,
                report=report,
                markdown=markdown,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("phase1-baseline", json_path.name)
            self.assertIn(run_dir.name, markdown_path.read_text())

    def test_build_phase1_report_calls_out_high_variance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            aligned_fast = _write_run(
                repo_root,
                "20260311-010000__serve__aligned-prefix__rep-fast",
                "aligned-prefix",
                ttft_p50=320.0,
                latency_p50=360.0,
                tokens_per_second=20.0,
                block_hits=4,
                shared_prefix_tokens=[0, 64],
            )
            aligned_slow = _write_run(
                repo_root,
                "20260311-010100__serve__aligned-prefix__rep-slow",
                "aligned-prefix",
                ttft_p50=610.0,
                latency_p50=650.0,
                tokens_per_second=12.0,
                block_hits=4,
                shared_prefix_tokens=[0, 64],
            )
            control = _write_run(
                repo_root,
                "20260311-010200__serve__no-overlap-control__rep-01",
                "no-overlap-control",
                ttft_p50=355.0,
                latency_p50=380.0,
                tokens_per_second=21.0,
                block_hits=0,
                shared_prefix_tokens=[0, 0],
            )

            report = build_phase1_report(
                repo_root=repo_root,
                run_dirs=[aligned_fast, aligned_slow, control],
                report_slug="phase1-baseline",
            )

            finding_kinds = {finding["kind"] for finding in report["findings"]}
            self.assertIn("aligned-variance-caveat", finding_kinds)

    def test_build_phase1_report_calls_out_near_aligned_intermediate_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            aligned = _write_run(
                repo_root,
                "20260311-010000__serve__aligned-prefix__rep-01",
                "aligned-prefix",
                ttft_p50=340.0,
                latency_p50=420.0,
                tokens_per_second=18.5,
                block_hits=8,
                shared_prefix_tokens=[0, 64],
            )
            near_aligned = _write_run(
                repo_root,
                "20260311-010100__serve__near-aligned-prefix__rep-01",
                "near-aligned-prefix",
                ttft_p50=350.0,
                latency_p50=430.0,
                tokens_per_second=18.1,
                block_hits=6,
                shared_prefix_tokens=[0, 48],
            )
            control = _write_run(
                repo_root,
                "20260311-010200__serve__no-overlap-control__rep-01",
                "no-overlap-control",
                ttft_p50=355.0,
                latency_p50=380.0,
                tokens_per_second=21.0,
                block_hits=0,
                shared_prefix_tokens=[0, 0],
            )

            report = build_phase1_report(
                repo_root=repo_root,
                run_dirs=[aligned, near_aligned, control],
                report_slug="phase1-boundary-case",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("near-aligned-intermediate-case", findings)
            self.assertEqual(
                findings["near-aligned-intermediate-case"]["evidence"][
                    "near_aligned_block_hits_total"
                ],
                6,
            )

    def test_build_phase1_report_calls_out_mixed_short_request_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            mixed = _write_run(
                repo_root,
                "20260311-030000__serve__mixed-long-short__rep-01",
                "mixed-long-short",
                ttft_p50=475.0,
                latency_p50=560.0,
                tokens_per_second=13.5,
                block_hits=0,
                shared_prefix_tokens=[0, 0],
                request_records=[
                    {
                        "request_id": "req-1",
                        "prompt_tokens": 160,
                        "output_tokens": 8,
                        "ttft_ms": 500.0,
                        "latency_ms": 700.0,
                        "inter_token_latencies_ms": [],
                        "status": "ok",
                        "arrival_offset_ms": 0.0,
                        "started_offset_ms": 0.0,
                        "completed_offset_ms": 700.0,
                    },
                    {
                        "request_id": "req-2",
                        "prompt_tokens": 24,
                        "output_tokens": 8,
                        "ttft_ms": 450.0,
                        "latency_ms": 500.0,
                        "inter_token_latencies_ms": [],
                        "status": "ok",
                        "arrival_offset_ms": 25.0,
                        "started_offset_ms": 25.0,
                        "completed_offset_ms": 525.0,
                    },
                ],
            )

            report = build_phase1_report(
                repo_root=repo_root,
                run_dirs=[mixed],
                report_slug="phase1-mixed-slice",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("mixed-short-request-pressure", findings)
            self.assertEqual(
                findings["mixed-short-request-pressure"]["evidence"][
                    "short_prompt_tokens"
                ],
                24,
            )

    def test_build_phase1_report_calls_out_bursty_overlap_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            bursty = _write_run(
                repo_root,
                "20260311-040000__serve__bursty-arrivals__rep-01",
                "bursty-arrivals",
                ttft_p50=660.0,
                latency_p50=780.0,
                tokens_per_second=11.2,
                block_hits=12,
                shared_prefix_tokens=[0, 64, 64, 64],
                request_records=[
                    {
                        "request_id": "req-1",
                        "prompt_tokens": 72,
                        "output_tokens": 8,
                        "ttft_ms": 520.0,
                        "latency_ms": 760.0,
                        "inter_token_latencies_ms": [],
                        "status": "ok",
                        "arrival_offset_ms": 0.0,
                        "started_offset_ms": 0.0,
                        "completed_offset_ms": 760.0,
                    },
                    {
                        "request_id": "req-2",
                        "prompt_tokens": 72,
                        "output_tokens": 8,
                        "ttft_ms": 560.0,
                        "latency_ms": 790.0,
                        "inter_token_latencies_ms": [],
                        "status": "ok",
                        "arrival_offset_ms": 0.0,
                        "started_offset_ms": 2.0,
                        "completed_offset_ms": 792.0,
                    },
                    {
                        "request_id": "req-3",
                        "prompt_tokens": 72,
                        "output_tokens": 8,
                        "ttft_ms": 620.0,
                        "latency_ms": 760.0,
                        "inter_token_latencies_ms": [],
                        "status": "ok",
                        "arrival_offset_ms": 120.0,
                        "started_offset_ms": 122.0,
                        "completed_offset_ms": 882.0,
                    },
                    {
                        "request_id": "req-4",
                        "prompt_tokens": 72,
                        "output_tokens": 8,
                        "ttft_ms": 640.0,
                        "latency_ms": 780.0,
                        "inter_token_latencies_ms": [],
                        "status": "ok",
                        "arrival_offset_ms": 120.0,
                        "started_offset_ms": 124.0,
                        "completed_offset_ms": 904.0,
                    },
                ],
            )

            report = build_phase1_report(
                repo_root=repo_root,
                run_dirs=[bursty],
                report_slug="phase1-bursty-slice",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("bursty-overlap-pressure", findings)
            self.assertEqual(
                findings["bursty-overlap-pressure"]["evidence"]["burst_gap_ms"],
                120.0,
            )
