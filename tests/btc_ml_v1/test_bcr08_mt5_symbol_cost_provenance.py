from __future__ import annotations

import ast
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR08_mt5_symbol_cost_provenance"
    / "python"
    / "run_bcr08_mt5_symbol_cost_provenance.py"
)


def module_constants() -> dict[str, object]:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    namespace: dict[str, object] = {"__name__": "bcr08_static_test"}
    exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace


def test_script_compiles() -> None:
    compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")


def test_forbidden_mt5_functions_absent() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden = {
        "order_send",
        "order_check",
        "positions_get",
        "orders_get",
        "history_orders_get",
        "history_deals_get",
        "symbol_select",
    }
    assert called_attributes.isdisjoint(forbidden)


def test_account_allowlist_excludes_identity_balance_and_pnl() -> None:
    namespace = module_constants()
    allowlist = set(namespace["ACCOUNT_ALLOWLIST"])
    forbidden = set(namespace["FORBIDDEN_ACCOUNT_FIELDS"])
    assert allowlist.isdisjoint(forbidden)
