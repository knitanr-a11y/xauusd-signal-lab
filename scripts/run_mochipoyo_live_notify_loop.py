#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run Mochipoyo live notification loop.

This is the integrated loop:
1. Run strict dry-run scanner for GOLD/BTC.
2. Enrich GOLD payload with SL/TP/risk fields.
3. Send compact Discord messages for new payload_key only.
4. Repeat every interval.

Safety:
- No AI review.
- No order placement.
- Discord sending requires --send.
- Duplicate Discord sending is prevented by send ledger payload_key.
- Webhook URL is read from --webhook-url, environment variable, or .env.

.env example:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = "data/results/mochipoyo/live_dryrun/mochipoyo_live_dryrun_strict_ledger.csv"
DEFAULT_SEND_LEDGER = "data/results/mochipoyo/live_dryrun/mochipoyo_discord_send_ledger.csv"

GOLD_STRICT_PAYLOAD = "data/results/mochipoyo/live_dryrun/gold_mochipoyo_live_dryrun_strict_payloads.csv"
GOLD_ENRICHED_PAYLOAD = "data/results/mochipoyo/live_dryrun/gold_mochipoyo_live_dryrun_strict_payloads_enriched.csv"
BTC_STRICT_PAYLOAD = "data/results/mochipoyo/live_dryrun/btc_mochipoyo_live_dryrun_strict_payloads.csv"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def quote_cmd(cmd: Iterable[str]) -> str:
    return " ".join(shlex.quote(str(x)) for x in cmd)


def run_cmd(cmd: list[str], *, cwd: Path, stop_on_error: bool = True) -> int:
    print("CMD:", quote_cmd(cmd), flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        print(proc.stdout, flush=True)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, flush=True)
    if stop_on_error and proc.returncode != 0:
        raise RuntimeError(f"Command failed returncode={proc.returncode}: {quote_cmd(cmd)}")
    return int(proc.returncode)


def split_symbols(text: str) -> list[str]:
    out = []
    for s in str(text).split(","):
        s = s.strip().upper()
        if s in {"GOLD", "BTC"} and s not in out:
            out.append(s)
    if not out:
        raise RuntimeError("No valid symbols. Use --symbols GOLD,BTC")
    return out


def strict_scan_cmd(args: argparse.Namespace, symbol: str) -> list[str]:
    py = args.python
    cmd = [
        py,
        "scripts/run_mochipoyo_live_dryrun_strict.py",
        "--symbols", symbol,
        "--scan-recent-events", str(args.scan_recent_events),
        "--ledger-csv", args.ledger_csv,
    ]
    if symbol == "GOLD":
        cmd += [
            "--gold-m1-csv", args.gold_m1_csv,
            "--gold-m5-csv", args.gold_m5_csv,
            "--gold-m15-csv", args.gold_m15_csv,
            "--gold-h1-csv", args.gold_h1_csv,
            "--gold-h4-csv", args.gold_h4_csv,
            "--gold-d1-csv", args.gold_d1_csv,
        ]
    elif symbol == "BTC":
        cmd += [
            "--btc-m1-csv", args.btc_m1_csv,
            "--btc-m5-csv", args.btc_m5_csv,
            "--btc-m15-csv", args.btc_m15_csv,
            "--btc-h1-csv", args.btc_h1_csv,
            "--btc-h4-csv", args.btc_h4_csv,
            "--btc-d1-csv", args.btc_d1_csv,
            "--btc-rr", str(args.btc_rr),
            "--btc-point-size", str(args.btc_point_size),
            "--btc-min-stop-distance", str(args.btc_min_stop_distance),
        ]
        if args.btc_spread_points > 0:
            cmd += ["--btc-spread-points", str(args.btc_spread_points)]
    return cmd


def enrich_gold_cmd(args: argparse.Namespace) -> list[str]:
    return [
        args.python,
        "scripts/enrich_mochipoyo_live_payload_risk.py",
        "--symbol", "GOLD",
        "--input-csv", GOLD_STRICT_PAYLOAD,
        "--output-csv", GOLD_ENRICHED_PAYLOAD,
        "--m1-csv", args.gold_m1_csv,
        "--m5-csv", args.gold_m5_csv,
        "--rr", str(args.gold_rr),
        "--min-stop-distance", str(args.gold_min_stop_distance),
    ]


def send_cmd(args: argparse.Namespace, symbol: str, input_csv: str) -> list[str]:
    cmd = [
        args.python,
        "scripts/send_mochipoyo_discord_messages.py",
        "--input-csv", input_csv,
        "--symbol", symbol,
        "--max-rows", str(args.max_send_rows),
        "--style", "compact",
        "--send-ledger-csv", args.send_ledger_csv,
        "--preview-txt", f"data/results/mochipoyo/live_dryrun/{symbol.lower()}_discord_loop_preview.txt",
        "--preview-json", f"data/results/mochipoyo/live_dryrun/{symbol.lower()}_discord_loop_preview.json",
        "--webhook-env", args.webhook_env,
    ]
    if args.webhook_url:
        cmd += ["--webhook-url", args.webhook_url]
    if args.send:
        cmd += ["--send"]
    return cmd


def run_one_cycle(args: argparse.Namespace, symbols: list[str], cycle_no: int) -> None:
    print("=" * 88, flush=True)
    print(f"MOCHIPOYO NOTIFY LOOP CYCLE {cycle_no}", flush=True)
    print(f"send_enabled: {args.send}", flush=True)
    print(f"symbols: {symbols}", flush=True)

    for symbol in symbols:
        print("-" * 88, flush=True)
        print(f"SCAN {symbol}", flush=True)
        run_cmd(strict_scan_cmd(args, symbol), cwd=DEFAULT_ROOT, stop_on_error=not args.continue_on_error)

        if symbol == "GOLD":
            print(f"ENRICH {symbol}", flush=True)
            run_cmd(enrich_gold_cmd(args), cwd=DEFAULT_ROOT, stop_on_error=not args.continue_on_error)
            input_csv = GOLD_ENRICHED_PAYLOAD
        else:
            input_csv = BTC_STRICT_PAYLOAD

        print(f"SEND/PREVIEW {symbol}", flush=True)
        run_cmd(send_cmd(args, symbol, input_csv), cwd=DEFAULT_ROOT, stop_on_error=not args.continue_on_error)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Mochipoyo live notification loop.")
    p.add_argument("--symbols", default="GOLD,BTC")
    p.add_argument("--interval-seconds", type=int, default=300)
    p.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    p.add_argument("--send", action="store_true", help="Actually send Discord messages. Without this, preview only.")
    p.add_argument("--max-send-rows", type=int, default=5, help="Check/send latest N payload rows per symbol per cycle. Duplicates are skipped by send ledger.")
    p.add_argument("--scan-recent-events", type=int, default=20)
    p.add_argument("--ledger-csv", default=DEFAULT_LEDGER)
    p.add_argument("--send-ledger-csv", default=DEFAULT_SEND_LEDGER)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--dotenv", default=".env")
    p.add_argument("--webhook-env", default="DISCORD_WEBHOOK_URL")
    p.add_argument("--webhook-url", default=None)
    p.add_argument("--continue-on-error", action="store_true")

    p.add_argument("--gold-rr", type=float, default=1.2)
    p.add_argument("--gold-min-stop-distance", type=float, default=1.0)
    p.add_argument("--gold-m1-csv", required=True)
    p.add_argument("--gold-m5-csv", required=True)
    p.add_argument("--gold-m15-csv", required=True)
    p.add_argument("--gold-h1-csv", required=True)
    p.add_argument("--gold-h4-csv", required=True)
    p.add_argument("--gold-d1-csv", required=True)

    p.add_argument("--btc-rr", type=float, default=1.2)
    p.add_argument("--btc-point-size", type=float, default=0.01)
    p.add_argument("--btc-spread-points", type=float, default=0.0)
    p.add_argument("--btc-min-stop-distance", type=float, default=50.0)
    p.add_argument("--btc-m1-csv", required=True)
    p.add_argument("--btc-m5-csv", required=True)
    p.add_argument("--btc-m15-csv", required=True)
    p.add_argument("--btc-h1-csv", required=True)
    p.add_argument("--btc-h4-csv", required=True)
    p.add_argument("--btc-d1-csv", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(DEFAULT_ROOT / args.dotenv)
    symbols = split_symbols(args.symbols)

    if args.send and not (args.webhook_url or os.environ.get(args.webhook_env)):
        print(f"ERROR: --send was specified, but webhook was not found. Set {args.webhook_env} in .env or pass --webhook-url.", file=sys.stderr)
        return 2

    cycle_no = 1
    while True:
        try:
            run_one_cycle(args, symbols, cycle_no)
        except KeyboardInterrupt:
            print("Interrupted by user.")
            return 130
        except Exception as e:
            print(f"LOOP ERROR: {e!r}", file=sys.stderr, flush=True)
            if not args.continue_on_error:
                return 1
        if args.once:
            break
        cycle_no += 1
        print(f"sleep {args.interval_seconds} seconds...", flush=True)
        time.sleep(args.interval_seconds)

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
