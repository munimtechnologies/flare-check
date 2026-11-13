# SPDX-License-Identifier: Apache-2.0
import random
import unittest

from flarecheck.diary import parse_text
from flarecheck.sim import (FOODS, config_name, grade, run_config, run_methods,
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
        d = parse_text(TEXT)
        res = run_methods(d, ["x"], lags=(0,), min_exposed=2, min_unexposed=2, min_shift=2)
        self.assertEqual(res["tests"], 1)
        self.assertEqual(res["naive"], set())
        self.assertEqual(res["t_bh"], set())
        self.assertEqual(res["shift_bh"], set())

    def test_configs(self):
        cs = study_configs()
        self.assertEqual(len(cs), 24)
        names = [config_name(c) for c in cs]
        self.assertEqual(len(set(names)), 24)
        self.assertIn("null-all-n60-phi0.6-habit0.0", names)
        self.assertIn("power-suspects-n90-phi0.6-habit0.0", names)
        self.assertEqual(len(FOODS), 20)

    def test_run_config_smoke(self):
        c = {"kind": "power", "mode": "suspects", "n": 30, "phi": 0.6, "habit": 0.0, "delta": 1.0}
        row = run_config(c, 2, "1")
        self.assertEqual(row["name"], "power-suspects-n30-phi0.6-habit0.0")
        self.assertEqual(row["diaries"], 2)
        for m in ("naive", "t_bh", "shift_bh"):
            self.assertTrue(0.0 <= row[m + "_power"] <= 1.0)
            self.assertTrue(0.0 <= row[m + "_any"] <= 1.0)

    def test_grade(self):
        rows = []
        for c in study_configs():
            r = dict(c)
            r["name"] = config_name(c)
            r["naive_any"] = 0.9
            r["t_bh_any"] = 0.5
            r["shift_bh_any"] = 0.08
            r["shift_bh_power"] = 0.0
            r["t_bh_power"] = 0.8
            rows.append(r)
        for r in rows:
            if r["name"] == "power-suspects-n90-phi0.6-habit0.0":
                r["shift_bh_power"] = 0.7
        g = grade(rows)
        self.assertEqual(g["P1"], "PASS (0.9)")
        self.assertEqual(g["P2"], "PASS (0.08)")
        self.assertEqual(g["P3"], "PASS (0.5)")
        self.assertEqual(g["P4"], "PASS (0.0)")
        self.assertEqual(g["P5"], "PASS (0.7)")
        self.assertEqual(g["P6"], "PASS (0.0)")
        self.assertEqual(g["P7"], "PASS (0.8)")
        rows[0]["shift_bh_any"] = 0.2
        self.assertEqual(grade(rows)["P2"], "FAIL (0.2)")


if __name__ == "__main__":
    unittest.main()
