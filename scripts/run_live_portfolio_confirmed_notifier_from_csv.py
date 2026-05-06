from __future__ import annotations

import argparse
import sys
from pathlib import Path

import run_live_portfolio_notifier_from_csv as portfolio


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def path_arg(value: Path | str) -> str:
    return str(value)


def build_gold_confirmed_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_live_gold_notifier_confirmed_from_csv.py"),
        "--m15-csv",
        path_arg(args.gold_m15_csv),
        "--h1-csv",
        path_arg(args.gold_h1_csv),
        "--history-csv",
        path_arg(args.history_csv),
        "--ledger-csv",
        path_arg(args.gold_ledger_csv),
        "--out-dir",
        path_arg(args.out_dir),
        "--env-file",
        path_arg(args.env_file),
        "--scan-recent-bars",
        str(args.gold_scan_recent_bars),
        "--bar-offset",
        str(args.bar_offset),
    ]
    if args.gold_include_excluded:
        cmd.append("--include-excluded")
    portfolio.append_common_flags(cmd, args)
    return cmd


def build_btc_confirmed_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_live_btc_mtf_spread_filtered_confirmed_notifier_from_csv.py"),
        "--m5-csv",
        path_arg(args.btc_m5_csv),
        "--m15-csv",
        path_arg(args.btc_m15_csv),
        "--h1-csv",
        path_arg(args.btc_h1_csv),
        "--h4-csv",
        path_arg(args.btc_h4_csv),
        "--history-csv",
        path_arg(args.history_csv),
        "--ledger-csv",
        path_arg(args.btc_ledger_csv),
        "--out-dir",
        path_arg(args.out_dir),
        "--env-file",
        path_arg(args.env_file),
        "--scan-recent-m5-bars",
        str(args.btc_scan_recent_m5_bars),
        "--scan-recent-m15-bars",
        str(args.btc_scan_recent_m15_bars),
        "--bar-offset",
        str(args.bar_offset),
        "--exclude-entry-hours",
        args.btc_exclude_entry_hours,
        "--spread-mode",
        args.btc_spread_mode,
        "--spread-source",
        args.btc_spread_source,
        "--point-size",
        str(args.btc_point_size),
        "--spread-round-digits",
        str(args.btc_spread_round_digits),
        "--btc-pip-size",
        str(args.btc_pip_size),
        "--min-net-tp-pips",
        str(args.btc_min_net_tp_pips),
        "--max-spread-to-sl-ratio",
        str(args.btc_max_spread_to_sl_ratio),
        "--min-effective-rr",
        str(args.btc_min_effective_rr),
    ]
    if args.btc_fixed_spread_price is not None:
        cmd.extend(["--fixed-spread-price", str(args.btc_fixed_spread_price)])
    if args.btc_include_zero_spread_in_mode:
        cmd.append("--include-zero-spread-in-mode")
    portfolio.append_common_flags(cmd, args)
    return cmd


def main() -> int:
    portfolio.build_gold_command = build_gold_confirmed_command
    portfolio.build_btc_command = build_btc_confirmed_command
    print("Confirmed-time portfolio wrapper enabled.")
    print("GOLD: M15 uses only H1 candles closed by the M15 close time.")
    print("BTC : M5/M15 uses only context candles closed by the signal candle close time.")
    return portfolio.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting confirmed portfolio notifier.")
        raise SystemExit(130)
