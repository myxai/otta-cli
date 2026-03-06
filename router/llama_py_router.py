from __future__ import annotations
import os
from typing import Any, Dict
from .json_utils import best_effort_json, validate_router
from .prompt_manager import PromptManager

class LlamaPythonRouter:
    def __init__(self, gguf: str, *, n_ctx: int = 1024, n_threads: int = 0, n_gpu_layers: int = 0, verbose: bool = False, cap_file: str = None, topn: int = 60):
        try:
            from llama_cpp import Llama  # type: ignore
        except Exception as e:
            raise RuntimeError("llama-cpp-python is not installed. pip install llama-cpp-python") from e
        self.verbose = verbose
        # 使用统一的 Prompt 管理器
        self.pm = PromptManager(cap_file, topn)
        self.llm = Llama(
            model_path=gguf,
            n_ctx=n_ctx,
            n_threads=n_threads if n_threads > 0 else None,
            n_gpu_layers=n_gpu_layers,
            logits_all=False,
            verbose=False,
        )

    def predict(self, user_text: str) -> Dict[str, Any]:
        # 使用统一的 ChatML 格式
        prompt = self.pm.build_chatml(user_text)
        if self.verbose:
            print(f"[router-prompt]\n{prompt}")
        # 使用 <|im_end|> 作为停止符，避免过早截断
        out = self.llm(prompt, max_tokens=256, temperature=0.0, stop=["<|im_end|>"])
        text = ""
        try:
            text = out["choices"][0]["text"]
        except Exception:
            text = str(out)
        if self.verbose:
            print(f"[router-raw-output]\n{text}")
        try:
            obj = best_effort_json(text)
            return validate_router(obj)
        except (ValueError, Exception) as e:
            if self.verbose:
                print(f"[router-parse-error] {e}")
            raise

    def chat(self, system_msg: str, user_msg: str, *, max_tokens: int = 512, temperature: float = 0.2) -> str:
        """通用聊天接口，用于回放总结等场景"""
        # 构建 ChatML 格式的 prompt
        prompt = f"<|im_start|>system\n{system_msg}<|im_end|>\n<|im_start|>user\n{user_msg}<|im_end|>\n<|im_start|>assistant\n"
        
        out = self.llm(prompt, max_tokens=max_tokens, temperature=temperature, stop=["<|im_end|>"])
        try:
            return out["choices"][0]["text"].strip()
        except Exception:
            return str(out)

def from_env() -> "LlamaPythonRouter":
    gguf = os.environ.get("OTTA_ROUTER_GGUF","").strip()
    if not gguf:
        raise RuntimeError("Missing OTTA_ROUTER_GGUF for py backend")
    n_ctx = int(os.environ.get("OTTA_ROUTER_CTX","1024"))
    n_threads = int(os.environ.get("OTTA_ROUTER_THREADS","0"))
    n_gpu_layers = int(os.environ.get("OTTA_ROUTER_GPU_LAYERS","0"))
    cap_file = os.environ.get("OTTA_CAP_FILE","").strip() or None
    topn = int(os.environ.get("OTTA_CAP_TOPN","60"))
    return LlamaPythonRouter(gguf, n_ctx=n_ctx, n_threads=n_threads, n_gpu_layers=n_gpu_layers, cap_file=cap_file, topn=topn)
