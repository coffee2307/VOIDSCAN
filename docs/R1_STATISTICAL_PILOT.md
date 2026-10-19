# VOIDSCAN — Phase R1: Statistical Baseline Pilot

## Status (19 October 2026)
**R1 engineering baseline: implemented for experimental use. R1 real-world validation: NOT PASSED.**
The refreshed Meta token was checked against the user's authorized Pages (read-only): two Pages were accessible. The first uploaded photo tested on each Page returned LIKE, LOVE, WOW, HAHA, SAD, and ANGRY aggregate counts successfully via PageID_PhotoID. A complete `collect_once()` path for a verified Photo ID also returned all six reaction counts. This is a connectivity check, not evidence of bot-identification accuracy.

The local historical research database still contained only **one saved snapshot, one object, and zero active watches** when the pilot began. Do not backfill timestamps or fabricate a distribution for past contests.

## Candidate detection algorithms

Module: research_baselines.py; it operates on the same aggregate snapshots as the existing report. All methods are deterministic and compare each interval **only with earlier intervals**. They work separately for each reaction type and photo object.

1. **robust_mad:** rolling median reaction/minute; conservative threshold using median absolute deviation, >= 4× median, and >= 4 reactions/minute.
2. **rolling_p95:** threshold >= 3× the interpolated 95th-percentile rate from historical observations and >= 4/minute.
3. **mean_5sigma:** threshold >= mean + 5 population standard deviations, >= 4× mean, and >= 4/minute.

Each method also requires at least **20 net new reactions** in the tested interval and **five earlier valid intervals** in the current uninterrupted segment. Previous rates are not carried through missing/invalid readings, negative corrections, non-monotone timestamps, or gaps longer than 15 minutes for the 10-minute polling cadence.

These are **three correlated heuristics**, not an ensemble validated as a fraud classifier. Three methods agreeing is not an independent corroboration or a probability. Every model can mistakenly flag legitimate virality.

Reported numbers:
- flagged_growth = aggregate reaction increase measured in a flagged window; not a verified count of illegitimate likes.
- excess_above_reference = observed increase minus a median-based reference, floored to zero; not an estimate of bots.
- multi_method_agreement_intervals = count of periods where >= 2 candidates flagged; not model certainty.
- bot_probability_pct = null; automatic_deduction = 0.

## How to test and reproduce locally

Run the complete unit and isolated HTTP suite with no token needed:

    cd F:\VOIDSCAN
    python -m unittest discover -s tests -v
    python tests\smoke_http.py

View data readiness without exporting any Page/photo IDs:

    python research_cli.py audit

The browser has a collapsed report section **R1 · Đối chiếu ba phương pháp thống kê (thử nghiệm)**. The main scan output stays easy to understand: it shows only statistics supported by actual observations, never fake-account certainty.

## Obtain real time-series data — pilot step requiring owner selection

1. Open http://127.0.0.1:3000 and choose an authorized Facebook Page.
2. Choose the exact photo from "Chọn ảnh đã đăng", or the particular child photo in a multi-photo post. Do **not** select the parent post to score an attached photo.
3. Scan. Verify that the reaction type is available; Meta can change individual fields.
4. Click **Bật theo dõi định kỳ** on THAT photo. The existing monitor records a new snapshot approximately every 10 minutes while the VOIDSCAN server is running, subject to Meta permissions and rate limits.
5. Observe for multiple sessions. Data loss or server shutdown results in invalid gaps; do not interpolate counts.
6. Repeat for multiple authorized contest photos, with clearly documented valid sharing campaigns, posting times, prizes, boosted ads (where known) and voting windows.

No Page/photo was automatically selected as a monitored contest entry by Phase R1. Users must choose the specific Page/object and enable watch in the UI. Observe Meta API rate limits and data minimization obligations.

## Next research milestone — R1.5

The local interface now accepts time-bounded operator context for each photo, and the offline replay tool recomputes four frozen event-level flags from independently reviewed aggregate series rather than trusting a manually-entered prediction. See [R1.5 methodology](R1_FALSE_POSITIVE_REPLAY.md). This does not validate bot accounts or suppress statistical warnings.

## Validation protocol for real events

R1 unit tests and simulated spikes test code behavior only. **They cannot estimate true precision, recall, or false-positive rate on Facebook.**

Before any production claim:
- Collect uninterrupted time series across several campaigns and diverse cases, including public promotions and legitimate viral spikes.
- Freeze thresholds before evaluation and withhold entire later contests for independent testing.
- Have an independent reviewer establish case-level ground truth using evidence beyond VOIDSCAN's own anomaly flag.
- Evaluate precision, recall, false-positive rate, and confidence intervals with research_validation.py; record label provenance, class balance, temporal holdout, and false-positive case studies.
- Only consider calibration when a real probabilistic model and adequate independent labels exist. No individual fake-account labels can be derived from Meta aggregate reactions alone.

Read docs/R0_RESEARCH_PROTOCOL.md for the data/label contract.

## Limitations / safety

A legitimate influencer shares a contest photo; hundreds of real voters react at once. A purchased-reaction service creates the same aggregate time series. **All three models produce identical scores for identical input time series.** Context must be examined before drawing conclusions.

Do not automatically remove votes, accuse a person, publish named suspicious accounts, or claim 90%+ confidence from heuristic agreement. This prototype does not determine the number of Facebook bots.
