import unittest

from money_machine.text_utils import normalize_text, slugify


class TextUtilsTests(unittest.TestCase):
    def test_normalize_removes_mojibake(self):
        raw = "hello â€” world\r\n\r\n\r\nline"
        norm = normalize_text(raw, ascii_only=True)
        self.assertIn("hello - world", norm)
        self.assertNotIn("â€”", norm)

    def test_slugify(self):
        self.assertEqual(slugify("A/B Test: Money!"), "a-b-test-money")


if __name__ == "__main__":
    unittest.main()
