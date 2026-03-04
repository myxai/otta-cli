from __future__ import annotations
import os, subprocess
from typing import Any, Dict
from .json_utils import best_effort_json, validate_router

ROUTER_SYS = """你是一个路由器，只输出严格 JSON（不要解释、不要 markdown）。JSON 字段:
route: direct|replay|cloud|block
risk: low|medium|high
need_confirm: true|false
case_key: string
direct_id: string (可为空)
slots: object
"""

class LlamaCliRouter:
    def __init__(self, llama_cli: str, gguf: str, extra: str = ""):
        self.llama_cli = llama_cli
        self.gguf = gguf
        self.extra = extra

    def predict(self, user_text: str) -> Dict[str, Any]:
        prompt = ROUTER_SYS + "\n用户: " + user_text + "\n输出JSON: "
        cmd = [self.llama_cli, "-m", self.gguf, "-p", prompt, "--n-predict", "256"]
        if self.extra:
            cmd += self.extra.split()
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        out = (proc.stdout or "").strip()
        obj = best_effort_json(out)
        return validate_router(obj)

def from_env() -> "LlamaCliRouter":
    llama_cli = os.environ.get("OTTA_LLAMA_CLI","").strip()
    gguf = os.environ.get("OTTA_ROUTER_GGUF","").strip()
    extra = os.environ.get("OTTA_LLAMA_EXTRA","").strip()
    if not llama_cli or not gguf:
        raise RuntimeError("Missing OTTA_LLAMA_CLI or OTTA_ROUTER_GGUF for cli backend")
    return LlamaCliRouter(llama_cli, gguf, extra=extra)
