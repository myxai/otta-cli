from __future__ import annotations
from typing import Any, Dict, Tuple

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

def run_plan_with_nanobot(agent, plan: Dict[str, Any], slots: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], int, str]:
    """Execute plan steps via nanobot tools.execute().

    Preferred step schema:
      {"capability": "name", "args": {...}}
    Backward compat:
      {"tool": "name", "args": {...}}
    """
    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        return False, {"error":"invalid_steps"}, 0, "plan"

    result: Dict[str, Any] = {}
    eff = 0
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, {"error":"invalid_step","step":idx}, eff, f"step{idx}"
        cap = step.get("capability") or step.get("tool")
        if not isinstance(cap, str) or not cap:
            return False, {"error":"missing_capability","step":idx}, eff, f"step{idx}"
        args = _render(step.get("args", {}), slots)
        if not isinstance(args, dict):
            return False, {"error":"args_not_object","step":idx}, eff, f"step{idx}"
        try:
            out = agent.tools.execute(cap, args)
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
