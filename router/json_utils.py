from __future__ import annotations
import json
from typing import Any, Dict
from jsonschema import validate
from pathlib import Path

SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text(encoding="utf-8"))

def best_effort_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        s = raw.find("{"); e = raw.rfind("}")
        if s >= 0 and e > s:
            return json.loads(raw[s:e+1])
    raise ValueError("router output is not json")

def validate_router(obj: Dict[str, Any]) -> Dict[str, Any]:
    validate(instance=obj, schema=SCHEMA)
    obj.setdefault("direct_id","")
    obj.setdefault("slots",{})
    return obj
