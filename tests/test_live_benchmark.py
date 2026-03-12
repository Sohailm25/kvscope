# ABOUTME: Validates client lifecycle handling in the live benchmark path.
# ABOUTME: The first serving slice should shut down cleanly after requests complete.

import time
import unittest

from bench.workloads import WorkloadArtifact, WorkloadRequest
from serve.live_benchmark import run_workload, wait_for_model


class _FakeModels:
    def list(self):  # noqa: D401
        class _Response:
            data = ["ready"]

        return _Response()


class _FakeStreamEvent:
    def __init__(self, text: str) -> None:
        class _Choice:
            def __init__(self, text: str) -> None:
                self.text = text

        self.choices = [_Choice(text)]


class _FakeCompletions:
    def create(self, **_: object):
        return iter([_FakeStreamEvent("tokA"), _FakeStreamEvent(" tokB")])


class _DelayedCompletions:
    def create(self, **_: object):
        def _iterator():
            time.sleep(0.05)
            yield _FakeStreamEvent("tokA")
            time.sleep(0.01)
            yield _FakeStreamEvent(" tokB")

        return _iterator()


class _FakeClient:
    def __init__(self, *_: object, **__: object) -> None:
        self.models = _FakeModels()
        self.completions = _FakeCompletions()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _SimpleTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        del add_special_tokens
        return [index for index, _ in enumerate(text.split(), start=1)]


class _DelayedClient(_FakeClient):
    def __init__(self, registry: list["_DelayedClient"], *_: object, **__: object) -> None:
        super().__init__()
        self.completions = _DelayedCompletions()
        registry.append(self)


class LiveBenchmarkTests(unittest.TestCase):
    def test_wait_for_model_closes_client_after_readiness_check(self) -> None:
        client = _FakeClient()

        wait_for_model(
            base_url="https://example.test",
            api_key="token",
            timeout_seconds=1,
            client_factory=lambda **_: client,
        )

        self.assertTrue(client.closed)

    def test_run_workload_closes_client_after_requests_finish(self) -> None:
        client = _FakeClient()
        workload = WorkloadArtifact(
            schema_version="kvscope-workload-v1",
            workload_id="aligned-prefix-demo",
            workload_family="aligned-prefix",
            block_size_tokens=16,
            requests=[
                WorkloadRequest(
                    request_id="req-1",
                    prompt="tok1 tok2",
                    output_tokens_target=2,
                    shared_prefix_token_count=0,
                )
            ],
        )

        observations = run_workload(
            base_url="https://example.test",
            api_key="token",
            model_name="test-model",
            workload=workload,
            tokenizer=_SimpleTokenizer(),
            client_factory=lambda **_: client,
        )

        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].status, "ok")
        self.assertTrue(client.closed)

    def test_run_workload_honors_arrival_offsets_and_keeps_request_order(self) -> None:
        clients: list[_DelayedClient] = []
        workload = WorkloadArtifact(
            schema_version="kvscope-workload-v1",
            workload_id="mixed-demo",
            workload_family="mixed-long-short",
            block_size_tokens=16,
            requests=[
                WorkloadRequest(
                    request_id="req-1",
                    prompt="tok1 tok2 tok3 tok4",
                    output_tokens_target=2,
                    shared_prefix_token_count=0,
                    arrival_offset_ms=0,
                ),
                WorkloadRequest(
                    request_id="req-2",
                    prompt="tok5 tok6",
                    output_tokens_target=2,
                    shared_prefix_token_count=0,
                    arrival_offset_ms=20,
                ),
            ],
        )

        observations = run_workload(
            base_url="https://example.test",
            api_key="token",
            model_name="test-model",
            workload=workload,
            tokenizer=_SimpleTokenizer(),
            client_factory=lambda **_: _DelayedClient(clients),
        )

        self.assertEqual([obs.request_id for obs in observations], ["req-1", "req-2"])
        self.assertEqual(observations[1].arrival_offset_ms, 20)
        self.assertGreaterEqual(observations[1].started_offset_ms, 10.0)
        self.assertLess(
            observations[1].started_offset_ms,
            observations[0].completed_offset_ms,
        )
        self.assertEqual(len(clients), 2)
        self.assertTrue(all(client.closed for client in clients))
