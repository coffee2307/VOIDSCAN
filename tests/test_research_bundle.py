"""R2 aggregate research export: privacy, integrity and robustness tests."""
from __future__ import annotations

import copy
import io
import json
from contextlib import redirect_stdout
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

import reaction_history
from research_bundle import build_bundle, verify_bundle, MAX_OBJECTS, MAX_SAMPLES_PER_OBJECT
from research_cli import main as cli_main

PAGE="1234567890123"
PHOTO="9876543210987"
POST="1234567890123_9876543210987"
NOW=datetime(2026,10,20,9,tzinfo=timezone.utc)


def record(count,at=NOW,page=PAGE,photo=PHOTO):
    return {
        "page":{"id":page,"name":"Owner Example Secret Page"},
        "post":{"id":POST,"url":"https://facebook.com/example/private-photo"},
        "object":{"id":photo,"type":"photo"},
        "observed_at":at.isoformat(),
        "reaction":{"status":"partial","counts":{
            "LIKE":count,"LOVE":count,"WOW":1,"HAHA":2,"SAD":None,"ANGRY":0
        }},
    }


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"example.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_database_not_created(self):
        result=build_bundle(self.db,now=NOW)
        self.assertFalse(self.db.exists())
        self.assertEqual(result["payload"]["objects"],[])
        self.assertTrue(verify_bundle(result))

    def test_export_redacts_ids_names_urls_and_credentials(self):
        for i in range(7):
            reaction_history.store_observation(record(i*10,NOW-timedelta(minutes=(6-i)*10)),self.db)
        package=build_bundle(self.db,now=NOW)
        serial=json.dumps(package)
        for forbidden in (PAGE,PHOTO,POST,"Secret Page","facebook.com",
                          "access_token","META_USER_ACCESS_TOKEN","bot_account"):
            self.assertNotIn(forbidden,serial)
        self.assertEqual(package["payload"]["audit"]["total_saved_objects"],1)
        item=package["payload"]["objects"][0]
        self.assertEqual(len(item["observations"]),7)
        self.assertEqual(item["observations"][0]["counts"]["LOVE"],0)
        self.assertIsNone(item["observations"][0]["counts"]["SAD"])
        self.assertEqual(item["quality"]["LOVE"]["eligible_adjacent_intervals"],6)
        self.assertTrue(item["quality"]["LOVE"]["ready_for_review"])
        self.assertTrue(verify_bundle(package))
        self.assertEqual(package["payload"]["confirmed_manipulation_labels"],0)
        self.assertEqual(package["payload"]["automatic_deduction"],0)

    def test_recent_sample_cap_and_exact_truncation_count(self):
        for idx in range(6):
            reaction_history.store_observation(
                record(idx,NOW-timedelta(minutes=(5-idx)*10)),self.db)
        with patch("research_bundle.MAX_SAMPLES_PER_OBJECT",3):
            package=build_bundle(self.db,now=NOW)
        values=[x["counts"]["LOVE"] for x in package["payload"]["objects"][0]["observations"]]
        self.assertEqual(values,[3,4,5])
        self.assertEqual(package["payload"]["audit"]["records_truncated"],3)
        self.assertTrue(verify_bundle(package))

    def test_each_export_uses_fresh_secret(self):
        reaction_history.store_observation(record(100),self.db)
        one=build_bundle(self.db,now=NOW)
        two=build_bundle(self.db,now=NOW)
        self.assertNotEqual(one["payload"]["objects"][0]["object_pseudonym"],
                            two["payload"]["objects"][0]["object_pseudonym"])
        self.assertNotEqual(one["payload"]["objects"][0]["page_pseudonym"],
                            two["payload"]["objects"][0]["page_pseudonym"])

    def test_verify_detects_tampering(self):
        reaction_history.store_observation(record(100),self.db)
        p=build_bundle(self.db,now=NOW)
        self.assertTrue(verify_bundle(p))
        changed=copy.deepcopy(p)
        changed["payload"]["objects"][0]["observations"][0]["counts"]["LOVE"]=9999
        self.assertFalse(verify_bundle(changed))
        changed=copy.deepcopy(p)
        changed["integrity"]["payload_sha256"]="0"*64
        self.assertFalse(verify_bundle(changed))
        self.assertFalse(verify_bundle({"payload":{}}))

    def test_reject_invalid_inputs_and_no_write_back(self):
        with self.assertRaises(ValueError):
            build_bundle(self.db,max_objects=0)
        with self.assertRaises(ValueError):
            build_bundle(self.db,max_objects=MAX_OBJECTS+1)
        with self.assertRaises(ValueError):
            build_bundle(self.db,now=datetime(2026,10,20))
        reaction_history.store_observation(record(40),self.db)
        before=self.db.read_bytes()
        build_bundle(self.db,now=NOW)
        self.assertEqual(self.db.read_bytes(),before)

    def test_cli_local_export_verify_and_no_overwrite(self):
        reaction_history.store_observation(record(123),self.db)
        output=Path(self.temp.name)/"export.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli_main(["bundle","--db",str(self.db),
                                       "--output",str(output)]),0)
            self.assertTrue(output.is_file())
            self.assertEqual(cli_main(["verify-bundle","--input",str(output)]),0)
            # Existing output may not be silently overwritten.
            self.assertEqual(cli_main(["bundle","--db",str(self.db),
                                       "--output",str(output)]),2)
        payload=json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(verify_bundle(payload))

    def test_multiple_objects_share_page_pseudonym_in_one_bundle(self):
        reaction_history.store_observation(record(20,photo=PHOTO),self.db)
        reaction_history.store_observation(record(30,photo="9876543210986"),self.db)
        bundle=build_bundle(self.db,now=NOW)
        self.assertEqual(len(bundle["payload"]["objects"]),2)
        a,b=bundle["payload"]["objects"]
        self.assertEqual(a["page_pseudonym"],b["page_pseudonym"])
        self.assertNotEqual(a["object_pseudonym"],b["object_pseudonym"])
        self.assertNotIn(PHOTO,json.dumps(bundle))

if __name__=="__main__":
    unittest.main()
