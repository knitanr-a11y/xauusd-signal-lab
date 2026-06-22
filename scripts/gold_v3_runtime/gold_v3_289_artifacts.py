#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read frozen Stage289 artifacts stored as one text file or ordered text parts."""
from __future__ import annotations
import base64
import gzip
from pathlib import Path
import lightgbm as lgb


def read_artifact_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="ascii")
    parts = sorted(path.parent.glob(path.name + ".part*"))
    if not parts:
        raise FileNotFoundError(path)
    return "".join(part.read_text(encoding="ascii") for part in parts)


def load_frozen_booster(path: Path) -> lgb.Booster:
    decoded = gzip.decompress(base64.b64decode(read_artifact_text(path))).decode("utf-8")
    return lgb.Booster(model_str=decoded)
