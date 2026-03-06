from __future__ import annotations
from typing import Any, Dict, Protocol

class Router(Protocol):
    def predict(self, user_text: str) -> Dict[str, Any]:
        ...
    
    def chat(self, system_msg: str, user_msg: str, *, max_tokens: int = 512, temperature: float = 0.2) -> str:
        """通用聊天接口，用于回放总结等场景"""
        ...