from __future__ import annotations
import os, subprocess
from typing import Any, Dict
from .json_utils import best_effort_json, validate_router
from .prompt_manager import PromptManager

class LlamaCliRouter:
    def __init__(self, llama_cli: str, gguf: str, extra: str = "", verbose: bool = False, cap_file: str = None, topn: int = 60):
        self.llama_cli = llama_cli
        self.gguf = gguf
        self.extra = extra
        self.verbose = verbose
        # 使用统一的 Prompt 管理器
        self.pm = PromptManager(cap_file, topn)

    def predict(self, user_text: str) -> Dict[str, Any]:
        # 使用统一的 ChatML 格式
        prompt = self.pm.build_chatml(user_text)
        if self.verbose:
            print(f"[router-prompt]\n{prompt}")
        cmd = [self.llama_cli, "-m", self.gguf, "-p", prompt, "--n-predict", "256"]
        if self.extra:
            cmd += self.extra.split()
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        out = (proc.stdout or "").strip()
        if self.verbose:
            print(f"[router-raw-output]\n{out}")
            if proc.stderr:
                print(f"[router-stderr]\n{proc.stderr.strip()}")
        try:
            obj = best_effort_json(out)
            return validate_router(obj)
        except (ValueError, Exception) as e:
            if self.verbose:
                print(f"[router-parse-error] {e}")
            raise

def from_env() -> "LlamaCliRouter":
    llama_cli = os.environ.get("OTTA_LLAMA_CLI","").strip()
    gguf = os.environ.get("OTTA_ROUTER_GGUF","").strip()
    extra = os.environ.get("OTTA_LLAMA_EXTRA","").strip()
    cap_file = os.environ.get("OTTA_CAP_FILE","").strip() or None
    topn = int(os.environ.get("OTTA_CAP_TOPN","60"))
    if not llama_cli or not gguf:
        raise RuntimeError("Missing OTTA_LLAMA_CLI or OTTA_ROUTER_GGUF for cli backend")
    return LlamaCliRouter(llama_cli, gguf, extra=extra, cap_file=cap_file, topn=topn)
