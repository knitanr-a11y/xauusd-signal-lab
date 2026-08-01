from __future__ import annotations

import tempfile
from pathlib import Path

from . import source_audit

HEADER = "time,open,high,low,close,tick_volume,spread,real_volume\n"


def write(path: Path, rows: list[str]) -> None:
    path.write_text(HEADER + "".join(rows), encoding="utf-8")


def row(timestamp: str, close: str = "100.5") -> str:
    return f"{timestamp},100,101,99,{close},10,2,0\n"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gu1_source_audit_") as tmp:
        root = Path(tmp)
        old = root / "old.csv"
        sharp = root / "sharp.csv"
        write(
            old,
            [
                row("2026.01.01 00:00:00"),
                row("2026.01.01 00:01:00"),
            ],
        )
        write(
            sharp,
            [
                row("2026.01.01 00:01:00"),
                row("2026.01.01 00:02:00"),
            ],
        )
        valid = source_audit.inspect_csv(old)
        if not (
            valid.get("schema_ok")
            and valid.get("strictly_increasing")
            and valid.get("malformed_row_count") == 0
            and valid.get("invalid_ohlc_row_count") == 0
        ):
            raise RuntimeError(f"VALID_SOURCE_SELF_TEST_FAILED: {valid}")

        exact = source_audit.compare_overlap(old, sharp)
        if not exact.get("exact_overlap") or exact.get("overlap_rows") != 1:
            raise RuntimeError(f"EXACT_OVERLAP_SELF_TEST_FAILED: {exact}")

        write(
            sharp,
            [
                row("2026.01.01 00:01:00", close="100.6"),
                row("2026.01.01 00:02:00"),
            ],
        )
        mismatch = source_audit.compare_overlap(old, sharp)
        if mismatch.get("exact_overlap") or mismatch.get("mismatch_rows") != 1:
            raise RuntimeError(f"MISMATCH_SELF_TEST_FAILED: {mismatch}")

        duplicate = root / "duplicate.csv"
        write(
            duplicate,
            [
                row("2026.01.01 00:00:00"),
                row("2026.01.01 00:00:00"),
            ],
        )
        duplicate_report = source_audit.inspect_csv(duplicate)
        if duplicate_report.get("strictly_increasing") or duplicate_report.get("duplicate_time_count") != 1:
            raise RuntimeError(f"DUPLICATE_SELF_TEST_FAILED: {duplicate_report}")

    print("[OK] GU1 source audit self-test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
