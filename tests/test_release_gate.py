import unittest

from release_gate import should_deploy


class ReleaseGateTests(unittest.TestCase):
    def test_allows_release_below_budget(self):
        self.assertTrue(should_deploy(1, 100))

    def test_allows_release_at_budget(self):
        self.assertTrue(should_deploy(5, 100))

    def test_blocks_release_above_budget(self):
        self.assertFalse(should_deploy(6, 100))
