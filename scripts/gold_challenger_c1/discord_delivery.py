from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .shadow_common import path_value, read_json
from .shadow_data import resolve_data_sources


def discord_settings(config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config.get("discord")
    if not isinstance(settings, dict) or not settings.get("enabled", True):
        raise ValueError("Challenger Discord notification is disabled")
    if settings.get("webhook_source") != "V19_LOCAL_CONFIG":
        raise ValueError("Only the existing V19 local webhook may be used")
    v19_config = read_json(path_value(str(config["v19"]["local_config_path"])))
    v19_discord = v19_config.get("discord")
    if not isinstance(v19_discord, dict):
        raise ValueError("V19 local Discord config is missing")
    url = v19_discord.get("webhook_url")
    if not isinstance(url, str) or not url.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        raise ValueError("V19 local Discord webhook is not configured")
    return {**settings, "webhook_url": url, "username": str(settings.get("username", "GOLD Challenger C1 Shadow"))}


def number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if result == result else None
    except (TypeError, ValueError):
        return None


def price(value: Any) -> str:
    parsed = number(value)
    return "不明" if parsed is None else f"{parsed:.2f}"


def message(event: Mapping[str, Any]) -> str:
    side = str(event.get("chosen_side", "UNKNOWN")).upper()
    icon = "🟢" if side == "LONG" else "🔴" if side == "SHORT" else "⚪"
    rank = number(event.get("chosen_rank"))
    rank_text = "不明" if rank is None else f"{rank:.4f}"
    return "\n".join(
        [
            "📣 **GOLD Challenger C1 Shadow エントリー**",
            f"方向: {icon} **{side}**",
            f"時刻（MT5）: `{event.get('decision_dt', '不明')}`",
            f"Entry: `{price(event.get('entry_price'))}`",
            f"TP: `{price(event.get('tp_price'))}` / SL: `{price(event.get('sl_price'))}`",
            f"波動状態: `{event.get('wave_state', '不明')}`",
            f"chosen rank: `{rank_text}`（固定条件 `< P90`）",
            "V19優先: V19保有中は抑制、実際のV19発火時だけpreempt",
            "状態: **観測専用・実注文なし**",
            "注記: retrospective formal gateは不合格のままです。",
        ]
    )


def send(url: str, username: str, content: str, image: Path | None = None) -> None:
    boundary = "----GoldChallengerC1" + uuid.uuid4().hex
    parts: list[bytes] = []

    def add(text: str) -> None:
        parts.append(text.encode("utf-8"))

    add(f"--{boundary}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json; charset=utf-8\r\n\r\n")
    add(json.dumps({"username": username, "content": content, "allowed_mentions": {"parse": []}}, ensure_ascii=False) + "\r\n")
    if image is not None and image.exists():
        add(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"{image.name}\"\r\nContent-Type: image/png\r\n\r\n")
        parts.append(image.read_bytes())
        add("\r\n")
    add(f"--{boundary}--\r\n")
    request = urllib.request.Request(
        url,
        data=b"".join(parts),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "GOLD-Challenger-C1-Discord/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.getcode() not in (200, 204):
                raise RuntimeError(f"Discord returned HTTP {response.getcode()}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Discord returned HTTP {exc.code}: {exc.read(500).decode('utf-8', 'replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Discord connection failed: {exc.reason}") from exc


def _read_chart_bars(config: Mapping[str, Any], event_time: pd.Timestamp) -> pd.DataFrame:
    from .data_io import derive_m15_from_m1, read_union
    sources = resolve_data_sources(config)
    m1 = read_union(sources["M1"])
    bars = derive_m15_from_m1(m1)
    closed_through = pd.Timestamp(m1.time.iloc[-1]) + pd.Timedelta(minutes=1)
    bars = bars[bars.time + pd.Timedelta(minutes=15) <= closed_through]
    return bars[bars.time <= event_time].tail(80).reset_index(drop=True)


def chart(config: Mapping[str, Any], event: Mapping[str, Any], root: Path) -> Path | None:
    settings = config.get("discord", {})
    if not settings.get("attach_chart", True):
        return None
    event_time = pd.to_datetime(event.get("decision_dt"), errors="coerce")
    if pd.isna(event_time):
        return None
    bars = _read_chart_bars(config, pd.Timestamp(event_time))
    if bars.empty:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, axis = plt.subplots(figsize=(12, 6.5), dpi=120)
    x = mdates.date2num(list(pd.to_datetime(bars.time).dt.to_pydatetime()))
    width = (x[1] - x[0]) * 0.68 if len(x) > 1 else 0.006
    for index, row in bars.iterrows():
        color = "#2ca02c" if row.close >= row.open else "#d62728"
        axis.vlines(x[index], row.low, row.high, color=color, linewidth=1)
        bottom = min(row.open, row.close)
        axis.add_patch(Rectangle((x[index] - width / 2, bottom), width, max(abs(row.close - row.open), 0.01), facecolor=color, edgecolor=color))
    for key, color, style, label in (
        ("entry_price", "#1f77b4", "-", "Entry"),
        ("tp_price", "#2ca02c", "--", "TP"),
        ("sl_price", "#d62728", "--", "SL"),
    ):
        value = number(event.get(key))
        if value is not None:
            axis.axhline(value, color=color, linestyle=style, linewidth=1.1, label=f"{label} {value:.2f}")
    axis.axvline(mdates.date2num(pd.Timestamp(event_time)), color="#9467bd", linestyle=":", label="Entry time")
    axis.set_title(f"GOLD Challenger C1 Shadow | {event.get('chosen_side')} | M15 | MT5 {event.get('decision_dt')}")
    axis.set_ylabel("XAUUSD")
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    axis.grid(alpha=0.2)
    axis.legend(loc="best")
    fig.tight_layout()
    output = root / "outputs" / "discord_charts" / f"entry_{uuid.uuid4().hex[:10]}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output
