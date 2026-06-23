from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass(frozen=True)
class StrictShortConfig:
    base_candidate_name: str = "SHORT_EXHAUST_Q90_EMA20_E225_CD120"
    score_max: float = 2.992581130893
    risk_m15_ret4_mean_max: float = 0.410970621210


@dataclass(frozen=True)
class AdmissionConfig:
    common_realized_dd_max: float = 30.0
    shared_candidate_cooldown_hours: float = 12.0
    strict_short_realized_dd_max: float = 10.0
    candidate_loss_lockout_hours: float = 24.0
    priorities: dict[str, int] = field(default_factory=lambda: {
        "BASE": 0,
        "STAGE280": 10,
        "STAGE281": 20,
        "SHORT_STRICT": 60,
    })


@dataclass(frozen=True)
class RolloverConfig:
    enabled: bool = True
    sources: tuple[str, ...] = ("BASE",)
    blocked_server_hours: tuple[int, ...] = (0, 1)


@dataclass(frozen=True)
class RuntimeGuardConfig:
    entry_spread_cap_usd: float = 0.30
    quote_age_seconds_max: float = 2.0
    max_adverse_fill_slippage_usd: float = 0.20
    enforcement: str = "DIAGNOSTIC_ONLY"


@dataclass(frozen=True)
class Flags:
    audit_only: bool = True
    live_ready: bool = False
    final_signal: bool = False
    mt5_order: bool = False
    discord_notify: bool = False
    partial_close: bool = False


@dataclass(frozen=True)
class LiveSafeConfig:
    status: str = "GOLD_V3_286_SAFE_PORTFOLIO_LIVE_SHADOW_AUDIT_ONLY"
    time_basis: str = "MT5_SERVER_NAIVE"
    strict_short: StrictShortConfig = field(default_factory=StrictShortConfig)
    admission: AdmissionConfig = field(default_factory=AdmissionConfig)
    rollover: RolloverConfig = field(default_factory=RolloverConfig)
    runtime_guards: RuntimeGuardConfig = field(default_factory=RuntimeGuardConfig)
    flags: Flags = field(default_factory=Flags)

    def validate(self) -> None:
        if not self.flags.audit_only:
            raise ValueError("audit_only must remain true")
        forbidden = {
            "live_ready": self.flags.live_ready,
            "final_signal": self.flags.final_signal,
            "mt5_order": self.flags.mt5_order,
            "discord_notify": self.flags.discord_notify,
            "partial_close": self.flags.partial_close,
        }
        enabled = [name for name, value in forbidden.items() if value]
        if enabled:
            raise ValueError(f"forbidden runtime flags enabled: {enabled}")
        if self.runtime_guards.enforcement not in {"DIAGNOSTIC_ONLY", "OFF"}:
            raise ValueError("runtime guards may only be DIAGNOSTIC_ONLY or OFF")
        required = {"BASE", "STAGE280", "STAGE281", "SHORT_STRICT"}
        if set(self.admission.priorities) != required:
            raise ValueError(f"priorities must contain exactly {sorted(required)}")


def _construct(data: dict[str, Any]) -> LiveSafeConfig:
    cfg = LiveSafeConfig(
        status=data.get("status", LiveSafeConfig.status),
        time_basis=data.get("time_basis", "MT5_SERVER_NAIVE"),
        strict_short=StrictShortConfig(**data.get("strict_short", {})),
        admission=AdmissionConfig(**data.get("admission", {})),
        rollover=RolloverConfig(**{
            **data.get("rollover", {}),
            "sources": tuple(data.get("rollover", {}).get("sources", ["BASE"])),
            "blocked_server_hours": tuple(data.get("rollover", {}).get("blocked_server_hours", [0, 1])),
        }),
        runtime_guards=RuntimeGuardConfig(**data.get("runtime_guards", {})),
        flags=Flags(**data.get("flags", {})),
    )
    cfg.validate()
    return cfg


def load_config(path: str | Path) -> LiveSafeConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return _construct(data)
