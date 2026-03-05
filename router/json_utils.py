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
    """验证路由器输出，并提供友好的错误处理"""
    try:
        validate(instance=obj, schema=SCHEMA)
    except Exception as e:
        # 提供更友好的错误信息
        import sys
        print(f"[WARN] Router output validation failed: {e}", file=sys.stderr)
        print(f"[WARN] Raw output: {obj}", file=sys.stderr)
        
        # 尝试修复常见问题
        if "case_key" in obj and isinstance(obj["case_key"], str):
            # case_key 太短，添加前缀
            if len(obj["case_key"]) < 1:
                obj["case_key"] = "unknown"
        
        # 重新验证
        validate(instance=obj, schema=SCHEMA)
    
    obj.setdefault("direct_id", "")
    obj.setdefault("slots", {})
    return obj
