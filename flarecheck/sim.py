# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents (Claude) working in MV2's name.
"""Synthetic diaries and the pre-registered calibration study (version 2).

No real person's data is used anywhere. Each synthetic diary has 20 foods.
Food k is eaten on a day with probability p_k (drawn from 0.15-0.60 per
diary); with habit > 0 eating follows a two-state Markov chain whose
day-to-day correlation is `habit` (people eat the same things for stretches).
The symptom score is mu + a_t, where a_t is an AR(1) series with
correlation `phi` and unit variance (bad days come in runs). In "power"
diaries, food01 raises the next day's score by `delta` (in SD units).

Five ways of flagging foods are compared on the same diaries:
  naive         Welch t-test per food and lag, flag if p < 0.05, no correction
  t_bh          the same t-tests, Benjamini-Hochberg q <= 0.10
  shift_bh_ms3  flarecheck 0.1.0: circular-shift p skipping rotations 1-2 and
                n-2..n-1 (min_shift=3), Benjamini-Hochberg q <= 0.10
  shift_bh      flarecheck 0.2.0 bh method: every rotation (min_shift=1), BH q <= 0.10
  maxt          flarecheck 0.2.0 default: joint max-|t| rotation, adjusted p <= 0.10
Pre-registration: findings/calibration-prereg-v2-2026-11-14.md. Version 1
(seed 20261113, grade P1-P7) is frozen in release v0.1.0 and its results in
findings/calibration-results-v1-2026-11-14.md.

Usage: python -m flarecheck.sim --k 500 --seed 20261114 --out-dir out
"""
import argparse
import datetime
import json
import math
import os
import random
import sys
import time

from flarecheck import CODE_VERSION
from flarecheck.check import exposure_series
from flarecheck.diary import Diary
from flarecheck.stats import (bh_qvalues, circular_shift_p, mean_diff,
                              rotation_maxt, t_two_sided_p, welch)

PREREG = "findings/calibration-prereg-v2-2026-11-14.md"
FOODS = ["food%02d" % j for j in range(1, 21)]
SUSPECTS = ["food01", "food02", "food03"]
EFFECT_FOOD = "food01"
LAGS = (0, 1)
MIN_DAYS = 5
LEGACY_MIN_SHIFT = 3
ALPHA = 0.05
Q_ALERT = 0.10
METHODS = ("naive", "t_bh", "shift_bh_ms3", "shift_bh", "maxt")


def simulate_diary(rng, n_days, food_probs, phi=0.6, habit=0.0, delta=0.0,
                   effect_food=None, effect_lag=1, mu=4.0):
    names = sorted(food_probs)
    eaten = {f: [] for f in names}
    for f in names:
        p = food_probs[f]
        p11 = p + habit * (1.0 - p)
        p01 = p * (1.0 - habit)
        state = rng.random() < p
        for i in range(n_days):
            if i > 0:
                state = rng.random() < (p11 if state else p01)
            eaten[f].append(state)
    foods = [frozenset(f for f in names if eaten[f][i]) for i in range(n_days)]
    k = math.sqrt(1.0 - phi * phi)
    a = rng.gauss(0.0, 1.0)
    scores = []
    for i in range(n_days):
        if i > 0:
            a = phi * a + k * rng.gauss(0.0, 1.0)
        y = mu + a
        j = i - effect_lag
        if effect_food is not None and j >= 0 and effect_food in foods[j]:
            y += delta
        scores.append(y)
    return Diary(datetime.date(2026, 1, 1), foods, scores)


def run_methods(diary, foods, lags=LAGS, min_exposed=MIN_DAYS, min_unexposed=MIN_DAYS,
                alpha=ALPHA, q_alert=Q_ALERT):
    tests = []
    for f in foods:
        for lag in lags:
            e = exposure_series(diary, f, lag)
            _, n1, n0 = mean_diff(e, diary.scores)
            if n1 < min_exposed or n0 < min_unexposed:
                continue
            tests.append((f, lag, e))
    p_t = []
    p_old = []
    p_new = []
    for f, lag, e in tests:
        x1 = [y for ee, y in zip(e, diary.scores) if ee == 1 and y is not None]
        x0 = [y for ee, y in zip(e, diary.scores) if ee == 0 and y is not None]
        w = welch(x1, x0)
        p_t.append(1.0 if w is None else t_two_sided_p(w[0], w[1]))
        p, _ = circular_shift_p(e, diary.scores, min_shift=LEGACY_MIN_SHIFT)
        p_old.append(1.0 if p is None else p)
        p, _ = circular_shift_p(e, diary.scores, min_shift=1)
        p_new.append(1.0 if p is None else p)
    p_max, _, _ = rotation_maxt([e for _, _, e in tests], diary.scores)
    q_t = bh_qvalues(p_t)
    q_old = bh_qvalues(p_old)
    q_new = bh_qvalues(p_new)
    keys = [(f, lag) for f, lag, _ in tests]
    return {
        "tests": len(tests),
        "naive": {k for k, p in zip(keys, p_t) if p < alpha},
        "t_bh": {k for k, q in zip(keys, q_t) if q is not None and q <= q_alert},
        "shift_bh_ms3": {k for k, q in zip(keys, q_old) if q is not None and q <= q_alert},
        "shift_bh": {k for k, q in zip(keys, q_new) if q is not None and q <= q_alert},
        "maxt": {k for k, p in zip(keys, p_max) if p is not None and p <= q_alert},
    }


def config_name(c):
    return "%s-%s-n%d-phi%s-habit%s" % (c["kind"], c["mode"], c["n"], c["phi"], c["habit"])


def study_configs():
    out = []
    for phi, habit in ((0.0, 0.0), (0.6, 0.0), (0.6, 0.6)):
        for n in (30, 60, 90, 180):
            out.append({"kind": "null", "mode": "all", "n": n, "phi": phi, "habit": habit, "delta": 0.0})
    for habit in (0.6, 0.8):
        for n in (30, 60, 90, 180):
            out.append({"kind": "null", "mode": "suspects", "n": n, "phi": 0.6, "habit": habit,
                        "delta": 0.0})
    for mode in ("all", "suspects"):
        for n in (30, 60, 90, 180):
            out.append({"kind": "power", "mode": mode, "n": n, "phi": 0.6, "habit": 0.0, "delta": 1.0})
    return out


def run_config(c, k, seed):
    name = config_name(c)
    rng = random.Random("%s-%s" % (seed, name))
    test_foods = SUSPECTS if c["mode"] == "suspects" else FOODS
    any_flag = {m: 0 for m in METHODS}
    hit = {m: 0 for m in METHODS}
    false_flag = {m: 0 for m in METHODS}
    tests_total = 0
    for _ in range(k):
        probs = {f: rng.uniform(0.15, 0.60) for f in FOODS}
        effect = EFFECT_FOOD if c["kind"] == "power" else None
        diary = simulate_diary(rng, c["n"], probs, phi=c["phi"], habit=c["habit"],
                               delta=c["delta"], effect_food=effect)
        res = run_methods(diary, test_foods)
        tests_total += res["tests"]
        for m in METHODS:
            flags = res[m]
            if flags:
                any_flag[m] += 1
            if any(f == EFFECT_FOOD for f, _ in flags) and effect:
                hit[m] += 1
            if any(f != EFFECT_FOOD for f, _ in flags):
                false_flag[m] += 1
    row = dict(c)
    row["name"] = name
    row["diaries"] = k
    row["mean_tests"] = round(tests_total / k, 2) if k else 0.0
    for m in METHODS:
        row[m + "_any"] = round(any_flag[m] / k, 4) if k else 0.0
        row[m + "_power"] = round(hit[m] / k, 4) if (k and c["kind"] == "power") else None
        row[m + "_false"] = round(false_flag[m] / k, 4) if k else 0.0
    return row


def _get(rows, name, key):
    for r in rows:
        if r["name"] == name:
            return r[key]
    return None


def _grade(ok, value):
    if value is None:
        return "NOT GRADED (missing)"
    return ("PASS" if ok else "FAIL") + " (%s)" % value


def _worst(rows, key):
    nulls = [r for r in rows if r["kind"] == "null"]
    if len(nulls) != 20:
        return None
    return max(r[key] for r in nulls)


def grade(rows):
    """Version 2 predictions R1-R7, exactly as pre-registered."""
    g = {}
    v = _get(rows, "null-suspects-n90-phi0.6-habit0.6", "shift_bh_ms3_any")
    g["R1"] = _grade(v is not None and v >= 0.12, v)
    v = _worst(rows, "shift_bh_any")
    g["R2"] = _grade(v is not None and v <= 0.13, v)
    v = _worst(rows, "maxt_any")
    g["R3"] = _grade(v is not None and v <= 0.13, v)
    v = _get(rows, "power-all-n90-phi0.6-habit0.0", "maxt_power")
    g["R4"] = _grade(v is not None and v >= 0.50, v)
    v = _get(rows, "power-suspects-n60-phi0.6-habit0.0", "maxt_power")
    g["R5"] = _grade(v is not None and v >= 0.50, v)
    v = _get(rows, "null-suspects-n90-phi0.6-habit0.8", "shift_bh_ms3_any")
    g["R6"] = _grade(v is not None and v >= 0.12, v)
    v = _get(rows, "power-suspects-n90-phi0.6-habit0.0", "shift_bh_power")
    g["R7"] = _grade(v is not None and v >= 0.50, v)
    return g


def to_markdown(result):
    lines = ["# flarecheck calibration results (version 2)", "",
             "Code %s, %d synthetic diaries per setting, seed %s. Pre-registration: %s." % (
                 result["code_version"], result["k"], result["seed"], result["prereg"]),
             "",
             "| setting | mean tests | naive any | t_bh any | shift_bh_ms3 any | shift_bh any | maxt any"
             " | t_bh power | shift_bh_ms3 power | shift_bh power | maxt power |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], r["mean_tests"], r["naive_any"], r["t_bh_any"], r["shift_bh_ms3_any"],
            r["shift_bh_any"], r["maxt_any"], r["t_bh_power"], r["shift_bh_ms3_power"],
            r["shift_bh_power"], r["maxt_power"]))
    lines.append("")
    lines.append("Grades: " + "; ".join("%s %s" % (k, v) for k, v in sorted(result["grades"].items())))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flarecheck.sim")
    ap.add_argument("--k", type=int, default=500)
    ap.add_argument("--seed", default="20261114")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    rows = []
    t0 = time.time()
    for c in study_configs():
        row = run_config(c, a.k, a.seed)
        row["seconds"] = round(time.time() - t0, 1)
        rows.append(row)
        print(row["name"], row["shift_bh_ms3_any"], row["shift_bh_any"], row["maxt_any"],
              row["maxt_power"], row["seconds"], flush=True)
        with open(os.path.join(a.out_dir, "partial.json"), "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
    result = {"code_version": CODE_VERSION, "prereg": PREREG, "k": a.k, "seed": a.seed,
              "rows": rows, "grades": grade(rows)}
    with open(os.path.join(a.out_dir, "calibration.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    with open(os.path.join(a.out_dir, "calibration.md"), "w", encoding="utf-8") as fh:
        fh.write(to_markdown(result))
    print("GRADES", json.dumps(result["grades"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
