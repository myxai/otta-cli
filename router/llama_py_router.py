from __future__ import annotations
import os
from typing import Any, Dict
from .json_utils import best_effort_json, validate_router
from .llamacpp_router import ROUTER_SYS

class LlamaPythonRouter:
    def __init__(self, gguf: str, *, n_ctx: int = 1024, n_threads: int = 0, n_gpu_layers: int = 0):
        try:
            from llama_cpp import Llama  # type: ignore
        except Exception as e:
            raise RuntimeError("llama-cpp-python is not installed. pip install llama-cpp-python") from e
        self.llm = Llama(
            model_path=gguf,
            n_ctx=n_ctx,
            n_threads=n_threads if n_threads > 0 else None,
            n_gpu_layers=n_gpu_layers,
            logits_all=False,
            verbose=False,
        )

    def predict(self, user_text: str) -> Dict[str, Any]:
        prompt = ROUTER_SYS + "\n用户: " + user_text + "\n输出JSON: "
        out = self.llm(prompt, max_tokens=256, temperature=0.0, stop=["\n\n", "```"])
        text = ""
        try:
            text = out["choices"][0]["text"]
        except Exception:
            text = str(out)
        obj = best_effort_json(text)
        return validate_router(obj)

def from_env() -> "LlamaPythonRouter":
    gguf = os.environ.get("OTTA_ROUTER_GGUF","").strip()
    if not gguf:
        raise RuntimeError("Missing OTTA_ROUTER_GGUF for py backend")
    n_ctx = int(os.environ.get("OTTA_ROUTER_CTX","1024"))
    n_threads = int(os.environ.get("OTTA_ROUTER_THREADS","0"))
    n_gpu_layers = int(os.environ.get("OTTA_ROUTER_GPU_LAYERS","0"))
    return LlamaPythonRouter(gguf, n_ctx=n_ctx, n_threads=n_threads, n_gpu_layers=n_gpu_layers)
