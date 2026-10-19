import os
import unittest
from unittest.mock import patch

import meta_pages
from scan import graph_scan, scan

P1="1234567890123"
P2="9876543210123"
POSTID=P1+"_8888888888"
PAGEURL="https://www.facebook.com/myshop/posts/8888888888"

class ManagedPageTests(unittest.TestCase):
    def test_unconfigured_pages_are_empty(self):
        with patch.dict(os.environ, {"META_USER_ACCESS_TOKEN":"","META_PAGE_ACCESS_TOKEN":""}):
            self.assertEqual(meta_pages.configured_mode(), "none")
            self.assertEqual(meta_pages.managed_pages(), {})

    def test_single_page_token_must_match_owner(self):
        with patch.dict(os.environ, {
            "META_USER_ACCESS_TOKEN":"", "META_PAGE_ACCESS_TOKEN":"secret",
            "META_PAGE_ID":P1
        }), patch("meta_pages.graph_get", return_value={"id":P1,"name":"Owned Page","category":"Clothing Store"}) as get:
            pages=meta_pages.managed_pages()
            self.assertEqual(set(pages),{P1})
            self.assertEqual(pages[P1]["token"],"secret")
            self.assertNotIn("secret",str(meta_pages.public_pages(pages)))
            self.assertEqual(get.call_args.args[0],"me")

    def test_single_page_rejects_mismatch(self):
        with patch.dict(os.environ, {
            "META_USER_ACCESS_TOKEN":"", "META_PAGE_ACCESS_TOKEN":"secret",
            "META_PAGE_ID":P2
        }), patch("meta_pages.graph_get", return_value={"id":P1,"name":"Wrong Page","category":"Brand"}):
            with self.assertRaises(meta_pages.MetaAccessError):
                meta_pages.managed_pages()

    def test_user_token_masquerading_as_page_token_is_rejected(self):
        with patch.dict(os.environ, {
            "META_USER_ACCESS_TOKEN":"", "META_PAGE_ACCESS_TOKEN":"wrong-type",
            "META_PAGE_ID":P1
        }), patch("meta_pages.graph_get", return_value={"id":P1,"name":"User"}):
            with self.assertRaises(meta_pages.MetaAccessError):
                meta_pages.managed_pages()

    def test_user_token_lists_managed_pages_but_hides_page_tokens(self):
        with patch.dict(os.environ, {
            "META_USER_ACCESS_TOKEN":"user-secret", "META_PAGE_ACCESS_TOKEN":"",
        }), patch("meta_pages.graph_get", return_value={"data":[
            {"id":P1,"name":"First","access_token":"page-secret",
             "tasks":["ANALYZE"]},
            {"id":P2,"name":"Other","access_token":"page2-secret",
             "tasks":["MODERATE"]},
            {"id":"no_id","name":"Bad","access_token":"bad"},
            {"id":"1011110002222","name":"Token missing"},
        ]}):
            pages=meta_pages.managed_pages()
            self.assertEqual(len(pages),2)
            out=meta_pages.public_pages(pages)
            self.assertNotIn("secret",str(out))
            self.assertEqual(out[0]["tasks"],["ANALYZE"])

    def test_recent_post_requires_verified_page_ownership(self):
        page={"id":P1,"name":"Owned","token":"page-secret"}
        with patch("meta_pages.managed_pages",return_value={P1:page}), patch(
            "meta_pages.page_posts",return_value={
                "items":[{"id":POSTID,"url":PAGEURL,"created_time":"","excerpt":"ok"}],
                "partial":False
            }):
            resolved,post,partial=meta_pages.resolve_page_and_post(PAGEURL,P1)
            self.assertEqual(resolved["id"],P1)
            self.assertEqual(post["id"],POSTID)
            self.assertFalse(partial)
            with self.assertRaises(meta_pages.MetaAccessError):
                meta_pages.resolve_page_and_post(PAGEURL,P2)

    def test_wrong_post_fails_closed_before_comments(self):
        page={"id":P1,"name":"Owned","token":"page-secret"}
        with patch("meta_pages.managed_pages",return_value={P1:page}), patch(
            "meta_pages.page_posts",return_value={"items":[
                {"id":POSTID,"url":PAGEURL}
            ],"partial":False}), patch("meta_pages.graph_get") as api:
            result=graph_scan("https://www.facebook.com/elsewhere/posts/9999999999",P1)
            self.assertEqual(result["status"],"unavailable")
            self.assertFalse(result["ownership_verified"])
            api.assert_not_called()

    def test_authorized_graph_scan_reports_sample(self):
        page={"id":P1,"name":"Owned","token":"secret"}
        msgs=[
            {"id":"a","message":"Repeat eight chars","created_time":"2026-01-01T12:00:00+00:00"},
            {"id":"b","message":"Repeat eight chars","created_time":"2026-01-01T12:00:10+00:00"},
            {"id":"c","message":"Repeat eight chars","created_time":"2026-01-01T12:00:20+00:00"}
        ]
        with patch("meta_pages.resolve_page_and_post",return_value=(
              page,{"id":POSTID,"url":PAGEURL},False)), patch("meta_pages.graph_get",
              return_value={"data":msgs, "paging":{}}):
            result=graph_scan(PAGEURL,P1)
            self.assertEqual(result["status"],"live")
            self.assertTrue(result["ownership_verified"])
            self.assertEqual(result["comments"],3)
            self.assertEqual(result["suspicious"],3)
            self.assertFalse(result["coverage"]["all_engagement_accessible"])

    def test_graph_rate_error_is_sanitized(self):
        page={"id":P1,"name":"Owned","token":"secret"}
        with patch("meta_pages.resolve_page_and_post",return_value=(
              page,{"id":POSTID,"url":PAGEURL},False)), patch("meta_pages.graph_get",
              side_effect=meta_pages.MetaAccessError("rate_limit",613)):
            result=graph_scan(PAGEURL,P1)
            self.assertEqual(result["status"],"unavailable")
            self.assertIn("613",str(result["diagnostic"]))
            self.assertNotIn("secret",str(result))

    def test_reject_pagination_host_injection(self):
        with self.assertRaises(ValueError):
            meta_pages.graph_get("../evil",{}, "secret")

if __name__ == "__main__":
    unittest.main()
