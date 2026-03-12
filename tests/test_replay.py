# ABOUTME: Validates bounded offline replay policies for KVScope.
# ABOUTME: Replay depth only matters if new policies reveal real differences on interpretable traces.

import unittest

from kvtrace.replay import replay_block_sequence


class ReplayPolicyTests(unittest.TestCase):
    def test_replay_block_sequence_supports_lfu_on_frequency_skewed_trace(self) -> None:
        block_keys = ["H", "A", "H", "B", "H", "C", "H", "A", "D", "E", "F", "G", "H", "A", "H", "B"]

        lru = replay_block_sequence(
            policy_name="lru",
            capacity_blocks=3,
            block_keys=block_keys,
        )
        lfu = replay_block_sequence(
            policy_name="lfu",
            capacity_blocks=3,
            block_keys=block_keys,
        )

        self.assertEqual(lru["hits"], 4)
        self.assertEqual(lfu["hits"], 6)
        self.assertGreater(lfu["hit_rate"], lru["hit_rate"])
