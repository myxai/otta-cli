from __future__ import annotations
import os, json, urllib.request
import os, json, urllib.request
from typing import Any, Dict
from .json_utils import best_effort_json, validate_router
from .prompt_manager import PromptManager

def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

class OllamaRouter:
    def __init__(self, base_url: str, model: str, verbose: bool = False, cap_file: str = None, topn: int = 60):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.verbose = verbose
        # 使用统一的 Prompt 管理器
        self.pm = PromptManager(cap_file, topn)

    def predict(self, user_text: str) -> Dict[str, Any]:
        # 使用统一的 ChatML 格式
        prompt = self.pm.build_chatml(user_text)
        if self.verbose:
            print(f"[router-prompt]\n{prompt}")
        url = self.base_url + "/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 256,
                "stop": ["<|im_end|>"],
            },
        }
        out = _post_json(url, payload, timeout=int(os.environ.get("OTTA_OLLAMA_TIMEOUT","30")))
        text = out.get("response","") if isinstance(out, dict) else str(out)
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
        
        url = self.base_url + "/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "stop": ["<|im_end|>"],
            },
        }
        out = _post_json(url, payload, timeout=int(os.environ.get("OTTA_OLLAMA_TIMEOUT","30")))
        return out.get("response", "").strip() if isinstance(out, dict) else str(out)

def from_env() -> "OllamaRouter":
    base_url = os.environ.get("OTTA_OLLAMA_URL","http://127.0.0.1:11434").strip()
    model = os.environ.get("OTTA_OLLAMA_MODEL","qwen2.5:0.5b-instruct").strip()
    cap_file = os.environ.get("OTTA_CAP_FILE","").strip() or None
    topn = int(os.environ.get("OTTA_CAP_TOPN","60"))
    return OllamaRouter(base_url, model, cap_file=cap_file, topn=topn)
