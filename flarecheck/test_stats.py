# SPDX-License-Identifier: Apache-2.0
import math
import unittest

from flarecheck.stats import (betai, bh_qvalues, circular_shift_p, days_needed,
                              mean_diff, rotation_maxt, shift, t_two_sided_p,
                              welch, welch_abs_t)

# Hand case for the 0.2.0 tests: exposed on days 0-1 of 6.
E6 = [1, 1, 0, 0, 0, 0]
F6 = [0, 0, 1, 1, 0, 0]
Y6 = [4.0, 2.0, 1.0, 0.0, 0.0, 1.0]
# |t| of E6 rotated by s (exposed days s and s+1):
#   s=0 2.5/sqrt(13/12) = 2.4019   s=1 0.2335   s=2 1.2632
#   s=3 2/sqrt(0.5)     = 2.8284   s=4 1.2632   s=5 1.1114


class TestStats(unittest.TestCase):
    def test_mean_diff_skips_missing(self):
        d, n1, n0 = mean_diff([1, 0, 1, 0, None], [4.0, 2.0, 6.0, None, 9.0])
        self.assertAlmostEqual(d, 3.0)
        self.assertEqual((n1, n0), (2, 1))

    def test_mean_diff_empty_group(self):
        self.assertEqual(mean_diff([1, 1], [2.0, 3.0]), (None, 2, 0))

    def test_shift(self):
        self.assertEqual(shift(["A", "B", "C", "D"], 1), ["D", "A", "B", "C"])
        self.assertEqual(shift(["A", "B", "C", "D"], 4), ["A", "B", "C", "D"])

    def test_circular_shift_p_hand_case(self):
        e = [1, 1, 0, 0, 0, 0, 0, 0]
        y = [5.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        p, k = circular_shift_p(e, y, min_shift=2)
        self.assertEqual(k, 5)
        self.assertAlmostEqual(p, 1.0 / 6.0)

    def test_circular_shift_p_full_group_default(self):
        # Mean differences over rotations 1..5: 0.25, -1.25, -2, -1.25, 1.75; observed 2.5.
        p, k = circular_shift_p(E6, Y6)
        self.assertEqual(k, 5)
        self.assertAlmostEqual(p, 1.0 / 6.0)

    def test_circular_shift_p_no_signal(self):
        e = [1, 1, 0, 0, 0, 0, 0, 0]
        y = [2.0] * 8
        p, k = circular_shift_p(e, y, min_shift=2)
        self.assertEqual(k, 5)
        self.assertAlmostEqual(p, 1.0)

    def test_circular_shift_p_undefined(self):
        self.assertEqual(circular_shift_p([0, 0, 0, 0, 0, 0], [1.0] * 6, min_shift=2), (None, 0))

    def test_welch_abs_t(self):
        self.assertAlmostEqual(welch_abs_t(E6, Y6), 2.5 * math.sqrt(12.0 / 13.0))
        self.assertAlmostEqual(welch_abs_t(E6, Y6), abs(welch([4.0, 2.0], [1.0, 0.0, 0.0, 1.0])[0]))
        self.assertAlmostEqual(welch_abs_t(E6, Y6, 1), 0.25 / math.sqrt(0.25 + 10.75 / 12.0))
        self.assertAlmostEqual(welch_abs_t(E6, Y6, 3), 2.0 * math.sqrt(2.0))
        self.assertIsNone(welch_abs_t([1, 0, 0], [1.0, 2.0, 3.0]))
        self.assertIsNone(welch_abs_t([1, 1, 0, 0], [5.0, 5.0, 0.0, 0.0]))
        self.assertIsNone(welch_abs_t([1, 1, None, 0], [5.0, 4.0, 1.0, 0.0]))

    def test_rotation_maxt_single(self):
        # Only rotation 3 (2.8284) beats the observed 2.4019.
        p, obs, k = rotation_maxt([E6], Y6)
        self.assertEqual(k, 5)
        self.assertAlmostEqual(p[0], 2.0 / 6.0)
        self.assertAlmostEqual(obs[0], 2.5 * math.sqrt(12.0 / 13.0))

    def test_rotation_maxt_two_series(self):
        # F6 is E6 two days later, so its |t| at rotation s is E6's at s+2.
        # Max over both per rotation 1..5: 2.8284, 1.2632, 2.8284, 2.4019, 1.1114.
        p, obs, k = rotation_maxt([E6, F6], Y6)
        self.assertEqual(k, 5)
        self.assertAlmostEqual(p[0], 4.0 / 6.0)
        self.assertAlmostEqual(p[1], 5.0 / 6.0)
        self.assertAlmostEqual(obs[1], 1.25 / math.sqrt(0.25 + 8.75 / 12.0))

    def test_rotation_maxt_undefined(self):
        self.assertEqual(rotation_maxt([[1, 1, 0, 0]], [5.0, 5.0, 0.0, 0.0]), ([None], [None], 0))
        self.assertEqual(rotation_maxt([], Y6), ([], [], 0))

    def test_bh(self):
        q = bh_qvalues([0.01, 0.04, None, 0.03])
        self.assertAlmostEqual(q[0], 0.03)
        self.assertAlmostEqual(q[1], 0.04)
        self.assertIsNone(q[2])
        self.assertAlmostEqual(q[3], 0.04)
        self.assertEqual(bh_qvalues([None]), [None])

    def test_days_needed(self):
        self.assertEqual(days_needed(1, 0.1, 3), 14)
        self.assertEqual(days_needed(40, 0.1, 3), 404)
        self.assertEqual(days_needed(1, 0.1, 2), 12)
        self.assertEqual(days_needed(0, 0.1, 2), 12)
        self.assertEqual(days_needed(6, 0.1), 60)
        self.assertEqual(days_needed(1, 0.1), 10)

    def test_welch(self):
        t, df = welch([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        self.assertAlmostEqual(t, -3.0 / math.sqrt(2.0 / 3.0))
        self.assertAlmostEqual(df, 4.0)
        self.assertIsNone(welch([1.0], [2.0, 3.0]))
        self.assertIsNone(welch([5.0, 5.0], [0.0, 0.0]))

    def test_t_p_closed_forms(self):
        # df = 1 is the Cauchy distribution: P(|T| > 1) = 0.5.
        self.assertAlmostEqual(t_two_sided_p(1.0, 1.0), 0.5, places=9)
        # df = 2: P(|T| > t) = 1 - t / sqrt(2 + t^2).
        self.assertAlmostEqual(t_two_sided_p(1.0, 2.0), 1.0 - 1.0 / math.sqrt(3.0), places=9)
        self.assertAlmostEqual(t_two_sided_p(3.0, 2.0), 1.0 - 3.0 / math.sqrt(11.0), places=9)
        self.assertAlmostEqual(t_two_sided_p(0.0, 7.0), 1.0)

    def test_betai_edges(self):
        self.assertEqual(betai(2.0, 3.0, 0.0), 0.0)
        self.assertEqual(betai(2.0, 3.0, 1.0), 1.0)
        # I_x(1, b) = 1 - (1 - x)^b
        self.assertAlmostEqual(betai(1.0, 2.5, 0.3), 1.0 - 0.7 ** 2.5, places=9)


if __name__ == "__main__":
    unittest.main()
