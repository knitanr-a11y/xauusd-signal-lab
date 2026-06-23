#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Iterable

TOKENS = {
    "threshold": b"0.5927349103795366",
    "fixture": b"0.5949591748604749",
    "auc": b"0.6904307891978236",
    "pr_auc": b"0.08009367826075599",
    "candidate": b"REV_LONG_Q95_BRK6_E175",
    "stage280": b"STAGE280",
    "lgbm": b"LGBMClassifier",
}
TEXT_EXTENSIONS = {
    ".py", ".json", ".txt", ".md", ".csv", ".ipynb", ".bat", ".ps1",
    ".yml", ".yaml", ".log", ".ini", ".cfg", ".toml",
}
MODEL_EXTENSIONS = {
    ".model", ".bin", ".pkl", ".pickle", ".joblib", ".txt", ".json",
    ".cbm", ".onnx",
}
FORBIDDEN_MARKERS = (
    "gold_v2", "old_gold", "disc8", "stage41", "legacy_gold",
)
MAX_TEXT_BYTES = 8 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-results", type=int, default=200)
    return parser.parse_args()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def repo_root_from_git(start: Path) -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], start)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return Path(result.stdout.decode("utf-8", errors="replace").strip()).resolve()


def forbidden(path_text: str) -> bool:
    lower = path_text.lower().replace("\\", "/")
    return any(marker in lower for marker in FORBIDDEN_MARKERS)


def token_hits(data: bytes) -> list[str]:
    return [name for name, token in TOKENS.items() if token in data]


def score_result(path_text: str, hits: list[str], size: int) -> int:
    score = 0
    weights = {
        "threshold": 20,
        "fixture": 20,
        "auc": 15,
        "pr_auc": 15,
        "candidate": 10,
        "stage280": 4,
        "lgbm": 3,
    }
    score += sum(weights[name] for name in hits)
    lower = path_text.lower()
    if "stage280" in lower:
        score += 8
    if "rev" in lower:
        score += 4
    if "model" in lower:
        score += 5
    if "train" in lower or "audit" in lower:
        score += 4
    if Path(lower).suffix in MODEL_EXTENSIONS:
        score += 2
    if size == 0:
        score -= 5
    return score


def candidate_roots(repo_root: Path) -> list[Path]:
    roots: list[Path] = [repo_root]
    repo_parent = repo_root.parent
    for child in repo_parent.iterdir():
        if child.is_dir() and "xauusd-signal-lab" in child.name.lower():
            roots.append(child.resolve())
    current = repo_root
    for _ in range(8):
        if current.name.lower() == "files" and current.parent.name.lower() == "mql5":
            break
        if current.parent == current:
            break
        current = current.parent
    if current.name.lower() == "files":
        roots.append(current.resolve())
        fx = current / "FX_OUTPUTS" / "gold_v3"
        if fx.exists():
            roots.append(fx.resolve())
    dedup: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).lower()
        if key not in seen and root.exists():
            seen.add(key)
            dedup.append(root)
    return dedup


def iter_files(root: Path, repo_root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        relative_text = str(current).lower().replace("\\", "/")
        dirnames[:] = [
            name
            for name in dirnames
            if name not in {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
            and not forbidden(relative_text + "/" + name)
        ]
        try:
            relative_depth = len(current.relative_to(root).parts)
        except ValueError:
            relative_depth = 0
        if root != repo_root and relative_depth > 4:
            dirnames[:] = []
        for filename in filenames:
            path = current / filename
            if forbidden(str(path)):
                continue
            lower = filename.lower()
            suffix = path.suffix.lower()
            interesting_name = any(
                token in lower
                for token in ("stage280", "rev_long", "rev", "model", "booster", "train")
            )
            if suffix in TEXT_EXTENSIONS or (interesting_name and suffix in MODEL_EXTENSIONS):
                yield path


def scan_filesystem(repo_root: Path) -> tuple[list[dict], list[str]]:
    results: list[dict] = []
    scanned_roots: list[str] = []
    visited: set[str] = set()
    for root in candidate_roots(repo_root):
        scanned_roots.append(str(root))
        for path in iter_files(root, repo_root):
            key = str(path.resolve()).lower()
            if key in visited:
                continue
            visited.add(key)
            try:
                stat = path.stat()
            except OSError:
                continue
            hits: list[str] = []
            if stat.st_size <= MAX_TEXT_BYTES and path.suffix.lower() in TEXT_EXTENSIONS:
                try:
                    hits = token_hits(path.read_bytes())
                except OSError:
                    hits = []
            lower_name = path.name.lower()
            model_like = (
                path.suffix.lower() in MODEL_EXTENSIONS
                and any(word in lower_name for word in ("stage280", "rev", "model", "booster"))
            )
            if not hits and not model_like:
                continue
            results.append(
                {
                    "source": "filesystem",
                    "path": str(path.resolve()),
                    "size": int(stat.st_size),
                    "mtime": int(stat.st_mtime),
                    "token_hits": hits,
                    "score": score_result(str(path), hits, int(stat.st_size)),
                }
            )
    return results, scanned_roots


def parse_rev_list(output: bytes) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for raw_line in output.decode("utf-8", errors="replace").splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split(" ", 1)
        sha = parts[0].strip()
        path = parts[1].strip() if len(parts) > 1 else ""
        if path and forbidden(path):
            continue
        rows.append((sha, path))
    return rows


def read_blob(repo_root: Path, sha: str, size: int) -> bytes:
    if size > MAX_TEXT_BYTES:
        return b""
    result = run(["git", "cat-file", "blob", sha], repo_root)
    return result.stdout if result.returncode == 0 else b""


def scan_git_history(repo_root: Path) -> list[dict]:
    results: list[dict] = []
    rev = run(["git", "rev-list", "--objects", "--all"], repo_root)
    if rev.returncode == 0:
        for sha, path in parse_rev_list(rev.stdout):
            lower_path = path.lower()
            suffix = Path(path).suffix.lower()
            interesting_path = any(
                word in lower_path
                for word in ("stage280", "rev_long", "rev", "model", "train", "audit")
            )
            if path and not interesting_path and suffix not in TEXT_EXTENSIONS:
                continue
            size_result = run(["git", "cat-file", "-s", sha], repo_root)
            if size_result.returncode != 0:
                continue
            try:
                size = int(size_result.stdout.strip())
            except ValueError:
                continue
            data = read_blob(repo_root, sha, size)
            hits = token_hits(data) if data else []
            model_like = interesting_path and suffix in MODEL_EXTENSIONS
            if not hits and not model_like:
                continue
            results.append(
                {
                    "source": "git_reachable_blob",
                    "blob_sha": sha,
                    "path": path,
                    "size": size,
                    "token_hits": hits,
                    "score": score_result(path, hits, size),
                }
            )

    fsck = run(["git", "fsck", "--full", "--no-reflogs", "--unreachable"], repo_root)
    for line in fsck.stdout.decode("utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] != "blob":
            continue
        sha = parts[2]
        size_result = run(["git", "cat-file", "-s", sha], repo_root)
        if size_result.returncode != 0:
            continue
        try:
            size = int(size_result.stdout.strip())
        except ValueError:
            continue
        data = read_blob(repo_root, sha, size)
        hits = token_hits(data) if data else []
        if not hits:
            continue
        results.append(
            {
                "source": "git_unreachable_blob",
                "blob_sha": sha,
                "path": "",
                "size": size,
                "token_hits": hits,
                "score": score_result(sha, hits, size),
            }
        )
    return results


def main() -> int:
    args = parse_args()
    start = Path(args.repo_root).expanduser().resolve() if args.repo_root else Path.cwd()
    repo_root = repo_root_from_git(start)
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else repo_root / "data" / "results" / "stage301_stage280_artifact_recovery.json"
    )

    filesystem_results, roots = scan_filesystem(repo_root)
    git_results = scan_git_history(repo_root)
    all_results = filesystem_results + git_results
    all_results.sort(key=lambda row: (-int(row["score"]), str(row.get("path", ""))))

    exact_token_candidates = [
        row
        for row in all_results
        if {"threshold", "fixture"}.issubset(set(row.get("token_hits", [])))
    ]
    source_candidates = [
        row
        for row in all_results
        if row.get("source") != "filesystem"
        or str(row.get("path", "")).lower().endswith((".py", ".ipynb", ".json", ".txt"))
    ]

    report = {
        "status": "GOLD_V3_301_STAGE280_ARTIFACT_RECOVERY_READY",
        "repo_root": str(repo_root),
        "scanned_roots": roots,
        "forbidden_paths_skipped": list(FORBIDDEN_MARKERS),
        "summary": {
            "filesystem_candidates": len(filesystem_results),
            "git_candidates": len(git_results),
            "exact_token_candidates": len(exact_token_candidates),
            "total_candidates": len(all_results),
        },
        "exact_token_candidates": exact_token_candidates[: args.max_results],
        "ranked_candidates": source_candidates[: args.max_results],
        "decision": (
            "ORIGINAL_SOURCE_OR_ARTIFACT_CANDIDATE_FOUND"
            if exact_token_candidates
            else "ORIGINAL_SOURCE_NOT_FOUND_IN_SCANNED_LOCATIONS"
        ),
        "note": "Recovery-only diagnostic. No model, threshold, signal, order, or Discord state is changed.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
