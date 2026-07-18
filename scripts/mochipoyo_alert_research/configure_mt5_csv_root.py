from __future__ import annotations

import os
import tempfile
from pathlib import Path

from mt5_csv_contract import FILE_MAP


def default_local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip() or tempfile.gettempdir()
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def update_env(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    result: list[str] = []
    replaced = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            result.append(f"{key}={value}")
            replaced = True
        else:
            result.append(line)
    if not replaced:
        if result and result[-1] != "":
            result.append("")
        result.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(result).rstrip() + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    local_root = default_local_root()
    env_path = local_root / ".env"
    print("Mochipoyo MT5 CSV root configuration")
    print("Paste the MQL5\\Files folder. Quotes are accepted.")
    raw = input("MT5 Files folder: ").strip().strip('"')
    root = Path(raw).expanduser()
    if not root.is_dir():
        print("[ERROR] Folder does not exist.")
        return 2
    missing = []
    for files in FILE_MAP.values():
        for filename in files.values():
            if not (root / filename).is_file():
                missing.append(filename)
    if missing:
        print("[ERROR] Required CSV files are missing:")
        for filename in sorted(set(missing)):
            print(f"  {filename}")
        return 2
    update_env(env_path, "MT5_FILES_ROOT", str(root.resolve()))
    longest = max(len(str(root.resolve() / name)) for group in FILE_MAP.values() for name in group.values())
    print("[PASS] MT5 CSV root saved to the local Mochipoyo .env")
    print(f"Validated files: {sum(len(v) for v in FILE_MAP.values())}")
    print(f"Longest input path length: {longest}")
    print("CSV files were not modified or copied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
