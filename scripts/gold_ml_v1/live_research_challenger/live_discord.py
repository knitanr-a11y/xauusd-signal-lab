from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class DiscordError(RuntimeError):
    pass


def _wait_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if not any(key == "wait" for key, _ in query):
        query.append(("wait", "true"))
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(query),
            parsed.fragment,
        )
    )


def send_webhook(
    webhook_url: str,
    *,
    content: str,
    username: str,
    timeout_seconds: float = 10.0,
    max_retries: int = 1,
) -> dict[str, Any] | None:
    if not webhook_url.startswith("https://"):
        raise DiscordError("Discord webhook URL must use https")
    payload = json.dumps(
        {
            "content": content[:2000],
            "username": username[:80],
            "allowed_mentions": {"parse": []},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request_url = _wait_url(webhook_url)

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            request_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GML1-XAUUSD-Live/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read()
                if response.status < 200 or response.status >= 300:
                    raise DiscordError(f"Discord returned HTTP {response.status}")
                return json.loads(body.decode("utf-8")) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt < max_retries:
                retry_after = 1.0
                try:
                    retry_after = max(
                        0.1, float(json.loads(body).get("retry_after", 1.0))
                    )
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
                time.sleep(min(retry_after, 10.0))
                continue
            raise DiscordError(f"Discord HTTP {exc.code}: {body[:300]}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            raise DiscordError(f"Discord connection failed: {exc.reason}") from exc
    raise DiscordError("Discord delivery failed")
