# VOIDSCAN — Research and evidence review (19 October 2026)

VOIDSCAN detects observable engagement anomalies, not the true identity or automation status of every Facebook account.

## Definitions

- Fake or Sybil account: an identity intentionally constructed to deceive a network or its users, potentially run by a person or software.
- Social bot: an automated agent; it may be authorized, benign or malicious.
- Coordinated activity: multiple entities act with statistical dependence; coordination by itself can be legitimate.
- Coordinated inauthentic behavior: deception plus coordination, not merely coincident timestamps.
- Anomaly: an observation worthy of review. This is the proper label for unverified evidence.

## Research reviewed

1. Yang et al. (2025), "Coordinated link sharing on Facebook", Scientific Reports, DOI: https://doi.org/10.1038/s41598-025-00233-w . Research corpus: around 11.24 million URL posts by 16,169 Facebook Pages in Jan-Apr 2021. Mixture distributions identified rapid and frequent co-sharing in the studied corpus. Its thresholds around 27 seconds and nine shared URLs MUST NOT be reused universally. Manual validation found legitimate common-ownership Page coordination too.
2. Graham, Hames & Alpert (2024), "The coordination network toolkit", Journal of Computational Social Science. DOI: https://doi.org/10.1007/s42001-024-00260-z . Directed weighted multigraphs with sliding windows avoid false-positive links when an account is the victim of coordinated abuse. Validation is primarily Twitter-oriented. MIT software: https://github.com/QUT-Digital-Observatory/coordination-network-toolkit .
3. Giglietto, Righetti, Rossi & Marino (2020), "Coordinated Link Sharing Behavior as a Signal to Surface Sources of Problematic Information on Facebook". DOI: https://doi.org/10.1145/3400806.3400817 . Research on repeated rapid co-sharing by Facebook Pages and groups. CooRnet https://github.com/fabiogiglietto/CooRnet (MIT) was archived September 2024 after CrowdTangle shut down.
4. Cresci et al. (2017), "Social Fingerprinting: detection of spambot groups through DNA-inspired behavioral modeling". IEEE TDSC. DOI: https://doi.org/10.1109/TDSC.2017.2681672 . Behavioral sequence resemblance can reveal networks, but empirical focus is not contemporary Facebook and does not provide confirmed identity on a per-post basis.
5. Wang et al. (2012), "Social Turing Tests: Crowdsourcing Sybil Detection". https://arxiv.org/abs/1205.3856 . Historically valuable Facebook and Renren human-review study, but not directly representative of Facebook in 2026. Ground truth based partly on account disappearance and human review is imperfect.
6. Smith, Ehrett & Warren (2025), "Unsupervised detection of coordinated information operations in the wild", EPJ Data Science. DOI: https://doi.org/10.1140/epjds/s13688-025-00544-y . Bayesian unsupervised coordination detection, mainly validated on Twitter datasets.
7. Liu et al. (2024), systematic review of ML for deceptive social activity (36 studies), https://arxiv.org/abs/2410.20293 . Reports selection bias, class imbalance and inaccurate reliance on raw accuracy as evaluation.
8. Meta explanation of internal fake-account signals: https://about.fb.com/news/2019/05/fake-accounts/ . Meta uses internal signals about signup, use and suspicious networks unavailable to unaffiliated outside analysis.

## Constraints of data acquisition

- Facebook Page and Post Graph API endpoints require appropriate Page tasks, token type, app permissions, and sometimes Page Public Content Access. A URL is not authorization to obtain personal profiles, reactors or private shares.
- CrowdTangle stopped on 14 August 2024. Do not build a production service depending on it.
- Meta Content Library/API is intended for eligible approved research institutions through ICPSR and does not offer open general-purpose access to all reactions: https://about.fb.com/news/2023/11/new-tools-to-support-independent-research/
- Unofficial public scrapers are not proof of completeness and may have operational or platform-policy restrictions.

## Implementation stages

### Current baseline: implemented and tested
- Clean bootstrap with no historical CSV datasets.
- Local post URL scan via permissioned Graph API comments where supported, with honest unavailability mode.
- Optional new CSV import for authorized datasets; no automatic dependence on historical files.
- Detect repeated identical comment messages and report busiest 60-second window as descriptive context.
- Scan jobs persisted in SQLite with evidence and provenance summaries, not raw profile names or comment content. 90-day rolling retention.
- No fake-account probability, confirmation label or autonomous sanctions.

### Next: permissions and reliable collection
- Provider contract and permission diagnostics for the Page owner, link-to-Post-ID resolution and retry policy with explicit Graph API errors.
- Support reproducible test fixtures and full/partial pagination and sampling indicators.
- Privacy policy and account-scoped data rights before any deployment beyond localhost.

### Future: calibrated coordination engine
- Multiple posts and consenting/authorized actor-level data, time sequences, normalized content, independent provenance.
- Directed weighted multigraphs, adaptive thresholds, simulated null models, manual adjudication.
- Independent verified labels, temporal holdout, per-account splits, precision, recall, false-positive rates, PR-AUC, and calibration assessment.
- Auditability, review, appeals, and fail-closed response on insufficient evidence.

## Strong warning

Sharing similar comments, rapidly sharing a link, identical profile names or having no public posts cannot by itself establish a fake account. Evidence for coordinated behavior does not establish malicious intent; popular Page administrators may legitimately coordinate messages. No percentage authenticity score should be displayed without independent training labels and out-of-sample validation.
