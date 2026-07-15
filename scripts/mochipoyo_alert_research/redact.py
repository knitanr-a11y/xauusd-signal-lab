from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SECRET_KEYS = {
    "authorization",
    "token",
    "read_token",
    "api_key",
    "apikey",
    "secret",
    "password",
}
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_LONG_SECRET_RE = re.compile(
    r"(?i)\b(read_token|token|api[_-]?key|secret|password)\s*[:=]\s*([^\s,;]+)"
)


def redact_url(url: str) -> str:
    """Remove credentials and secret-looking query values from a URL."""
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        safe_query = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            safe_query.append((key, "<redacted>" if key.lower() in _SECRET_KEYS else value))
        return urlunsplit((parts.scheme, host, parts.path, urlencode(safe_query), ""))
    except Exception:
        return redact_text(url)


def redact_text(text: object, secrets: tuple[str, ...] = ()) -> str:
    value = "" if text is None else str(text)
    for secret in secrets:
        if secret:
            value = value.replace(secret, "<redacted>")
    value = _BEARER_RE.sub("Bearer <redacted>", value)
    value = _LONG_SECRET_RE.sub(lambda match: f"{match.group(1)}=<redacted>", value)
    return value
