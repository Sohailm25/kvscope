import unittest

from serve.runtime_contract import (
    TRANSFORMERS_VERSION,
    modal_environment,
    runtime_packages,
)


class RuntimeContractTests(unittest.TestCase):
    def test_vllm_runtime_pins_transformers_to_supported_major(self) -> None:
        packages = runtime_packages()

        self.assertIn(f"transformers=={TRANSFORMERS_VERSION}", packages)
        self.assertTrue(TRANSFORMERS_VERSION.startswith("4."))
        self.assertNotIn("transformers", packages)

    def test_modal_environment_avoids_known_warning_sources(self) -> None:
        environment = modal_environment()

        self.assertEqual(environment["TOKENIZERS_PARALLELISM"], "false")
        self.assertNotIn("TRANSFORMERS_CACHE", environment)
