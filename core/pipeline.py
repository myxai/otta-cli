from __future__ import annotations
import asyncio, time, json, uuid
from typing import Any, Dict, List, Tuple

from store.db import Store
from plans.runner import run_plan_with_nanobot


def _run_async(coro):
    """同步调用 async 协程。"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _process_and_capture(agent, user_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """调用 agent.process_direct 并拦截工具调用，用于 golden promotion。

    使用独立 session_key 避免 nanobot 从会话记忆直接回答而跳过工具调用。
    """
    captured: List[Dict[str, Any]] = []
    original_execute = agent.tools.execute

    async def _interceptor(name, arguments):
        captured.append({
            "capability": name,
            "args": dict(arguments) if isinstance(arguments, dict) else {},
        })
        return await original_execute(name, arguments)

    agent.tools.execute = _interceptor
    try:
        session_key = f"cli:once:{uuid.uuid4().hex[:8]}"
        response = await agent.process_direct(user_text, session_key=session_key)
    finally:
        agent.tools.execute = original_execute

    return response, captured


def _templatize_plan(steps: List[Dict], slots: Dict[str, Any]) -> List[Dict]:
    """将工具调用参数中的具体 slot 值替换回 {{key}} 模板，使 plan 可复用。"""
    if not slots:
        return steps
    raw = json.dumps(steps, ensure_ascii=False)
    for key, value in slots.items():
        sv = str(value)
        if sv:
            raw = raw.replace(sv, "{{" + key + "}}")
    return json.loads(raw)


def run_once(
    user_text: str,
    *,
    db_path: str = "runtime/otta_min.db",
    router,
    agent,
    provider,
    verbose: bool = False,
) -> Dict[str, Any]:
    store = Store(db_path)
    store.init()

    t0 = time.time()
    r = router.predict(user_text)
    print("[router]", json.dumps(r, ensure_ascii=False))

    intent = r.get("intent", "unknown")

    # ── 1) block 优先 ──
    if r["route"] == "block" or r["risk"] == "high" or r["need_confirm"]:
        store.log_run(r["case_key"], "block", "router", False,
                      int((time.time() - t0) * 1000), 0, False, "blocked",
                      intent=intent)
        return {"blocked": True, "router": r}

    case_key = r["case_key"]
    slots = r.get("slots", {}) or {}

    # ── 2) golden replay（只要没 block 就先查，不看 route） ──
    g = store.get_golden(case_key)
    if g and g.replayable:
        print(f"[golden] hit {case_key} v{g.version} → replay")
        ok, result, eff, stage = run_plan_with_nanobot(agent, g.plan, slots)
        store.log_run(case_key, "golden", "golden", ok,
                      int((time.time() - t0) * 1000), eff, False, stage,
                      intent=intent)
        store.touch_golden(case_key)
        if ok:
            store.update_capability_graph_from_plan(g.plan)
            return {"ok": True, "route": "golden", "result": result}
        print(f"[golden] replay failed → fallback llm")
    elif g:
        print(f"[golden] found {case_key} but not replayable → fallback llm")
    else:
        print(f"[golden] miss {case_key} → fallback llm")

    # ── 3) llm：走 nanobot agent loop（拦截工具调用） ──
    print("[llm] → nanobot")
    response, tool_calls = _run_async(_process_and_capture(agent, user_text))

    ok = bool(response)
    store.log_run(case_key, "llm", "nanobot", ok,
                  int((time.time() - t0) * 1000), len(tool_calls), True, "",
                  intent=intent)

    # ── 4) promote to golden：成功 + 有工具调用 + router 判定 golden ──
    if ok and tool_calls and r.get("route") == "golden":
        steps = _templatize_plan(tool_calls, slots)
        plan = {"template_id": case_key, "steps": steps}
        store.upsert_golden(case_key, case_key, plan, replayable=1)
        print(f"[golden] promoted {case_key} ({len(steps)} steps)")
        print(f"[golden] plan: {json.dumps(plan, ensure_ascii=False)}")
    elif ok and tool_calls:
        print(f"[golden] skip promote: route={r.get('route')} (not golden)")
    elif ok:
        print(f"[golden] skip promote: no tool calls (pure text response)")

    return {"ok": True, "route": "llm", "result": response}
