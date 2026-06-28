from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from live_settings import RuntimeSettings, SLEEVES, load_runtime_settings

AUTOTRADE_SYMBOL = "GOLD#"
AUTOTRADE_VOLUME = 0.01


def apply_autotrade_profile(settings: RuntimeSettings) -> RuntimeSettings:
    return replace(
        settings,
        mt5_symbol=AUTOTRADE_SYMBOL,
        volumes={comp: AUTOTRADE_VOLUME for comp in SLEEVES},
    )


def load_autotrade_settings(live_dir: Path, repo_root: Path) -> RuntimeSettings:
    return apply_autotrade_profile(load_runtime_settings(live_dir, repo_root))


def profile_payload() -> dict[str, object]:
    return {
        "symbol": AUTOTRADE_SYMBOL,
        "volume_by_sleeve": {comp: AUTOTRADE_VOLUME for comp in SLEEVES},
    }
