# SPDX-License-Identifier: Apache-2.0
import math
import unittest

from flarecheck.stats import (betai, bh_qvalues, circular_shift_p, days_needed,
                              mean_diff, shift, t_two_sided_p, welch)


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

    def test_circular_shift_p_no_signal(self):
        e = [1, 1, 0, 0, 0, 0, 0, 0]
        y = [2.0] * 8
        p, k = circular_shift_p(e, y, min_shift=2)
        self.assertEqual(k, 5)
        self.assertAlmostEqual(p, 1.0)

    def test_circular_shift_p_undefined(self):
        self.assertEqual(circular_shift_p([0, 0, 0, 0, 0, 0], [1.0] * 6, min_shift=2), (None, 0))

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
