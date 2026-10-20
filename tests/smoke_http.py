"""End-to-end HTTP smoke test with isolated temporary data; safe for CI."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def get_json(url):
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)

def post_json(url, body):
    request = urllib.request.Request(
        url, json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)

def main():
    with tempfile.TemporaryDirectory(prefix="voidscan-http-") as temp:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ)
        env["VOIDSCAN_DATA_DIR"] = temp
        # Keep smoke tests strictly isolated from real encrypted Meta tokens.
        env["LOCALAPPDATA"] = str(Path(temp) / "empty-user-profile")
        env["VOIDSCAN_PORT"] = str(port)
        env.pop("META_PAGE_ACCESS_TOKEN", None)
        env.pop("META_USER_ACCESS_TOKEN", None)
        env.pop("META_PAGE_ID", None)
        proc = subprocess.Popen(
            [sys.executable, "-u", "server.py"],
            cwd=str(ROOT), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            base = f"http://127.0.0.1:{port}"
            ready = False
            for _ in range(60):
                if proc.poll() is not None:
                    raise AssertionError("Local server exited before readiness")
                try:
                    ready = get_json(base + "/api/health")["ok"]
                    if ready:
                        break
                except (OSError, ValueError):
                    time.sleep(0.1)
            assert ready, "Server did not start"
            bundle=get_json(base + "/api/research/bundle.json")
            assert bundle["payload"]["objects"] == []
            assert bundle["payload"]["automatic_deduction"] == 0
            assert bundle["payload"]["confirmed_manipulation_labels"] == 0
            assert len(bundle["integrity"]["payload_sha256"]) == 64
            diagnostics=get_json(base + "/api/research/readiness")
            assert diagnostics["status"] == "no_data"
            assert diagnostics["snapshots"] == 0
            assert diagnostics["active_watches"] == 0
            assert diagnostics["bot_probability_validated"] is False
            assert diagnostics["automatic_deduction"] == 0
            pages = get_json(base + "/api/meta/pages")
            assert pages["status"] == "unconfigured" and pages["pages"] == []
            try:
                get_json(base + "/api/meta/posts?page_id=123456789")
                raise AssertionError("Unowned page should not be returned")
            except urllib.error.HTTPError as exc:
                assert exc.code == 403
            unavailable_photo=get_json(base+"/api/reactions/photos?page_id=123456789")
            assert unavailable_photo["status"]=="unavailable"
            report=get_json(base+"/api/reactions/report?page_id=123456789&object_id=123456789&type=LOVE")
            assert report["assessment"]["current_reactions"] is None
            assert report["assessment"]["bot_probability_pct"] is None
            assert report["assessment"]["suspicious_share_pct"] is None
            assert report["assessment"]["automatic_deduction"] == 0
            comparison=report["r1_research_comparison"]
            assert comparison["status"]=="insufficient_history"
            assert comparison["bot_probability_pct"] is None
            assert comparison["automatic_deduction"] == 0
            assert len(comparison["method_results"])==3
            assert report["observations"] == []
            assert report["r1_context_events"] == []
            annotation=post_json(base+"/api/reactions/context",{
                "action":"add",
                "page_id":"123456789",
                "object_id":"123456789",
                "event_type":"organizer_announcement",
                "start_utc":"2026-10-20T00:00:00+00:00",
                "end_utc":"2026-10-20T01:00:00+00:00",
                "evidence_ref":"NOTICE-01",
                "note":"Thông báo bình chọn đã được đăng."
            })
            assert annotation["created"] is True
            stored=get_json(base+"/api/reactions/context?page_id=123456789&object_id=123456789")
            assert stored["context_is_unverified"] is True
            assert len(stored["items"])==1
            report_with_context=get_json(base+"/api/reactions/report?page_id=123456789&object_id=123456789&type=LOVE")
            assert len(report_with_context["r1_context_events"])==1
            assert report_with_context["assessment"]["automatic_deduction"]==0
            removed=post_json(base+"/api/reactions/context",{
                "action":"remove","id":annotation["id"],
                "page_id":"123456789","object_id":"123456789"
            })
            assert removed["deleted"] is True
            assert not get_json(base+"/api/reactions/context?page_id=123456789&object_id=123456789")["items"]
            empty_reactions=get_json(base+"/api/reactions/history?page_id=123456789&object_id=123456789&type=LOVE")
            assert empty_reactions["snapshots"]==[]
            assert empty_reactions["authoritative_bot_count"] is None
            try:
                post_json(base+"/api/reactions/snapshot",{
                    "page_id":"123456789","post_id":"123456789","object_id":"123456789"})
                raise AssertionError("Unowned Page should be refused")
            except urllib.error.HTTPError as exc:
                assert exc.code==403
            initial = get_json(base + "/api/status")
            assert initial["stats"]["scans"] == 0
            assert initial["connectors"]["meta"] is False
            assert get_json(base + "/api/overview")["counts"]["total"] == 0
            result = post_json(base + "/api/scan", {
                "url": "https://www.facebook.com/reel/1527428255063081/"})
            assert result["status"] == "unavailable"
            assert len(result["scan_id"]) == 32
            history = get_json(base + "/api/scans")["items"]
            assert len(history) == 1
            assert history[0]["status"] == "unavailable"
            item = get_json(base + "/api/scans/" + result["scan_id"])
            assert item["result"]["status"] == "unavailable"
            assert "examples" not in item["result"]
            with urllib.request.urlopen(base + "/api/export-history.csv", timeout=3) as response:
                content = response.read().decode("utf-8-sig")
                assert "Scan ID" in content
                assert result["scan_id"] in content
            try:
                post_json(base + "/api/scan", {
                    "url": "https://facebook.com.evil.invalid/posts/1234567"})
                raise AssertionError("Unsafe URL should be rejected")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400
            assert get_json(base + "/api/status")["stats"]["scans"] == 1
            print("HTTP smoke: PASS | empty baseline, scan, audit history, export, invalid URL")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            if proc.stderr:
                proc.stderr.close()

if __name__ == "__main__":
    main()
