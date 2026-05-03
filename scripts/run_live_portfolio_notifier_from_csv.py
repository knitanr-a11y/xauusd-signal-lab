from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GOLD_M15_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_m15.csv"
DEFAULT_GOLD_H1_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_h1.csv"
DEFAULT_BTC_M5_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m5.csv"
DEFAULT_BTC_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_BTC_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_BTC_H4_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h4.csv"
DEFAULT_HISTORY_CSV = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "live_payloads"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_GOLD_LEDGER_CSV = DEFAULT_OUT_DIR / "notified_gold_signals_ledger.csv"
DEFAULT_BTC_LEDGER_CSV = DEFAULT_OUT_DIR / "notified_btc_signals_ledger.csv"


@dataclass(frozen=True)
class ChildRunResult:
    name: str
    command: list[str]
    returncode: int


def path_arg(value: Path | str) -> str:
    return str(value)


def append_common_flags(cmd: list[str], args: argparse.Namespace) -> None:
    if args.enable_ai_review:
        cmd.append("--enable-ai-review")
    if args.ai_model:
        cmd.extend(["--ai-model", args.ai_model])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.mark_dry_run_notified:
        cmd.append("--mark-dry-run-notified")
    if args.send_discord:
        cmd.append("--send-discord")
    if args.discord_webhook_url:
        cmd.extend(["--discord-webhook-url", args.discord_webhook_url])
    if args.max_notifications is not None:
        cmd.extend(["--max-notifications", str(args.max_notifications)])


def build_gold_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_live_gold_notifier_from_csv.py"),
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
    append_common_flags(cmd, args)
    return cmd


def build_btc_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_live_btc_mtf_spread_filtered_notifier_from_csv.py"),
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
    append_common_flags(cmd, args)
    return cmd


def print_command(cmd: list[str]) -> None:
    print(" ".join(f'"{x}"' if " " in x else x for x in cmd))


def run_child(name: str, cmd: list[str], *, print_only: bool) -> ChildRunResult:
    print("\n" + "#" * 100)
    print(f"{name} notifier")
    print("#" * 100)
    print("Command:")
    print_command(cmd)
    if print_only:
        return ChildRunResult(name=name, command=cmd, returncode=0)
    completed = subprocess.run(cmd, cwd=PROJECT_ROOT)
    print(f"\n{name} return code:", completed.returncode)
    return ChildRunResult(name=name, command=cmd, returncode=completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run GOLD and BTC live CSV notifiers in one command. BTC always uses the spread-filtered notifier."
    )
    parser.add_argument("--gold-m15-csv", type=Path, default=DEFAULT_GOLD_M15_CSV)
    parser.add_argument("--gold-h1-csv", type=Path, default=DEFAULT_GOLD_H1_CSV)
    parser.add_argument("--btc-m5-csv", type=Path, default=DEFAULT_BTC_M5_CSV)
    parser.add_argument("--btc-m15-csv", type=Path, default=DEFAULT_BTC_M15_CSV)
    parser.add_argument("--btc-h1-csv", type=Path, default=DEFAULT_BTC_H1_CSV)
    parser.add_argument("--btc-h4-csv", type=Path, default=DEFAULT_BTC_H4_CSV)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--gold-ledger-csv", type=Path, default=DEFAULT_GOLD_LEDGER_CSV)
    parser.add_argument("--btc-ledger-csv", type=Path, default=DEFAULT_BTC_LEDGER_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)

    parser.add_argument("--gold-scan-recent-bars", type=int, default=60)
    parser.add_argument("--gold-include-excluded", action="store_true", help="Debug only: include GOLD excluded labels.")
    parser.add_argument("--btc-scan-recent-m5-bars", type=int, default=60)
    parser.add_argument("--btc-scan-recent-m15-bars", type=int, default=20)
    parser.add_argument("--bar-offset", type=int, default=1)

    parser.add_argument("--btc-exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--btc-spread-mode", choices=["csv_mode", "fixed"], default="csv_mode")
    parser.add_argument("--btc-spread-source", choices=["m5", "m15"], default="m5")
    parser.add_argument("--btc-fixed-spread-price", type=float, default=None)
    parser.add_argument("--btc-point-size", type=float, default=0.01)
    parser.add_argument("--btc-spread-round-digits", type=int, default=2)
    parser.add_argument("--btc-include-zero-spread-in-mode", action="store_true")
    parser.add_argument("--btc-pip-size", type=float, default=10.0)
    parser.add_argument("--btc-min-net-tp-pips", type=float, default=5.0)
    parser.add_argument("--btc-max-spread-to-sl-ratio", type=float, default=0.50)
    parser.add_argument("--btc-min-effective-rr", type=float, default=1.0)

    parser.add_argument("--enable-ai-review", action="store_true")
    parser.add_argument("--ai-model", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mark-dry-run-notified", action="store_true")
    parser.add_argument("--send-discord", action="store_true")
    parser.add_argument("--discord-webhook-url", default=None)
    parser.add_argument("--max-notifications", type=int, default=5)

    parser.add_argument("--skip-gold", action="store_true")
    parser.add_argument("--skip-btc", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--print-only", action="store_true", help="Print child commands without running them.")
    args = parser.parse_args()

    if args.skip_gold and args.skip_btc:
        raise ValueError("Both --skip-gold and --skip-btc were specified. Nothing to run.")

    print("Project root:", PROJECT_ROOT)
    print("Portfolio notifier dry_run:", bool(args.dry_run))
    print("Portfolio notifier send_discord:", bool(args.send_discord))
    print("BTC notifier: spread-filtered only")

    results: list[ChildRunResult] = []
    if not args.skip_gold:
        result = run_child("GOLD", build_gold_command(args), print_only=bool(args.print_only))
        results.append(result)
        if args.stop_on_error and result.returncode != 0:
            print("Stopping because GOLD failed and --stop-on-error is set.")
            return result.returncode

    if not args.skip_btc:
        result = run_child("BTC", build_btc_command(args), print_only=bool(args.print_only))
        results.append(result)
        if args.stop_on_error and result.returncode != 0:
            print("Stopping because BTC failed and --stop-on-error is set.")
            return result.returncode

    print("\n" + "#" * 100)
    print("Portfolio notifier summary")
    print("#" * 100)
    for result in results:
        status = "OK" if result.returncode == 0 else "FAILED"
        print(f"{result.name}: {status} returncode={result.returncode}")

    failed = [result for result in results if result.returncode != 0]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
