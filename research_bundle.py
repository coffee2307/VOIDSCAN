"""R2 research evidence bundles: offline, explicit export of aggregate measurements.

No tokens, user identities, Page IDs, photo IDs, post URLs, manual notes, or
claimed ground-truth labels leave this exporter. Pseudonyms are unlinkable
across exports because a new private HMAC key is generated per invocation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from reaction_collector import REACTIONS
from research_quality import audit_series, parse_utc
from storage import DEFAULT_DB

VERSION=1
MAX_OBJECTS=25
MAX_SAMPLES_PER_OBJECT=3000
ALLOWED_SOURCES={"meta_graph_api"}
ALLOWED_STATUSES={"ok","partial"}
ALLOWED_TYPES={"photo","post","attachment"}


def canonical(document):
    return json.dumps(document,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def _pseudo(secret,category,value):
    return category+"_"+hmac.new(secret,(category+"\0"+str(value)).encode("utf-8"),
                                hashlib.sha256).hexdigest()[:20]


def _read_only(path):
    uri=Path(path).resolve().as_uri()+"?mode=ro"
    db=sqlite3.connect(uri,uri=True,timeout=8)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def build_bundle(path=DEFAULT_DB,*,now=None,max_objects=MAX_OBJECTS):
    """Read ONLY saved aggregate snapshots. Never create/change local database."""
    if not isinstance(max_objects,int) or not 1 <= max_objects <= MAX_OBJECTS:
        raise ValueError("max_objects must be 1..25")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Timestamp must have timezone")
    # Invisible pseudonymization secret is never serialized with the dataset.
    secret=secrets.token_bytes(32)
    payload={
        "schema_version":VERSION,
        "kind":"voidscan_aggregate_reaction_research",
        "generated_at":now.astimezone(timezone.utc).isoformat(),
        "scope":"locally_stored_aggregate_observations_only",
        "actor_level_data_available":False,
        "confirmed_manipulation_labels":0,
        "bot_probability_validated":False,
        "automatic_deduction":0,
        "pseudonymization":"random_key_hmac_sha256_per_bundle_not_linkable_across_exports",
        "objects":[],
        "audit":{"objects_omitted":0,"records_rejected":0,
                 "records_truncated":0,"total_saved_objects":0},
        "limitations":[
            "Does not establish whether any reacting account is fake.",
            "Contains no independently verified fraud or legitimacy labels.",
            "Each export uses new opaque identifiers; two exports cannot be reliably joined.",
            "Integrity checksum detects later edits but does not authenticate Meta source data.",
            "Only stored measurements are included; unavailable past history cannot be reconstructed.",
        ],
    }
    file=Path(path)
    if not file.is_file():
        return _finish(payload)
    with closing(_read_only(file)) as db:
        # One consistent read transaction even if a monitor writes concurrently.
        db.execute("BEGIN")
        all_objects=db.execute("""
            SELECT page_id,object_id,COUNT(*) AS n
            FROM reaction_snapshots GROUP BY page_id,object_id
            ORDER BY MAX(observed_at) DESC,page_id,object_id
        """).fetchall()
        payload["audit"]["total_saved_objects"]=len(all_objects)
        payload["audit"]["objects_omitted"]=max(0,len(all_objects)-max_objects)
        for ob in all_objects[:max_objects]:
            page_id,object_id=ob["page_id"],ob["object_id"]
            rows=db.execute("""
                SELECT observed_at,counts_json,object_type,status,source
                FROM reaction_snapshots
                WHERE page_id=? AND object_id=?
                ORDER BY observed_at DESC,id DESC
                LIMIT ?
            """,(page_id,object_id,MAX_SAMPLES_PER_OBJECT+1)).fetchall()
            payload["audit"]["records_truncated"]+=max(
                0,int(ob["n"])-MAX_SAMPLES_PER_OBJECT)
            rows=list(reversed(rows[:MAX_SAMPLES_PER_OBJECT]))
            readings=[]
            for row in rows:
                at=parse_utc(row["observed_at"])
                if at is None or row["source"] not in ALLOWED_SOURCES or (
                    row["status"] not in ALLOWED_STATUSES
                ) or row["object_type"] not in ALLOWED_TYPES:
                    payload["audit"]["records_rejected"]+=1
                    continue
                try:
                    counts=json.loads(row["counts_json"])
                except (ValueError,TypeError):
                    payload["audit"]["records_rejected"]+=1
                    continue
                if not isinstance(counts,dict):
                    payload["audit"]["records_rejected"]+=1
                    continue
                # Preserve missing as null; reject negative/boolean/float, never coerce.
                values={}
                malformed=False
                for kind in REACTIONS:
                    value=counts.get(kind)
                    if value is not None and (type(value) is not int or value<0):
                        malformed=True
                        break
                    values[kind]=value
                if malformed:
                    payload["audit"]["records_rejected"]+=1
                    continue
                readings.append({"observed_at":at.isoformat(),"counts":values,
                                 "status":row["status"],"source":row["source"]})
            payload["objects"].append({
                "page_pseudonym":_pseudo(secret,"page",page_id),
                "object_pseudonym":_pseudo(secret,"object",page_id+"/"+object_id),
                "object_type":(readings and next(
                    (r["object_type"] for r in reversed(rows)
                     if r["object_type"] in ALLOWED_TYPES),"unknown")) or "unknown",
                "observations":readings,
                "quality":{kind:_compact_quality(
                    audit_series(readings,kind,now=now)) for kind in REACTIONS},
            })
    return _finish(payload)


def _compact_quality(data):
    return {k:data[k] for k in (
        "total_snapshots","valid_snapshots","missing_counts",
        "invalid_timestamps","long_gaps","negative_corrections",
        "longest_contiguous_intervals","eligible_adjacent_intervals",
        "ready_for_review","stale")}


def _finish(payload):
    checksum=hashlib.sha256(canonical(payload)).hexdigest()
    return {"payload":payload,"integrity":{
        "algorithm":"sha256","canonicalization":"utf8_sorted_keys_compact_json",
        "payload_sha256":checksum,
        "note":"Checksum verifies byte-equivalent payload integrity, not authenticity."}}


def verify_bundle(bundle):
    if not isinstance(bundle,dict) or set(bundle)!={"payload","integrity"}:
        return False
    integrity=bundle.get("integrity")
    if not isinstance(integrity,dict) or integrity.get("algorithm")!="sha256":
        return False
    digest=integrity.get("payload_sha256")
    if not isinstance(digest,str) or len(digest)!=64:
        return False
    try:
        return hmac.compare_digest(digest,hashlib.sha256(
            canonical(bundle["payload"])).hexdigest())
    except (ValueError,TypeError,OverflowError):
        return False
