# ABOUTME: Validates the manifest and result bundle writer for live benchmark runs.
# ABOUTME: The first execution slice is only credible if every run lands in the documented artifact layout.

import json
import tempfile
import unittest
from pathlib import Path

from serve.artifacts import (
    RequestObservation,
    build_run_manifest,
    create_run_directory,
    summarize_observations,
    write_run_bundle,
)


class RunArtifactsTests(unittest.TestCase):
    def test_write_run_bundle_creates_expected_files(self) -> None:
        observations = [
            RequestObservation(
                request_id="req-1",
                prompt_tokens=16,
                output_tokens=8,
                ttft_ms=120.0,
                latency_ms=420.0,
                inter_token_latencies_ms=[10.0, 11.0, 12.0],
                status="ok",
            ),
            RequestObservation(
                request_id="req-2",
                prompt_tokens=16,
                output_tokens=8,
                ttft_ms=140.0,
                latency_ms=460.0,
                inter_token_latencies_ms=[12.0, 13.0, 14.0],
                status="ok",
            ),
        ]
        results = summarize_observations(observations)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = create_run_directory(
                artifacts_root=repo_root,
                module="serve",
                workload_family="aligned-prefix",
                slug="test-run",
                timestamp_override="20260311-020000",
            )
            manifest = build_run_manifest(
                run_id=run_dir.name,
                module="serve",
                engine="vllm",
                engine_version="0.8.3",
                model="test-model",
                gpu_type="L40S",
                workload_id="aligned-demo",
                workload_family="aligned-prefix",
                prefix_caching_enabled=True,
                cold_start=False,
                warmup_requests_discarded=4,
                commit="3e1c9ab",
                created_at_utc="2026-03-11T02:00:00Z",
                command="python -m serve.run",
            )
            write_run_bundle(
                run_dir=run_dir,
                manifest=manifest,
                results=results,
                stdout_text="stdout",
                stderr_text="stderr",
                kvtrace_events=[{"schema_version": "kvtrace-v2", "event_type": "request_arrival"}],
                live_metrics={
                    "schema_version": "live-metrics-v1",
                    "before": {"gauges": {}, "counters": {}, "histograms": {}},
                    "after": {"gauges": {}, "counters": {}, "histograms": {}},
                    "delta": {"gauges": {}, "counters": {}, "histograms": {}, "derived": {}},
                },
            )

            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "results.json").exists())
            self.assertTrue((run_dir / "stdout.log").exists())
            self.assertTrue((run_dir / "stderr.log").exists())
            self.assertTrue((run_dir / "kvtrace.ndjson").exists())
            self.assertTrue((run_dir / "live_metrics.json").exists())

            persisted_results = json.loads((run_dir / "results.json").read_text())
            self.assertEqual(persisted_results["request_count"], 2)
            self.assertIn("arrival_offset_ms", persisted_results["requests"][0])
            self.assertIn("started_offset_ms", persisted_results["requests"][0])
