from __future__ import annotations

import unittest

from offagent.domain.locators import parse_locator


class LocatorTests(unittest.TestCase):
    def test_parse_direct_locator(self) -> None:
        result = parse_locator("paragraph 17")
        self.assertEqual(result.locator_type, "direct")
        self.assertEqual(result.target_hint, "paragraph")
        self.assertEqual(result.tokens, ("paragraph", "17"))
        self.assertFalse(result.resolved)

    def test_parse_search_locator(self) -> None:
        result = parse_locator("the paragraph containing supplier shall")
        self.assertEqual(result.locator_type, "search")
        self.assertIsNone(result.target_hint)
        self.assertFalse(result.resolved)


if __name__ == "__main__":
    unittest.main()
