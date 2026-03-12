ABOUTME: Human-readable pointer to the machine-checkable run manifest fixture.
ABOUTME: Keep this file short so the real example remains the JSON artifact used by tests and tooling.

# Example Run Manifest

The canonical example manifest now lives in:

- [run-manifest-v1.example.json](artifacts/examples/run-manifest-v1.example.json)

That file is intentionally machine-parseable and is validated by:

- `scripts/validate_repo_readiness.py`
- `tests/test_contract_validation.py`
