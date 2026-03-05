from __future__ import annotations
from typing import Any, Dict, Tuple
import asyncio

def _render(x: Any, slots: Dict[str, Any]) -> Any:
    if isinstance(x, str):
        out = x
        for k, v in slots.items():
            out = out.replace("{{"+k+"}}", str(v))
        return out
    if isinstance(x, dict):
        return {k: _render(v, slots) for k, v in x.items()}
    if isinstance(x, list):
        return [_render(i, slots) for i in x]
    return x

def _tool_registry(agent) -> dict | None:
    """Best-effort get the tool registry dict from agent."""
    tools_obj = getattr(agent, "tools", None)
    if tools_obj is None:
        return None
    for attr in ("tools", "_tools", "registry"):
        m = getattr(tools_obj, attr, None)
        if isinstance(m, dict):
            return m
    return None


async def run_plan_with_nanobot_async(agent, plan: Dict[str, Any], slots: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], int, str]:
    """Execute plan steps via nanobot tools.execute() (async version).

    Preferred step schema:
      {"capability": "name", "args": {...}}
    Backward compat:
      {"tool": "name", "args": {...}}
    """
    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        return False, {"error":"invalid_steps"}, 0, "plan"

    registry = _tool_registry(agent)

    result: Dict[str, Any] = {}
    eff = 0
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, {"error":"invalid_step","step":idx}, eff, f"step{idx}"
        cap = step.get("capability") or step.get("tool")
        if not isinstance(cap, str) or not cap:
            return False, {"error":"missing_capability","step":idx}, eff, f"step{idx}"

        if registry is not None and cap not in registry:
            return False, {"error":"tool_not_in_registry","capability":cap,"step":idx}, eff, f"step{idx}"

        args = _render(step.get("args", {}), slots)
        if not isinstance(args, dict):
            return False, {"error":"args_not_object","step":idx}, eff, f"step{idx}"
        try:
            out = await agent.tools.execute(cap, args)
        except Exception as e:
            return False, {"error":"tool_execute_failed","capability":cap,"detail":str(e)}, eff, f"step{idx}"

        if isinstance(out, (str, bytes)):
            out = {"output": out.decode() if isinstance(out, bytes) else out}
        if isinstance(out, dict) and out.get("error"):
            return False, {"error":"tool_error","capability":cap,"detail":out}, eff, f"step{idx}"
        if isinstance(out, dict):
            result.update(out)
        else:
            result[f"step_{idx}"] = out
        eff += 1

    return True, result, eff, ""

def run_plan_with_nanobot(agent, plan: Dict[str, Any], slots: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], int, str]:
    """Synchronous wrapper for run_plan_with_nanobot_async.
    
    This function runs the async version in a new event loop or the current one if available.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, but called from sync code
            # Create a new event loop in a thread (not ideal but works)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_plan_with_nanobot_async(agent, plan, slots))
                return future.result()
        else:
            # No loop running, we can use run_until_complete
            return loop.run_until_complete(run_plan_with_nanobot_async(agent, plan, slots))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(run_plan_with_nanobot_async(agent, plan, slots))
