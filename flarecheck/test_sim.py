# SPDX-License-Identifier: Apache-2.0
import random
import unittest

from flarecheck.diary import parse_text
from flarecheck.sim import (FOODS, METHODS, config_name, grade, run_config, run_methods,
                            simulate_diary, study_configs)

TEXT = "date,foods,score\n2026-03-01,X,5\n2026-03-02,x,5\n" + "".join(
    "2026-03-0%d,-,0\n" % day for day in range(3, 9))


class TestSim(unittest.TestCase):
    def test_simulate_is_deterministic(self):
        probs = {"food01": 0.3, "food02": 0.5}
        a = simulate_diary(random.Random(7), 40, probs, phi=0.6, habit=0.6)
        b = simulate_diary(random.Random(7), 40, probs, phi=0.6, habit=0.6)
        self.assertEqual(len(a), 40)
        self.assertEqual(a.scores, b.scores)
        self.assertEqual(a.foods, b.foods)
        self.assertTrue(set(a.items()) <= {"food01", "food02"})

    def test_effect_is_added_next_day(self):
        probs = {"food01": 0.5}
        base = simulate_diary(random.Random(3), 30, probs, phi=0.0, delta=0.0)
        eff = simulate_diary(random.Random(3), 30, probs, phi=0.0, delta=2.0,
                             effect_food="food01")
        self.assertEqual(base.foods, eff.foods)
        for i in range(30):
            ate = i >= 1 and "food01" in base.foods[i - 1]
            self.assertAlmostEqual(eff.scores[i] - base.scores[i], 2.0 if ate else 0.0)

    def test_run_methods_hand_case(self):
        # Legacy p = 1/4 (3 rotations), every-rotation p = 1/8, Welch and max-|t| undefined
        # (no variance in either group): nothing reaches the alert level.
        d = parse_text(TEXT)
        res = run_methods(d, ["x"], lags=(0,), min_exposed=2, min_unexposed=2)
        self.assertEqual(res["tests"], 1)
        for m in METHODS:
            self.assertEqual(res[m], set(), m)

    def test_configs(self):
        cs = study_configs()
        self.assertEqual(len(cs), 28)
        names = [config_name(c) for c in cs]
        self.assertEqual(len(set(names)), 28)
        self.assertEqual(sum(1 for c in cs if c["kind"] == "null"), 20)
        self.assertIn("null-all-n60-phi0.6-habit0.0", names)
        self.assertIn("null-suspects-n90-phi0.6-habit0.6", names)
        self.assertIn("null-suspects-n90-phi0.6-habit0.8", names)
        self.assertIn("power-all-n90-phi0.6-habit0.0", names)
        self.assertIn("power-suspects-n60-phi0.6-habit0.0", names)
        self.assertIn("power-suspects-n90-phi0.6-habit0.0", names)
        self.assertEqual(len(FOODS), 20)

    def test_run_config_smoke(self):
        c = {"kind": "power", "mode": "suspects", "n": 30, "phi": 0.6, "habit": 0.0, "delta": 1.0}
        row = run_config(c, 2, "1")
        self.assertEqual(row["name"], "power-suspects-n30-phi0.6-habit0.0")
        self.assertEqual(row["diaries"], 2)
        for m in METHODS:
            self.assertTrue(0.0 <= row[m + "_power"] <= 1.0)
            self.assertTrue(0.0 <= row[m + "_any"] <= 1.0)

    def test_grade(self):
        rows = []
        for c in study_configs():
            r = dict(c)
            r["name"] = config_name(c)
            r["shift_bh_ms3_any"] = 0.2
            r["shift_bh_any"] = 0.08
            r["maxt_any"] = 0.07
            r["maxt_power"] = 0.7
            r["shift_bh_power"] = 0.9
            rows.append(r)
        g = grade(rows)
        self.assertEqual(g, {"R1": "PASS (0.2)", "R2": "PASS (0.08)", "R3": "PASS (0.07)",
                             "R4": "PASS (0.7)", "R5": "PASS (0.7)", "R6": "PASS (0.2)",
                             "R7": "PASS (0.9)"})
        rows[0]["maxt_any"] = 0.2
        for r in rows:
            if r["name"] == "null-suspects-n90-phi0.6-habit0.6":
                r["shift_bh_ms3_any"] = 0.1
        g = grade(rows)
        self.assertEqual(g["R1"], "FAIL (0.1)")
        self.assertEqual(g["R3"], "FAIL (0.2)")
        self.assertEqual(grade(rows[1:])["R2"], "NOT GRADED (missing)")


if __name__ == "__main__":
    unittest.main()
