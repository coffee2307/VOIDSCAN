from __future__ import annotations
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import reaction_collector as rc
import reaction_history as rh
from meta_pages import MetaAccessError

PAGE="1234567890123"
POST=PAGE+"_8888888888"
PHOTO="1234567890129"
URL="https://www.facebook.com/shop/posts/8888888888"

class ReactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"reactions.sqlite3"
        self.page={"id":PAGE,"name":"My Page","token":"MOCKSECRET"}
        self.post={"id":POST,"url":URL,"created_time":"","excerpt":"Photo album"}

    def tearDown(self):
        self.temp.cleanup()

    def sample(self,delta,minute):
        d=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=minute))
        return {"page":{"id":PAGE,"name":"Page"},"post":{"id":POST,"url":URL},
         "object":{"id":PHOTO,"type":"attachment"},
         "observed_at":d.isoformat(timespec="seconds"),
         "reaction":{"status":"ok","counts":{"LOVE":delta,"LIKE":1,"WOW":0,
                        "HAHA":0,"SAD":0,"ANGRY":0}}}

    def test_extract_does_not_invent_zeros(self):
        parsed=rc.extract_counts({"r_love":{"summary":{"total_count":50}},
                                  "r_like":{"summary":{"total_count":0}},
                                  "r_haha":{"summary":{"total_count":"900"}}})
        self.assertEqual(parsed["LOVE"],50)
        self.assertEqual(parsed["LIKE"],0)
        self.assertIsNone(parsed["HAHA"])
        self.assertIsNone(parsed["SAD"])

    def test_sad_is_isolated_from_supported_batch(self):
        fields=rc.reaction_fields()
        self.assertIn("type(LOVE)",fields)
        self.assertNotIn("type(SORRY)",fields)
        self.assertNotIn("type(SAD)",fields)

    def test_attachment_whitelist_and_no_parent_fallback(self):
        with patch("reaction_collector.managed_pages",return_value={PAGE:self.page}),patch(
          "reaction_collector.page_posts",return_value={"items":[self.post],"partial":False}),patch(
          "reaction_collector.attached_objects",return_value={"items":[{"id":PHOTO}],"status":"ok"}),patch(
          "reaction_collector.read_reactions",return_value={
            "status":"unavailable","counts":dict.fromkeys(rc.REACTIONS),
            "missing":list(rc.REACTIONS),"api_error":{"kind":"permission"}}) as reading:
            item=rc.collect_once(PAGE,POST,PHOTO)
            self.assertEqual(item["object"]["id"],PHOTO)
            self.assertEqual(item["reaction"]["status"],"unavailable")
            reading.assert_called_once_with(PHOTO,self.page)
        with patch("reaction_collector.managed_pages",return_value={PAGE:self.page}),patch(
          "reaction_collector.page_posts",return_value={"items":[self.post],"partial":False}),patch(
          "reaction_collector.attached_objects",return_value={"items":[{"id":PHOTO}],"status":"ok"}):
            with self.assertRaises(MetaAccessError):
                rc.collect_once(PAGE,POST,"7777777777777")

    def test_not_stored_without_count(self):
        sample=self.sample(10,0)
        sample["reaction"]={"status":"unavailable","counts":dict.fromkeys(rc.REACTIONS)}
        self.assertIsNone(rh.store_observation(sample,self.db))
        self.assertEqual(rh.history(PAGE,PHOTO,path=self.db),[])

    def test_stored_aggregates_only(self):
        sample=self.sample(15,0)
        sample["examples"]=[{"name":"PRIVATE PERSON"}]
        sample["reaction"]["counts"]["LOVE"]=15
        token=rh.store_observation(sample,self.db)
        self.assertEqual(len(token),32)
        history=rh.history(PAGE,PHOTO,path=self.db)
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]["counts"]["LOVE"],15)
        self.assertNotIn("PRIVATE PERSON",self.db.read_bytes().decode("utf-8",errors="ignore"))

    def test_uploaded_photo_page_connector(self):
        with patch("reaction_collector.graph_get",return_value={
            "data":[{"id":PHOTO,"link":"https://www.facebook.com/photo/?fbid="+PHOTO,
                     "created_time":"2026-10-19T09:00:00+0000",
                     "name":"Contest portrait"}]}):
            found=rc.page_photos(self.page)
            self.assertEqual(found["items"][0]["id"],PHOTO)
            self.assertFalse(found["partial"])

    def test_standalone_page_photo_verification(self):
        with patch("reaction_collector.managed_pages",return_value={PAGE:self.page}),patch(
          "reaction_collector.verify_photo",return_value=(
            {"id":PHOTO,"url":"https://www.facebook.com/photo/?fbid="+PHOTO},False)),patch(
          "reaction_collector.read_reactions",return_value={
            "status":"ok","counts":dict.fromkeys(rc.REACTIONS,0),
            "missing":[],"api_error":None}):
            result=rc.collect_once(PAGE,PHOTO,PHOTO)
            self.assertEqual(result["object"]["type"],"photo")
            self.assertEqual(result["object"]["id"],PHOTO)

    def test_photo_reaction_uses_verified_page_composite_id(self):
        with patch("reaction_collector.managed_pages",return_value={PAGE:self.page}),patch(
          "reaction_collector.verify_photo",return_value=({"id":PHOTO,"url":URL},False)),patch(
          "reaction_collector.read_reactions",return_value={
            "status":"partial","counts":dict.fromkeys(rc.REACTIONS,0),
            "missing":[],"api_error":None}) as reader:
            result=rc.collect_once(PAGE,PHOTO,PHOTO)
            self.assertEqual(result["object"]["id"],PHOTO)
            reader.assert_called_once_with(PAGE+"_"+PHOTO,self.page)

    def test_old_photo_does_not_bypass_creator_check(self):
        with patch("reaction_collector.page_photos",
                   return_value={"items":[],"partial":True}),patch(
                   "reaction_collector.graph_get",return_value={
                       "id":PHOTO,"from":{"id":"999999999999"},"link":URL}):
            with self.assertRaises(MetaAccessError):
                rc.verify_photo(self.page,PHOTO)

    def test_old_page_post_direct_owner_lookup(self):
        old_id=PAGE+"_777777777777"
        with patch("reaction_collector.page_posts",return_value={"items":[],"partial":True}),patch(
          "reaction_collector.graph_get",return_value={
             "id":old_id,"from":{"id":PAGE},"permalink_url":URL
          }):
            post,partial=rc.select_post(self.page,post_id=old_id)
            self.assertEqual(post["id"],old_id)
            self.assertTrue(partial)

    def test_rate_limit_never_spawns_multiple_retry_calls(self):
        with patch("reaction_collector.graph_get",
          side_effect=MetaAccessError("rate_limit",613)) as graph:
            value=rc.read_reactions(PHOTO,self.page)
            self.assertEqual(value["status"],"unavailable")
            self.assertEqual(graph.call_count,1)

    def test_watch_toggle(self):
        wid=rh.watch(PAGE,POST,PHOTO,self.db)
        self.assertTrue(rh.set_watch(wid,False,self.db))
        self.assertFalse(rh.watch_list(self.db)[0]["active"])
        rh.watch(PAGE,POST,PHOTO,self.db)
        self.assertTrue(rh.watch_list(self.db)[0]["active"])

    def test_history_only_anomaly_and_zero_deduction(self):
        points=[]
        for i in range(8):
            sample=self.sample(i*10,i*10)
            points.append({"observed_at":sample["observed_at"],
                           "counts":sample["reaction"]["counts"]})
        spike=self.sample(700,80)
        points.append({"observed_at":spike["observed_at"],"counts":spike["reaction"]["counts"]})
        result=rh.anomaly_report(points,"LOVE")
        self.assertEqual(result["flagged_intervals"],1)
        self.assertEqual(result["flagged_net_increase"],630)
        self.assertTrue(result["not_fake_count"])
        self.assertEqual(result["deductible_reactions"],0)
        self.assertFalse(result["intervals"][0]["flagged"])
        self.assertIsNone(result["intervals"][0]["baseline_rate"])
        self.assertTrue(result["intervals"][-1]["flagged"])

if __name__=="__main__":
    unittest.main()
