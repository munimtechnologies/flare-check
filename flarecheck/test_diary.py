# SPDX-License-Identifier: Apache-2.0
import datetime
import unittest

from flarecheck.diary import norm_item, parse_text

TEXT = (
    "Date, Foods ,Score\n"
    "2026-01-01,Milk; bread,3\n"
    "2026-01-03,-,5\n"
    "2026-01-03,,7\n"
    "2026-01-04,,\n"
    "\n"
)


class TestDiary(unittest.TestCase):
    def test_parse(self):
        d = parse_text(TEXT)
        self.assertEqual(d.start, datetime.date(2026, 1, 1))
        self.assertEqual(len(d), 4)
        self.assertEqual(d.foods[0], frozenset(["milk", "bread"]))
        self.assertIsNone(d.foods[1])
        self.assertEqual(d.foods[2], frozenset())
        self.assertIsNone(d.foods[3])
        self.assertEqual(d.scores, [3.0, None, 7.0, None])
        self.assertEqual(d.items(), ["bread", "milk"])
        self.assertEqual(d.days_with_foods(), 2)
        self.assertEqual(d.days_with_score(), 2)

    def test_norm_item(self):
        self.assertEqual(norm_item("  Whole   MILK "), "whole milk")
        self.assertEqual(norm_item(None), "")

    def test_bad_score(self):
        with self.assertRaises(ValueError):
            parse_text("date,foods,score\n2026-01-01,MILK,nan\n")
        with self.assertRaises(ValueError):
            parse_text("date,foods,score\n2026-01-01,MILK,high\n")

    def test_empty(self):
        with self.assertRaises(ValueError):
            parse_text("date,foods,score\n")


if __name__ == "__main__":
    unittest.main()
