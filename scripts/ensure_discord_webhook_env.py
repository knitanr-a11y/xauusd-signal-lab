#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
from typing import Iterable

KEY = "DISCORD_WEBHOOK_URL"
ALLOWED_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://canary.discord.com/api/webhooks/",
    "https://ptb.discord.com/api/webhooks/",
)


def valid_webhook(value: str) -> bool:
    value = value.strip()
    return any(value.startswith(prefix) for prefix in ALLOWED_PREFIXES) and len(value) > 60


def read_env_value(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except Exception:
        return ""
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == KEY:
            return value.strip().strip('"').strip("'")
    return ""


def candidate_env_files(repo_root: Path, target: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    candidates: list[Path] = [target, repo_root / ".env"]
    current = repo_root
    for _ in range(6):
        candidates.extend([current / ".env", current / "Files" / ".env"])
        if current.parent == current:
            break
        current = current.parent
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield path


def write_env_value(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8-sig").splitlines()
        except Exception:
            existing = []
    output: list[str] = []
    replaced = False
    for raw in existing:
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _ = line.split("=", 1)
            if key.strip() == KEY:
                if not replaced:
                    output.append(f"{KEY}={value}")
                    replaced = True
                continue
        output.append(raw)
    if not replaced:
        output.append(f"{KEY}={value}")
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    temp.replace(path)


def resolve_webhook(repo_root: Path, target: Path, interactive: bool) -> tuple[str, str]:
    from_environment = os.environ.get(KEY, "").strip()
    if valid_webhook(from_environment):
        return from_environment, "WINDOWS_ENVIRONMENT"

    for path in candidate_env_files(repo_root, target):
        value = read_env_value(path)
        if valid_webhook(value):
            return value, str(path.resolve())

    if not interactive:
        return "", "NOT_FOUND"

    print("Discord Webhook URL が未設定です。")
    print("Discordのチャンネル設定 → 連携サービス → ウェブフック でURLをコピーし、ここへ貼り付けてください。")
    value = getpass.getpass("Discord Webhook URL（入力内容は表示されません）: ").strip()
    if not valid_webhook(value):
        return "", "INVALID_INPUT"
    return value, "INTERACTIVE_INPUT"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find or create the local Discord webhook environment file.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--target-env", type=Path, required=True)
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target = args.target_env if args.target_env.is_absolute() else repo_root / args.target_env
    value, source = resolve_webhook(repo_root, target, interactive=not args.non_interactive)
    if not valid_webhook(value):
        print(f"[ERROR] {KEY} を取得できませんでした。source={source}")
        return 1
    write_env_value(target, value)
    print(f"[OK] Discord Webhook設定を確認しました。保存先: {target}")
    print(f"[OK] source={source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
