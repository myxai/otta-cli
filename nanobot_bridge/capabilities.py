from __future__ import annotations
import os, glob
from typing import List, Dict

def _scan_tools(agent) -> List[Dict]:
    out=[]
    tools_obj=getattr(agent,"tools",None)
    if tools_obj:
        for attr in ["tools","_tools","registry"]:
            m=getattr(tools_obj,attr,None)
            if isinstance(m,dict):
                for k in m.keys():
                    out.append({"name":str(k),"type":"tool","domain":"tool"})
                return out
    return out

def _scan_skills(workspace: str) -> List[Dict]:
    skills=[]
    path=os.path.join(workspace,"skills")
    if not os.path.isdir(path):
        return skills
    for f in glob.glob(os.path.join(path,"*.md")):
        name=os.path.splitext(os.path.basename(f))[0]
        skills.append({"name":name,"type":"skill","domain":"skill"})
    return skills

def _scan_mcp_from_config() -> List[Dict]:
    out=[]
    try:
        from nanobot.config.loader import load_config
        cfg = load_config()
        servers = getattr(cfg.tools, "mcp_servers", None)
        if isinstance(servers, dict):
            for name in servers.keys():
                out.append({"name":str(name),"type":"mcp","domain":"mcp"})
        elif isinstance(servers, list):
            for x in servers:
                if isinstance(x, str):
                    out.append({"name":x,"type":"mcp","domain":"mcp"})
                elif isinstance(x, dict) and "name" in x:
                    out.append({"name":str(x["name"]),"type":"mcp","domain":"mcp"})
    except Exception:
        pass
    return out

def build_capabilities(agent, workspace: str) -> Dict:
    caps=[]
    caps += _scan_tools(agent)
    caps += _scan_skills(workspace)
    caps += _scan_mcp_from_config()

    seen=set()
    out=[]
    for c in caps:
        n=c.get("name")
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(c)
    return {"capabilities": out}


def get_tool_names(agent) -> set:
    """返回仅来自 tool registry 的可执行能力名称集合（不含 skill/mcp）"""
    return {d["name"] for d in _scan_tools(agent)}
