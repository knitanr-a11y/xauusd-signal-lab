from __future__ import annotations

import argparse
import csv
import datetime as dt
import getpass
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping

SHADOW_ID = "GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW"
CONTRACT_VERSION = "2026-08-01-v1"
NOTIFIER_VERSION = "2026-08-01-discord-v1"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return obj


def write_json(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def p(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def state_dir(config: Mapping[str, Any]) -> Path:
    value = config.get("state_dir")
    if not isinstance(value, str) or not value:
        raise ValueError("state_dir is missing")
    return p(value)


def discord_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if config.get("shadow_id") != SHADOW_ID or config.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("GOLD V19 shadow contract mismatch")
    value = config.get("discord")
    if not isinstance(value, dict) or not value.get("enabled"):
        raise ValueError("Discord is not configured; run 06_CONFIGURE_DISCORD.bat")
    url = value.get("webhook_url")
    if not isinstance(url, str) or not url.startswith((
        "https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/"
    )):
        raise ValueError("Discord webhook URL is invalid")
    return value


def configure(config_path: Path) -> None:
    config = read_json(config_path)
    url = getpass.getpass("Discord Webhook URL (input hidden): ").strip()
    if not url.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        raise ValueError("The value is not a Discord webhook URL")
    config["discord"] = {
        "enabled": True,
        "webhook_url": url,
        "username": "GOLD V19 Shadow",
        "notify_entry": True,
        "notify_exit": False,
        "attach_chart": True,
        "chart_timeframe": "M15",
        "chart_bars": 80,
        "poll_seconds": int(config.get("poll_seconds", 2)),
    }
    write_json(config_path, config)
    print("Saved locally. The webhook URL is ignored by Git and is not uploaded.")


def logger_for(root: Path) -> logging.Logger:
    (root / "logs").mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("gold_v19_discord")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (
        logging.FileHandler(root / "logs" / "discord_notifier.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ):
        handler.setFormatter(fmt)
        log.addHandler(handler)
    return log


def lock_instance(root: Path):
    path = root / "discord_notifier.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise RuntimeError("Discord notifier is already running") from exc
    return handle


def accepted_count(runtime: Mapping[str, Any]) -> int:
    try:
        return int(runtime.get("counters", {}).get("accepted_trades", 0))
    except (AttributeError, TypeError, ValueError):
        return 0


def last_row(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    row: dict[str, Any] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for item in csv.DictReader(f):
            row = {str(k).strip().lower().replace("-", "_"): v for k, v in item.items()}
    return row


def pick(*sources: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for source in sources:
        for name in names:
            value = source.get(name)
            if value not in (None, "", "nan", "NaN"):
                return value
    return None


def number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if result == result else None
    except (TypeError, ValueError):
        return None


def event_from(runtime: Mapping[str, Any], root: Path) -> dict[str, Any]:
    opened = runtime.get("open_trade") if isinstance(runtime.get("open_trade"), dict) else {}
    opened = {str(k).lower(): v for k, v in opened.items()}
    candidate = last_row(root / "outputs" / "shadow_candidate_ledger.csv")
    trade = last_row(root / "outputs" / "shadow_trade_ledger.csv")
    side = str(pick(opened, candidate, trade, names=("direction", "side", "signal", "selected_side")) or "UNKNOWN").upper()
    entry = number(pick(opened, candidate, trade, names=("entry_price", "entry", "open_price", "price")))
    tp = number(pick(opened, candidate, trade, names=("tp_price", "target_price", "tp", "target")))
    sl = number(pick(opened, candidate, trade, names=("sl_price", "stop_price", "sl", "stop")))
    if entry is not None:
        tp = tp if tp is not None else entry + (20 if side == "LONG" else -20)
        sl = sl if sl is not None else entry + (-10 if side == "LONG" else 10)
    when = pick(opened, candidate, trade, names=(
        "entry_dt", "entry_time", "entry_datetime", "decision_time", "decision_dt", "time", "timestamp"
    )) or runtime.get("last_processed_decision_time", "UNKNOWN")
    return {"side": side, "entry_time": str(when), "entry": entry, "tp": tp, "sl": sl, "count": accepted_count(runtime)}


def price(value: Any) -> str:
    value = number(value)
    return "不明" if value is None else f"{value:.2f}"


def message(event: Mapping[str, Any]) -> str:
    side = str(event.get("side", "UNKNOWN"))
    icon = "🟢" if side == "LONG" else "🔴" if side == "SHORT" else "⚪"
    return "\n".join([
        "📣 **GOLD V19 Shadow エントリー候補**",
        f"方向: {icon} **{side}**",
        f"時刻（MT5）: `{event.get('entry_time', '不明')}`",
        f"Entry: `{price(event.get('entry'))}`",
        f"TP: `{price(event.get('tp'))}` / SL: `{price(event.get('sl'))}`",
        "波動状態: `IMPULSE_EARLY`",
        "条件: このepisodeで最初の方向スコア上位10%候補",
        "状態: **観測専用・実注文なし**",
    ])


def parse_time(value: Any) -> dt.datetime | None:
    text = str(value).strip().replace("Z", "+00:00")
    try:
        value = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def read_ohlc(path: Path):
    import pandas as pd
    frame = None
    error: Exception | None = None
    for kwargs in ({"sep": ";"}, {"sep": ","}, {"sep": "\t"}, {"sep": None, "engine": "python"}):
        try:
            trial = pd.read_csv(path, encoding="utf-8-sig", **kwargs)
            if trial.shape[1] >= 5:
                frame = trial
                break
        except Exception as exc:
            error = exc
    if frame is None:
        raise RuntimeError(f"Could not read {path}: {error}")
    frame = frame.rename(columns={c: str(c).strip().lower().replace("<", "").replace(">", "") for c in frame.columns})
    if "datetime" in frame:
        timestamp = pd.to_datetime(frame["datetime"], errors="coerce")
    elif "date" in frame and "time" in frame:
        timestamp = pd.to_datetime(frame["date"].astype(str) + " " + frame["time"].astype(str), errors="coerce")
    elif "time" in frame:
        timestamp = pd.to_datetime(frame["time"], errors="coerce")
    else:
        raise ValueError(f"No time column in {path}")
    required = ["open", "high", "low", "close"]
    if any(c not in frame for c in required):
        raise ValueError(f"OHLC columns are missing in {path}")
    result = frame.assign(timestamp=timestamp)[["timestamp", *required]].copy()
    for column in required:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.dropna().sort_values("timestamp")


def chart(config: Mapping[str, Any], discord: Mapping[str, Any], event: Mapping[str, Any], root: Path) -> Path | None:
    if not discord.get("attach_chart", True):
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd
    from matplotlib.patches import Rectangle

    tf = str(discord.get("chart_timeframe", "M15")).upper()
    raw_paths = config.get("data_sources", {}).get(tf, [])
    frames = [read_ohlc(p(x)) for x in raw_paths if isinstance(x, str) and p(x).exists()]
    if not frames:
        return None
    bars = pd.concat(frames).drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    when = parse_time(event.get("entry_time"))
    if when:
        bars = bars[bars["timestamp"] <= when]
    bars = bars.tail(max(30, min(200, int(discord.get("chart_bars", 80))))).reset_index(drop=True)
    if bars.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=120)
    x = mdates.date2num(list(bars["timestamp"].dt.to_pydatetime()))
    width = (x[1] - x[0]) * 0.68 if len(x) > 1 else 0.006
    for i, row in bars.iterrows():
        color = "#2ca02c" if row["close"] >= row["open"] else "#d62728"
        ax.vlines(x[i], row["low"], row["high"], color=color, linewidth=1)
        bottom = min(row["open"], row["close"])
        ax.add_patch(Rectangle((x[i] - width / 2, bottom), width, max(abs(row["close"] - row["open"]), 0.01), facecolor=color, edgecolor=color))
    for key, color, style, label in (
        ("entry", "#1f77b4", "-", "Entry"), ("tp", "#2ca02c", "--", "TP"), ("sl", "#d62728", "--", "SL")
    ):
        value = number(event.get(key))
        if value is not None:
            ax.axhline(value, color=color, linestyle=style, linewidth=1.1, label=f"{label} {value:.2f}")
    if when:
        ax.axvline(mdates.date2num(when), color="#9467bd", linestyle=":", label="Entry time")
    ax.set_title(f"GOLD V19 Shadow | {event.get('side')} | {tf} | MT5 {event.get('entry_time')}")
    ax.set_ylabel("XAUUSD")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    ax.grid(alpha=0.2)
    ax.legend(loc="best")
    fig.tight_layout()
    out = root / "outputs" / "discord_charts" / f"entry_{int(event.get('count', 0)):05d}_{uuid.uuid4().hex[:8]}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out


def send(url: str, username: str, content: str, image: Path | None = None) -> None:
    boundary = "----GoldV19" + uuid.uuid4().hex
    parts: list[bytes] = []
    def add(text: str) -> None:
        parts.append(text.encode("utf-8"))
    add(f"--{boundary}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json; charset=utf-8\r\n\r\n")
    add(json.dumps({"username": username, "content": content, "allowed_mentions": {"parse": []}}, ensure_ascii=False) + "\r\n")
    if image and image.exists():
        add(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"{image.name}\"\r\nContent-Type: image/png\r\n\r\n")
        parts.append(image.read_bytes())
        add("\r\n")
    add(f"--{boundary}--\r\n")
    request = urllib.request.Request(url, data=b"".join(parts), method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "GOLD-V19-Shadow-Discord/1.0"
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.getcode() not in (200, 204):
                raise RuntimeError(f"Discord returned HTTP {response.getcode()}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Discord returned HTTP {exc.code}: {exc.read(500).decode('utf-8', 'replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Discord connection failed: {exc.reason}") from exc


def notifier_state(runtime: Mapping[str, Any]) -> dict[str, Any]:
    count = accepted_count(runtime)
    return {
        "shadow_id": SHADOW_ID, "contract_version": CONTRACT_VERSION, "notifier_version": NOTIFIER_VERSION,
        "activated_at_utc": now_utc(),
        "startup_policy": "NO_BACKFILL; baseline current accepted_trades and notify future increments only",
        "baseline_accepted_trades": count, "last_seen_accepted_trades": count,
        "sent_entry_notifications": 0, "last_sent_at_utc": None, "last_error": None,
    }


def loop(config_path: Path) -> None:
    config = read_json(config_path)
    discord = discord_config(config)
    root = state_dir(config)
    log = logger_for(root)
    lock = lock_instance(root)
    runtime_path = root / "runtime_state.json"
    if not runtime_path.exists():
        raise FileNotFoundError(f"Runtime state not found: {runtime_path}")
    runtime = read_json(runtime_path)
    status = notifier_state(runtime)
    status_path = root / "discord_notifier_state.json"
    write_json(status_path, status)
    seen = accepted_count(runtime)
    delay = max(1, int(discord.get("poll_seconds", config.get("poll_seconds", 2))))
    log.info("READY; no-backfill baseline accepted_trades=%s", seen)
    try:
        while True:
            try:
                runtime = read_json(runtime_path)
                current = accepted_count(runtime)
                if current < seen:
                    log.warning("accepted_trades moved backwards: %s -> %s", seen, current)
                    seen = current
                elif current > seen:
                    if current - seen != 1:
                        log.warning("Missed %s entries while notifier was unavailable; delayed alerts suppressed", current - seen)
                        seen = current
                    else:
                        event = event_from(runtime, root)
                        image = None
                        try:
                            image = chart(config, discord, event, root)
                        except Exception:
                            log.exception("Chart generation failed; sending text only")
                        send(str(discord["webhook_url"]), str(discord.get("username", "GOLD V19 Shadow")), message(event), image)
                        seen = current
                        status["sent_entry_notifications"] = int(status["sent_entry_notifications"]) + 1
                        status["last_sent_at_utc"] = now_utc()
                        status["last_error"] = None
                        log.info("Sent entry alert count=%s side=%s MT5=%s", current, event["side"], event["entry_time"])
                status["last_seen_accepted_trades"] = seen
                write_json(status_path, status)
            except Exception as exc:
                status["last_error"] = {"at_utc": now_utc(), "message": str(exc)}
                write_json(status_path, status)
                log.exception("Notifier iteration failed")
            time.sleep(delay)
    except KeyboardInterrupt:
        log.info("Stopped by user")
    finally:
        lock.close()


def test(config_path: Path) -> None:
    config = read_json(config_path)
    discord = discord_config(config)
    root = state_dir(config)
    runtime_path = root / "runtime_state.json"
    runtime = read_json(runtime_path) if runtime_path.exists() else {}
    event = event_from(runtime, root)
    image = None
    try:
        image = chart(config, discord, event, root)
    except Exception:
        pass
    send(str(discord["webhook_url"]), str(discord.get("username", "GOLD V19 Shadow")),
         "✅ **GOLD V19 Shadow Discord接続テスト**\n観測専用通知の接続に成功しました。実注文は行いません。", image)
    print("Discord test notification sent.")


def status(config_path: Path) -> None:
    config = read_json(config_path)
    path = state_dir(config) / "discord_notifier_state.json"
    print(json.dumps(read_json(path) if path.exists() else {"status": "NOT_STARTED", "path": str(path)}, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GOLD V19 observation-only Discord notifier")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("command", choices=["configure", "test", "loop", "status"])
    args = parser.parse_args(argv)
    try:
        {"configure": configure, "test": test, "loop": loop, "status": status}[args.command](args.config)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
