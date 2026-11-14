# Calibration study v1: results (graded 2026-11-14)

Written by AI agents (Claude) working in MV2's name (Munim, Inc.) on 14 November 2026. Licence of
this text: CC BY 4.0. Pre-registration (frozen before the run, release v0.1.0):
[`calibration-prereg-v1-2026-11-13.md`](calibration-prereg-v1-2026-11-13.md).

**Headline: one of the seven predictions failed, and it is the one that matters most.** In one
setting flarecheck 0.1.0 raised a false alarm in 19% of synthetic diaries in which no food had any
effect, against a pre-registered limit of 12% (its target was 10%). As the pre-registration
required, flare-check 0.1.0's "possible pattern" label must not be trusted. Version 0.2.0 changes the
method and marks every flag "unverified" until a second pre-registered study has run.

## How it ran

- Code: flarecheck 0.1.0 exactly as released (tag v0.1.0), Python 3.12 standard library, in a
  sealed container with no network on MV2's compute queue (job `flarecheck-cal-v1`, 13-14 November
  2026, 371 seconds). All 26 unit tests passed first.
- `python -m flarecheck.sim --k 200 --seed 20261113`: 24 settings x 200 synthetic diaries. No real
  person's data.
- Grades were computed by `grade()` in `flarecheck/sim.py` of v0.1.0 and are copied here verbatim.

## Grades (verbatim)

`P1 PASS (0.835); P2 FAIL (0.19); P3 PASS (0.715); P4 PASS (0.0); P5 PASS (0.93); P6 PASS (0.03); P7 PASS (0.68)`

| # | Prediction | Result |
|---|---|---|
| P1 | uncorrected t-tests over 20 foods (60 days) flag something in >= 75% of no-effect diaries | PASS, 83.5% |
| P2 | flarecheck's false-alarm rate <= 12% in every one of the 16 no-effect settings | **FAIL, worst 19%** |
| P3 | Benjamini-Hochberg-corrected t-tests flag something in >= 30% of no-effect diaries when eating and symptoms both come in runs (90 days) | PASS, 71.5% |
| P4 | testing all 20 foods, flarecheck finds a real 1 SD next-day effect in <= 5% of 60-day diaries | PASS, 0% |
| P5 | with 3 suspects named in advance, flarecheck finds it in >= 50% of 90-day diaries | PASS, 93% |
| P6 | ... and in <= 5% of 30-day diaries | PASS, 3% |
| P7 | corrected t-tests find it in >= 50% of 60-day diaries (all foods) | PASS, 68% |

## Full table

"any" = share of diaries with at least one flag; "power" = share of effect diaries in which the
real food (food01) was flagged. `shift_bh` is flarecheck 0.1.0.

| setting | mean tests | naive any | t_bh any | shift_bh any | naive power | t_bh power | shift_bh power |
|---|---|---|---|---|---|---|---|
| null-all-n30-phi0.0-habit0.0 | 36.97 | 0.845 | 0.1 | 0.0 | - | - | - |
| null-all-n60-phi0.0-habit0.0 | 39.95 | 0.87 | 0.125 | 0.0 | - | - | - |
| null-all-n90-phi0.0-habit0.0 | 39.99 | 0.865 | 0.085 | 0.0 | - | - | - |
| null-all-n180-phi0.0-habit0.0 | 40.0 | 0.865 | 0.115 | 0.0 | - | - | - |
| null-all-n30-phi0.6-habit0.0 | 36.83 | 0.82 | 0.135 | 0.0 | - | - | - |
| null-all-n60-phi0.6-habit0.0 | 39.91 | 0.835 | 0.1 | 0.0 | - | - | - |
| null-all-n90-phi0.6-habit0.0 | 40.0 | 0.85 | 0.135 | 0.005 | - | - | - |
| null-all-n180-phi0.6-habit0.0 | 40.0 | 0.825 | 0.1 | 0.005 | - | - | - |
| null-all-n30-phi0.6-habit0.6 | 32.7 | 0.965 | 0.56 | 0.0 | - | - | - |
| null-all-n60-phi0.6-habit0.6 | 38.84 | 0.99 | 0.705 | 0.005 | - | - | - |
| null-all-n90-phi0.6-habit0.6 | 39.72 | 1.0 | 0.715 | 0.0 | - | - | - |
| null-all-n180-phi0.6-habit0.6 | 40.0 | 1.0 | 0.735 | 0.015 | - | - | - |
| null-suspects-n30-phi0.6-habit0.6 | 4.95 | 0.495 | 0.385 | 0.025 | - | - | - |
| null-suspects-n60-phi0.6-habit0.6 | 5.77 | 0.49 | 0.335 | 0.045 | - | - | - |
| **null-suspects-n90-phi0.6-habit0.6** | 5.95 | 0.595 | 0.46 | **0.19** | - | - | - |
| null-suspects-n180-phi0.6-habit0.6 | 6.0 | 0.575 | 0.395 | 0.085 | - | - | - |
| power-all-n30-phi0.6-habit0.0 | 37.33 | 0.92 | 0.355 | 0.0 | 0.645 | 0.295 | 0.0 |
| power-all-n60-phi0.6-habit0.0 | 39.87 | 0.985 | 0.68 | 0.0 | 0.94 | 0.68 | 0.0 |
| power-all-n90-phi0.6-habit0.0 | 39.99 | 1.0 | 0.885 | 0.0 | 0.985 | 0.88 | 0.0 |
| power-all-n180-phi0.6-habit0.0 | 40.0 | 1.0 | 1.0 | 0.035 | 1.0 | 1.0 | 0.035 |
| power-suspects-n30-phi0.6-habit0.0 | 5.54 | 0.725 | 0.53 | 0.03 | 0.635 | 0.5 | 0.03 |
| power-suspects-n60-phi0.6-habit0.0 | 6.0 | 0.945 | 0.835 | 0.04 | 0.93 | 0.82 | 0.04 |
| power-suspects-n90-phi0.6-habit0.0 | 6.0 | 0.98 | 0.96 | 0.93 | 0.975 | 0.96 | 0.93 |
| power-suspects-n180-phi0.6-habit0.0 | 6.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

With 200 diaries per setting, a rate near 10% has a standard error of about 2 percentage points,
so 19% is well above the 10% target and not plausibly chance.

## What the results say

1. **Simple per-food checks raise false alarms most of the time (P1, P3).** With 20 foods and two
   lags, uncorrected t-tests flagged at least one food in 82-100% of diaries in which no food did
   anything. Correcting for the number of tests (Benjamini-Hochberg) fixed that only when days were
   independent; when eating and symptoms both came in runs, the corrected t-test still flagged
   something in 56-74% of no-effect diaries. That is the problem flare-check was built to solve, and
   it is confirmed.
2. **flarecheck 0.1.0 did not fully solve it (P2 failed).** With three suspects named in advance and
   90 days, it flagged a food in 19% of no-effect diaries.
3. **Testing every food made flarecheck 0.1.0 almost blind (P4, and the power-all rows).** Its
   smallest possible p-value is about 1/n, so 40 Benjamini-Hochberg-corrected tests could not reach
   the alert level before about 400 days. A real effect was found in 0% of 30-90-day diaries and
   3.5% at 180 days. Naming suspects in advance worked (P5: 93% at 90 days).

## Why P2 failed (diagnosis, to be tested)

This is a hypothesis written after seeing the result, not a finding. flarecheck 0.1.0 compared the
observed food series with its rotations by 3 to n-3 days and skipped rotations of 1 and 2 days (and
n-1, n-2), to avoid comparing a day with its neighbours. A rotation test is exact only when the
observed series competes against **every** rotation: then, if no food matters, the observed
statistic is equally likely to rank anywhere among them. When eating habits and symptoms both run
in stretches, the statistic changes smoothly from one rotation to the next, so a chance peak spans
several neighbouring rotations. Skipping the near neighbours means the rotations just beside the
top of such a peak are never compared with it, so two or three rotations around one chance peak can
each look like "beats everything it is compared with". That makes the smallest p-values about two to
three times too common, which matches 19% where about 7-10% is expected.

## What changes

- **flare-check 0.2.0** uses every rotation (min_shift=1) and adds a joint max-|t| rotation test
  (all foods and lags rotated together; each food's |t| is compared with the largest |t| of every
  rotation). Its smallest possible adjusted p is 1/n however many foods are tested, which should
  also fix the blindness in point 3. It is the new default.
- Until a second study passes, every flag reads **"possible pattern (unverified)"**.
- The second study is pre-registered in
  [`calibration-prereg-v2-2026-11-14.md`](calibration-prereg-v2-2026-11-14.md), with predictions
  that test this diagnosis (the old method should fail again on new diaries; the new methods should
  not).

## Limits

Synthetic diaries only: real diaries have weekly cycles, missing days, effects that last more than a
day, foods eaten together, and scores on short integer scales. One effect size (1 SD) and one lag
(1 day). Results describe these methods, not anyone's diet. Not medical advice. Rotation tests
are standard statistics (circular-shift or "toroidal" tests); what is new here is only a published,
pre-registered measurement of how they behave in a diet-diary tool, including the failure.
