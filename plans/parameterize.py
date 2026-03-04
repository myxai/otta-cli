from __future__ import annotations
from typing import Any, Dict, Tuple
import re

PATH_RE = re.compile(r"^([~A-Za-z]:)?[\\/].+|^~/.+")

def _looks_path(s: str) -> bool:
    s = s.strip()
    return bool(PATH_RE.match(s))

def parameterize_plan(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Any]]:
    slots_schema: Dict[str, str] = {}
    defaults: Dict[str, Any] = {}

    def slotize(k: str, v: Any) -> Any:
        if isinstance(v, str) and _looks_path(v):
            slots_schema.setdefault("path","string")
            defaults.setdefault("path", v)
            return "{{path}}"
        if isinstance(v, str) and k in ("query","q","text") and 1 <= len(v) <= 200:
            slots_schema.setdefault("query","string")
            defaults.setdefault("query", v)
            return "{{query}}"
        if isinstance(v, (int,float)) and k in ("k","topk","max_tokens","max_len"):
            slots_schema.setdefault("max_len","number")
            defaults.setdefault("max_len", v)
            return "{{max_len}}"
        return v

    def walk(x: Any) -> Any:
        if isinstance(x, dict):
            return {kk: walk(slotize(kk, vv)) for kk, vv in x.items()}
        if isinstance(x, list):
            return [walk(i) for i in x]
        return x

    out = walk(plan)
    out["_slots_schema"] = slots_schema
    out["_slot_defaults"] = defaults
    return out, slots_schema, defaults
