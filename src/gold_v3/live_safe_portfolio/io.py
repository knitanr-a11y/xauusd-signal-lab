from __future__ import annotations

from pathlib import Path
import json
from typing import Iterable

from .models import Candidate, Resolution


def read_jsonl(path: str | Path) -> list[dict]:
    out: list[dict] = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"{path}:{lineno}: each line must be an object")
        out.append(raw)
    return out


def read_candidates(path: str | Path) -> list[Candidate]:
    return [Candidate.from_dict(raw) for raw in read_jsonl(path)]


def read_resolutions(path: str | Path) -> list[Resolution]:
    return [Resolution.from_dict(raw) for raw in read_jsonl(path)]


def append_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
