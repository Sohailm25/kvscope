import unittest
from pathlib import Path

from scripts.shared.repo_readiness import (
    collect_readiness_errors,
    load_kvtrace_events,
    load_run_manifest,
    validate_required_section_headings,
    validate_kvtrace_events,
    validate_run_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ContractValidationTests(unittest.TestCase):
    def test_example_run_manifest_is_valid(self) -> None:
        manifest = load_run_manifest(
            REPO_ROOT / "artifacts/examples/run-manifest-v1.example.json"
        )

        self.assertEqual(validate_run_manifest(manifest), [])

    def test_example_kvtrace_fixture_is_valid(self) -> None:
        events = load_kvtrace_events(
            REPO_ROOT / "artifacts/examples/kvtrace-v2.example.ndjson"
        )

        self.assertEqual(validate_kvtrace_events(events), [])

    def test_repo_readiness_errors_are_empty(self) -> None:
        self.assertEqual(collect_readiness_errors(REPO_ROOT), [])

    def test_required_step_zero_section_headings_exist(self) -> None:
        self.assertEqual(validate_required_section_headings(REPO_ROOT), [])
