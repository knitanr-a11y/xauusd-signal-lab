from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "scripts/gold_ml_v1/exploration"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
if str(ROOT / "scripts/gold_ml_v1") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/gold_ml_v1"))

from package_batch024_raw_for_assistant import ARCHIVE_NAME, run
from run_next_local import write_upload_file


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Batch024RawPackageTests(unittest.TestCase):
    def test_package_validates_hashes_and_does_not_run_exploration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            raw = repo / "raw"
            output = repo / "outputs/gold_ml_v1/exploration_batch024_data_upload"
            raw.mkdir(parents=True)
            files = {}
            for timeframe, name in {
                "M1": "m1.csv",
                "M15": "m15.csv",
                "H1": "h1.csv",
            }.items():
                path = raw / name
                path.write_text("time,open,high,low,close,tick_volume,spread\n2026.01.01 00:00:00,1,2,0,1,10,5\n", encoding="utf-8")
                files[timeframe] = name

            config = {
                "input_contract": {
                    "raw_dir_filenames": files,
                    "expected_sha256": {
                        name: sha256(raw / name) for name in files.values()
                    },
                }
            }
            config_path = repo / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = run(raw, config_path, output, repo)
            self.assertEqual(result, 0)
            archive = output / ARCHIVE_NAME
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
                self.assertEqual(
                    names,
                    {
                        "m1.csv",
                        "m15.csv",
                        "h1.csv",
                        "batch024_input_manifest.json",
                        "exploration_batch024_frozen_config.json",
                    },
                )
                manifest = json.loads(zf.read("batch024_input_manifest.json"))
            self.assertFalse(manifest["exploration_executed_locally"])
            self.assertTrue(all(item["hash_match"] for item in manifest["files"]))
            pointer = repo / "outputs/gold_ml_v1/next_action/PRIMARY_UPLOAD_PATH.txt"
            self.assertEqual(Path(pointer.read_text().strip()), archive.resolve())

    def test_dispatcher_selects_binary_primary_artifact_only_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            phase = repo / "outputs/gold_ml_v1/phase"
            next_dir = repo / "outputs/gold_ml_v1/next_action"
            phase.mkdir(parents=True)
            next_dir.mkdir(parents=True)
            archive = phase / "input.zip"
            archive.write_bytes(b"zip-placeholder")
            (next_dir / "LATEST_NEXT_ACTION.txt").write_text("status=PASS\n", encoding="utf-8")
            (next_dir / "FULL_CONSOLE_LOG.txt").write_text("console\n", encoding="utf-8")
            config = {
                "upload_output_dir": "outputs/gold_ml_v1/phase",
                "upload_filename": "UPLOAD_THIS_GOLD_ML_V1.txt",
                "primary_upload_path": "outputs/gold_ml_v1/phase/input.zip",
                "upload_sections": [],
            }
            mapping = {
                "REPO_ROOT": str(repo),
                "USER_HOME": str(repo),
                "MQL5_FILES": str(repo),
                "RAW_HISTORY_DIR": str(repo),
                "BATCH023_ZIP": str(repo / "batch.zip"),
            }
            selected = write_upload_file(repo, 0, config=config, mapping=mapping)
            self.assertEqual(selected, archive)
            current = Path((next_dir / "CURRENT_UPLOAD_PATH.txt").read_text().strip())
            self.assertEqual(current, archive.resolve())

            failed = write_upload_file(repo, 4, config=config, mapping=mapping)
            self.assertEqual(failed, phase / "UPLOAD_THIS_GOLD_ML_V1.txt")


if __name__ == "__main__":
    unittest.main()
