# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents (Claude) working in MV2's name.
"""Read a personal food and symptom diary.

CSV with a header row and three columns:
  date   YYYY-MM-DD
  foods  items eaten that day, separated by ';'. Write '-' for a day on which
         you logged that you ate none of your tracked items. Leave it blank if
         you did not log food that day (the day is then left out).
  score  symptom score for that day (any number scale, e.g. 0-10); blank if
         not logged.
Several rows for one date are merged: foods are combined and the highest
score is kept. Dates with no row at all count as not logged.
"""
import csv
import datetime
import io
import math


class Diary:
    """One entry per calendar day from the first to the last date."""

    def __init__(self, start, foods, scores):
        self.start = start      # datetime.date of index 0
        self.foods = foods      # list of frozenset, or None if not logged
        self.scores = scores    # list of float, or None if not logged

    def __len__(self):
        return len(self.foods)

    def items(self):
        seen = set()
        for f in self.foods:
            if f:
                seen |= f
        return sorted(seen)

    def days_with_foods(self):
        return sum(1 for f in self.foods if f is not None)

    def days_with_score(self):
        return sum(1 for s in self.scores if s is not None)


def norm_item(text):
    return " ".join((text or "").strip().lower().split())


def parse_rows(rows):
    by_day = {}
    for raw in rows:
        r = {}
        for k, v in raw.items():
            if isinstance(k, str):
                r[k.strip().lower()] = v if isinstance(v, str) else ""
        date_text = (r.get("date") or "").strip()
        food_text = (r.get("foods") or "").strip()
        score_text = (r.get("score") or "").strip()
        if not date_text and not food_text and not score_text:
            continue
        day = datetime.date.fromisoformat(date_text)
        logged = bool(food_text)
        foods = set()
        for part in food_text.split(";"):
            item = norm_item(part)
            if item and item != "-":
                foods.add(item)
        score = None
        if score_text:
            score = float(score_text)
            if not math.isfinite(score):
                raise ValueError("score is not a finite number on " + date_text)
        if day in by_day:
            was_logged, prev_foods, prev_score = by_day[day]
            if score is not None and prev_score is not None:
                score = max(score, prev_score)
            elif score is None:
                score = prev_score
            by_day[day] = (was_logged or logged, prev_foods | foods, score)
        else:
            by_day[day] = (logged, foods, score)
    if not by_day:
        raise ValueError("the diary has no dated rows")
    start = min(by_day)
    end = max(by_day)
    n = (end - start).days + 1
    foods_out = []
    scores_out = []
    for i in range(n):
        day = start + datetime.timedelta(days=i)
        if day in by_day:
            logged, foods, score = by_day[day]
            foods_out.append(frozenset(foods) if logged else None)
            scores_out.append(score)
        else:
            foods_out.append(None)
            scores_out.append(None)
    return Diary(start, foods_out, scores_out)


def parse_text(text):
    return parse_rows(csv.DictReader(io.StringIO(text)))


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return parse_rows(csv.DictReader(fh))
