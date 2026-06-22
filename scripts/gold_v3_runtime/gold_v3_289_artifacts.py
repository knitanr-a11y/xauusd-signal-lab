#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 local LightGBM artifact loader.

Normal operation uses raw model text produced locally from the existing closed
`goldsharp_*.csv` history. Legacy gzip/bz2 split packages remain readable only
for audit reproduction; no model download or fallback is performed.
"""
from __future__ import annotations
import base64,bz2,gzip
from pathlib import Path
import lightgbm as lgb

def read_joined_text(path:Path)->str:
 if path.exists(): return path.read_text(encoding='ascii').strip()
 parts=sorted(path.parent.glob(path.name+'.part*'))
 if not parts: raise FileNotFoundError(path)
 return ''.join(p.read_text(encoding='ascii').strip() for p in parts)

def decoded_model_bytes(path:Path)->bytes:
 packed=base64.b64decode(read_joined_text(path))
 return bz2.decompress(packed) if '.bz2.b64' in path.name else gzip.decompress(packed)

def load_frozen_booster(path:Path)->lgb.Booster:
 if path.suffix=='.txt': return lgb.Booster(model_file=str(path))
 return lgb.Booster(model_str=decoded_model_bytes(path).decode('utf-8'))
