import unittest

from release_gate import should_deploy


class ReleaseGateTests(unittest.TestCase):
    def test_allows_release_below_budget(self):
        self.assertTrue(should_deploy(1, 100))

    def test_allows_release_at_budget(self):
        self.assertTrue(should_deploy(5, 100))

    def test_blocks_release_above_budget(self):
        self.assertFalse(should_deploy(6, 100))

    def test_rejects_empty_check_set(self):
        with self.assertRaisesRegex(
            ValueError, "total_checks must be greater than zero"
        ):
            should_deploy(0, 0)