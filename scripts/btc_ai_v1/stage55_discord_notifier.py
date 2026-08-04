from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

VALID_WEBHOOK_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)

FAMILY_LABELS = {
    "M1_FALSE_LONG_REVERSAL_SHORT": "M1騙し後・陰転確認SHORT",
    "M5_LEVEL_REJECTION_REVERSAL_SHORT": "M5水準拒否・弱気反転SHORT",
}


def expand_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def discord_settings(config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config.get("discord")
    if not isinstance(settings, dict) or not bool(settings.get("enabled", False)):
        raise ValueError("Discord entry notification is disabled in local_config.json")
    source = str(settings.get("webhook_source", "LOCAL_CONFIG"))
    if source != "LOCAL_CONFIG":
        raise ValueError("Stage55 supports webhook_source=LOCAL_CONFIG only")
    url = settings.get("webhook_url")
    if not isinstance(url, str) or not url.startswith(VALID_WEBHOOK_PREFIXES):
        raise ValueError("Discord webhook_url is not configured in local_config.json")
    return {
        "webhook_url": url,
        "username": str(settings.get("username", "BTC Stage55 Shadow")),
        "attach_chart": bool(settings.get("attach_chart", True)),
        "chart_bars": max(30, int(settings.get("chart_bars", 120))),
        "poll_seconds": max(5, int(settings.get("poll_seconds", 15))),
        "max_notification_age_minutes": 10,
    }


def _num(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if np.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def _price(value: Any) -> str:
    parsed = _num(value)
    return "不明" if parsed is None else f"{parsed:,.2f}"


def target_price(event: Mapping[str, Any]) -> float | None:
    entry = _num(event.get("entry_price"))
    stop = _num(event.get("stop_price"))
    if entry is None or stop is None or stop <= entry:
        return None
    return entry - 2.0 * (stop - entry)


def entry_message(event: Mapping[str, Any]) -> str:
    family = str(event.get("family", "UNKNOWN"))
    label = FAMILY_LABELS.get(family, family)
    entry = _num(event.get("entry_price"))
    stop = _num(event.get("stop_price"))
    target = target_price(event)
    risk = None if entry is None or stop is None else stop - entry
    lines = [
        "📣 **BTC Stage55 Shadow エントリー**",
        "方向: 🔴 **SHORT**",
        f"候補: `{label}`",
        f"Source（MT5）: `{event.get('source_decision_time', '不明')}`",
        f"騙し警告（MT5）: `{event.get('alert_time', '不明')}`",
        f"弱気確認（MT5）: `{event.get('confirmation_time', '不明')}`",
        f"Entry（MT5）: `{event.get('entry_time', '不明')}`",
        f"Entry: `{_price(entry)}`",
        f"SL: `{_price(stop)}` / TP 2R: `{_price(target)}`",
        f"Risk幅: `{_price(risk)}` / 最大保有: `{int(float(event.get('max_minutes', 0)))}分`",
    ]
    score = _num(event.get("detector_score"))
    threshold = _num(event.get("detector_threshold"))
    if score is not None and threshold is not None:
        lines.append(f"騙しscore: `{score:.4f}` / 固定閾値: `{threshold:.4f}`")
    lines.extend(
        [
            "状態: **Prospective Shadow・観測専用・実注文なし**",
            "通知は目視確認用で、採否・成績・条件変更には使用しません。",
            "MT5発注 / live trading / final_signal / live_ready: **OFF**",
        ]
    )
    return "\n".join(lines)


def send_discord(url: str, username: str, content: str, image: Path | None = None) -> None:
    boundary = "----BTCStage55" + uuid.uuid4().hex
    parts: list[bytes] = []

    def add(text: str) -> None:
        parts.append(text.encode("utf-8"))

    add(
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="payload_json"\r\n'
        "Content-Type: application/json; charset=utf-8\r\n\r\n"
    )
    add(json.dumps({"username": username, "content": content, "allowed_mentions": {"parse": []}}, ensure_ascii=False) + "\r\n")
    if image is not None and image.exists():
        add(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files[0]"; filename="{image.name}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        )
        parts.append(image.read_bytes())
        add("\r\n")
    add(f"--{boundary}--\r\n")
    request = urllib.request.Request(
        url,
        data=b"".join(parts),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "BTC-Stage55-Shadow/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.getcode() not in (200, 204):
                raise RuntimeError(f"Discord returned HTTP {response.getcode()}")
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", "replace")
        raise RuntimeError(f"Discord returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Discord connection failed: {exc.reason}") from exc


def load_ohlc(path: Path, tf: str) -> pd.DataFrame:
    minutes = {"M1": 1, "M5": 5}[tf]
    frame = pd.read_csv(path, sep=";")
    frame["time"] = pd.to_datetime(frame["time"], format="%Y.%m.%d %H:%M:%S", errors="raise")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time")
    frame["close_time"] = frame["time"] + pd.to_timedelta(minutes, unit="m")
    return frame.reset_index(drop=True)


def make_chart(config: Mapping[str, Any], event: Mapping[str, Any], state_root: Path, bars: int) -> Path | None:
    family = str(event.get("family", ""))
    tf = "M1" if family == "M1_FALSE_LONG_REVERSAL_SHORT" else "M5"
    path_value = config.get("ohlc_paths", {}).get(tf)
    if not isinstance(path_value, str) or not path_value:
        return None
    event_time = pd.to_datetime(event.get("entry_time"), errors="coerce")
    if pd.isna(event_time):
        return None
    try:
        data = load_ohlc(expand_path(path_value), tf)
        subset = data[data["close_time"] <= pd.Timestamp(event_time)].tail(bars).copy()
        if len(subset) < 10:
            return None
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except (ImportError, OSError, ValueError, KeyError):
        return None

    fig, axis = plt.subplots(figsize=(12, 6.5), dpi=120)
    times = list(pd.to_datetime(subset["time"]).dt.to_pydatetime())
    x_values = mdates.date2num(times)
    width = (x_values[1] - x_values[0]) * 0.68 if len(x_values) > 1 else 0.0005
    for position, (_, row) in enumerate(subset.iterrows()):
        color = "#2ca02c" if row["close"] >= row["open"] else "#d62728"
        axis.vlines(x_values[position], row["low"], row["high"], color=color, linewidth=0.8)
        bottom = min(row["open"], row["close"])
        height = max(abs(row["close"] - row["open"]), 0.01)
        axis.add_patch(Rectangle((x_values[position] - width / 2, bottom), width, height, facecolor=color, edgecolor=color))

    entry = _num(event.get("entry_price"))
    stop = _num(event.get("stop_price"))
    target = target_price(event)
    for value, color, style, label in (
        (entry, "#1f77b4", "-", "Entry"),
        (stop, "#d62728", "--", "SL"),
        (target, "#2ca02c", "--", "TP 2R"),
    ):
        if value is not None:
            axis.axhline(value, color=color, linestyle=style, linewidth=1.1, label=f"{label} {value:.2f}")
    for key, color, label in (
        ("source_decision_time", "#7f7f7f", "Source"),
        ("alert_time", "#ff7f0e", "Alert"),
        ("confirmation_time", "#9467bd", "Confirm"),
        ("entry_time", "#1f77b4", "Entry time"),
    ):
        value = pd.to_datetime(event.get(key), errors="coerce")
        if not pd.isna(value):
            axis.axvline(mdates.date2num(pd.Timestamp(value)), color=color, linestyle=":", linewidth=1.0, label=label)
    axis.set_title(f"BTC Stage55 Shadow | {FAMILY_LABELS.get(family, family)} | {tf}")
    axis.set_ylabel("BTCUSD#")
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    axis.grid(alpha=0.2)
    axis.legend(loc="best", fontsize=8)
    fig.tight_layout()
    output = state_root / "outputs" / "discord_charts" / f"entry_{str(event.get('candidate_key', uuid.uuid4().hex)).replace('|', '_').replace(':', '-')}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def read_trade_ledger(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path)
    for column in ("entry_time", "confirmation_time"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if "observation_status" in frame:
        frame = frame[frame["observation_status"] == "ACCEPTED_SHADOW"].copy()
    sort_columns = [column for column in ("entry_time", "family") if column in frame.columns]
    if sort_columns:
        frame = frame.sort_values(sort_columns)
    return frame.reset_index(drop=True)


def append_csv(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def current_latest_m1_close(state_root: Path, config: Mapping[str, Any]) -> pd.Timestamp:
    health_path = state_root / "runtime_health.json"
    if health_path.exists():
        health = read_json(health_path)
        latest = pd.to_datetime(health.get("latest_m1_close"), errors="coerce")
        if not pd.isna(latest):
            return pd.Timestamp(latest)
    m1 = load_ohlc(expand_path(config["ohlc_paths"]["M1"]), "M1")
    return pd.Timestamp(m1["close_time"].iloc[-1])


def initialize_state(state_path: Path, ledger: pd.DataFrame, latest_m1_close: pd.Timestamp) -> dict[str, Any]:
    baseline = sorted(set(ledger.get("candidate_key", pd.Series(dtype=str)).dropna().astype(str)))
    state = {
        "contract_id": "BTC_AI_V1_STAGE55_DISCORD_ENTRY_ALERT_SIDECAR",
        "activated_at_utc": now_utc(),
        "activated_at_latest_m1_close": latest_m1_close.isoformat(),
        "baseline_candidate_keys": baseline,
        "sent_candidate_keys": [],
        "missed_candidate_keys": [],
        "last_scan_m1_close": latest_m1_close.isoformat(),
        "runs": 1,
    }
    write_json(state_path, state)
    return state


def run_once(config_path: Path) -> dict[str, Any]:
    config = read_json(config_path)
    settings = discord_settings(config)
    state_root = expand_path(config["state_root"])
    state_root.mkdir(parents=True, exist_ok=True)
    outputs = state_root / "outputs"
    ledger = read_trade_ledger(outputs / "shadow_trade_ledger.csv")
    latest = current_latest_m1_close(state_root, config)
    state_path = state_root / "discord_notifier_state.json"
    health_path = state_root / "discord_notifier_health.json"
    if not state_path.exists():
        state = initialize_state(state_path, ledger, latest)
        health = {
            "status": "READY_NO_BACKFILL_NOTIFIER_ACTIVATED",
            "latest_m1_close": latest,
            "baseline_entries": len(state["baseline_candidate_keys"]),
            "sent_entries": 0,
            "missed_entries": 0,
            "discord": True,
            "mt5_orders": False,
        }
        write_json(health_path, health)
        return health

    state = read_json(state_path)
    known = set(state.get("baseline_candidate_keys", [])) | set(state.get("sent_candidate_keys", [])) | set(state.get("missed_candidate_keys", []))
    sent = set(state.get("sent_candidate_keys", []))
    missed = set(state.get("missed_candidate_keys", []))
    sent_this_run = 0
    failed_this_run = 0
    stale_this_run = 0
    max_age = float(settings["max_notification_age_minutes"])

    for _, event in ledger.iterrows():
        key = str(event.get("candidate_key", ""))
        if not key or key in known:
            continue
        entry_time = pd.to_datetime(event.get("entry_time"), errors="coerce")
        if pd.isna(entry_time):
            missed.add(key)
            stale_this_run += 1
            known.add(key)
            continue
        age = (latest - pd.Timestamp(entry_time)).total_seconds() / 60.0
        if age > max_age:
            missed.add(key)
            known.add(key)
            stale_this_run += 1
            append_csv(
                outputs / "discord_missed_ledger.csv",
                {
                    "candidate_key": key,
                    "family": event.get("family", ""),
                    "entry_time": event.get("entry_time", ""),
                    "latest_m1_close": latest,
                    "age_minutes": age,
                    "reason": "STALE_ENTRY_NO_BACKFILL",
                    "recorded_at_utc": now_utc(),
                },
            )
            continue
        try:
            image = make_chart(config, event, state_root, settings["chart_bars"]) if settings["attach_chart"] else None
            send_discord(settings["webhook_url"], settings["username"], entry_message(event), image)
            sent.add(key)
            known.add(key)
            sent_this_run += 1
            append_csv(
                outputs / "discord_send_ledger.csv",
                {
                    "candidate_key": key,
                    "family": event.get("family", ""),
                    "source_decision_time": event.get("source_decision_time", ""),
                    "confirmation_time": event.get("confirmation_time", ""),
                    "entry_time": event.get("entry_time", ""),
                    "entry_price": event.get("entry_price", ""),
                    "stop_price": event.get("stop_price", ""),
                    "target_price": target_price(event),
                    "sent_at_utc": now_utc(),
                },
            )
        except Exception as exc:
            failed_this_run += 1
            append_csv(
                outputs / "discord_error_ledger.csv",
                {
                    "candidate_key": key,
                    "family": event.get("family", ""),
                    "entry_time": event.get("entry_time", ""),
                    "error": str(exc),
                    "recorded_at_utc": now_utc(),
                },
            )

    state.update(
        {
            "sent_candidate_keys": sorted(sent),
            "missed_candidate_keys": sorted(missed),
            "last_scan_m1_close": latest.isoformat(),
            "runs": int(state.get("runs", 0)) + 1,
        }
    )
    write_json(state_path, state)
    health = {
        "status": "READY_ENTRY_NOTIFICATIONS",
        "latest_m1_close": latest,
        "ledger_entries": int(len(ledger)),
        "sent_entries": len(sent),
        "missed_entries": len(missed),
        "sent_this_run": sent_this_run,
        "failed_this_run": failed_this_run,
        "stale_this_run": stale_this_run,
        "discord": True,
        "mt5_orders": False,
        "live_trading": False,
    }
    write_json(health_path, health)
    return health


def test_discord(config_path: Path) -> None:
    config = read_json(config_path)
    settings = discord_settings(config)
    content = "\n".join(
        [
            "✅ **BTC Stage55 Shadow Discord 接続テスト**",
            "通知対象: 新しく受理されたM1/M5 reverse-SHORT entryのみ",
            "通知しないもの: NO_SIGNAL、回復再生、決済、過去entry",
            "状態: Prospective Shadow・観測専用・実注文なし",
            "MT5発注 / live trading / final_signal / live_ready: OFF",
        ]
    )
    send_discord(settings["webhook_url"], settings["username"], content)


def status(config_path: Path) -> dict[str, Any]:
    config = read_json(config_path)
    root = expand_path(config["state_root"])
    state_path = root / "discord_notifier_state.json"
    health_path = root / "discord_notifier_health.json"
    return {
        "state_root": str(root),
        "state": read_json(state_path) if state_path.exists() else None,
        "health": read_json(health_path) if health_path.exists() else None,
        "mt5_orders": False,
        "live_trading": False,
    }


def acquire_lock(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Discord notifier is already running: {path}") from exc


def run_loop(config_path: Path) -> None:
    config = read_json(config_path)
    settings = discord_settings(config)
    root = expand_path(config["state_root"])
    lock_path = root / "discord_notifier.lock"
    lock_fd = acquire_lock(lock_path)
    try:
        while True:
            try:
                print(json.dumps(run_once(config_path), ensure_ascii=False, default=str))
            except Exception as exc:
                write_json(
                    root / "discord_notifier_health.json",
                    {
                        "status": "ERROR_RETRYING",
                        "error": str(exc),
                        "recorded_at_utc": now_utc(),
                        "discord": True,
                        "mt5_orders": False,
                    },
                )
            time.sleep(settings["poll_seconds"])
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC Stage55 Discord entry notification sidecar")
    parser.add_argument("command", choices=("run-once", "run-loop", "test-discord", "status"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    if args.command == "run-once":
        print(json.dumps(run_once(config_path), ensure_ascii=False, indent=2, default=str))
    elif args.command == "run-loop":
        run_loop(config_path)
    elif args.command == "test-discord":
        test_discord(config_path)
        print("Discord test sent")
    elif args.command == "status":
        print(json.dumps(status(config_path), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
