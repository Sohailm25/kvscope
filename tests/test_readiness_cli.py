# ABOUTME: Exercises the readiness CLI that future contributors and hooks will use.
# ABOUTME: The CLI is part of the repo's trust surface because it summarizes whether the contracts still hold.

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReadinessCliTests(unittest.TestCase):
    def test_readiness_cli_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_repo_readiness.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Repository readiness checks passed.", result.stdout)
