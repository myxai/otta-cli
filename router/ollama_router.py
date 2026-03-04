from __future__ import annotations
import os, json, urllib.request
from typing import Any, Dict
from .json_utils import best_effort_json, validate_router
from .llamacpp_router import ROUTER_SYS

def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

class OllamaRouter:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def predict(self, user_text: str) -> Dict[str, Any]:
        prompt = ROUTER_SYS + "\n用户: " + user_text + "\n输出JSON: "
        url = self.base_url + "/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 256,
                "stop": ["\n\n", "```"],
            },
        }
        out = _post_json(url, payload, timeout=int(os.environ.get("OTTA_OLLAMA_TIMEOUT","30")))
        text = out.get("response","") if isinstance(out, dict) else str(out)
        obj = best_effort_json(text)
        return validate_router(obj)

def from_env() -> "OllamaRouter":
    base_url = os.environ.get("OTTA_OLLAMA_URL","http://127.0.0.1:11434").strip()
    model = os.environ.get("OTTA_OLLAMA_MODEL","qwen2.5:0.5b-instruct").strip()
    return OllamaRouter(base_url, model)
