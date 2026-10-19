# VOIDSCAN

VOIDSCAN is a local-first Facebook share and comment audit dashboard. It imports authorized CSV exports, identifies repeat records by Profile ID within a class, visualizes class totals, and supports human review. It DOES NOT claim to prove an account is fake.

## Start on Windows

1. Install Python 3.10+ (Python 3.12 is supported).
2. Open PowerShell in the repository folder and run: python server.py
3. Open http://localhost:3000 in your browser. Or double-click start-voidscan.bat.

The application uses Python standard libraries and plain JavaScript. By design the HTTP server binds to 127.0.0.1 and is intended ONLY for local single-user access.

## How to scan a Facebook post URL

Paste a facebook.com post or reel URL in the Scan panel on the overview page.

- LOCAL CSV MODE: If the post matches a Source URL in already imported exports, VOIDSCAN reports the records, duplicates by Profile ID and missing identifiers in the local file. This is not a live refresh.
- PERMISSIONED META MODE: If you have Meta Page access and the correct privileges, set the META_PAGE_ACCESS_TOKEN environment variable before starting the server. VOIDSCAN then tries Graph API v26.0 to retrieve available comments (up to 300) and detect repeated texts and unusual timing bursts. API permissions and resource accessibility vary by Page and post type. Meta may refuse the request.
- WITHOUT DATA: If no matching local exports or authorized Graph access exist, VOIDSCAN explains that the scan cannot proceed. A URL alone does not disclose all shares, likers, commenters or personal account details.

PowerShell example for your own Meta Page:
    $env:META_PAGE_ACCESS_TOKEN = "REPLACE_WITH_YOUR_OWN_PAGE_TOKEN"
    python server.py

The token stays server-side. Do not enter your Facebook password or use an account cookie.

## CSV importer

Under Nguon du lieu, import one or more CSV exports with Profile Name and Profile ID columns. Supported layouts include comma-delimited files and semicolon-delimited files with a preamble. Imports and decisions are saved only in the local data directory (ignored by Git).

- Same profile ID repeated in the same class: duplicate record. This can result from multiple legitimate shares or repeated exports.
- Same profile ID shared across different classes: cross-class activity, not automatically suspicious.
- Same profile name but different IDs: treated as separate identities.
- Missing profile ID: insufficient data, not a fake-account finding.

The manual review workflow supports Keep / Exclude decisions and filtering. Report CSV exports preserve evidence metadata; originals remain unchanged.

## Tests

    python -m unittest discover -s tests -v
    node --check web/app.js
    python -m py_compile server.py engine.py scan.py

## Repository and privacy

The original one-off research scripts are excluded from the repository because the legacy Apify script contained an embedded API credential. You must REVOKE and ROTATE that credential in your Apify account; Git does not remove copies from existing local files or earlier transfers.

This repository is public. Do not add .env, local data, CSV exports, spreadsheets, access tokens or personally identifying data. The provided .gitignore excludes these by default.

## Architecture

- server.py — dependency-free local HTTP server and JSON API
- engine.py — CSV normalization, same-class deduplication and summaries
- scan.py — local post URL matching, authorized Meta Graph API comments and screening signals
- web/index.html, app.css, app.js — responsive dashboard
- tests/ — parser, data safety, scan and validation tests

## Research sources (for methods, NOT plug-and-play Facebook bot classifiers)

- QUT Digital Observatory Coordination Network Toolkit: https://github.com/QUT-Digital-Observatory/coordination-network-toolkit (MIT). Network coactivity methods can be adapted to Facebook with suitable event data.
- CooRTweet: https://github.com/nicolarighetti/CooRTweet . Detects coordinated sharing networks, historically Twitter-oriented; requires underlying event data.
- OSoMe Botometer Python: https://github.com/osome-iu/botometer-python (MIT). Twitter/X API client; not a Facebook detector.
- facebook-scraper: https://github.com/kevinzg/facebook-scraper (MIT). Scraping library, not a fake engagement model; verify maintenance and Meta access rules before using.
- Recent small projects sometimes demonstrate Isolation Forest and DBSCAN on synthetic social media data, but metrics on synthetic datasets are NOT validation of Facebook performance.

None of these projects can reliably label every Facebook reaction as genuine or fake. Treat duplicate text, timing bursts and unusual coordination as human-review signals only.

## Limitations and future work

The current URL scan cannot access arbitrary personal posts, private engagements or all reactions. A public-facing service will need authentication, abuse protection, data retention controls, stronger API permission handling and explicit security review before deployment.
