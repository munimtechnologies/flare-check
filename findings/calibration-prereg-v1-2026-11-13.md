# Pre-registration: how often do food-diary pattern checks raise false alarms? (v1, 2026-11-13)

Written by AI agents (Claude) working in MV2's name (Munim, Inc.) on 13 November 2026, before any
simulation was run. Code: flarecheck 0.1.0 (`flarecheck/sim.py`), seed `20261113`, 200 synthetic
diaries per setting. No real person's data is used. Licence of this text: CC BY 4.0.

## Question

Diet-tracking apps for autoimmune and gut conditions often show "your symptoms are worse after
food X". When a person logs 20 foods for a few weeks, how often does a simple per-food comparison
point at a food by chance, and how many logged days does a stricter check need before it can point
at a food that really matters?

## Design

- Each synthetic diary has 20 foods. Food k is eaten on a given day with probability p_k, drawn
  from 0.15-0.60 for each diary. With `habit` > 0, eating follows a two-state Markov chain whose
  day-to-day correlation is `habit` (stretches of eating the same thing).
- Symptom score = 4 + a_t, where a_t is AR(1) with correlation `phi` and variance 1 (bad days come in
  runs). In "power" settings, food01 raises the NEXT day's score by `delta` = 1.0 SD.
- Tests: every tested food at lag 0 (same day) and lag 1 (next day). A test runs only if at least 5
  days fall in each group. "all" mode tests all 20 foods (up to 40 tests); "suspects" mode tests 3
  foods named in advance (food01-food03; up to 6 tests).
- Methods, on the same diaries:
  - `naive`: Welch t-test per test, flag if p < 0.05, no correction for the number of tests.
  - `t_bh`: the same t-tests, Benjamini-Hochberg q <= 0.10.
  - `shift_bh`: flarecheck's circular-shift p-value (the food series is rotated against the score
    series by 3 to n-3 days, which keeps both series' runs), Benjamini-Hochberg q <= 0.10.
- Settings (24): null diaries (delta 0) with (phi, habit) = (0, 0), (0.6, 0), (0.6, 0.6) in "all"
  mode and (0.6, 0.6) in "suspects" mode, each at n = 30, 60, 90, 180 days; power diaries
  (phi 0.6, habit 0, delta 1.0) in "all" and "suspects" mode at n = 30, 60, 90, 180.
- Measures: `any` = share of diaries with at least one flagged test; `power` = share of power diaries
  in which a test of food01 (either lag) is flagged; `false` = share with a flag on any other food.

## Predictions (graded automatically by `grade()` in sim.py, exactly as written here)

- **P1** null-all-n60-phi0.6-habit0.0: `naive` any >= 0.75 (uncorrected checks over many foods
  usually point at something).
- **P2** every one of the 16 null settings: `shift_bh` any <= 0.12 (flarecheck keeps false alarms near
  its 10% level).
- **P3** null-all-n90-phi0.6-habit0.6: `t_bh` any >= 0.30 (when both eating and symptoms come in runs,
  even a corrected t-test raises too many false alarms).
- **P4** power-all-n60-phi0.6-habit0.0: `shift_bh` power <= 0.05 (testing every food, 60 days are too
  few for the strict check to single out a real effect).
- **P5** power-suspects-n90-phi0.6-habit0.0: `shift_bh` power >= 0.50 (naming 3 suspects in advance,
  90 days usually suffice for a 1 SD next-day effect).
- **P6** power-suspects-n30-phi0.6-habit0.0: `shift_bh` power <= 0.05 (30 days are too few even then).
- **P7** power-all-n60-phi0.6-habit0.0: `t_bh` power >= 0.50 (the t-test is not powerless; the price of
  the strict check is resolution, which P4 measures).

## What would change the plan

- P2 fails: flarecheck's alert level is not trustworthy; the tool must not say "possible pattern" until
  it is fixed.
- P3 fails: in these settings the corrected t-test is acceptable, and the README must not claim that
  runs of eating and symptoms break it.
- P5 fails: the "name your suspects in advance" advice in the README needs a longer diary length.

## Limits stated in advance

Synthetic data only: real diaries have weekly cycles, missing days, delayed effects beyond one day,
foods eaten together, and scores on short integer scales. One effect size (1 SD) and one effect lag
(1 day) are studied. Results describe these methods, not any person's diet, and are not medical advice.
