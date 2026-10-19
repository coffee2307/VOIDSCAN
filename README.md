# VOIDSCAN 2.3 — Reaction Intelligence Research Preview

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
- Vietnamese-first responsive interface using local Windows Segoe UI fonts (no external font dependency), high-contrast light theme by default and an optional dark theme. The theme toggle is available in the top-right corner and remembered locally.
- GitHub Actions unit tests on each push.
- **One-time encrypted Meta token setup:** paste using a masked Windows dialog (Ctrl+V, right-click Paste, or a dedicated clipboard button); storage uses Windows DPAPI outside Git. The encrypted token takes precedence over stale environment tokens and is hot-reloaded by the running server when updated. Use `VOIDSCAN_USE_ENV_TOKEN=1` for explicit manual-env override. Double-click `start-voidscan.bat` for one-click browser/server launch. See [Token setup](docs/TOKEN_SETUP.md).
- **Reaction Intelligence (experimental):** authorized Page post and photo reaction counts, timestamped SQLite observations, 10-minute local monitor for up to 5 objects, audit CSV export and review-only anomaly screening. It does not infer the number of bot accounts or automatically deduct votes. See [Reaction Integrity Audit](docs/REACTION_AUDIT.md).

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
