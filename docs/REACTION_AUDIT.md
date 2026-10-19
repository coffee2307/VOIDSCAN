# VOIDSCAN 2.3 — Reaction Integrity Audit

This is a local research preview for audits of contests run on managed Facebook Pages.

## What can be measured

- Page Post or Page-uploaded Photo ID, verified by the official Page token.
- Counts by LIKE, LOVE, WOW, HAHA, SAD and ANGRY when Meta Graph API returns an explicit summary.total_count.
- Timestamped aggregate snapshots and rate-of-change anomalies for each verified object.
- Retrospective baseline at time of first collection and prospective monitoring every 10 minutes (configurable 300–3600 seconds, up to 5 objects). The local computer and server must remain running.
- Local CSV evidence export. Stored snapshots do not include people who reacted.

## What cannot be established

VOIDSCAN cannot access a complete list of user IDs who reacted through the PagePost reaction edge. It cannot assert that, among 1000 hearts, precisely 800 are fake. The number of reactions during an abnormal time window is not a count of fake accounts.

Meta documentation: https://developers.facebook.com/docs/graph-api/reference/v26.0/object/reactions

## For a contest with a multi-photo post

1. Start the server with your authorized Meta User token as described in META_PAGE_SETUP.md.
2. Choose the managed Page.
3. Click Xem bài gần đây to select the parent post and Tìm ảnh trong bài đã chọn to request available child Photo IDs.
4. Alternatively click Xem ảnh đã đăng to view photo objects from the official Page photos?type=uploaded API.
5. For a short URL such as https://www.facebook.com/share/.../, use Tìm ảnh trong bài đã chọn. A limited, public HEAD-redirect-only resolver tries to identify the linked Photo. Redirects are restricted to official facebook.com hosts, with no cookies, login, private content retrieval or access-control bypass. If no verified Photo ID is found, choose it manually from the Page gallery.
6. Select the individual Photo ID. Never automatically use the parent post count as the photo count.
7. Click Ghi nhận số liệu hiện tại to store a baseline. For future contests, enable Bật theo dõi định kỳ and leave the local server online.
8. Export timestamped data and review anomalous intervals. Click Dừng theo dõi định kỳ to stop a target.

Page Photos documentation:
https://developers.facebook.com/docs/graph-api/reference/page/photos/

## Important count and identity limitations

- LIKE can include CARE: the Meta reaction count API does not consistently separate these. VOIDSCAN clearly labels LIKE as potentially including CARE.
- Meta uses SORRY for the SAD reaction enum on the PagePost reactions edge.
- If a Photo object does not support reactions summary for your permissions and Meta API mode, the field remains null / no data; VOIDSCAN does not manufacture a value of zero or silently substitute the parent post.
- Reaction count decreases are possible when people withdraw or change reactions. Each snapshot is a reading at its timestamp, not the exact timestamp of individual votes.
- Photos and posts from other Pages are rejected even if the URL is public.
- Older posts/photos may require direct Page-owner verification. If Meta does not expose authorship or matching Page upload metadata, VOIDSCAN fails closed.

## Historical contests

If the event took place before monitoring began, only current aggregated numbers and other independently preserved authorized historical records can be investigated. You cannot reconstruct every old reaction, its timestamp or actor by scraping visible current totals. If an old photo has 1000 hearts today, any estimate of past bots requires independent evidence; the first snapshot cannot prove fraud.

## Provisional anomaly methodology

For each reaction type, the tool compares the current time interval only with earlier intervals. At least five previous valid interval rates are needed. A provisional review signal requires a net increase of at least 20 reactions and a rate of at least 4/min, exceeding conservative historical median/MAD thresholds. These heuristics are not calibrated on verified Facebook-bot labels. They do not produce any valid bot probability or number of fake reactions.

The flagged_net_increase value is the total positive net growth during intervals marked for review; it is NOT the number of bot reactions.

The automatic deduction count is deliberately zero. Contest decisions should be based on published rules, independent corroboration, traceable evidence, human adjudication and an appeal procedure, not a naked anomaly threshold.

Relevant study: Rogers & Righetti (2025), Coordinated inauthentic behaviour on Facebook? A typology of manufactured attention. https://doi.org/10.1177/29768624251369784

## Data storage and access

- Reaction snapshots are saved under local data/voidscan.sqlite3, ignored by Git.
- Only aggregate counts, object IDs, Page IDs and timestamps are persisted; no individual Facebook reaction identities.
- Snapshots remain until archived/deleted by the user. The separate scan-job summary policy of 90 days does not apply to reaction evidence. Keep secure backups.
- The local app is single-user, bound to localhost only, without public authentication. Do not port-forward it to the internet.
- Monitoring only runs while VOIDSCAN server is up and token still works. It pauses on errors and never records fabricated counts for failed Meta calls.

## HTTP API

GET /api/reactions/photos?page_id=PAGE_ID
GET /api/reactions/objects?page_id=PAGE_ID&post_id=POST_ID
GET /api/reactions/resolve-share?page_id=PAGE_ID&url=FACEBOOK_URL
POST /api/reactions/snapshot with JSON page_id, post_id, object_id
POST /api/reactions/watch with JSON page_id, post_id, object_id
POST /api/reactions/toggle with JSON id and active
GET /api/reactions/watches
GET /api/reactions/history?page_id=PAGE_ID&object_id=OBJECT_ID&type=LOVE
GET /api/reactions/export.csv?page_id=PAGE_ID&object_id=OBJECT_ID

No endpoint writes, removes, manipulates or reacts to Facebook objects.
