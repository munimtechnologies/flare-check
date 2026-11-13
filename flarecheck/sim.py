# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents (Claude) working in MV2's name.
"""Synthetic diaries and the pre-registered calibration study.

No real person's data is used anywhere. Each synthetic diary has 20 foods.
Food k is eaten on a day with probability p_k (drawn from 0.15-0.60 per
diary); with habit > 0 eating follows a two-state Markov chain whose
day-to-day correlation is `habit` (people eat the same things for stretches).
The symptom score is mu + a_t, where a_t is an AR(1) series with
correlation `phi` and unit variance (bad days come in runs). In "power"
diaries, food01 raises the next day's score by `delta` (in SD units).

Three ways of flagging foods are compared on the same diaries:
  naive    Welch t-test per food and lag, flag if p < 0.05, no correction
  t_bh     the same t-tests, Benjamini-Hochberg q <= 0.10
  shift_bh flarecheck's circular-shift p-values, Benjamini-Hochberg q <= 0.10
Pre-registration: findings/calibration-prereg-v1-2026-11-13.md.

Usage: python -m flarecheck.sim --k 200 --seed 20261113 --out-dir out
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
                              t_two_sided_p, welch)

PREREG = "findings/calibration-prereg-v1-2026-11-13.md"
FOODS = ["food%02d" % j for j in range(1, 21)]
SUSPECTS = ["food01", "food02", "food03"]
EFFECT_FOOD = "food01"
LAGS = (0, 1)
MIN_DAYS = 5
MIN_SHIFT = 3
ALPHA = 0.05
Q_ALERT = 0.10


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
                min_shift=MIN_SHIFT, alpha=ALPHA, q_alert=Q_ALERT):
    tests = []
    for f in foods:
        for lag in lags:
            e = exposure_series(diary, f, lag)
            _, n1, n0 = mean_diff(e, diary.scores)
            if n1 < min_exposed or n0 < min_unexposed:
                continue
            tests.append((f, lag, e))
    p_t = []
    p_s = []
    for f, lag, e in tests:
        x1 = [y for ee, y in zip(e, diary.scores) if ee == 1 and y is not None]
        x0 = [y for ee, y in zip(e, diary.scores) if ee == 0 and y is not None]
        w = welch(x1, x0)
        p_t.append(1.0 if w is None else t_two_sided_p(w[0], w[1]))
        p, _ = circular_shift_p(e, diary.scores, min_shift=min_shift)
        p_s.append(1.0 if p is None else p)
    q_t = bh_qvalues(p_t)
    q_s = bh_qvalues(p_s)
    keys = [(f, lag) for f, lag, _ in tests]
    return {
        "tests": len(tests),
        "naive": {k for k, p in zip(keys, p_t) if p < alpha},
        "t_bh": {k for k, q in zip(keys, q_t) if q is not None and q <= q_alert},
        "shift_bh": {k for k, q in zip(keys, q_s) if q is not None and q <= q_alert},
    }


def config_name(c):
    return "%s-%s-n%d-phi%s-habit%s" % (c["kind"], c["mode"], c["n"], c["phi"], c["habit"])


def study_configs():
    out = []
    for phi, habit in ((0.0, 0.0), (0.6, 0.0), (0.6, 0.6)):
        for n in (30, 60, 90, 180):
            out.append({"kind": "null", "mode": "all", "n": n, "phi": phi, "habit": habit, "delta": 0.0})
    for n in (30, 60, 90, 180):
        out.append({"kind": "null", "mode": "suspects", "n": n, "phi": 0.6, "habit": 0.6, "delta": 0.0})
    for mode in ("all", "suspects"):
        for n in (30, 60, 90, 180):
            out.append({"kind": "power", "mode": mode, "n": n, "phi": 0.6, "habit": 0.0, "delta": 1.0})
    return out


def run_config(c, k, seed):
    name = config_name(c)
    rng = random.Random("%s-%s" % (seed, name))
    test_foods = SUSPECTS if c["mode"] == "suspects" else FOODS
    methods = ("naive", "t_bh", "shift_bh")
    any_flag = {m: 0 for m in methods}
    hit = {m: 0 for m in methods}
    false_flag = {m: 0 for m in methods}
    tests_total = 0
    for _ in range(k):
        probs = {f: rng.uniform(0.15, 0.60) for f in FOODS}
        effect = EFFECT_FOOD if c["kind"] == "power" else None
        diary = simulate_diary(rng, c["n"], probs, phi=c["phi"], habit=c["habit"],
                               delta=c["delta"], effect_food=effect)
        res = run_methods(diary, test_foods)
        tests_total += res["tests"]
        for m in methods:
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
    for m in methods:
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


def grade(rows):
    g = {}
    v = _get(rows, "null-all-n60-phi0.6-habit0.0", "naive_any")
    g["P1"] = _grade(v is not None and v >= 0.75, v)
    nulls = [r for r in rows if r["kind"] == "null"]
    worst = max((r["shift_bh_any"] for r in nulls), default=None)
    g["P2"] = _grade(worst is not None and worst <= 0.12 and len(nulls) == 16, worst)
    v = _get(rows, "null-all-n90-phi0.6-habit0.6", "t_bh_any")
    g["P3"] = _grade(v is not None and v >= 0.30, v)
    v = _get(rows, "power-all-n60-phi0.6-habit0.0", "shift_bh_power")
    g["P4"] = _grade(v is not None and v <= 0.05, v)
    v = _get(rows, "power-suspects-n90-phi0.6-habit0.0", "shift_bh_power")
    g["P5"] = _grade(v is not None and v >= 0.50, v)
    v = _get(rows, "power-suspects-n30-phi0.6-habit0.0", "shift_bh_power")
    g["P6"] = _grade(v is not None and v <= 0.05, v)
    v = _get(rows, "power-all-n60-phi0.6-habit0.0", "t_bh_power")
    g["P7"] = _grade(v is not None and v >= 0.50, v)
    return g


def to_markdown(result):
    lines = ["# flarecheck calibration results", "",
             "Code %s, %d synthetic diaries per setting, seed %s. Pre-registration: %s." % (
                 result["code_version"], result["k"], result["seed"], result["prereg"]),
             "",
             "| setting | mean tests | naive any | t_bh any | shift_bh any | naive power | t_bh power | shift_bh power |",
             "|---|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], r["mean_tests"], r["naive_any"], r["t_bh_any"], r["shift_bh_any"],
            r["naive_power"], r["t_bh_power"], r["shift_bh_power"]))
    lines.append("")
    lines.append("Grades: " + "; ".join("%s %s" % (k, v) for k, v in sorted(result["grades"].items())))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flarecheck.sim")
    ap.add_argument("--k", type=int, default=200)
    ap.add_argument("--seed", default="20261113")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    rows = []
    t0 = time.time()
    for c in study_configs():
        row = run_config(c, a.k, a.seed)
        row["seconds"] = round(time.time() - t0, 1)
        rows.append(row)
        print(row["name"], row["naive_any"], row["t_bh_any"], row["shift_bh_any"],
              row["shift_bh_power"], row["seconds"], flush=True)
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
