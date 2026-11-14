# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents (Claude) working in MV2's name.
"""Small, dependency-free statistics used by flarecheck.

- mean_diff: mean symptom score on exposed days minus unexposed days.
- circular_shift_p: a permutation p-value that keeps the day-to-day
  autocorrelation of both series (the food series is rotated, not shuffled).
- welch_abs_t / rotation_maxt: a joint rotation test over all foods and lags
  at once (single-step max-|t|), which controls the chance of ANY false
  alarm and whose smallest possible p does not grow with the number of tests.
- bh_qvalues: Benjamini-Hochberg adjusted p-values (q-values).
- welch / t_two_sided_p: the ordinary Welch t-test, used only as a
  comparison in the calibration study.

Why every rotation is used (0.2.0): a rotation test is exact only when the
observed series is compared with ALL other rotations, because then the
observed statistic is just one member of a group whose members are equally
likely to be the largest. flarecheck 0.1.0 skipped the rotations within 2 days
of the observed one (min_shift=3). When eating habits and symptoms both come
in runs, the statistic changes smoothly from one rotation to the next, and
skipping the near neighbours let several rotations around a chance peak each
count as "beats everything it is compared with". The pre-registered
calibration (findings/calibration-results-v1-2026-11-14.md) measured 19%
false alarms against a 10% target in one setting. The default is now
min_shift=1, i.e. every rotation.
"""
import math


def mean_diff(exposure, scores):
    """Return (difference, n_exposed, n_unexposed).

    exposure: list of 1, 0 or None; scores: list of float or None.
    Pairs with a None on either side are skipped. The difference is None
    when either group is empty.
    """
    s1 = 0.0
    s0 = 0.0
    n1 = 0
    n0 = 0
    for e, y in zip(exposure, scores):
        if e is None or y is None:
            continue
        if e:
            s1 += y
            n1 += 1
        else:
            s0 += y
            n0 += 1
    if n1 == 0 or n0 == 0:
        return None, n1, n0
    return s1 / n1 - s0 / n0, n1, n0


def shift(seq, s):
    """Rotate seq right by s positions: out[i] = seq[(i - s) mod n]."""
    n = len(seq)
    return [seq[(i - s) % n] for i in range(n)]


def circular_shift_p(exposure, scores, min_shift=1, min_group=1):
    """Two-sided circular-shift permutation p-value for mean_diff.

    Every rotation s with min_shift <= s <= n - min_shift is one draw from
    the null. p = (1 + number of rotations at least as extreme) /
    (1 + number of usable rotations). Returns (p, usable rotations), or
    (None, 0) if the observed difference or every rotation is undefined.
    The smallest possible p is 1 / (n - 2 * min_shift + 2).
    min_shift=1 (every rotation, the default) is the valid choice; larger
    values are kept only to reproduce flarecheck 0.1.0 and are not valid
    when the statistic is smooth across rotations.
    """
    n = len(exposure)
    obs, _, _ = mean_diff(exposure, scores)
    if obs is None:
        return None, 0
    hits = 0
    valid = 0
    for s in range(min_shift, n - min_shift + 1):
        d, a, b = mean_diff(shift(exposure, s), scores)
        if d is None or a < min_group or b < min_group:
            continue
        valid += 1
        if abs(d) >= abs(obs) - 1e-9:
            hits += 1
    if valid == 0:
        return None, 0
    return (1 + hits) / (1 + valid), valid


def welch_abs_t(exposure, scores, s=0):
    """|Welch t| of scores on exposed vs other days, exposure rotated right by s.

    The rotated exposure is out[i] = exposure[(i - s) mod n]. Days with None
    on either side are skipped. Returns None if either group has fewer than
    2 days or both groups have zero variance.
    """
    n = len(exposure)
    n1 = 0
    n0 = 0
    s1 = 0.0
    s0 = 0.0
    q1 = 0.0
    q0 = 0.0
    for i in range(n):
        y = scores[i]
        e = exposure[(i - s) % n]
        if e is None or y is None:
            continue
        if e:
            n1 += 1
            s1 += y
            q1 += y * y
        else:
            n0 += 1
            s0 += y
            q0 += y * y
    if n1 < 2 or n0 < 2:
        return None
    m1 = s1 / n1
    m0 = s0 / n0
    v1 = max(q1 - s1 * m1, 0.0) / (n1 - 1)
    v0 = max(q0 - s0 * m0, 0.0) / (n0 - 1)
    se2 = v1 / n1 + v0 / n0
    if se2 <= 0.0:
        return None
    return abs(m1 - m0) / math.sqrt(se2)


def rotation_maxt(exposures, scores):
    """Joint rotation test over several exposure series (single-step max-|t|).

    All series are rotated TOGETHER against the scores by every s = 1..n-1.
    For each rotation, M(s) is the largest |Welch t| over all series. For
    series j, the adjusted p is
        (1 + number of rotations with M(s) >= observed |t_j|) / (1 + usable rotations).
    A rotation is usable if at least one series has a defined t there.
    Adjusted p <= alpha controls the chance of any false alarm at alpha when
    no food matters (for a diary whose statistics are unchanged by rotation).
    Returns (adjusted p list, observed |t| list, usable rotations); entries are
    None where the observed |t| is undefined.
    """
    m = len(exposures)
    n = len(scores)
    obs = [welch_abs_t(e, scores, 0) for e in exposures]
    if all(o is None for o in obs):
        return [None] * m, obs, 0
    hits = [0] * m
    valid = 0
    for s in range(1, n):
        best = None
        for e in exposures:
            t = welch_abs_t(e, scores, s)
            if t is not None and (best is None or t > best):
                best = t
        if best is None:
            continue
        valid += 1
        for j, o in enumerate(obs):
            if o is not None and best >= o - 1e-9:
                hits[j] += 1
    if valid == 0:
        return [None] * m, obs, 0
    p = [None if o is None else (1 + h) / (1 + valid) for o, h in zip(obs, hits)]
    return p, obs, valid


def bh_qvalues(pvals):
    """Benjamini-Hochberg q-values; None entries are left out and stay None."""
    idx = [i for i, p in enumerate(pvals) if p is not None]
    m = len(idx)
    q = [None] * len(pvals)
    if m == 0:
        return q
    order = sorted(idx, key=lambda i: pvals[i])
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        val = min(prev, pvals[i] * m / rank)
        q[i] = val
        prev = val
    return q


def days_needed(tests, q_alert=0.10, min_shift=1):
    """Fewest diary days at which ONE test could reach q <= q_alert (BH method).

    With n days there are n - 2*min_shift + 1 rotations, so the smallest
    p is 1 / (n - 2*min_shift + 2) and the smallest single q is that
    times the number of tests. For the joint max-|t| test call it with
    tests=1: its smallest adjusted p is 1/n whatever the number of tests.
    """
    tests = max(int(tests), 1)
    return int(math.ceil(tests / q_alert - 1e-9)) + 2 * min_shift - 2


def welch(x1, x0):
    """Welch t statistic and degrees of freedom, or None if undefined."""
    n1 = len(x1)
    n0 = len(x0)
    if n1 < 2 or n0 < 2:
        return None
    m1 = sum(x1) / n1
    m0 = sum(x0) / n0
    v1 = sum((x - m1) ** 2 for x in x1) / (n1 - 1)
    v0 = sum((x - m0) ** 2 for x in x0) / (n0 - 1)
    a = v1 / n1
    b = v0 / n0
    if a + b <= 0.0:
        return None
    t = (m1 - m0) / math.sqrt(a + b)
    df = (a + b) ** 2 / (a * a / (n1 - 1) + b * b / (n0 - 1))
    return t, df


def _betacf(a, b, x):
    # Continued fraction for the incomplete beta function (modified Lentz).
    maxit = 300
    eps = 3e-14
    fpmin = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        dl = d * c
        h *= dl
        if abs(dl - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
           + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(lbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t, df):
    """Two-sided p-value of Student's t with df degrees of freedom."""
    x = df / (df + t * t)
    return min(1.0, max(0.0, betai(df / 2.0, 0.5, x)))
