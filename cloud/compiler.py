from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple
from nanobot_bridge.agent import provider_chat

def _build_sys(allowed_caps: List[str]) -> str:
    cap_list = ", ".join(allowed_caps[:120]) if allowed_caps else ""
    return f"""你是一个“执行计划编译器”。把用户请求编译成可回放的 plan JSON。
只输出 JSON，不要解释，不要 markdown。

JSON 结构：
{{
  "template_id": "string",
  "steps": [{{"capability":"<capability_name>","args":{{...}}}}, ...],
  "_risk": "low|medium|high"
}}

硬约束：
- steps <= 3
- capability 必须来自允许列表（否则会被判无效）
- args 必须是 JSON object
- 如果无法完成，请输出：
  {{"template_id":"reject","steps":[],"_risk":"high"}}

允许 capability 列表（仅可从中选择 capability）：
{cap_list}
"""

def _best_effort_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        s = raw.find("{"); e = raw.rfind("}")
        if s >= 0 and e > s:
            return json.loads(raw[s:e+1])
    raise ValueError("cloud plan is not json")

def validate_plan(plan: Dict[str, Any], allowed_caps: List[str]) -> Tuple[bool, str]:
    if not isinstance(plan, dict):
        return False, "not_dict"
    steps = plan.get("steps")
    if not isinstance(steps, list):
        return False, "steps_not_list"
    if len(steps) > 3:
        return False, "too_many_steps"
    allow = set(allowed_caps or [])
    for i, st in enumerate(steps):
        if not isinstance(st, dict):
            return False, f"step_{i}_not_dict"
        cap = st.get("capability") or st.get("tool")
        if not isinstance(cap, str) or not cap:
            return False, f"step_{i}_cap_missing"
        if allow and cap not in allow:
            return False, f"step_{i}_cap_not_allowed:{cap}"
        args = st.get("args", {})
        if not isinstance(args, dict):
            return False, f"step_{i}_args_not_object"
        st.pop("tool", None)
        st["capability"] = cap
    return True, ""

def compile_plan(provider, user_text: str, case_key: str, slots: Dict[str, Any], allowed_caps: List[str], *, max_retries: int = 2) -> Dict[str, Any]:
    sys = _build_sys(allowed_caps)
    last_err = ""
    for _ in range(max_retries + 1):
        messages = [
            {"role":"system","content":sys},
            {"role":"user","content":f"user_text={user_text}\ncase_key={case_key}\nslots={json.dumps(slots,ensure_ascii=False)}\nlast_error={last_err}"}
        ]
        raw = provider_chat(provider, messages, max_tokens=750, temperature=0.2)
        plan = _best_effort_json(raw)
        ok, reason = validate_plan(plan, allowed_caps)
        if ok:
            return plan
        last_err = reason
    return {"template_id":"reject","steps":[],"_risk":"high","_error":last_err}
