from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
V2_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun.py"

spec = importlib.util.spec_from_file_location("ff05_recovery_rerun_base", V2_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load prior rerun module: {V2_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

REAL_LOCAL_BASE = module.LOCAL_BASE


def _copy_prerequisite_latest(isolated_local_base: Path) -> list[str]:
    """Mirror only each prerequisite's LATEST directory, never historical archives."""
    isolated_local_base.mkdir(parents=True, exist_ok=True)
    allowed_prefixes = ("01_", "02_", "03_", "04_")
    copied: list[str] = []
    if not REAL_LOCAL_BASE.is_dir():
        raise FileNotFoundError(f"real prerequisite output root missing: {REAL_LOCAL_BASE}")

    for source_root in sorted(REAL_LOCAL_BASE.iterdir(), key=lambda p: p.name.lower()):
        if not source_root.is_dir() or not source_root.name.startswith(allowed_prefixes):
            continue
        source_latest = source_root / "LATEST"
        if not source_latest.is_dir():
            continue
        target_root = isolated_local_base / source_root.name
        target_latest = target_root / "LATEST"
        if target_root.exists():
            shutil.rmtree(target_root)
        target_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_latest, target_latest)
        copied.append(source_root.name)

    if not any(name.startswith("04_") for name in copied):
        raise RuntimeError(
            "FF04 prerequisite LATEST output was not mirrored into isolated LOCALAPPDATA"
        )
    return sorted(copied)


def create_isolated_terminal_v4(output_root: Path, manifest):
    """Build an isolated Windows profile using only merged BTC history and LATEST gates."""
    profile_root = output_root / "_isolated_profile_v4"
    if profile_root.exists():
        shutil.rmtree(profile_root)

    roaming = profile_root / "AppData" / "Roaming"
    local = profile_root / "AppData" / "Local"
    temp_root = local / "Temp"
    temp_root.mkdir(parents=True, exist_ok=True)

    isolated_output_base = local / "xauusd_signal_lab" / "btc_ml_v1" / "outputs"
    mirrored_prerequisites = _copy_prerequisite_latest(isolated_output_base)

    terminal_roots = {
        roaming / "MetaQuotes" / "Terminal" / "FF05_MERGED_FULL_HISTORY" / "MQL5" / "Files",
        local / "MetaQuotes" / "Terminal" / "FF05_MERGED_FULL_HISTORY" / "MQL5" / "Files",
        profile_root / "MetaQuotes" / "Terminal" / "FF05_MERGED_FULL_HISTORY" / "MQL5" / "Files",
    }
    for files_dir in terminal_roots:
        files_dir.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}
    for row in manifest.to_dict(orient="records"):
        source = Path(str(row["merged_path"]))
        primary_target = (
            roaming
            / "MetaQuotes"
            / "Terminal"
            / "FF05_MERGED_FULL_HISTORY"
            / "MQL5"
            / "Files"
            / source.name
        )
        for files_dir in terminal_roots:
            target = files_dir / source.name
            shutil.copyfile(source, target)
            os.utime(target, None)
            actual_sha = module.sha256_path(target)
            if actual_sha != str(row["merged_sha256"]):
                raise RuntimeError(f"isolated copy SHA mismatch: {target}")
        copied[str(row["timeframe"])] = str(primary_target)

    drive, tail = os.path.splitdrive(str(profile_root))
    environment_paths = {
        "USERPROFILE": str(profile_root),
        "HOME": str(profile_root),
        "APPDATA": str(roaming),
        "LOCALAPPDATA": str(local),
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
        "HOMEDRIVE": drive or "C:",
        "HOMEPATH": tail or str(profile_root),
        "BTC_FF05_ISOLATED_PREREQUISITES": ";".join(mirrored_prerequisites),
        "BTC_FF05_RECOVERY_MODE": "MERGED_FULL_HISTORY_ISOLATED_PROFILE_V4",
    }

    probe_env = os.environ.copy()
    probe_env.update(environment_paths)
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os; from pathlib import Path; "
                "print(Path.home()); print(os.environ.get('APPDATA')); "
                "print(os.environ.get('LOCALAPPDATA'))"
            ),
        ],
        env=probe_env,
        cwd=module.ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    expected_probe = [str(profile_root), str(roaming), str(local)]
    actual_probe = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
    if probe.returncode != 0 or actual_probe[:3] != expected_probe:
        raise RuntimeError(
            "isolated environment probe failed: "
            f"returncode={probe.returncode} actual={actual_probe} expected={expected_probe} "
            f"stderr={probe.stderr.strip()}"
        )

    return profile_root, copied, environment_paths


module.create_isolated_terminal = create_isolated_terminal_v4

if __name__ == "__main__":
    raise SystemExit(module.main())
