# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
import os
import tempfile
import unittest

from flarecheck.check import analyze, exposure_series, format_report, main
from flarecheck.diary import parse_text

# Food X on the first two days, a score of 5 on those days and 0 on the other six.
TEXT = "date,foods,score\n2026-03-01,X,5\n2026-03-02,x,5\n" + "".join(
    "2026-03-0%d,-,0\n" % day for day in range(3, 9))


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.diary = parse_text(TEXT)

    def test_exposure_series(self):
        self.assertEqual(exposure_series(self.diary, "x", 0), [1, 1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(exposure_series(self.diary, "x", 1), [None, 1, 1, 0, 0, 0, 0, 0])

    def test_hand_case(self):
        res = analyze(self.diary, lags=(0,), min_exposed=2, min_unexposed=2, min_shift=2)
        self.assertEqual(len(res["rows"]), 1)
        r = res["rows"][0]
        self.assertEqual(r["food"], "x")
        self.assertEqual((r["days_exposed"], r["days_not_exposed"]), (2, 6))
        self.assertAlmostEqual(r["mean_difference"], 5.0)
        self.assertEqual(r["shifts"], 5)
        self.assertAlmostEqual(r["p"], 0.1667)
        self.assertAlmostEqual(r["q"], 0.1667)
        self.assertEqual(r["status"], "no clear pattern")
        s = res["summary"]
        self.assertEqual(s["tests"], 1)
        self.assertEqual(s["days"], 8)
        self.assertEqual(s["days_needed_for_any_alert"], 12)
        self.assertEqual(s["mode"], "all foods")

    def test_too_few_days(self):
        res = analyze(self.diary, lags=(1,))
        r = res["rows"][0]
        self.assertEqual((r["days_exposed"], r["days_not_exposed"]), (2, 5))
        self.assertAlmostEqual(r["mean_difference"], 2.5)
        self.assertIsNone(r["p"])
        self.assertIsNone(r["q"])
        self.assertEqual(r["status"], "too few days")
        self.assertEqual(res["summary"]["tests"], 0)

    def test_suspects(self):
        res = analyze(self.diary, lags=(0,), suspects=["X", "Pasta", "x"],
                      min_exposed=2, min_unexposed=2, min_shift=2)
        self.assertEqual([r["food"] for r in res["rows"]], ["x", "pasta"])
        self.assertEqual(res["rows"][1]["status"], "not in diary")
        self.assertEqual(res["summary"]["tests"], 1)
        self.assertEqual(res["summary"]["mode"], "suspects named in advance")

    def test_report_and_cli(self):
        res = analyze(self.diary, lags=(0,), min_exposed=2, min_unexposed=2, min_shift=2)
        text = format_report(res)
        self.assertIn("not medical advice", text)
        self.assertIn("x | 0 | 2 | 6 | 5.0 | 0.1667 | 0.1667 | no clear pattern", text)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "diary.csv")
            out = os.path.join(tmp, "out.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(TEXT)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([path, "--lags", "0", "--min-days", "2", "--min-shift", "2", "--json", out])
            self.assertEqual(rc, 0)
            self.assertIn("no clear pattern", buf.getvalue())
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["rows"][0]["shifts"], 5)


if __name__ == "__main__":
    unittest.main()
