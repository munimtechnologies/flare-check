# Pre-registration v2: does using every rotation fix flare-check's false alarms? (2026-11-14)

Written by AI agents (Claude) working in MV2's name (Munim, Inc.) on 14 November 2026, after the
version 1 results ([`calibration-results-v1-2026-11-14.md`](calibration-results-v1-2026-11-14.md))
and before any version 2 simulation was run. Code: flarecheck 0.2.0 (`flarecheck/sim.py`), seed
`20261114` (new diaries, not the version 1 ones), 500 synthetic diaries per setting. No real
person's data. Licence of this text: CC BY 4.0. Version 1 stays frozen; this is a dated addendum.

## Question

Version 1 found that flarecheck 0.1.0 raised false alarms in 19% of no-effect diaries in one setting
(target 10%). The diagnosis offered there: skipping the rotations nearest the observed one breaks the
rotation test's exactness when the statistic is smooth across rotations. If that is right, (a) the
old method fails again on new diaries, worse when eating is more habitual, and (b) the same test using
every rotation, and a joint max-|t| rotation test, keep false alarms near or below 10%.

## Design (changes from version 1 in bold)

- Synthetic diaries exactly as in version 1 (20 foods, eating probability 0.15-0.60, optional
  Markov "habit", AR(1) symptoms with correlation phi, food01 raising the next day's score by 1 SD
  in "power" diaries; lags 0 and 1; a test runs only with >= 5 days in each group).
- **Seed 20261114 and 500 diaries per setting** (version 1: 20261113, 200).
- **28 settings**: the 24 of version 1 plus **null-suspects at phi 0.6, habit 0.8, n = 30, 60, 90,
  180** (20 no-effect settings in all).
- Methods, on the same diaries:
  - `naive`, `t_bh`: as in version 1.
  - `shift_bh_ms3`: flarecheck 0.1.0 (rotations 3..n-3, Benjamini-Hochberg q <= 0.10).
  - **`shift_bh`: every rotation 1..n-1, Benjamini-Hochberg q <= 0.10** (flare-check 0.2.0 `--method bh`).
  - **`maxt`: all tests rotated together by every s = 1..n-1; each test's |Welch t| is compared with
    the largest |t| over all tests at each rotation; flag if adjusted p <= 0.10** (flare-check 0.2.0
    default).

## Predictions (graded automatically by `grade()` in sim.py, exactly as written here)

- **R1** null-suspects-n90-phi0.6-habit0.6: `shift_bh_ms3` any >= 0.12 (the old method fails again
  on new diaries).
- **R2** every one of the 20 no-effect settings: `shift_bh` any <= 0.13.
- **R3** every one of the 20 no-effect settings: `maxt` any <= 0.13.
- **R4** power-all-n90-phi0.6-habit0.0: `maxt` power >= 0.50 (testing all 20 foods is no longer
  blind at 90 days; version 1's method had 0%).
- **R5** power-suspects-n60-phi0.6-habit0.0: `maxt` power >= 0.50.
- **R6** null-suspects-n90-phi0.6-habit0.8: `shift_bh_ms3` any >= 0.12 (the old failure also
  appears with stronger eating habits).
- **R7** power-suspects-n90-phi0.6-habit0.0: `shift_bh` power >= 0.50 (using every rotation does
  not destroy the power of naming suspects; version 1's method had 93%).

The limit 0.13 (not 0.12) allows for chance: with 500 diaries a true 10% rate has a standard error of
1.3 percentage points.

## What would change the plan

- R2 and R3 pass: flare-check drops "(unverified)" from its flags for the method(s) that passed, and
  a SKILL.md may point at it. R4 and R5 decide which method stays the default.
- R3 fails but R2 passes: the default becomes `bh`; `maxt` stays experimental.
- R2 and R3 both fail: the diagnosis is wrong or incomplete; flags stay "unverified" and a third
  study is needed before any public claim of error control.
- R1 or R6 fails: the version 1 failure did not repeat on new diaries, so the diagnosis is not
  supported, whatever R2/R3 show; this will be said plainly.

## Limits stated in advance

Synthetic data only (see version 1). The exactness argument for rotation tests assumes a diary whose
statistics do not change when it is rotated; real diaries have trends and a seam where the end
wraps to the start. One effect size and one lag. Not medical advice.
