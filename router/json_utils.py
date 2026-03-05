from __future__ import annotations
import json, re, sys
from typing import Any, Dict
from jsonschema import validate
from pathlib import Path

SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text(encoding="utf-8"))

_DIRECT_ID_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")

def best_effort_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        s = raw.find("{"); e = raw.rfind("}")
        if s >= 0 and e > s:
            return json.loads(raw[s:e+1])
    raise ValueError("router output is not json")

def _sanitize_direct_id(obj: Dict[str, Any]) -> None:
    """清理不合法的 direct_id：含非 ASCII 字符时清空并降级到 cloud"""
    did = obj.get("direct_id", "")
    if did and not _DIRECT_ID_RE.match(did):
        print(f"[WARN] invalid direct_id '{did}', clearing and falling back to cloud", file=sys.stderr)
        obj["direct_id"] = ""
        if obj.get("route") == "direct":
            obj["route"] = "cloud"

def validate_router(obj: Dict[str, Any]) -> Dict[str, Any]:
    """验证路由器输出，并提供友好的错误处理"""
    _sanitize_direct_id(obj)

    try:
        validate(instance=obj, schema=SCHEMA)
    except Exception as e:
        print(f"[WARN] Router output validation failed: {e}", file=sys.stderr)
        print(f"[WARN] Raw output: {obj}", file=sys.stderr)
        
        if "case_key" in obj and isinstance(obj["case_key"], str):
            if len(obj["case_key"]) < 1:
                obj["case_key"] = "unknown"
        
        _sanitize_direct_id(obj)
        validate(instance=obj, schema=SCHEMA)
    
    obj.setdefault("direct_id", "")
    obj.setdefault("slots", {})
    return obj
