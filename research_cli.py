"""Safe offline R0 commands. No token required and no raw reactor identities."""
from __future__ import annotations
import argparse
import json
import os
from contextlib import closing
from collections import Counter
from pathlib import Path

import reaction_history
from reaction_collector import REACTIONS
from research_quality import audit_series
from research_validation import evaluate
from research_replay import replay
from research_readiness import readiness
from research_bundle import build_bundle, verify_bundle


def audit_local(path=None):
    """Summarize local observations without emitting Page, post or actor IDs."""
    db_path = path or reaction_history.DEFAULT_DB
    # Do not create/modify the user's DB during a read-only audit.
    if not Path(db_path).exists():
        return {"status":"no_database","snapshots":0,"objects":0,
                "watches":0,"active_watches":0,"types":{}}
    with closing(reaction_history.connection(db_path)) as db:
        row=db.execute("SELECT count(*) AS n FROM reaction_snapshots").fetchone()
        grouped=db.execute(
            "SELECT page_id,object_id,count(*) AS n FROM reaction_snapshots "
            "GROUP BY page_id,object_id ORDER BY page_id,object_id LIMIT 1000").fetchall()
        watchers=db.execute("SELECT active FROM reaction_watches").fetchall()
    by_type={}
    for kind in REACTIONS:
        measures=Counter()
        for group in grouped:
            history=reaction_history.history(group["page_id"],group["object_id"],
                                              limit=500,path=db_path)
            q=audit_series(history,kind)
            measures["objects_with_counts"]+=int(q["valid_snapshots"]>0)
            measures["valid_observations"]+=q["valid_snapshots"]
            measures["eligible_intervals"]+=q["eligible_adjacent_intervals"]
            measures["long_gaps"]+=q["long_gaps"]
            measures["missing_values"]+=q["missing_counts"]
            measures["objects_ready_for_review"]+=int(q["ready_for_review"])
        by_type[kind]=dict(measures)
    return {"status":"measured_aggregates_only","snapshots":row["n"],
            "objects":len(grouped),"object_listing_truncated":len(grouped)==1000,
            "watches":len(watchers),
            "active_watches":sum(int(x["active"]) for x in watchers),
            "types":by_type,"actor_level_labels":0,"bot_probability_validated":False}


def main(argv=None):
    p=argparse.ArgumentParser(description="VOIDSCAN R0 reproducible evidence audit")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("audit",help="Read-only aggregate quality audit")
    a.add_argument("--db",help="Local SQLite file; default VOIDSCAN DB")
    ev=sub.add_parser("evaluate",help="Held-out research evaluation using external labels")
    ev.add_argument("--input",required=True,help="JSON document of independently reviewed events")
    rep=sub.add_parser("replay",help="Recompute frozen R1 flags from independent event snapshots")
    rep.add_argument("--input",required=True,help="JSON reviewed event histories, outside Git")
    live=sub.add_parser("readiness",help="Read-only local monitoring diagnostics, no Meta token needed")
    live.add_argument("--db",help="Local SQLite file; default VOIDSCAN DB")
    exp=sub.add_parser("bundle",help="Create privacy-preserving aggregate research bundle explicitly")
    exp.add_argument("--output",required=True,help="New JSON path; refuses overwrite")
    exp.add_argument("--db",help="Source local SQLite; default VOIDSCAN DB")
    verify=sub.add_parser("verify-bundle",help="Verify research bundle checksum (not provenance)")
    verify.add_argument("--input",required=True,help="Previously exported JSON research bundle")
    args=p.parse_args(argv)
    try:
        if args.cmd=="audit":
            result=audit_local(args.db)
        elif args.cmd=="readiness":
            result=readiness(args.db or reaction_history.DEFAULT_DB)
        elif args.cmd=="bundle":
            output=Path(args.output).resolve()
            root=Path(__file__).resolve().parent
            # Prevent accidental commit of an export to a tracked project directory.
            if output.is_relative_to(root) and not output.is_relative_to(root/"data"):
                raise ValueError("Research bundles must be outside the tracked repository")
            if not output.parent.is_dir():
                raise ValueError("Output directory does not exist")
            bundle=build_bundle(args.db or reaction_history.DEFAULT_DB)
            data=json.dumps(bundle,ensure_ascii=False,indent=2).encode("utf-8")
            fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            try:
                with os.fdopen(fd,"wb") as target:
                    target.write(data)
            except BaseException:
                output.unlink(missing_ok=True)
                raise
            result={"status":"saved","objects":len(bundle["payload"]["objects"]),
                    "snapshots":sum(len(x["observations"]) for x in bundle["payload"]["objects"]),
                    "sha256":bundle["integrity"]["payload_sha256"],
                    "note":"Local-only research data; not proof of bot accounts."}
        elif args.cmd=="verify-bundle":
            source=Path(args.input)
            if source.stat().st_size > 20000000:
                raise ValueError("Bundle too large")
            checked=verify_bundle(json.loads(source.read_text(encoding="utf-8")))
            result={"valid_payload_checksum":checked,
                    "source_authenticity_verified":False}
            print(json.dumps(result,ensure_ascii=True,indent=2))
            return 0 if checked else 2
        else:
            path=Path(args.input)
            if path.stat().st_size > 4_000_000:
                raise ValueError("Label file too large")
            document=json.loads(path.read_text(encoding="utf-8"))
            result=replay(document) if args.cmd=="replay" else evaluate(document)
        print(json.dumps(result,ensure_ascii=True,indent=2,sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        # Only emit the exception class; user-supplied content may contain secrets.
        print(json.dumps({"status":"error","kind":type(exc).__name__}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
