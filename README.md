# flare-check

An open, offline checker for a personal food and symptom diary. It asks one careful question:
**does any food line up with worse symptoms more than chance would explain?** It is built for
people tracking diet with autoimmune or gut conditions and for researchers building diet-tracking
tools. Python standard library only; no account, no server, no data leaves your computer.

**Not medical advice.** flare-check is an information tool. It does not diagnose, and its output is
not a recommendation to eat or avoid anything. Talk to your clinician or a registered dietitian
before changing your diet; cutting out foods can cause harm of its own.

Made by AI agents (Claude) working in the name of MV2 of Munim, Inc. (mv2@munimtech.com).
Code: Apache-2.0. Text and findings: CC BY 4.0. Not affiliated with or endorsed by NIH or any
other agency.

## Why another diary checker

A typical app compares average symptoms on days after each food with other days. Two things make
that unreliable for one person's diary:

1. **Many foods, many comparisons.** Track 20 foods at two lags and you run 40 comparisons; some will
   look striking by chance.
2. **Runs.** Symptoms come in runs of good and bad days, and people eat the same things for stretches.
   When both happen, ordinary tests treat 30 correlated days as 30 independent facts.

flare-check handles both: it rotates the food series against the symptom series (a circular-shift
permutation test, which keeps both runs intact) and corrects for the number of foods and lags tested
(Benjamini-Hochberg). It also tells you how many logged days your diary would need before any
single food could reach its alert level, and it lets you **name 1-3 suspect foods in advance**, which
needs far fewer days than testing everything.

## Use

Diary CSV (see `examples/diary-example.csv`, which is invented):

```
date,foods,score
2026-01-01,oats;milk;coffee,3
2026-01-02,-,2
```

`foods` lists what you ate that day, separated by `;` (`-` = none of your tracked foods; blank = not
logged). `score` is your symptom score on any scale (blank = not logged).

```
python -m flarecheck.check my-diary.csv
python -m flarecheck.check my-diary.csv --suspects "milk;wheat" --json result.json
```

Each food and lag gets: days after eating, other days, mean difference in score, p, q, and a status:
`possible pattern` (q <= 0.10), `no clear pattern`, `too few days` (fewer than 5 days in either group),
or `not in diary`.

## What has and has not been checked (13 November 2026)

- Unit tests (hand-checked cases for every statistic, the diary reader and the report) run before
  every commit.
- **Not yet run:** the pre-registered calibration study in
  [`findings/calibration-prereg-v1-2026-11-13.md`](findings/calibration-prereg-v1-2026-11-13.md),
  which measures on synthetic diaries how often flare-check and two simpler methods raise false
  alarms, and how many days each needs to find a real effect. Its results will be added as a dated
  note, graded exactly as pre-registered, pass or fail.
- Not tested with real people or real diaries. Not a medical device.

## Run the calibration study yourself

```
python -m unittest discover -v
python -m flarecheck.sim --k 200 --seed 20261113 --out-dir out
```
