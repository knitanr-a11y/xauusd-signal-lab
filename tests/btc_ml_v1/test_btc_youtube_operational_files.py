from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_btc_youtube_candidates_operational_forever.py"
spec = importlib.util.spec_from_file_location("run_btc_youtube_candidates_operational_forever", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_resolve_exact_files(tmp_path: Path) -> None:
    for name in ["btcusdsharp_m5.csv", "btcusdsharp_m15.csv", "btcusdsharp_h4.csv"]:
        (tmp_path / name).write_text("time,open,high,low,close\n", encoding="utf-8")
    assert module.resolve_live_csv(tmp_path, "m5").name == "btcusdsharp_m5.csv"
    assert module.resolve_live_csv(tmp_path, "m15").name == "btcusdsharp_m15.csv"
    assert module.resolve_live_csv(tmp_path, "h4").name == "btcusdsharp_h4.csv"


def test_resolve_alias_file(tmp_path: Path) -> None:
    (tmp_path / "btcusdsharp_5m.csv").write_text("time,open,high,low,close\n", encoding="utf-8")
    assert module.resolve_live_csv(tmp_path, "m5").name == "btcusdsharp_5m.csv"
