# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
import os
import tempfile
import unittest

from flarecheck.check import FLAG, analyze, exposure_series, format_report, main
from flarecheck.diary import parse_text

# Food X on the first two days, a score of 5 on those days and 0 on the other six.
TEXT = "date,foods,score\n2026-03-01,X,5\n2026-03-02,x,5\n" + "".join(
    "2026-03-0%d,-,0\n" % day for day in range(3, 9))

# Six days, food X on days 1-2, scores 4 2 1 0 0 1 (the E6/Y6 case in test_stats).
TEXT2 = ("date,foods,score\n2026-03-01,X,4\n2026-03-02,X,2\n2026-03-03,-,1\n"
         "2026-03-04,-,0\n2026-03-05,-,0\n2026-03-06,-,1\n")

# The same, plus food W on days 3-4 (the F6 case in test_stats).
TEXT3 = ("date,foods,score\n2026-03-01,X,4\n2026-03-02,X,2\n2026-03-03,W,1\n"
         "2026-03-04,w,0\n2026-03-05,-,0\n2026-03-06,-,1\n")


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.diary = parse_text(TEXT)

    def test_exposure_series(self):
        self.assertEqual(exposure_series(self.diary, "x", 0), [1, 1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(exposure_series(self.diary, "x", 1), [None, 1, 1, 0, 0, 0, 0, 0])

    def test_hand_case_bh(self):
        res = analyze(self.diary, lags=(0,), min_exposed=2, min_unexposed=2, min_shift=2,
                      method="bh")
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
        self.assertEqual(s["method"], "bh")

    def test_maxt_default(self):
        res = analyze(parse_text(TEXT2), lags=(0,), min_exposed=2, min_unexposed=2)
        r = res["rows"][0]
        self.assertEqual((r["days_exposed"], r["days_not_exposed"]), (2, 4))
        self.assertAlmostEqual(r["mean_difference"], 2.5)
        self.assertAlmostEqual(r["p"], 0.3333)
        self.assertAlmostEqual(r["q"], 0.3333)
        self.assertEqual(r["shifts"], 5)
        self.assertEqual(r["status"], "no clear pattern")
        s = res["summary"]
        self.assertEqual(s["method"], "maxt")
        self.assertEqual(s["tests"], 1)
        self.assertEqual(s["min_shift"], 1)
        self.assertEqual(s["days_needed_for_any_alert"], 10)
        self.assertFalse(s["calibrated"])

    def test_bh_full_group_default(self):
        res = analyze(parse_text(TEXT2), lags=(0,), min_exposed=2, min_unexposed=2, method="bh")
        r = res["rows"][0]
        self.assertAlmostEqual(r["p"], 0.1667)
        self.assertEqual(r["shifts"], 5)
        self.assertEqual(res["summary"]["days_needed_for_any_alert"], 10)

    def test_maxt_two_foods(self):
        res = analyze(parse_text(TEXT3), lags=(0,), min_exposed=2, min_unexposed=2)
        self.assertEqual([r["food"] for r in res["rows"]], ["w", "x"])
        self.assertAlmostEqual(res["rows"][0]["p"], 0.8333)
        self.assertAlmostEqual(res["rows"][1]["p"], 0.6667)
        self.assertEqual(res["summary"]["tests"], 2)

    def test_flag_is_marked_unverified(self):
        res = analyze(parse_text(TEXT2), lags=(0,), min_exposed=2, min_unexposed=2,
                      method="bh", q_alert=0.2)
        self.assertEqual(res["rows"][0]["status"], FLAG)
        self.assertEqual(FLAG, "possible pattern (unverified)")

    def test_bad_method(self):
        with self.assertRaises(ValueError):
            analyze(self.diary, method="naive")

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
                      min_exposed=2, min_unexposed=2, min_shift=2, method="bh")
        self.assertEqual([r["food"] for r in res["rows"]], ["x", "pasta"])
        self.assertEqual(res["rows"][1]["status"], "not in diary")
        self.assertEqual(res["summary"]["tests"], 1)
        self.assertEqual(res["summary"]["mode"], "suspects named in advance")

    def test_report_and_cli(self):
        res = analyze(self.diary, lags=(0,), min_exposed=2, min_unexposed=2, min_shift=2,
                      method="bh")
        text = format_report(res)
        self.assertIn("not medical advice", text)
        self.assertIn("unverified", text)
        self.assertIn("x | 0 | 2 | 6 | 5.0 | 0.1667 | 0.1667 | no clear pattern", text)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "diary.csv")
            out = os.path.join(tmp, "out.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(TEXT2)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main([path, "--lags", "0", "--min-days", "2", "--json", out])
            self.assertEqual(rc, 0)
            self.assertIn("x | 0 | 2 | 4 | 2.5 | 0.3333 | 0.3333 | no clear pattern", buf.getvalue())
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["rows"][0]["shifts"], 5)
            self.assertEqual(data["summary"]["method"], "maxt")


if __name__ == "__main__":
    unittest.main()
