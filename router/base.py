from __future__ import annotations
from typing import Any, Dict, Protocol

class Router(Protocol):
    def predict(self, user_text: str) -> Dict[str, Any]:
        ...
