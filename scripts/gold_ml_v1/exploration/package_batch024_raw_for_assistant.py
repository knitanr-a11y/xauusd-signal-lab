from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

FIXED_ZIP_TIME = (2026, 6, 25, 0, 0, 0)
ARCHIVE_NAME = "GOLD_ML_V1_BATCH024_FROZEN_RAW_INPUT.zip"
MANIFEST_NAME = "batch024_input_manifest.json"
SUMMARY_NAME = "LATEST_RUN_SUMMARY.txt"
ERROR_NAME = "PACKAGE_RUN_ERROR.txt"
PRIMARY_UPLOAD_POINTER = Path("outputs/gold_ml_v1/next_action/PRIMARY_UPLOAD_PATH.txt")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def count_csv_rows(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for _ in handle:
            count += 1
    return max(0, count - 1)


def backup_output(output_dir: Path) -> Path | None:
    if not output_dir.exists() or not any(output_dir.iterdir()):
        output_dir.mkdir(parents=True, exist_ok=True)
        return None
    backup_root = output_dir.parent / f"{output_dir.name}_backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = backup_root / stamp
    suffix = 1
    while destination.exists():
        destination = backup_root / f"{stamp}_{suffix:02d}"
        suffix += 1
    shutil.move(str(output_dir), str(destination))
    output_dir.mkdir(parents=True, exist_ok=True)
    return destination


def deterministic_add_file(zf: zipfile.ZipFile, source: Path, archive_name: str) -> None:
    info = zipfile.ZipInfo(archive_name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with source.open("rb") as src, zf.open(info, "w", force_zip64=True) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def deterministic_add_bytes(zf: zipfile.ZipFile, data: bytes, archive_name: str) -> None:
    info = zipfile.ZipInfo(archive_name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zf.writestr(info, data)


def run(raw_dir: Path, config_path: Path, output_dir: Path, repo_root: Path) -> int:
    config = load_json(config_path)
    expected = config["input_contract"]["expected_sha256"]
    filenames = config["input_contract"]["raw_dir_filenames"]
    required_timeframes = ("M1", "M15", "H1")

    backup = backup_output(output_dir)
    archive_path = output_dir / ARCHIVE_NAME
    manifest_path = output_dir / MANIFEST_NAME
    file_records: list[dict[str, Any]] = []

    for timeframe in required_timeframes:
        filename = str(filenames[timeframe])
        source = raw_dir / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        actual_hash = sha256_file(source)
        expected_hash = str(expected[filename])
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"Frozen RAW hash mismatch for {filename}: {actual_hash} != {expected_hash}"
            )
        file_records.append(
            {
                "timeframe": timeframe,
                "filename": filename,
                "size_bytes": source.stat().st_size,
                "data_rows": count_csv_rows(source),
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "hash_match": True,
            }
        )

    manifest = {
        "record_id": "GML1-BATCH024-FROZEN-RAW-INPUT-PACKAGE",
        "status": "PASS",
        "created_local": datetime.now().isoformat(timespec="seconds"),
        "purpose": "INPUT_TRANSFER_TO_ASSISTANT_FOR_ASSISTANT_SIDE_EXPLORATION_ONLY",
        "exploration_executed_locally": False,
        "raw_dir": str(raw_dir),
        "frozen_config_path": str(config_path),
        "frozen_config_sha256": sha256_file(config_path),
        "files": file_records,
        "existing_frozen_nine_modified": False,
        "audit_only": True,
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")

    with zipfile.ZipFile(
        archive_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as zf:
        for record in file_records:
            deterministic_add_file(zf, raw_dir / record["filename"], record["filename"])
        deterministic_add_bytes(zf, manifest_text.encode("utf-8"), MANIFEST_NAME)
        deterministic_add_file(zf, config_path, "exploration_batch024_frozen_config.json")

    archive_hash = sha256_file(archive_path)
    summary_lines = [
        "GOLD_ML_V1 BATCH024 RAW INPUT PACKAGE",
        "status=PASS",
        f"created_local={datetime.now().isoformat(timespec='seconds')}",
        f"archive={archive_path}",
        f"archive_size_bytes={archive_path.stat().st_size}",
        f"archive_sha256={archive_hash}",
        f"previous_output_backup={backup if backup else 'NONE'}",
        "exploration_executed_locally=FALSE",
        "purpose=TRANSFER_FROZEN_RAW_INPUT_TO_ASSISTANT",
        "existing_frozen_nine_modified=FALSE",
        "",
        "Validated files:",
    ]
    for record in file_records:
        summary_lines.append(
            f"{record['timeframe']} filename={record['filename']} rows={record['data_rows']} "
            f"size={record['size_bytes']} sha256={record['sha256']} hash_match=TRUE"
        )
    summary_lines.extend(
        [
            "",
            "Next:",
            "Upload the selected ZIP to ChatGPT. The assistant performs exploration first.",
            "Do not interpret this packaging PASS as an exploration result.",
        ]
    )
    (output_dir / SUMMARY_NAME).write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (output_dir / ERROR_NAME).write_text("status=PASS\nerror=NONE\n", encoding="utf-8")

    pointer = repo_root / PRIMARY_UPLOAD_POINTER
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(str(archive_path.resolve()) + "\n", encoding="utf-8")

    print("=" * 72)
    print("GOLD_ML_V1 BATCH024 RAW INPUT PACKAGE - PASS")
    print(f"Archive: {archive_path}")
    print(f"Archive SHA256: {archive_hash}")
    print("No exploration was executed locally.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package frozen Batch024 RAW inputs for assistant-side exploration"
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    repo_root = args.repo_root.resolve()
    try:
        return run(
            args.raw_dir.resolve(),
            args.config.resolve(),
            output_dir,
            repo_root,
        )
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        pointer = repo_root / PRIMARY_UPLOAD_POINTER
        if pointer.exists():
            pointer.unlink()
        error = f"{type(exc).__name__}: {exc}"
        (output_dir / ERROR_NAME).write_text(
            f"status=FAIL\nerror={error}\n\n{traceback.format_exc()}", encoding="utf-8"
        )
        (output_dir / SUMMARY_NAME).write_text(
            "GOLD_ML_V1 BATCH024 RAW INPUT PACKAGE\n"
            "status=FAIL\n"
            f"error={error}\n"
            "exploration_executed_locally=FALSE\n",
            encoding="utf-8",
        )
        print(f"[FAIL] {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
