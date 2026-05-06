from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
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
DEFAULT_RUNTIME_LOG_DIR = DEFAULT_OUT_DIR / "runtime_logs"


@dataclass(frozen=True)
class ChildRunResult:
    name: str
    command: list[str]
    returncode: int
    started_at: datetime
    finished_at: datetime
    stdout: str = ""
    stderr: str = ""

    @property
    def duration_sec(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


def path_arg(value: Path | str) -> str:
    return str(value)


def now_local() -> datetime:
    return datetime.now()


def dt_text(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


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


def run_child(name: str, cmd: list[str], *, print_only: bool, capture_child_output: bool) -> ChildRunResult:
    print("\n" + "#" * 100)
    print(f"{name} notifier")
    print("#" * 100)
    print("Command:")
    print_command(cmd)

    started_at = now_local()
    if print_only:
        finished_at = now_local()
        return ChildRunResult(name=name, command=cmd, returncode=0, started_at=started_at, finished_at=finished_at)

    try:
        if capture_child_output:
            completed = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            if stdout:
                print(stdout, end="" if stdout.endswith("\n") else "\n")
            if stderr:
                print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
        else:
            completed = subprocess.run(cmd, cwd=PROJECT_ROOT)
            stdout = ""
            stderr = ""
    except KeyboardInterrupt:
        finished_at = now_local()
        print(f"\nInterrupted by user while running {name} notifier.")
        return ChildRunResult(name=name, command=cmd, returncode=130, started_at=started_at, finished_at=finished_at)

    finished_at = now_local()
    print(f"\n{name} return code:", completed.returncode)
    return ChildRunResult(
        name=name,
        command=cmd,
        returncode=completed.returncode,
        started_at=started_at,
        finished_at=finished_at,
        stdout=stdout,
        stderr=stderr,
    )


def parse_int_metric(text: str, label: str) -> int | str:
    pattern = re.compile(rf"^{re.escape(label)}:\s*(-?\d+)\s*$", re.MULTILINE)
    match = pattern.search(text)
    return int(match.group(1)) if match else ""


def parse_bool_metric(text: str, label: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}:\s*(True|False|true|false)\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1) if match else ""


def summarize_child_for_log(result: ChildRunResult) -> dict[str, int | float | str]:
    text = (result.stdout or "") + "\n" + (result.stderr or "")
    prefix = result.name.lower()
    summary: dict[str, int | float | str] = {
        f"{prefix}_returncode": result.returncode,
        f"{prefix}_duration_sec": round(result.duration_sec, 3),
    }

    if result.name.upper() == "GOLD":
        summary.update(
            {
                "gold_unnotified_selected": parse_int_metric(text, "Unnotified signals selected"),
                "gold_rejected_excluded": parse_int_metric(text, "Rejected excluded signals"),
                "gold_ledger_rows_appended": parse_int_metric(text, "Ledger rows appended"),
                "gold_ai_review_enabled": parse_bool_metric(text, "AI review enabled"),
                "gold_send_discord": parse_bool_metric(text, "Send Discord"),
            }
        )
    elif result.name.upper() == "BTC":
        summary.update(
            {
                "btc_raw_unnotified": parse_int_metric(text, "Raw unnotified signals"),
                "btc_rejected_spread_value": parse_int_metric(text, "Rejected by spread/value filters"),
                "btc_unnotified_selected": parse_int_metric(text, "Unnotified signals selected"),
                "btc_ledger_rows_appended": parse_int_metric(text, "Ledger rows appended"),
                "btc_ai_review_enabled": parse_bool_metric(text, "AI review enabled"),
                "btc_send_discord": parse_bool_metric(text, "Send Discord"),
            }
        )
    return summary


def monthly_health_log_path(log_root: Path, when: datetime) -> Path:
    year_dir = log_root / when.strftime("%Y")
    return year_dir / f"portfolio_loop_health_{when.strftime('%Y%m')}.csv"


def append_monthly_health_log(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_started_at",
        "run_finished_at",
        "duration_sec",
        "overall_returncode",
        "dry_run",
        "send_discord",
        "bar_offset",
        "gold_scan_recent_bars",
        "btc_scan_recent_m5_bars",
        "btc_scan_recent_m15_bars",
        "gold_returncode",
        "gold_duration_sec",
        "gold_unnotified_selected",
        "gold_rejected_excluded",
        "gold_ledger_rows_appended",
        "gold_ai_review_enabled",
        "gold_send_discord",
        "btc_returncode",
        "btc_duration_sec",
        "btc_raw_unnotified",
        "btc_rejected_spread_value",
        "btc_unnotified_selected",
        "btc_ledger_rows_appended",
        "btc_ai_review_enabled",
        "btc_send_discord",
        "error_summary",
    ]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


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
    parser.add_argument("--runtime-log-dir", type=Path, default=DEFAULT_RUNTIME_LOG_DIR)
    parser.add_argument("--no-runtime-health-log", action="store_true", help="Disable monthly one-line runtime health log.")

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

    portfolio_started_at = now_local()

    if args.skip_gold and args.skip_btc:
        raise ValueError("Both --skip-gold and --skip-btc were specified. Nothing to run.")

    print("Project root:", PROJECT_ROOT)
    print("Portfolio notifier dry_run:", bool(args.dry_run))
    print("Portfolio notifier send_discord:", bool(args.send_discord))
    print("BTC notifier: spread-filtered only")
    if not args.no_runtime_health_log:
        print("Runtime health log:", monthly_health_log_path(args.runtime_log_dir, portfolio_started_at))

    results: list[ChildRunResult] = []
    capture_child_output = not args.no_runtime_health_log
    early_return_code: int | None = None

    if not args.skip_gold:
        result = run_child("GOLD", build_gold_command(args), print_only=bool(args.print_only), capture_child_output=capture_child_output)
        results.append(result)
        if result.returncode == 130:
            early_return_code = 130
        elif args.stop_on_error and result.returncode != 0:
            print("Stopping because GOLD failed and --stop-on-error is set.")
            early_return_code = result.returncode

    if early_return_code is None and not args.skip_btc:
        result = run_child("BTC", build_btc_command(args), print_only=bool(args.print_only), capture_child_output=capture_child_output)
        results.append(result)
        if result.returncode == 130:
            early_return_code = 130
        elif args.stop_on_error and result.returncode != 0:
            print("Stopping because BTC failed and --stop-on-error is set.")
            early_return_code = result.returncode

    print("\n" + "#" * 100)
    print("Portfolio notifier summary")
    print("#" * 100)
    for result in results:
        status = "OK" if result.returncode == 0 else "FAILED"
        print(f"{result.name}: {status} returncode={result.returncode}")

    failed = [result for result in results if result.returncode != 0]
    overall_returncode = early_return_code if early_return_code is not None else (1 if failed else 0)
    portfolio_finished_at = now_local()

    if not args.no_runtime_health_log:
        row: dict[str, object] = {
            "run_started_at": dt_text(portfolio_started_at),
            "run_finished_at": dt_text(portfolio_finished_at),
            "duration_sec": round((portfolio_finished_at - portfolio_started_at).total_seconds(), 3),
            "overall_returncode": overall_returncode,
            "dry_run": bool(args.dry_run),
            "send_discord": bool(args.send_discord),
            "bar_offset": args.bar_offset,
            "gold_scan_recent_bars": args.gold_scan_recent_bars,
            "btc_scan_recent_m5_bars": args.btc_scan_recent_m5_bars,
            "btc_scan_recent_m15_bars": args.btc_scan_recent_m15_bars,
            "error_summary": " / ".join(f"{r.name}=returncode{r.returncode}" for r in failed),
        }
        for result in results:
            row.update(summarize_child_for_log(result))
        log_path = monthly_health_log_path(args.runtime_log_dir, portfolio_started_at)
        append_monthly_health_log(log_path, row)
        print("Runtime health row appended:", log_path)

    return overall_returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting portfolio notifier.")
        raise SystemExit(130)
