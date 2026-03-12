import json
import tempfile
import unittest
from pathlib import Path

from kvtrace.bridge_report import build_bridge_report, render_bridge_markdown


def _write_run(
    root: Path,
    run_id: str,
    workload_family: str,
    *,
    ttft_p50: float,
    block_lookup_keys: list[str],
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
                    "--workload-family aligned-prefix "
                    "--cache-capacity-blocks 2"
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


class BridgeReportTests(unittest.TestCase):
    def test_build_bridge_report_preserves_directional_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            aligned = _write_run(
                repo_root,
                "20260311-030000__serve__aligned-prefix__rep-01",
                "aligned-prefix",
                ttft_p50=340.0,
                block_lookup_keys=["A", "B", "A", "B"],
            )
            control = _write_run(
                repo_root,
                "20260311-030100__serve__no-overlap-control__rep-01",
                "no-overlap-control",
                ttft_p50=620.0,
                block_lookup_keys=["A", "B", "C", "D"],
            )

            report = build_bridge_report(
                repo_root=repo_root,
                run_dirs=[aligned, control],
                report_slug="bridge-demo",
            )

            findings = {finding["kind"] for finding in report["findings"]}
            self.assertIn("directional-live-to-replay-alignment", findings)
            self.assertEqual(
                report["families"]["aligned-prefix"]["policies"]["lru"]["hits_total"],
                2,
            )
            self.assertEqual(
                report["families"]["no-overlap-control"]["policies"]["lru"]["hits_total"],
                0,
            )

            markdown = render_bridge_markdown(report)
            self.assertIn("bridge-demo", markdown)

    def test_build_bridge_report_flags_policy_divergence_when_trace_supports_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            divergence = _write_run(
                repo_root,
                "20260311-030200__serve__eviction-ordering__rep-01",
                "eviction-ordering",
                ttft_p50=700.0,
                block_lookup_keys=["X", "A", "X", "B", "X", "A", "X", "C", "X", "A", "X", "B"],
            )

            report = build_bridge_report(
                repo_root=repo_root,
                run_dirs=[divergence],
                report_slug="bridge-divergence-demo",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("replay-policy-divergence", findings)
            self.assertGreater(
                report["families"]["eviction-ordering"]["policies"]["lru"]["hits_total"],
                report["families"]["eviction-ordering"]["policies"]["fifo"]["hits_total"],
            )

    def test_build_bridge_report_flags_policy_headroom_when_lfu_beats_lru(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            headroom = _write_run(
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

            report = build_bridge_report(
                repo_root=repo_root,
                run_dirs=[headroom],
                report_slug="bridge-headroom-demo",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("replay-policy-headroom", findings)
            self.assertGreater(
                report["families"]["hotset-scan"]["policies"]["lfu"]["hits_total"],
                report["families"]["hotset-scan"]["policies"]["lru"]["hits_total"],
            )

    def test_build_bridge_report_flags_policy_adaptation_when_lru_beats_lfu(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            adaptation = _write_run(
                repo_root,
                "20260311-030400__serve__locality-shift__rep-01",
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
            )

            report = build_bridge_report(
                repo_root=repo_root,
                run_dirs=[adaptation],
                report_slug="bridge-adaptation-demo",
            )

            findings = {finding["kind"]: finding for finding in report["findings"]}
            self.assertIn("replay-policy-adaptation", findings)
            self.assertGreater(
                report["families"]["locality-shift"]["policies"]["lru"]["hits_total"],
                report["families"]["locality-shift"]["policies"]["lfu"]["hits_total"],
            )
