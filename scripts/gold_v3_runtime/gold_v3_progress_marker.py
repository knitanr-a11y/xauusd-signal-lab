#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from datetime import datetime


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='')
    ap.add_argument('--message', default='')
    args = ap.parse_args()
    stage = str(args.stage).strip() or 'UNKNOWN'
    msg = str(args.message).strip() or 'progress'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[progress][{now}][Stage{stage}] {msg}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
