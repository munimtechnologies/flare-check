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

> **Status (14 November 2026): every flag is marked "possible pattern (unverified)".**
> The first pre-registered calibration study found that version 0.1.0 raised false alarms in 19% of
> no-effect diaries in one setting, against a 10% target
> ([results](findings/calibration-results-v1-2026-11-14.md)). Version 0.2.0 changes the method; a
> second pre-registered study ([v2](findings/calibration-prereg-v2-2026-11-14.md)) will show whether
> the change works. Until it passes, do not read a flag as a calibrated result.

## Why another diary checker

A typical app compares average symptoms on days after each food with other days. Two things make
that unreliable for one person's diary:

1. **Many foods, many comparisons.** Track 20 foods at two lags and you run 40 comparisons; some will
   look striking by chance.
2. **Runs.** Symptoms come in runs of good and bad days, and people eat the same things for stretches.
   When both happen, ordinary tests treat 30 correlated days as 30 independent facts.

The first study measured both on synthetic diaries. With 20 foods, uncorrected t-tests pointed at
some food in 82-100% of diaries in which no food did anything. A standard correction for many tests
fixed that only when days were independent: when eating and symptoms both came in runs, the
corrected t-test still pointed at something in 56-74% of no-effect diaries.

flare-check rotates the food series against the symptom series (a circular-shift permutation test,
which keeps both kinds of runs intact) and corrects for the number of foods and lags tested:

- `--method maxt` (default from 0.2.0): all foods and lags are rotated together, and each food's
  |t| is compared with the largest |t| at every rotation. This controls the chance of any false
  alarm, and its smallest possible p-value (1 / days logged) does not depend on how many foods you
  test.
- `--method bh`: one rotation p-value per food and lag, then Benjamini-Hochberg q-values.

Both use every rotation. Version 0.1.0 skipped the rotations nearest the real one, which the first
study showed to be unsafe. You can also **name 1-3 suspect foods in advance** (`--suspects`), which
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
python -m flarecheck.check my-diary.csv --method bh
```

Each food and lag gets: days after eating, other days, mean difference in score, p, adjusted p, and
a status: `possible pattern (unverified)` (adjusted p <= 0.10), `no clear pattern`, `too few days`
(fewer than 5 days in either group), or `not in diary`.

## What has and has not been checked (14 November 2026)

- Unit tests (hand-checked cases for every statistic, the diary reader and the report) run before
  every commit.
- **Calibration study v1 (version 0.1.0): ran, 6 of 7 predictions passed, the key one failed.**
  [Results](findings/calibration-results-v1-2026-11-14.md), graded exactly as
  [pre-registered](findings/calibration-prereg-v1-2026-11-13.md): false alarms up to 19% (limit
  12%); testing all 20 foods found a real effect in 0% of 30-90-day diaries; naming 3 suspects found
  it in 93% of 90-day diaries.
- **Calibration study v2 (version 0.2.0): pre-registered, not yet run.**
  [Pre-registration](findings/calibration-prereg-v2-2026-11-14.md), seven predictions, including
  that the old method fails again on new diaries and that both new methods keep false alarms at or
  below 13% in all 20 no-effect settings.
- Not tested with real people or real diaries. Not a medical device.

## Run the calibration study yourself

```
python -m unittest discover -v
python -m flarecheck.sim --k 500 --seed 20261114 --out-dir out
```

Version 1 of the study is reproducible from release v0.1.0
(`python -m flarecheck.sim --k 200 --seed 20261113 --out-dir out`).
