# VOIDSCAN 3.0 — Guided Reaction Integrity Research Preview

**Chrome extension v0.1.0 (new, no page-admin permission):** Load unpacked folder `F:\VOIDSCAN\chrome-extension` in the existing logged-in Chrome to collect URLs shown in an opened Facebook photo reaction dialog, grouped by Photo ID and reaction type, and export CSV/JSON compatible with Excel. Supports explicit bounded scrolling, deduplication per photo, and visible album photo links. It does not touch tokens/cookies, query hidden Facebook APIs, infer bots, or assert full coverage. Read [Extension README](chrome-extension/README.md).

**Chrome + Playwright on Windows (opt-in):** Run `setup-voidscan-facebook.bat` to open a dedicated Chrome window where you manually sign in to Facebook. This setup uses an isolated profile in `%LOCALAPPDATA%`, not your personal Chrome profile, and does not export cookies, passwords or MFA codes. The browser is opened, not a completed 38-photo scan or validated bot detector. Read [Facebook Chrome setup](docs/FACEBOOK_BROWSER_SETUP.md).

**Live monitoring cadence fix:** the running server now checks for due active watches approximately every 30 seconds, but calls Meta at most once per configured 10-minute interval per watched object, taking recent manual scans into account. Restarting VOIDSCAN does not reset the next-due timer. This does not run while the server is closed, and does not imply account-level bot identification. See [Monitoring Readiness](docs/R1_MONITOR_READINESS.md).

**Phase R2 human-ground-truth intake (research-only):** two blinded, independently pseudonymized reviewers must agree on event labels, or a separate third reviewer resolves disagreements before replay. No raw account identities or model predictions are accepted in the labeled dataset. Command: `python research_cli.py adjudicate --input ... --output ...`. See [R2 Ground Truth Review](docs/R2_GROUND_TRUTH_REVIEW.md). Self-attested independence and evidence are NOT authenticated by software, and this is NOT a validated bot model.

**Phase R2 data preparation (experimental):** export a privacy-reduced bundle of locally stored aggregate reaction histories from the History tab. Raw Facebook Page/photo IDs, URLs, token and names are excluded; identifiers are randomized per export. Integrity SHA-256 detects file modification, not authenticity. Optional commands: `python research_cli.py bundle --output ...` and `python research_cli.py verify-bundle --input ...`. See [R2 Research Bundle](docs/R2_RESEARCH_BUNDLE.md). This is NOT validated fraud classification.

**Phase R1.6 — Monitoring readiness dashboard:** the History tab now shows active watches, saved snapshots, enough-history objects and monitor failures. Errors retain safe Meta failure categories (expired, permission, rate-limit, network) instead of one generic error. Diagnostics are read-only and require no valid token: `python research_cli.py readiness`. See [Monitoring Readiness](docs/R1_MONITOR_READINESS.md). No fake-bot accuracy or automatic sanctions are claimed.

**Phase R1.5 — False-positive review and independent event replay:** each photo report can now record time-bounded promotion/sharing/advertising context without suppressing alerts. Researchers can recompute frozen R1 event flags from independently reviewed aggregate histories via `python research_cli.py replay --input ...`; no synthetic or user-asserted label becomes proven bot certainty. See [R1.5 False-positive Review](docs/R1_FALSE_POSITIVE_REPLAY.md).

**Phase R1 statistical pilot now included:** three transparent historical-only candidate baselines (median/MAD, 95th percentile, mean/standard deviation) compare growth in authorized Page photo reactions. A collapsed UI panel explains model agreement without treating it as bot probability. No real-world fraud precision has been established; select an authorized photo and enable watch before collecting a time series. Read [R1 Statistical Pilot](docs/R1_STATISTICAL_PILOT.md).

**Research Phase R0 now included:** reproducible quality checks for timestamped aggregate reactions, no interpolation over missed snapshots, and offline held-out event evaluation with independent labels (no fake-account probability or automatic deductions). Run `python research_cli.py audit`. Read [R0 research protocol](docs/R0_RESEARCH_PROTOCOL.md) and [R0 baseline](docs/R0_BASELINE_2026-10-19.md). Live Meta API validation still requires a valid token; a successful unit test does not prove bot-detection accuracy.

**Facebook engagement intelligence, not a fake-account oracle.**

VOIDSCAN is a local-first open-source research preview. It accepts a Facebook post link, identifies what evidence can be accessed through permissioned Meta APIs or user-supplied fresh exports, surfaces explainable patterns, and records limited scan metadata in a private SQLite database. It never invents interaction counts or asserts that a specific account is fake.

## Current status

- Clean baseline. No historic CSV records are shipped, automatically loaded, or referenced by the application.
- One-click URL Scan with source and access disclosures.
- Managed Page discovery from Meta User token (GET /me/accounts) or explicit Page token + Page ID. Page ownership checked before reading post comments.
- Page picker and authorized recent-post selection, read-only, with server-only token handling. See [Meta Page setup](docs/META_PAGE_SETUP.md).
- Optional Meta Page comments via Graph API (access token and Page permissions required; not yet end-to-end validated with a live token).
- Comment repetition review signals and descriptive one-minute activity peaks. Coordination/identity classification model is **not** implemented.
- Optional **new** CSV import from authorized sources, for local audit purposes only.
- SQLite history (90-day retention); saves aggregated counts and signal descriptions, not user names, profile IDs or raw comment bodies.
- Local-only server on 127.0.0.1. This is not a production internet-facing service.
- Rebuilt Vietnamese-first interface: three-stage Page → photo/link → scan flow, streamlined 3-tab navigation, dedicated integrity report and monitoring controls. Segoe UI local fonts, responsive high-contrast light design.
- GitHub Actions unit tests on each push.
- **One-time encrypted Meta token setup:** paste using a masked Windows dialog (Ctrl+V, right-click Paste, or a dedicated clipboard button); storage uses Windows DPAPI outside Git. The encrypted token takes precedence over stale environment tokens and is hot-reloaded by the running server when updated. Use `VOIDSCAN_USE_ENV_TOKEN=1` for explicit manual-env override. Double-click `start-voidscan.bat` for one-click browser/server launch. See [Token setup](docs/TOKEN_SETUP.md).
- **Reaction Intelligence (experimental):** verified Page photo ID is queried using PageID_PhotoID Graph object form (validated against two connected Pages); aggregates by type where Meta grants access, timestamped snapshots, 10-minute monitoring, provisional suspicious-window counts and shares, and local CSV export. A suspicious-window share is **not** a calibrated probability of bot activity. See [Reaction Integrity Audit](docs/REACTION_AUDIT.md) and [Integrity Report](docs/INTEGRITY_REPORT.md).

## Start (Windows, Python 3.10+)

Open PowerShell inside the repository:

    python server.py

Or run start-voidscan.bat. Open http://localhost:3000 . No dependency installation is needed.

For a User token that has appropriate Page permissions and tasks:

    $env:META_USER_ACCESS_TOKEN = "YOUR_USER_TOKEN"
    python server.py

For a Page token, also supply META_PAGE_ID. Detailed private setup: [META_PAGE_SETUP.md](docs/META_PAGE_SETUP.md).

Do not paste tokens into the UI, commit them to GitHub, or share them. Set the environment variable only in the server process and rotate any previously embedded API keys. Graph API v26.0 requires permissions and application approval depending on the type of post and task. Having a valid token alone does not prove permission to read a target post.

## What happens when you press Scan?

1. Validate that the URL is HTTPS to a recognized facebook.com host.
2. If configured, try a read-only Graph API request for comments available to the authorized Page token (limited sample). Never log into someone's personal account or access private reactors.
3. If Graph API does not provide evidence, try matching this URL against fresh, explicitly imported authorized exports.
4. If neither source has evidence, return **Unavailable / insufficient data** with the reason.
5. Preserve a local summary in the scan-history database. Raw comments and account details are not included in persistent scan history.

A Facebook link alone cannot reveal all individual likes, shares or authenticities. Comment timestamps and repeated content may be perfectly legitimate; they are only screening signals. No fixed threshold can diagnose fake users with certainty.

## Architecture

- server.py — local HTTP JSON API, strict local-only binding.
- scan.py — URL validation and permissioned Meta comments adapter, evidence signals.
- meta_pages.py — read-only Page discovery, authorized post listing, and fail-closed Page ownership verification.
- reaction_collector.py — Page post and Photo ID validation, authorized reactions summaries.
- reaction_history.py — SQLite aggregate snapshots, local monitoring and conservative anomaly detection.
- share_resolver.py — public Facebook /share redirects (HEAD only; no login/cookies).
- secret_store.py — native Windows CurrentUser DPAPI for saved Meta tokens.
- manage_token.py / token_dialog.py — native Windows paste-friendly token enrollment, status and delete.
- launch_voidscan.py — start/check local server and open browser automatically.
- engine.py — optional new CSV import/normalization and duplicate evidence, never an authenticity classifier.
- storage.py — SQLite scan history, 90-day retention and data minimization.
- web/ — responsive dependency-free HTML/CSS/JS dashboard.
- tests/ — fast unit tests, Windows-compatible DB cleanup.
- docs/RESEARCH.md — peer-reviewed literature, limitations and research roadmap.
- .github/workflows/tests.yml — automated CI checks.

Application state lives exclusively under data/ and is ignored by Git. CSV files, .env files, Excel exports, previous scripts, access tokens and local caches are never committed.

## Running tests

    python -m unittest discover -s tests -v
    python -m py_compile server.py scan.py engine.py storage.py
    node --check web/app.js

## Supported current inputs

- Facebook URL in the browser, for example a public Page post or reel.
- Optional fresh Facebook share CSV exports with Profile Name and Profile ID fields; they are not essential to run the app and must be collected lawfully.

## Scope and security

This build is for one authorized user on their own computer. It is not safe to expose the local HTTP server directly to the internet. For a hosted product you would need authentication, stronger upload validation, threat modeling, secret management, rate limiting, provenance verification, independent adjudication, informed privacy controls and legal access reviews.

Research and code references: [RESEARCH](docs/RESEARCH.md). Particularly relevant are Yang et al. (2025) on Facebook coordinated link sharing, Graham et al. (2024) on directed coordination networks, Cresci et al. (2017) on digital DNA, and Wang et al. (2012) on expert human review.
