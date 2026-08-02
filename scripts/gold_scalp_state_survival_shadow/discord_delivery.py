from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .common import path_value, read_json

VALID_WEBHOOK_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)


def discord_settings(config: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    settings = config.get("discord")
    if not isinstance(settings, dict) or not settings.get("enabled", True):
        raise ValueError("Discord notification is disabled")
    source = str(settings.get("webhook_source", "V19_LOCAL_CONFIG"))
    if source == "V19_LOCAL_CONFIG":
        v19_path_value = config.get("v19_local_config_path")
        if not isinstance(v19_path_value, str) or not v19_path_value:
            raise ValueError("v19_local_config_path is missing")
        v19_config = read_json(path_value(v19_path_value, config_path.parent))
        v19_discord = v19_config.get("discord")
        if not isinstance(v19_discord, dict):
            raise ValueError("V19 local Discord config is missing")
        url = v19_discord.get("webhook_url")
    elif source == "LOCAL_CONFIG":
        url = settings.get("webhook_url")
    else:
        raise ValueError("Unsupported Discord webhook_source")
    if not isinstance(url, str) or not url.startswith(VALID_WEBHOOK_PREFIXES):
        raise ValueError("Discord webhook is not configured")
    return {
        **settings,
        "webhook_url": url,
        "username": str(settings.get("username", "GOLD State Survival Shadow")),
    }


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if parsed == parsed else None
    except (TypeError, ValueError):
        return None


def _price(value: Any) -> str:
    parsed = _number(value)
    return "不明" if parsed is None else f"{parsed:.2f}"


def entry_message(event: Mapping[str, Any]) -> str:
    side = str(event.get("action", "UNKNOWN")).upper()
    icon = "🟢" if side == "LONG" else "🔴" if side == "SHORT" else "⚪"
    health = str(event.get("health_status", "ACTIVE"))
    return "\n".join(
        [
            "📣 **GOLD State Survival Shadow 疑似エントリー**",
            f"方向: {icon} **{side}**",
            f"Signal（MT5）: `{event.get('signal_time', '不明')}`",
            f"Entry（MT5）: `{event.get('entry_time', '不明')}`",
            f"Entry: `{_price(event.get('entry_price'))}`",
            f"75% TP: `{_price(event.get('partial_tp_price'))}`",
            f"残り25% TP: `{_price(event.get('final_tp_price'))}` / SL: `{_price(event.get('sl_price'))}`",
            f"状態: `{event.get('state', '不明')}`",
            f"Health: `{health}` / Episode: `REARMED_ENTRY`",
            "決済契約: +5で75%利確、残り建値、最終+10、初期SL5、最大240分",
            "状態: **Prospective Shadow・観測専用・実注文なし**",
            "MT5発注 / final_signal / live_ready: **OFF**",
        ]
    )


def send(url: str, username: str, content: str, image: Path | None = None) -> None:
    boundary = "----GoldStateSurvival" + uuid.uuid4().hex
    parts: list[bytes] = []

    def add(value: str) -> None:
        parts.append(value.encode("utf-8"))

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
            "User-Agent": "GOLD-State-Survival-Shadow/1.0",
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


def make_chart(m15: pd.DataFrame, event: Mapping[str, Any], root: Path, bars: int = 80) -> Path | None:
    event_time = pd.to_datetime(event.get("signal_time"), errors="coerce")
    if pd.isna(event_time):
        return None
    subset = m15[m15["time"] <= pd.Timestamp(event_time)].tail(max(20, int(bars))).copy()
    if subset.empty:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        return None

    fig, axis = plt.subplots(figsize=(12, 6.5), dpi=120)
    times = list(pd.to_datetime(subset["time"]).dt.to_pydatetime())
    x_values = mdates.date2num(times)
    width = (x_values[1] - x_values[0]) * 0.68 if len(x_values) > 1 else 0.006
    for position, (_, row) in enumerate(subset.iterrows()):
        color = "#2ca02c" if row["close"] >= row["open"] else "#d62728"
        axis.vlines(x_values[position], row["low"], row["high"], color=color, linewidth=1)
        bottom = min(row["open"], row["close"])
        body_height = max(abs(row["close"] - row["open"]), 0.01)
        axis.add_patch(
            Rectangle(
                (x_values[position] - width / 2, bottom),
                width,
                body_height,
                facecolor=color,
                edgecolor=color,
            )
        )
    for key, color, style, label in (
        ("entry_price", "#1f77b4", "-", "Entry"),
        ("partial_tp_price", "#17becf", "--", "TP75%"),
        ("final_tp_price", "#2ca02c", "--", "TP25%"),
        ("sl_price", "#d62728", "--", "SL"),
    ):
        value = _number(event.get(key))
        if value is not None:
            axis.axhline(value, color=color, linestyle=style, linewidth=1.1, label=f"{label} {value:.2f}")
    axis.axvline(mdates.date2num(pd.Timestamp(event_time)), color="#9467bd", linestyle=":", label="Signal")
    axis.set_title(f"GOLD State Survival Shadow | {event.get('action')} | {event.get('state')}")
    axis.set_ylabel("XAUUSD")
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    axis.grid(alpha=0.2)
    axis.legend(loc="best")
    fig.tight_layout()
    output = root / "outputs" / "discord_charts" / f"entry_{event.get('event_id', uuid.uuid4().hex[:10])}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output
