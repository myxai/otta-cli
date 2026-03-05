from __future__ import annotations
import json, re, sys
from typing import Any, Dict
from jsonschema import validate
from pathlib import Path

SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text(encoding="utf-8"))

_V1_TO_V4_ROUTE = {
    "direct": "llm",
    "replay": "golden",
    "cloud":  "llm",
}

_VALID_INTENTS = {"chat", "operate", "fs", "search", "cron", "sys", "unknown"}


def best_effort_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        s = raw.find("{"); e = raw.rfind("}")
        if s >= 0 and e > s:
            return json.loads(raw[s:e+1])
    raise ValueError("router output is not json")


def _migrate_v1(obj: Dict[str, Any]) -> None:
    """将 v1 route 枚举静默迁移为 v4，保证旧模型输出不会直接炸"""
    route = obj.get("route", "")
    if route in _V1_TO_V4_ROUTE:
        obj["route"] = _V1_TO_V4_ROUTE[route]

    obj.pop("direct_id", None)

    if "intent" not in obj or obj.get("intent") not in _VALID_INTENTS:
        obj["intent"] = "unknown"

    obj.pop("compiler", None)


def validate_router(obj: Dict[str, Any]) -> Dict[str, Any]:
    _migrate_v1(obj)

    try:
        validate(instance=obj, schema=SCHEMA)
    except Exception as e:
        print(f"[WARN] Router output validation failed: {e}", file=sys.stderr)
        print(f"[WARN] Raw output: {obj}", file=sys.stderr)

        if "case_key" in obj and isinstance(obj["case_key"], str):
            if len(obj["case_key"]) < 1:
                obj["case_key"] = "unknown"

        _migrate_v1(obj)
        validate(instance=obj, schema=SCHEMA)

    obj.setdefault("slots", {})
    return obj
