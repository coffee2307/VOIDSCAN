"""R1 local campaign context annotations are review notes, never bot labels."""
from __future__ import annotations
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from reaction_context import add,listing,remove,overlaps,validate_event

P="12345678901"
O="12345678902"
BASE=datetime(2026,10,20,1,tzinfo=timezone.utc)
def event(**changes):
    data={"page_id":P,"object_id":O,
          "event_type":"creator_share",
          "start_utc":BASE.isoformat(),
          "end_utc":(BASE+timedelta(hours=1)).isoformat(),
          "evidence_ref":"SHARE-01", "note":"Bình chọn hợp lệ đã được chia sẻ."}
    data.update(changes)
    return data

class ContextTests(unittest.TestCase):
    def test_add_list_remove_round_trip_and_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"study.db"
            self.assertEqual(listing(P,O,path),[])
            code=add(event(),path)
            got=listing(P,O,path)
            self.assertEqual(len(got),1)
            self.assertEqual(got[0]["id"],code)
            self.assertEqual(got[0]["event_type"],"creator_share")
            self.assertEqual(listing(P,"12345678903",path),[])
            self.assertFalse(remove(code,P,"12345678903",path))
            self.assertTrue(remove(code,P,O,path))
            self.assertFalse(remove(code,P,O,path))
            self.assertEqual(listing(P,O,path),[])

    def test_validates_bad_ids_dates_ranges_and_kinds(self):
        samples=[
            event(page_id="../etc/passwd"),
            event(object_id="anything"),
            event(event_type="bot_confirmed"),
            event(start_utc="2026-10-20 01:00",end_utc="2026-10-20 02:00"),
            event(end_utc=BASE.isoformat()),
            event(end_utc=(BASE+timedelta(days=35)).isoformat()),
            event(evidence_ref="https://example.com/private-user",note="valid"),
            event(note="a"*501),
        ]
        # URLs are not accepted as evidence references. They must be local codes.
        for i,case in enumerate(samples):
            with self.subTest(i=i):
                with self.assertRaises(ValueError):
                    validate_event(case)

    def test_context_overlap_never_suppresses_flag(self):
        inc=[{"from":(BASE+timedelta(minutes=10)).isoformat(),
              "to":(BASE+timedelta(minutes=20)).isoformat(),
              "flagged":True, "delta":900}]
        events=[{"id":"known-promotion","start_utc":BASE.isoformat(),
                 "end_utc":(BASE+timedelta(minutes=30)).isoformat()}]
        marked=overlaps(inc,events)
        self.assertTrue(marked[0]["flagged"])
        self.assertEqual(marked[0]["delta"],900)
        self.assertEqual(marked[0]["context_event_ids"],["known-promotion"])
        self.assertNotIn("context_event_ids",inc[0])

    def test_nonoverlapping_and_boundary(self):
        marked=overlaps([{"from":BASE.isoformat(),
                          "to":(BASE+timedelta(minutes=10)).isoformat(),"flagged":True}],
                [{"id":"later","start_utc":(BASE+timedelta(minutes=10)).isoformat(),
                  "end_utc":(BASE+timedelta(hours=1)).isoformat()}])
        self.assertEqual(marked[0]["context_event_ids"],[])
        self.assertTrue(marked[0]["flagged"])

    def test_no_actor_certainty_is_assigned(self):
        data=validate_event(event())
        self.assertNotIn("is_real",data)
        self.assertNotIn("bot_probability",data)
        self.assertNotIn("automatic_deduction",data)

if __name__=="__main__":
    unittest.main()
