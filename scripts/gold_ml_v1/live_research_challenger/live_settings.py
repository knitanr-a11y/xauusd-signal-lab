from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

SLEEVES = ("A_CORE", "B_STATE", "P18", "W024A")
LIVE_CONFIRM_TOKEN = "I_UNDERSTAND_THIS_SENDS_REAL_MT5_ORDERS"


@dataclass(frozen=True)
class RuntimeSettings:
    env_path: Path
    discord_enabled: bool
    discord_webhook_url: str | None
    discord_username: str
    mt5_enabled: bool
    mt5_dry_run: bool
    mt5_live_confirmed: bool
    mt5_symbol: str | None
    mt5_terminal_path: str | None
    mt5_login: int | None
    mt5_password: str | None
    mt5_server: str | None
    mt5_deviation_points: int
    mt5_max_entry_lag_seconds: int
    mt5_max_total_positions: int
    mt5_magic_base: int
    mt5_require_hedging: bool
    mt5_filling_mode: str
    volumes: dict[str, float | None]
    historical_results_dir: Path
    require_historical_win_rate: bool
    config_errors: tuple[str, ...]

    @property
    def real_orders_armed(self) -> bool:
        return (
            self.mt5_enabled
            and not self.mt5_dry_run
            and self.mt5_live_confirmed
            and not self.config_errors
        )

    def controls(self) -> dict[str, object]:
        return {
            "discord": self.discord_enabled,
            "mt5_order_requested": self.mt5_enabled,
            "mt5_dry_run": self.mt5_dry_run,
            "mt5_real_orders_armed": self.real_orders_armed,
            "require_historical_win_rate": self.require_historical_win_rate,
            "config_error_count": len(self.config_errors),
        }


def _strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    output: list[str] = []
    for char in value:
        if escaped:
            output.append(char)
            escaped = False
            continue
        if char == "\\":
            output.append(char)
            escaped = True
            continue
        if quote:
            output.append(char)
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            continue
        if char == "#" and (not output or output[-1].isspace()):
            break
        output.append(char)
    return "".join(output).strip()


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for number, raw in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{path.name}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
            raise ValueError(f"{path.name}:{number}: invalid environment variable name")
        value = _strip_inline_comment(value)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _merged_environment(dotenv: Mapping[str, str]) -> dict[str, str]:
    merged = dict(dotenv)
    merged.update({key: value for key, value in os.environ.items()})
    return merged


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    raise ValueError(f"{key} must be true/false")


def _int(env: Mapping[str, str], key: str, default: int | None = None) -> int | None:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    return int(raw.strip())


def _float(env: Mapping[str, str], key: str) -> float | None:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return None
    return float(raw.strip())


def _first(env: Mapping[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = env.get(key)
        if value is not None and value.strip():
            return value.strip()
    return None


def load_runtime_settings(live_dir: Path, repo_root: Path) -> RuntimeSettings:
    env_path = live_dir / ".env"
    dotenv = read_dotenv(env_path)
    env = _merged_environment(dotenv)

    webhook = _first(
        env,
        (
            "GML1_DISCORD_WEBHOOK_URL",
            "GML1_DISCORD_WEBHOOK",
            "DISCORD_WEBHOOK_URL",
            "DISCORD_WEBHOOK",
            "WEBHOOK_URL",
            "WEBHOOK",
        ),
    )
    discord_enabled = _bool(env, "GML1_DISCORD_ENABLED", bool(webhook))
    mt5_enabled = _bool(env, "GML1_MT5_ORDER_ENABLED", False)
    mt5_dry_run = _bool(env, "GML1_MT5_DRY_RUN", True)
    mt5_live_confirmed = (
        env.get("GML1_MT5_LIVE_CONFIRM", "").strip() == LIVE_CONFIRM_TOKEN
    )
    symbol = _first(env, ("GML1_MT5_SYMBOL", "MT5_SYMBOL"))
    global_volume = _float(env, "GML1_MT5_VOLUME")
    volumes: dict[str, float | None] = {}
    for comp in SLEEVES:
        volumes[comp] = _float(env, f"GML1_MT5_VOLUME_{comp}")
        if volumes[comp] is None:
            volumes[comp] = global_volume

    historical_dir_raw = env.get("GML1_HISTORICAL_RESULTS_DIR", "").strip()
    historical_dir = (
        Path(historical_dir_raw).expanduser()
        if historical_dir_raw
        else repo_root / "outputs/gold_ml_v1/research_challenger_local_runtime"
    )

    errors: list[str] = []
    if discord_enabled and not webhook:
        errors.append("Discord is enabled but no webhook URL was found in Files/.env")
    if mt5_enabled:
        if not symbol:
            errors.append("GML1_MT5_SYMBOL is required when MT5 execution is enabled")
        missing_volumes = [
            comp for comp, value in volumes.items() if value is None or value <= 0
        ]
        if missing_volumes:
            errors.append(
                "positive MT5 volume is required for: " + ", ".join(missing_volumes)
            )
        if not mt5_dry_run and not mt5_live_confirmed:
            errors.append(
                "real MT5 orders require GML1_MT5_LIVE_CONFIRM=" + LIVE_CONFIRM_TOKEN
            )

    login = _int(env, "GML1_MT5_LOGIN")
    deviation = int(_int(env, "GML1_MT5_DEVIATION_POINTS", 50) or 50)
    max_lag = int(_int(env, "GML1_MT5_MAX_ENTRY_LAG_SECONDS", 180) or 180)
    max_positions = int(_int(env, "GML1_MT5_MAX_TOTAL_POSITIONS", 1) or 1)
    magic_base = int(_int(env, "GML1_MT5_MAGIC_BASE", 982200) or 982200)
    if deviation < 0:
        errors.append("GML1_MT5_DEVIATION_POINTS must be non-negative")
    if max_lag < 60:
        errors.append("GML1_MT5_MAX_ENTRY_LAG_SECONDS must be at least 60")
    if max_positions < 1 or max_positions > 4:
        errors.append("GML1_MT5_MAX_TOTAL_POSITIONS must be between 1 and 4")

    filling = env.get("GML1_MT5_FILLING_MODE", "AUTO").strip().upper()
    if filling not in {"AUTO", "FOK", "IOC", "RETURN"}:
        errors.append("GML1_MT5_FILLING_MODE must be AUTO, FOK, IOC or RETURN")

    return RuntimeSettings(
        env_path=env_path,
        discord_enabled=discord_enabled,
        discord_webhook_url=webhook,
        discord_username=(
            env.get("GML1_DISCORD_USERNAME", "GML1 XAUUSD").strip()
            or "GML1 XAUUSD"
        ),
        mt5_enabled=mt5_enabled,
        mt5_dry_run=mt5_dry_run,
        mt5_live_confirmed=mt5_live_confirmed,
        mt5_symbol=symbol,
        mt5_terminal_path=_first(
            env, ("GML1_MT5_TERMINAL_PATH", "MT5_TERMINAL_PATH")
        ),
        mt5_login=login,
        mt5_password=_first(env, ("GML1_MT5_PASSWORD", "MT5_PASSWORD")),
        mt5_server=_first(env, ("GML1_MT5_SERVER", "MT5_SERVER")),
        mt5_deviation_points=deviation,
        mt5_max_entry_lag_seconds=max_lag,
        mt5_max_total_positions=max_positions,
        mt5_magic_base=magic_base,
        mt5_require_hedging=_bool(env, "GML1_MT5_REQUIRE_HEDGING", True),
        mt5_filling_mode=filling,
        volumes=volumes,
        historical_results_dir=historical_dir.resolve(),
        require_historical_win_rate=_bool(
            env, "GML1_REQUIRE_HISTORICAL_WIN_RATE", True
        ),
        config_errors=tuple(errors),
    )
