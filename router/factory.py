from __future__ import annotations
import os
from typing import List
from .base import Router

def _parse_list(s: str) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def from_env() -> Router:
    primary = os.environ.get("OTTA_ROUTER_BACKEND","").strip().lower()
    fallbacks = _parse_list(os.environ.get("OTTA_ROUTER_FALLBACKS","py,ollama,cli").lower())
    order = [primary] + [x for x in fallbacks if x != primary] if primary else fallbacks

    last_err = None
    for b in order:
        try:
            if b == "py":
                from .llama_py_router import from_env as f
                return f()
            if b == "ollama":
                from .ollama_router import from_env as f
                return f()
            if b == "cli":
                from .llamacpp_router import from_env as f
                return f()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Cannot init router backends {order}: {last_err}")
