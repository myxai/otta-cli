from __future__ import annotations
import argparse, os, logging
from router.factory import from_env, make_router_from_args
from nanobot_bridge.agent import make_agent_loop
from core.pipeline import run_once

# 抑制 LiteLLM 的网络警告
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

def main():
    ap = argparse.ArgumentParser(
        description="Otta CLI - 交互式对话模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置（从环境变量）
  python cli_chat.py
  
  # 指定路由器模型
  python cli_chat.py --router-model train/router.q4_k_m.gguf
  
  # 完整配置
  python cli_chat.py \\
    --router-backend py \\
    --router-model train/router.q4_k_m.gguf \\
    --router-gpu-layers 32

交互命令:
  /exit, /quit  - 退出
  /help         - 显示帮助
  /stats        - 显示统计信息
        """
    )
    
    # 数据库配置
    ap.add_argument("--db", default="runtime/otta_min.db", help="数据库路径 (默认: runtime/otta_min.db)")
    
    # 路由器配置（与 cli_once.py 相同）
    router_group = ap.add_argument_group("路由器配置")
    router_group.add_argument("--router-backend", choices=["py", "ollama", "cli"])
    router_group.add_argument("--router-model", help="路由器模型文件路径")
    router_group.add_argument("--router-gpu-layers", type=int, help="GPU 层数")
    router_group.add_argument("--router-threads", type=int, help="CPU 线程数")
    router_group.add_argument("--router-ctx-size", type=int, default=1024)
    
    ollama_group = ap.add_argument_group("Ollama 配置")
    ollama_group.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ollama_group.add_argument("--ollama-model")
    
    cli_group = ap.add_argument_group("CLI 执行器配置")
    cli_group.add_argument("--cli-executor")

    # 调试选项
    ap.add_argument("--verbose", "-v", action="store_true", help="显示路由器的原始输入/输出（用于调试）")
    
    args = ap.parse_args()

    # 创建路由器
    if args.router_backend or args.router_model:
        router = make_router_from_args(args)
        print(f"[配置] 使用命令行参数配置路由器")
    else:
        router = from_env()
        print(f"[配置] 使用环境变量配置路由器")
    
    print(f"[路由器] 后端={type(router).__name__}")
    
    agent, provider = make_agent_loop()

    print("\nOtta CLI - 交互模式")
    print("输入 /exit 退出, /help 查看帮助\n")
    
    exec_count = 0
    
    while True:
        try:
            s = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        
        if not s:
            continue
        
        # 命令处理
        if s.startswith("/"):
            cmd = s.lower()
            if cmd in ("/exit", "/quit"):
                print("再见！")
                break
            elif cmd == "/help":
                print("可用命令:")
                print("  /exit, /quit  - 退出")
                print("  /help         - 显示此帮助")
                print("  /stats        - 显示统计信息")
                continue
            elif cmd == "/stats":
                print(f"统计信息:")
                print(f"  - 本次会话执行: {exec_count} 次")
                try:
                    from store.db import Store
                    db_obj = Store(args.db)
                    db_obj.init()
                    total = db_obj.conn.execute("SELECT COUNT(*) FROM exec_runs").fetchone()[0]
                    golden = db_obj.conn.execute("SELECT COUNT(*) FROM exec_runs WHERE route='golden'").fetchone()[0]
                    print(f"  - 历史总执行: {total} 次")
                    if total > 0:
                        print(f"  - Golden 回放率: {golden/total*100:.1f}%")
                except Exception as e:
                    print(f"  - 无法读取历史统计: {e}")
                continue
            else:
                print(f"未知命令: {s}")
                continue
        
        # 执行用户指令
        out = run_once(s, db_path=args.db, router=router, agent=agent, provider=provider, verbose=getattr(args, 'verbose', False))
        exec_count += 1
        
        if out.get("blocked"):
            print("otta> [已拦截] 高风险操作需要确认")
        elif out.get("ok"):
            print("otta>", out.get("result"))
        else:
            print("otta> [失败]", out)

if __name__ == "__main__":
    main()
