from __future__ import annotations

import importlib
from typing import Any, Callable, Iterable

from .models import Candidate


class ProducerContractError(RuntimeError):
    pass


def load_producer(spec: str) -> Callable[..., Iterable[dict[str, Any]]]:
    if ":" not in spec:
        raise ProducerContractError("producer spec must be package.module:function")
    module_name, func_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name, None)
    if not callable(func):
        raise ProducerContractError(f"producer is not callable: {spec}")
    return func


def run_producer(spec: str, **kwargs: Any) -> list[Candidate]:
    rows = load_producer(spec)(**kwargs)
    if rows is None:
        return []
    forbidden = {"pnl", "pnl_new", "gross_pnl", "exit_dt", "exit_reason", "future_result", "label", "target"}
    candidates: list[Candidate] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise ProducerContractError(f"producer row {index} is not an object")
        leaked = sorted(forbidden & set(raw))
        if leaked:
            raise ProducerContractError(f"producer row {index} contains unavailable result fields: {leaked}")
        candidates.append(Candidate.from_dict(raw))
    return candidates
