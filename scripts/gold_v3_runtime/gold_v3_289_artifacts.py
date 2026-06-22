#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frozen model artifact loader for GOLD V3 Stage289.

Large base64 model artifacts may be stored either as one file or split into
`.partNNN` files. Parts are concatenated in lexical order and decoded without
writing temporary files. Both gzip and bz2 packages are supported.
"""
from __future__ import annotations

import base64
import bz2
import gzip
from pathlib import Path

import lightgbm as lgb


def read_joined_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="ascii").strip()
    parts = sorted(path.parent.glob(path.name + ".part*"))
    if not parts:
        raise FileNotFoundError(path)
    return "".join(p.read_text(encoding="ascii").strip() for p in parts)


def decoded_model_bytes(path: Path) -> bytes:
    packed = base64.b64decode(read_joined_text(path))
    if ".bz2.b64" in path.name:
        return bz2.decompress(packed)
    return gzip.decompress(packed)


def load_frozen_booster(path: Path) -> lgb.Booster:
    return lgb.Booster(model_str=decoded_model_bytes(path).decode("utf-8"))
