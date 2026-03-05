#!/usr/bin/env python3
"""
统一的路由器 Prompt 管理器

确保训练、评估、推理使用完全一致的提示词。
这对小参数模型（如 Qwen-0.5B）至关重要。
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 基础系统提示词 (英文，与训练数据保持一致)
BASE_SYSTEM_PROMPT = "You are a router. Output ONLY JSON."


def load_capabilities(cap_file: str, topn: int = 60) -> List[str]:
    """
    从 capabilities.json 加载能力列表
    
    Args:
        cap_file: capabilities.json 文件路径
        topn: 取前 N 个能力
        
    Returns:
        能力名称列表
    """
    try:
        with open(cap_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        caps = data.get("capabilities", [])
        names = [c["name"] for c in caps if "name" in c][:topn]
        return names
    except Exception as e:
        print(f"[WARN] 无法加载 capabilities: {e}", file=sys.stderr)
        return []


def build_system_prompt(cap_file: Optional[str] = None, topn: int = 60) -> str:
    """
    构建标准系统提示词
    
    Args:
        cap_file: capabilities.json 文件路径（可选）
        topn: 取前 N 个能力
        
    Returns:
        完整的系统提示词
    """
    sys_prompt = BASE_SYSTEM_PROMPT
    
    if cap_file:
        cap_names = load_capabilities(cap_file, topn)
        if cap_names:
            sys_prompt += "\nAvailable capabilities: " + ", ".join(cap_names)
    
    return sys_prompt


def build_chatml_prompt(system_prompt: str, user_text: str) -> str:
    """
    构建符合 Qwen ChatML 格式的完整 Prompt
    
    Args:
        system_prompt: 系统提示词
        user_text: 用户输入
        
    Returns:
        ChatML 格式的完整 Prompt
    """
    return (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_text}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def build_messages(system_prompt: str, user_text: str) -> List[Dict[str, str]]:
    """
    构建标准的消息格式（用于 apply_chat_template）
    
    Args:
        system_prompt: 系统提示词
        user_text: 用户输入
        
    Returns:
        消息列表
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]


class PromptManager:
    """路由器提示词管理器"""
    
    def __init__(self, cap_file: Optional[str] = None, topn: int = 60):
        """
        初始化提示词管理器
        
        Args:
            cap_file: capabilities.json 文件路径
            topn: 取前 N 个能力
        """
        self.cap_file = cap_file
        self.topn = topn
        self.system_prompt = build_system_prompt(cap_file, topn)
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.system_prompt
    
    def build_messages(self, user_text: str) -> List[Dict[str, str]]:
        """构建消息列表（用于 HF tokenizer.apply_chat_template）"""
        return build_messages(self.system_prompt, user_text)
    
    def build_chatml(self, user_text: str) -> str:
        """构建 ChatML 格式提示词（用于 GGUF llama.cpp）"""
        return build_chatml_prompt(self.system_prompt, user_text)
    
    def __repr__(self) -> str:
        cap_info = f"with {len(load_capabilities(self.cap_file, self.topn))} capabilities" if self.cap_file else "no capabilities"
        return f"PromptManager({cap_info})"


def main():
    """测试提示词生成"""
    import argparse
    
    ap = argparse.ArgumentParser(description="测试提示词生成")
    ap.add_argument("--cap-file", help="capabilities.json 文件路径")
    ap.add_argument("--topn", type=int, default=60, help="取前 N 个能力")
    ap.add_argument("--test-input", default="帮我整理桌面", help="测试输入")
    args = ap.parse_args()
    
    print("=" * 70)
    print("路由器提示词管理器测试")
    print("=" * 70)
    
    # 创建管理器
    pm = PromptManager(args.cap_file, args.topn)
    print(f"\n{pm}")
    
    # 显示系统提示词
    print(f"\n[系统提示词]")
    print("-" * 70)
    sys_prompt = pm.get_system_prompt()
    print(sys_prompt)
    print(f"\n长度: {len(sys_prompt)} 字符")
    
    # 显示 Messages 格式
    print(f"\n[Messages 格式 (用于 HF apply_chat_template)]")
    print("-" * 70)
    messages = pm.build_messages(args.test_input)
    print(json.dumps(messages, ensure_ascii=False, indent=2))
    
    # 显示 ChatML 格式
    print(f"\n[ChatML 格式 (用于 GGUF llama.cpp)]")
    print("-" * 70)
    chatml = pm.build_chatml(args.test_input)
    print(chatml)
    
    print("=" * 70)


if __name__ == "__main__":
    main()
