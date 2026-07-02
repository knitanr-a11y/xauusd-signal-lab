from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ensure_discord_webhook_env.py"
spec = importlib.util.spec_from_file_location("ensure_discord_webhook_env", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

VALID = "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
LEGACY = "https://discordapp.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def test_valid_webhook_accepts_current_and_legacy_domains() -> None:
    assert module.valid_webhook(VALID)
    assert module.valid_webhook(LEGACY)
    assert not module.valid_webhook("https://example.com/not-a-webhook")


def test_write_env_preserves_other_settings(tmp_path: Path) -> None:
    target = tmp_path / "Files" / ".env"
    target.parent.mkdir(parents=True)
    target.write_text("OTHER_SETTING=1\nDISCORD_WEBHOOK_URL=old\n", encoding="utf-8")
    module.write_env_value(target, VALID)
    text = target.read_text(encoding="utf-8")
    assert "OTHER_SETTING=1" in text
    assert text.count("DISCORD_WEBHOOK_URL=") == 1
    assert VALID in text


def test_resolve_webhook_finds_parent_files_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(module.KEY, raising=False)
    repo_root = tmp_path / "MQL5" / "Files" / "clean" / "repo"
    target = repo_root / "Files" / ".env"
    source = tmp_path / "MQL5" / "Files" / ".env"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(f"DISCORD_WEBHOOK_URL={VALID}\n", encoding="utf-8")
    value, origin = module.resolve_webhook(repo_root, target, interactive=False)
    assert value == VALID
    assert origin == str(source.resolve())


def test_environment_value_has_priority(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(module.KEY, VALID)
    value, origin = module.resolve_webhook(tmp_path, tmp_path / "Files" / ".env", interactive=False)
    assert value == VALID
    assert origin == "WINDOWS_ENVIRONMENT"
