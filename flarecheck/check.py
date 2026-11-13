# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents (Claude) working in MV2's name.
"""Check a personal food and symptom diary for food-symptom patterns.

For each food (or only the suspects you name in advance) and each lag
(0 = same day, 1 = the day after), it compares the mean symptom score on
days after eating the food with the other days. The p-value comes from
rotating the food series against the score series (circular shifts), which
keeps the run-of-bad-days structure of real symptoms and real eating habits,
and the q-value corrects for the number of foods and lags tested
(Benjamini-Hochberg).

This is an information tool. It is not medical advice and it does not
diagnose anything. A 'possible pattern' is not proof that a food causes
symptoms, and 'no clear pattern' does not prove that a food is safe.

Usage:
  python -m flarecheck.check diary.csv [--suspects "milk;bread"] [--lags 0,1]
                             [--min-days 5] [--min-shift 3] [--q 0.10]
                             [--json result.json]
"""
import argparse
import json
import sys

from flarecheck import CODE_VERSION
from flarecheck.diary import norm_item, read_csv
from flarecheck.stats import bh_qvalues, circular_shift_p, days_needed, mean_diff

NOTE = [
    "This is a pattern check on your own diary, not medical advice.",
    "A 'possible pattern' is not proof that a food causes symptoms, and 'no clear pattern'",
    "does not prove a food is safe. Talk to your clinician or a registered dietitian",
    "before changing your diet; cutting out foods can cause harm of its own.",
]


def exposure_series(diary, food, lag):
    """1 if `food` was eaten `lag` days before each day, 0 if not, None if unknown."""
    out = []
    for i in range(len(diary)):
        j = i - lag
        if j < 0 or diary.foods[j] is None:
            out.append(None)
        else:
            out.append(1 if food in diary.foods[j] else 0)
    return out


def analyze(diary, lags=(0, 1), suspects=None, min_exposed=5, min_unexposed=5,
            min_shift=3, q_alert=0.10):
    known = diary.items()
    if suspects:
        foods = []
        for s in suspects:
            s = norm_item(s)
            if s and s not in foods:
                foods.append(s)
    else:
        foods = known
    rows = []
    for food in foods:
        for lag in lags:
            row = {"food": food, "lag_days": lag, "days_exposed": 0,
                   "days_not_exposed": 0, "mean_difference": None,
                   "p": None, "q": None, "shifts": 0, "status": ""}
            if food not in known:
                row["status"] = "not in diary"
                rows.append(row)
                continue
            e = exposure_series(diary, food, lag)
            d, n1, n0 = mean_diff(e, diary.scores)
            row["days_exposed"] = n1
            row["days_not_exposed"] = n0
            if d is not None:
                row["mean_difference"] = round(d, 3)
            if n1 < min_exposed or n0 < min_unexposed:
                row["status"] = "too few days"
            else:
                p, k = circular_shift_p(e, diary.scores, min_shift=min_shift)
                row["p"] = p
                row["shifts"] = k
                if p is None:
                    row["status"] = "too few days"
            rows.append(row)
    qs = bh_qvalues([r["p"] for r in rows])
    for r, q in zip(rows, qs):
        r["q"] = q
        if not r["status"]:
            r["status"] = "possible pattern" if q <= q_alert else "no clear pattern"
        if r["p"] is not None:
            r["p"] = round(r["p"], 4)
        if r["q"] is not None:
            r["q"] = round(r["q"], 4)
    tested = sum(1 for r in rows if r["p"] is not None)
    summary = {
        "code_version": CODE_VERSION,
        "start": diary.start.isoformat(),
        "days": len(diary),
        "days_with_foods": diary.days_with_foods(),
        "days_with_score": diary.days_with_score(),
        "mode": "suspects named in advance" if suspects else "all foods",
        "lags": list(lags),
        "tests": tested,
        "q_alert": q_alert,
        "min_shift": min_shift,
        "days_needed_for_any_alert": days_needed(tested, q_alert, min_shift),
    }
    return {"summary": summary, "rows": rows}


def _fmt(x):
    return "-" if x is None else str(x)


def format_report(result):
    s = result["summary"]
    lines = [
        "flarecheck %s: %d days from %s (%d with foods, %d with a score); %d tests (%s)" % (
            s["code_version"], s["days"], s["start"], s["days_with_foods"],
            s["days_with_score"], s["tests"], s["mode"]),
        "",
        "food | lag days | days after eating | other days | mean difference | p | q | status",
    ]
    for r in result["rows"]:
        lines.append(" | ".join([
            r["food"], str(r["lag_days"]), str(r["days_exposed"]),
            str(r["days_not_exposed"]), _fmt(r["mean_difference"]),
            _fmt(r["p"]), _fmt(r["q"]), r["status"]]))
    lines.append("")
    lines.append(
        "With %d tests, no single food can reach q <= %s before about %d logged days. "
        "Naming 1-3 suspects in advance (--suspects) needs far fewer days." % (
            s["tests"], s["q_alert"], s["days_needed_for_any_alert"]))
    lines.extend(NOTE)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flarecheck.check", description=__doc__.split("\n\n")[0])
    ap.add_argument("diary")
    ap.add_argument("--suspects", default="", help="foods named in advance, separated by ';'")
    ap.add_argument("--lags", default="0,1")
    ap.add_argument("--min-days", type=int, default=5)
    ap.add_argument("--min-shift", type=int, default=3)
    ap.add_argument("--q", type=float, default=0.10)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    diary = read_csv(a.diary)
    lags = tuple(int(x) for x in a.lags.split(",") if x.strip())
    suspects = [x for x in a.suspects.split(";") if x.strip()] or None
    result = analyze(diary, lags=lags, suspects=suspects, min_exposed=a.min_days,
                     min_unexposed=a.min_days, min_shift=a.min_shift, q_alert=a.q)
    print(format_report(result))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
