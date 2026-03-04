from __future__ import annotations
from typing import Any, Dict, List, Tuple

def list_tool_names(agent) -> List[str]:
    """Best-effort extract nanobot tool names from AgentLoop instance."""
    tools_obj = getattr(agent, "tools", None)
    if tools_obj is None:
        return []

    # Common patterns
    for attr in ["tools", "_tools", "registry"]:
        m = getattr(tools_obj, attr, None)
        if isinstance(m, dict):
            return sorted([str(k) for k in m.keys()])

    # list_tools() method
    for fn_name in ["list_tools", "get_tools", "available_tools"]:
        fn = getattr(tools_obj, fn_name, None)
        if callable(fn):
            try:
                out = fn()
                if isinstance(out, dict):
                    return sorted([str(k) for k in out.keys()])
                if isinstance(out, list):
                    # list of names or tool objects
                    names=[]
                    for x in out:
                        if isinstance(x, str):
                            names.append(x)
                        elif isinstance(x, dict) and "name" in x:
                            names.append(str(x["name"]))
                        else:
                            nm = getattr(x, "name", None)
                            if nm: names.append(str(nm))
                    return sorted(set(names))
            except Exception:
                pass

    # fallback: dir scan for execute-able
    names=set()
    try:
        for k in dir(tools_obj):
            if k.startswith("_"): 
                continue
            v = getattr(tools_obj, k, None)
            if callable(v) and k not in ("execute",):
                # not reliable; ignore
                pass
    except Exception:
        pass
    return sorted(names)

def normalize_allowed_tools(agent, *, max_n: int = 120) -> List[str]:
    names = list_tool_names(agent)
    # keep list bounded to avoid prompt bloat
    if len(names) > max_n:
        return names[:max_n]
    return names
