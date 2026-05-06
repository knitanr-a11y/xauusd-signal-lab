#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight Mochipoyo live notification loop.

This is the always-on loop wrapper.

It does NOT full-scan every interval.
Instead it:
1. Reads only the latest timestamp from trigger CSVs.
2. Compares with a state JSON.
3. Skips all heavy work if there is no new confirmed trigger bar.
4. Runs the existing strict scanner + risk enrichment + Discord sender only when needed.

This is the first lightweight stage. The strict scanner still performs the
validated full scan when triggered. A later stage can add tail-row scanning.

Safety:
- No AI review.
- No order placement.
- Discord sending requires --send.
- Duplicate Discord sending is handled by send ledger payload_key.
- Webhook URL is read from --webhook-url, environment variable, or .env.

.env example:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_JSON = "data/results/mochipoyo/live_dryrun/mochipoyo_live_notify_loop_light_state.json"
DEFAULT_LEDGER = "data/results/mochipoyo/live_dryrun/mochipoyo_live_dryrun_strict_ledger.csv"
DEFAULT_SEND_LEDGER = "data/results/mochipoyo/live_dryrun/mochipoyo_discord_send_ledger.csv"

GOLD_STRICT_PAYLOAD = "data/results/mochipoyo/live_dryrun/gold_mochipoyo_live_dryrun_strict_payloads.csv"
GOLD_ENRICHED_PAYLOAD = "data/results/mochipoyo/live_dryrun/gold_mochipoyo_live_dryrun_strict_payloads_enriched.csv"
BTC_STRICT_PAYLOAD = "data/results/mochipoyo/live_dryrun/btc_mochipoyo_live_dryrun_strict_payloads.csv"


# -----------------------------------------------------------------------------
# Basic utilities
# -----------------------------------------------------------------------------

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


def safe_print(text: object = "") -> None:
    s = str(text)
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(s.encode(enc, errors="backslashreplace").decode(enc, errors="replace"), flush=True)


def run_cmd(cmd: list[str], *, cwd: Path, stop_on_error: bool = True) -> int:
    safe_print("CMD: " + quote_cmd(cmd))
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
        safe_print(proc.stdout.rstrip())
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
    if stop_on_error and proc.returncode != 0:
        raise RuntimeError(f"Command failed returncode={proc.returncode}: {quote_cmd(cmd)}")
    return int(proc.returncode)


def split_symbols(text: str) -> list[str]:
    out: list[str] = []
    for raw in str(text).split(","):
        s = raw.strip().upper()
        if s in {"GOLD", "BTC"} and s not in out:
            out.append(s)
    if not out:
        raise RuntimeError("No valid symbols. Use --symbols GOLD,BTC")
    return out


def sniff_sep_from_text(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def latest_csv_time(path: str | Path) -> str | None:
    """Read only the tail of a CSV and return the last parseable time.

    MT5 export files are time-ascending. This function avoids loading the whole
    file each loop.
    """
    p = Path(path)
    if not p.exists():
        return None
    # Read tail bytes. Handles very long CSVs cheaply.
    size = p.stat().st_size
    read_size = min(size, 65536)
    with p.open("rb") as f:
        f.seek(max(0, size - read_size))
        raw = f.read().decode("utf-8-sig", errors="replace")
    lines = [x for x in raw.splitlines() if x.strip()]
    if not lines:
        return None
    # If we started mid-line, the first line may be partial. Ignore it unless file is tiny.
    if size > read_size and len(lines) > 1:
        lines = lines[1:]
    if not lines:
        return None
    header_sample = ""
    try:
        with p.open("r", encoding="utf-8-sig", errors="replace") as f:
            header_sample = f.readline()
    except Exception:
        header_sample = lines[0]
    sep = sniff_sep_from_text(header_sample + "\n" + "\n".join(lines[-5:]))
    header = [h.strip().lower() for h in header_sample.strip().split(sep)]
    time_idx = 0
    if "time" in header:
        time_idx = header.index("time")
    elif "datetime" in header:
        time_idx = header.index("datetime")
    elif "timestamp" in header:
        time_idx = header.index("timestamp")
    for line in reversed(lines):
        parts = line.split(sep)
        if len(parts) <= time_idx:
            continue
        raw_time = parts[time_idx].strip().strip('"')
        if raw_time.lower() in {"time", "datetime", "timestamp"}:
            continue
        t = pd.to_datetime(raw_time, errors="coerce")
        if pd.notna(t):
            return t.strftime("%Y-%m-%d %H:%M:%S")
    return None


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"symbols": {}, "cycles": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"symbols": {}, "cycles": []}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Trigger detection
# -----------------------------------------------------------------------------

def trigger_files_for_symbol(args: argparse.Namespace, symbol: str) -> dict[str, str]:
    """Return trigger timeframe CSVs.

    We intentionally use M15 and H1 as the first lightweight gate because:
    - GOLD notification universe includes M5/M15/H1 base pairs, but scanning every
      M1/M5 update is too heavy.
    - BTC validated universe is H4 -> M15, so M15 is the key trigger.
    - H1 catches D1 -> H1 and slower context/base updates.
    """
    if symbol == "GOLD":
        return {"M15": args.gold_m15_csv, "H1": args.gold_h1_csv}
    if symbol == "BTC":
        return {"M15": args.btc_m15_csv, "H1": args.btc_h1_csv}
    raise RuntimeError(f"unknown symbol: {symbol}")


def current_trigger_signature(args: argparse.Namespace, symbol: str) -> dict[str, str | None]:
    files = trigger_files_for_symbol(args, symbol)
    return {tf: latest_csv_time(path) for tf, path in files.items()}


def should_run_symbol(args: argparse.Namespace, state: dict[str, Any], symbol: str) -> tuple[bool, dict[str, Any]]:
    sig = current_trigger_signature(args, symbol)
    sym_state = state.setdefault("symbols", {}).setdefault(symbol, {})
    prev_sig = sym_state.get("last_trigger_signature")
    reason = "changed"
    should = sig != prev_sig
    if args.force_scan:
        should = True
        reason = "force_scan"
    elif prev_sig is None:
        should = True
        reason = "first_run"
    elif not should:
        reason = "no_change"
    info = {"symbol": symbol, "should_run": should, "reason": reason, "signature": sig, "previous_signature": prev_sig}
    return should, info


def mark_symbol_processed(state: dict[str, Any], symbol: str, signature: dict[str, str | None], status: str) -> None:
    sym_state = state.setdefault("symbols", {}).setdefault(symbol, {})
    sym_state["last_trigger_signature"] = signature
    sym_state["last_status"] = status
    sym_state["last_processed_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z")


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------

def strict_scan_cmd(args: argparse.Namespace, symbol: str) -> list[str]:
    cmd = [
        args.python,
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
        "--preview-txt", f"data/results/mochipoyo/live_dryrun/{symbol.lower()}_discord_light_preview.txt",
        "--preview-json", f"data/results/mochipoyo/live_dryrun/{symbol.lower()}_discord_light_preview.json",
        "--webhook-env", args.webhook_env,
    ]
    if args.webhook_url:
        cmd += ["--webhook-url", args.webhook_url]
    if args.send:
        cmd += ["--send"]
    return cmd


def run_heavy_for_symbol(args: argparse.Namespace, symbol: str) -> None:
    safe_print("-" * 88)
    safe_print(f"RUN HEAVY SCAN {symbol}")
    run_cmd(strict_scan_cmd(args, symbol), cwd=ROOT, stop_on_error=not args.continue_on_error)
    if symbol == "GOLD":
        safe_print("ENRICH GOLD")
        run_cmd(enrich_gold_cmd(args), cwd=ROOT, stop_on_error=not args.continue_on_error)
        input_csv = GOLD_ENRICHED_PAYLOAD
    else:
        input_csv = BTC_STRICT_PAYLOAD
    safe_print(f"SEND/PREVIEW {symbol}")
    run_cmd(send_cmd(args, symbol, input_csv), cwd=ROOT, stop_on_error=not args.continue_on_error)


# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

def run_cycle(args: argparse.Namespace, symbols: list[str], cycle_no: int, state: dict[str, Any]) -> dict[str, Any]:
    safe_print("=" * 88)
    safe_print(f"MOCHIPOYO LIGHT NOTIFY LOOP CYCLE {cycle_no}")
    safe_print(f"send_enabled: {args.send}")
    safe_print(f"symbols: {symbols}")
    cycle = {
        "cycle_no": cycle_no,
        "started_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z"),
        "symbols": [],
    }
    for symbol in symbols:
        should, info = should_run_symbol(args, state, symbol)
        safe_print("-" * 88)
        safe_print(f"CHECK {symbol}: {info['reason']}")
        safe_print(f"signature: {info['signature']}")
        if not should:
            safe_print(f"SKIP {symbol}: trigger CSVs unchanged")
            cycle["symbols"].append(info)
            continue
        status = "OK"
        try:
            run_heavy_for_symbol(args, symbol)
        except Exception as e:
            status = f"ERROR: {e!r}"
            info["error"] = status
            safe_print(status)
            if not args.continue_on_error:
                raise
        mark_symbol_processed(state, symbol, info["signature"], status)
        info["status"] = status
        cycle["symbols"].append(info)
    cycle["finished_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z")
    state.setdefault("cycles", []).append(cycle)
    # Keep state compact.
    state["cycles"] = state["cycles"][-50:]
    return cycle


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run lightweight Mochipoyo live notification loop with update gating.")
    p.add_argument("--symbols", default="GOLD,BTC")
    p.add_argument("--interval-seconds", type=int, default=60)
    p.add_argument("--once", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--force-scan", action="store_true", help="Run heavy scan even if trigger timestamps did not change.")
    p.add_argument("--max-send-rows", type=int, default=5)
    p.add_argument("--scan-recent-events", type=int, default=20)
    p.add_argument("--state-json", default=DEFAULT_STATE_JSON)
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
    load_dotenv(ROOT / args.dotenv)
    symbols = split_symbols(args.symbols)
    state_path = ROOT / args.state_json
    state = load_state(state_path)

    if args.send and not (args.webhook_url or os.environ.get(args.webhook_env)):
        safe_print(f"ERROR: --send was specified, but webhook was not found. Set {args.webhook_env} in .env or pass --webhook-url.")
        return 2

    cycle_no = int(state.get("last_cycle_no", 0)) + 1
    while True:
        try:
            run_cycle(args, symbols, cycle_no, state)
            state["last_cycle_no"] = cycle_no
            save_state(state_path, state)
        except KeyboardInterrupt:
            safe_print("Interrupted by user.")
            save_state(state_path, state)
            return 130
        except Exception as e:
            safe_print(f"LOOP ERROR: {e!r}")
            save_state(state_path, state)
            if not args.continue_on_error:
                return 1
        if args.once:
            break
        cycle_no += 1
        safe_print(f"sleep {args.interval_seconds} seconds...")
        time.sleep(args.interval_seconds)

    safe_print(f"state_json: {state_path}")
    safe_print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
