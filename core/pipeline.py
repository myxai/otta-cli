from __future__ import annotations
import time, json
from typing import Any, Dict, Set

from store.db import Store
from plans.runner import run_plan_with_nanobot
from plans.parameterize import parameterize_plan
from cloud.compiler import compile_plan
from nanobot_bridge.capabilities import build_capabilities, get_tool_names

_cap_cache: Set[str] | None = None
_tool_cache: Set[str] | None = None

def _allowed_caps(agent) -> list[str]:
    """返回可执行的能力列表（仅 tool registry 中的 tool）"""
    global _cap_cache, _tool_cache
    if _tool_cache is None:
        _tool_cache = get_tool_names(agent)
    _cap_cache = set(_tool_cache)
    return sorted(_tool_cache)[:180]

def _is_valid_tool(agent, cap_name: str) -> bool:
    """检查 capability 是否存在于 tool registry（不含 skill/mcp）"""
    global _tool_cache
    if _tool_cache is None:
        _tool_cache = get_tool_names(agent)
    return cap_name in _tool_cache

def run_once(user_text: str, *, db_path: str = "runtime/otta_min.db", router, agent, provider) -> Dict[str, Any]:
    store = Store(db_path)
    store.init()

    t0 = time.time()
    r = router.predict(user_text)
    print("[router]", json.dumps(r, ensure_ascii=False))

    if r["route"] == "block" or r["risk"] == "high" or r["need_confirm"]:
        store.log_run(r["case_key"], "block", "router", False, int((time.time()-t0)*1000), 0, False, "blocked")
        return {"blocked": True, "router": r}

    case_key = r["case_key"]
    slots = r.get("slots", {}) or {}

    # golden replay first
    g = store.get_golden(case_key)
    if g and g.replayable:
        print(f"[replay] golden hit {case_key} v{g.version}")
        ok, result, eff, stage = run_plan_with_nanobot(agent, g.plan, slots)
        store.log_run(case_key, "replay", "golden", ok, int((time.time()-t0)*1000), eff, False, stage)
        store.touch_golden(case_key)
        if ok:
            store.update_capability_graph_from_plan(g.plan)
            return {"ok": True, "route":"replay", "result": result}
        print("[replay_fail] -> cloud", json.dumps(result, ensure_ascii=False))

    # direct as 1-step plan via nanobot
    if r["route"] == "direct" and r.get("direct_id"):
        direct_id = r["direct_id"]
        if _is_valid_tool(agent, direct_id):
            plan = {"template_id":"direct."+direct_id, "steps":[{"capability": direct_id, "args": slots}], "_risk": r["risk"]}
            ok, result, eff, stage = run_plan_with_nanobot(agent, plan, slots)
            store.log_run(case_key, "direct", "direct", ok, int((time.time()-t0)*1000), eff, False, stage)
            if ok:
                store.update_capability_graph_from_plan(plan)
                return {"ok": True, "route":"direct", "result": result}
            print("[direct_fail] -> cloud", json.dumps(result, ensure_ascii=False))
        else:
            print(f"[direct_skip] tool '{direct_id}' not found, falling back to cloud")

    # cloud compile candidate plan via nanobot provider (with capability whitelist)
    allowed_caps = _allowed_caps(agent)
    plan = compile_plan(provider, user_text, case_key, slots, allowed_caps, max_retries=2)
    template_id = plan.get("template_id","cloud.unknown")

    if template_id == "reject" or plan.get("_risk") == "high":
        store.log_run(case_key, "block", "cloud_reject", False, int((time.time()-t0)*1000), 0, True, "cloud_reject")
        return {"ok": False, "route":"block", "error": plan}

    cid = store.insert_candidate(case_key, template_id, plan)
    print("[cloud] candidate", cid, template_id)

    ok, result, eff, stage = run_plan_with_nanobot(agent, plan, slots)
    store.log_run(case_key, "cloud", "candidate", ok, int((time.time()-t0)*1000), eff, True, stage)

    if not ok:
        store.update_candidate(cid, "invalid", fail_reason=result.get("error",""))
        return {"ok": False, "route":"cloud", "error": result}

    store.update_candidate(cid, "tried")
    store.update_capability_graph_from_plan(plan)

    # promote
    pplan, slots_schema, defaults = parameterize_plan(plan)
    store.upsert_golden(case_key, template_id, pplan, replayable=1)
    store.update_candidate(cid, "promoted")
    return {"ok": True, "route":"cloud", "result": result, "promoted": {"case_key":case_key,"template_id":template_id,"slots_schema":slots_schema}}
