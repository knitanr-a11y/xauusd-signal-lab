#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

_ORIGINAL = Path(__file__).with_name("_send_mt5_order_from_payload_original.py")


def _patch_source(text: str) -> str:
    text = text.replace(
        'Position policies:\n- block_any: block if any open position exists for the broker symbol\n- allow_same_direction: allow additional same-direction positions up to max count/lot; block opposite direction\n- allow_any_until_max: allow any direction up to max count/lot\n',
        'Position policies:\n- block_any: block if any open position exists for the broker symbol\n- allow_same_direction: allow additional same-direction positions up to max count/lot; block opposite direction\n- allow_any_until_max: allow different magic IDs up to max count/lot; block same active magic\n',
        1,
    )
    text = text.replace(
        '    max_symbol_lot: float,\n) -> list[str]:\n',
        '    max_symbol_lot: float,\n    requested_magic: int | None = None,\n) -> list[str]:\n',
        1,
    )
    old = '''    if policy == POSITION_POLICY_ALLOW_ANY_UNTIL_MAX:\n        if after_count > int(max_symbol_positions):\n            errors.append(\n                f"position count limit exceeded: after_count={after_count}; max_symbol_positions={int(max_symbol_positions)}"\n            )\n        if after_lot > float(max_symbol_lot) + 1e-9:\n            errors.append(\n                f"position lot limit exceeded: after_lot={after_lot:.2f}; max_symbol_lot={float(max_symbol_lot):.2f}"\n            )\n        return errors\n'''
    new = '''    if policy == POSITION_POLICY_ALLOW_ANY_UNTIL_MAX:\n        if requested_magic is not None and int(requested_magic) != 0:\n            same_magic_positions = [p for p in positions if clean_int(p.get("magic"), 0) == int(requested_magic)]\n            if same_magic_positions:\n                tickets = ",".join(clean_str(p.get("ticket")) for p in same_magic_positions)\n                comments = " | ".join(clean_str(p.get("comment")) for p in same_magic_positions)\n                errors.append(\n                    f"position policy allow_any_until_max blocked same active magic: requested_magic={int(requested_magic)}; existing_tickets={tickets}; existing_comments={comments}"\n                )\n        if after_count > int(max_symbol_positions):\n            errors.append(\n                f"position count limit exceeded: after_count={after_count}; max_symbol_positions={int(max_symbol_positions)}"\n            )\n        if after_lot > float(max_symbol_lot) + 1e-9:\n            errors.append(\n                f"position lot limit exceeded: after_lot={after_lot:.2f}; max_symbol_lot={float(max_symbol_lot):.2f}"\n            )\n        return errors\n'''
    if old not in text:
        raise RuntimeError("allow_any_until_max block not found")
    text = text.replace(old, new, 1)
    text = text.replace(
        '                    max_symbol_lot=float(args.max_symbol_lot),\n                )\n',
        '                    max_symbol_lot=float(args.max_symbol_lot),\n                    requested_magic=magic,\n                )\n',
        1,
    )
    return text


def _run() -> None:
    source = _patch_source(_ORIGINAL.read_text(encoding="utf-8"))
    globals_dict = {
        "__name__": __name__,
        "__file__": str(_ORIGINAL),
        "__package__": None,
        "__cached__": None,
    }
    exec(compile(source, str(_ORIGINAL), "exec"), globals_dict)


_run()
