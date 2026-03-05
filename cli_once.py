from __future__ import annotations
import argparse, os, logging
from router.factory import from_env, make_router_from_args
from nanobot_bridge.agent import make_agent_loop
from core.pipeline import run_once

# 抑制 LiteLLM 的网络警告
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

def main():
    ap = argparse.ArgumentParser(
        description="Otta CLI - 单命令执行模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置（从环境变量）
  python cli_once.py "把下载目录按类型整理一下"
  
  # 指定路由器模型
  python cli_once.py "整理下载目录" --router-model train/router.q4_k_m.gguf
  
  # 完整配置
  python cli_once.py "搜索最新消息" \\
    --router-backend py \\
    --router-model train/router.q4_k_m.gguf \\
    --router-gpu-layers 32
        """
    )
    
    # 必需参数
    ap.add_argument("text", help="用户输入文本")
    
    # 数据库配置
    ap.add_argument("--db", default="runtime/otta_min.db", help="数据库路径 (默认: runtime/otta_min.db)")
    
    # 路由器配置
    router_group = ap.add_argument_group("路由器配置")
    router_group.add_argument(
        "--router-backend",
        choices=["py", "ollama", "cli"],
        help="路由器后端: py=Python绑定(推荐), ollama=Ollama, cli=CLI执行器"
    )
    router_group.add_argument(
        "--router-model",
        help="路由器模型文件路径 (GGUF 格式)"
    )
    router_group.add_argument(
        "--router-gpu-layers",
        type=int,
        help="GPU 层数 (0=纯CPU, 32=全部GPU)"
    )
    router_group.add_argument(
        "--router-threads",
        type=int,
        help="CPU 线程数"
    )
    router_group.add_argument(
        "--router-ctx-size",
        type=int,
        default=1024,
        help="上下文大小 (默认: 1024)"
    )
    
    # Ollama 配置
    ollama_group = ap.add_argument_group("Ollama 配置 (当 --router-backend=ollama 时)")
    ollama_group.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Ollama 服务地址 (默认: http://127.0.0.1:11434)"
    )
    ollama_group.add_argument(
        "--ollama-model",
        help="Ollama 模型名称"
    )
    
    # CLI 执行器配置
    cli_group = ap.add_argument_group("CLI 执行器配置 (当 --router-backend=cli 时)")
    cli_group.add_argument(
        "--cli-executor",
        help="llama-cli 可执行文件路径"
    )

    # Capabilities 配置
    cap_group = ap.add_argument_group("能力列表配置")
    cap_group.add_argument(
        "--cap-file",
        default=None,
        help="capabilities.json 路径 (也可通过 OTTA_CAP_FILE 环境变量设置)"
    )
    cap_group.add_argument(
        "--cap-topn",
        type=int,
        default=None,
        help="注入到 router prompt 的能力数量上限 (默认: 60)"
    )

    # 调试选项
    ap.add_argument("--verbose", "-v", action="store_true", help="显示路由器的原始输入/输出（用于调试）")
    
    args = ap.parse_args()

    # 创建路由器（优先使用命令行参数，回退到环境变量）
    if args.router_backend or args.router_model:
        # 使用命令行参数
        router = make_router_from_args(args)
        print(f"[配置] 使用命令行参数配置路由器")
    else:
        # 使用环境变量（向后兼容）
        router = from_env()
        print(f"[配置] 使用环境变量配置路由器")
    
    print(f"[路由器] 后端={type(router).__name__}")
    
    agent, provider = make_agent_loop()

    out = run_once(args.text, db_path=args.db, router=router, agent=agent, provider=provider, verbose=args.verbose)
    print(out)

if __name__ == "__main__":
    main()
