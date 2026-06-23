from __future__ import annotations

import argparse
import json

from .bootstrap import bootstrap_from_selected_ledger
from .config import load_config
from .engine import SafePortfolioEngine
from .io import read_candidates, read_resolutions
from .state import SQLiteStateStore
from .timeutil import parse_dt
from .watcher import process_inbox_once, watch_forever


def components(args):
    cfg = load_config(args.config)
    store = SQLiteStateStore(args.db, cfg.time_basis)
    return store, SafePortfolioEngine(cfg, store)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--db", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    p = sub.add_parser("ingest"); p.add_argument("--candidates", required=True)
    p = sub.add_parser("resolve"); p.add_argument("--resolutions", required=True)
    sub.add_parser("status")
    p = sub.add_parser("bootstrap")
    p.add_argument("--ledger", required=True)
    p.add_argument("--portfolio", default="PLUS_STRICT_SAFE")
    p.add_argument("--start-dt")
    p.add_argument("--through-dt")
    p = sub.add_parser("watch")
    p.add_argument("--inbox", required=True)
    p.add_argument("--archive", required=True)
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    store, engine = components(args)

    if args.command in {"init", "status"}:
        result = store.snapshot()
    elif args.command == "ingest":
        result = [{"candidate_id": d.candidate_id, "status": d.status.value,
                   "reason": d.reason, "dd_before_entry": d.dd_before_entry,
                   "diagnostics": d.diagnostics}
                  for d in engine.process_batch(read_candidates(args.candidates))]
    elif args.command == "resolve":
        rows = read_resolutions(args.resolutions)
        for row in rows:
            store.add_resolution(row)
        result = {"stored": len(rows)}
    elif args.command == "bootstrap":
        result = bootstrap_from_selected_ledger(
            store, args.ledger, portfolio=args.portfolio,
            start_dt=parse_dt(args.start_dt) if args.start_dt else None,
            through_dt=parse_dt(args.through_dt) if args.through_dt else None)
    elif args.once:
        result = process_inbox_once(engine, store, args.inbox, args.archive).__dict__
    else:
        watch_forever(engine, store, args.inbox, args.archive, args.poll_seconds)
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
