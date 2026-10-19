"""Safe offline R0 commands. No token required and no raw reactor identities."""
from __future__ import annotations
import argparse
import json
from contextlib import closing
from collections import Counter
from pathlib import Path

import reaction_history
from reaction_collector import REACTIONS
from research_quality import audit_series
from research_validation import evaluate


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
    args=p.parse_args(argv)
    try:
        if args.cmd=="audit":
            result=audit_local(args.db)
        else:
            path=Path(args.input)
            if path.stat().st_size > 4_000_000:
                raise ValueError("Label file too large")
            result=evaluate(json.loads(path.read_text(encoding="utf-8")))
        print(json.dumps(result,ensure_ascii=True,indent=2,sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        # Only emit the exception class; user-supplied content may contain secrets.
        print(json.dumps({"status":"error","kind":type(exc).__name__}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
