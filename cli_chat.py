from __future__ import annotations
import os
from router.factory import from_env
from nanobot_bridge.agent import make_agent_loop
from pipeline import run_once

def main():
    router = from_env()
    agent, provider = make_agent_loop()
    db = os.environ.get("OTTA_DB","otta_min.db")

    print("Otta minimal CLI. Type 'exit' to quit.")
    while True:
        try:
            s = input("you> ").strip()
        except EOFError:
            break
        if not s:
            continue
        if s.lower() in ("exit","quit"):
            break
        out = run_once(s, db_path=db, router=router, agent=agent, provider=provider)
        if out.get("blocked"):
            print("otta> [blocked] high risk / need confirm")
        elif out.get("ok"):
            print("otta>", out.get("result"))
        else:
            print("otta> [fail]", out)

if __name__ == "__main__":
    main()
