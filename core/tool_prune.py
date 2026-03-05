"""按 intent 裁剪 capabilities 列表。

策略：基于工具名前缀/关键词做映射。
如果 intent 没有命中任何规则或者裁剪后列表为空，返回全量列表（安全 fallback）。
"""
from __future__ import annotations
from typing import Dict, FrozenSet, List, Set

_INTENT_KEYWORDS: Dict[str, FrozenSet[str]] = {
    "fs": frozenset({
        "read_file", "write_file", "edit_file", "list_dir",
        "exec", "message", "spawn",
    }),
    "search": frozenset({
        "web_search", "web_fetch", "message",
    }),
    "cron": frozenset({
        "cron", "exec", "read_file", "write_file", "list_dir", "message",
    }),
    "sys": frozenset({
        "exec", "spawn", "list_dir", "read_file", "message",
    }),
    "operate": frozenset({
        "exec", "read_file", "write_file", "edit_file",
        "list_dir", "web_search", "web_fetch",
        "spawn", "message",
    }),
}

_PREFIX_MAP: Dict[str, List[str]] = {
    "fs":      ["fs.", "file.", "dir."],
    "search":  ["web.", "search.", "http."],
    "cron":    ["cron.", "schedule.", "timer."],
    "sys":     ["sys.", "proc.", "net.", "disk."],
    "operate": [],
}


def allowed_caps_by_intent(all_caps: List[str], intent: str) -> List[str]:
    if intent in ("chat", "unknown"):
        return all_caps

    keywords = _INTENT_KEYWORDS.get(intent)
    prefixes = _PREFIX_MAP.get(intent, [])

    if not keywords and not prefixes:
        return all_caps

    result: List[str] = []
    seen: Set[str] = set()
    for cap in all_caps:
        if cap in seen:
            continue
        hit = False
        if keywords and cap in keywords:
            hit = True
        if not hit:
            for pfx in prefixes:
                if cap.startswith(pfx):
                    hit = True
                    break
        if hit:
            seen.add(cap)
            result.append(cap)

    if not result:
        return all_caps

    return result
