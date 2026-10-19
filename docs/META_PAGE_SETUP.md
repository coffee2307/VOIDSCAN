# Connecting a Facebook Page to VOIDSCAN

**Status:** The connector is implemented and covered by mocked tests; it has NOT been tested against a real Page token in this installation. The current app is a local research preview, not a hosted OAuth integration.

## Meta requirements

- You administer the Facebook Page and have rights to use its post/comment data.
- A Meta developer app: https://developers.facebook.com/apps/
- A token issued for your own app/Page (generate privately in Graph API Explorer: https://developers.facebook.com/tools/explorer/ ).
- Permissions appropriate for your usage. For listing your Page through a User token, Meta's official collection documents pages_show_list. Common Page reading permissions include pages_read_engagement; reading visitor comments may also require pages_read_user_content. Granting permissions and Advanced Access depends on your Meta app's review, mode, and Page tasks.
- There is no automatic right to scrape all actors who reacted, share accounts, or personal/private comments.

Meta's official Pages API token example:
https://www.postman.com/meta/facebook/request/bqfxwbp/get-access-tokens-of-pages-you-manage

## Choose a connection mode

### Option A: User token (recommended for multiple Pages)

In a new local PowerShell terminal:

    cd F:\VOIDSCAN
    $env:META_USER_ACCESS_TOKEN = "PASTE_YOUR_TOKEN_LOCALLY"
    Remove-Item Env:META_PAGE_ACCESS_TOKEN -ErrorAction SilentlyContinue
    python server.py

The server (not the browser) requests GET /v26.0/me/accounts with Page names, IDs, Page tokens and granted tasks; only Page names, IDs and tasks are returned to the frontend. Token values are kept in process memory. If the token expires, acquire a new one through Meta.

### Option B: One Page token

    cd F:\VOIDSCAN
    $env:META_PAGE_ACCESS_TOKEN = "PASTE_YOUR_PAGE_TOKEN_LOCALLY"
    $env:META_PAGE_ID = "YOUR_NUMERIC_PAGE_ID"
    Remove-Item Env:META_USER_ACCESS_TOKEN -ErrorAction SilentlyContinue
    python server.py

The app checks GET /v26.0/me?fields=id,name,category and requires that it identifies the exact META_PAGE_ID. A User token accidentally pasted as a Page token will not be accepted if the result cannot be verified as the specified Page.

### Security

- Do not send the token in ChatGPT messages, GitHub issues, Discord, screenshots or files to be committed.
- Prefer an environment variable in the server session; the .env.example is documentation only, not an automatic secret loader.
- Do not place your token directly into the address bar or URL.
- Never expose the local VOIDSCAN server to the internet (no authentication or hosted OAuth implementation yet).
- VOIDSCAN uses GET requests to the fixed graph.facebook.com host via a bearer header. No browser cookie scraping.

## Using the UI

1. Start the server and open http://localhost:3000 .
2. At Scan bài đăng, choose an authorized Page from the list. Nguồn dữ liệu → Kiểm tra Page đã cấp quyền refreshes this list.
3. Click Xem bài gần đây to list published Page posts that Graph API allows.
4. Choose a post or paste its Facebook permalink (HTTPS); click Scan.
5. The server matches the URL against the Page's OWN returned post permalinks before requesting comments. Only then does it request limited comments and calculate duplicate-content signals.
6. Scan results include which Page and post were verified, observed comment counts, any sample cap, and the incompleteness warning.

**Current URL coverage:** Graph /{page_id}/posts, up to 200 posts. Video/reel-specific Page edges, old posts beyond this window, share shortlinks and restricted posts might NOT resolve yet. The app will return no verified match rather than querying unverified posts.

**Current comment coverage:** three request pages, up to 300 comments. This limit is intentional. It is not a full audit of all comments when pagination continues. Likes, share identities and fake-account certainty are not accessible here.

## How to diagnose issues

- "Chưa cấu hình token": the server process has no META_USER_ACCESS_TOKEN or META_PAGE_ACCESS_TOKEN. Restart it in the PowerShell session in which you set the variable.
- "Token ... hết hạn": request another valid Meta token.
- "Meta từ chối quyền": check the Meta app's permission grants, Page tasks, app review and whether the post is accessible.
- "Không xác minh được tài nguyên": confirm selected Page and click Xem bài gần đây. The post may be older, a reel, a reshare, or hidden from the selected Page edge.
- "Meta giới hạn tần suất": wait; VOIDSCAN does not automate circumvention of rate limits.

## Next iterations

Add official Page OAuth login for multiple users with encrypted server-side token storage, token refresh/expiration guidance, dedicated Reel/Video resolver, Graph API webhook ingestion where available, and a verified test dataset for false-positive evaluation. None of these are represented as ready in the current alpha.
