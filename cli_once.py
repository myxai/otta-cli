from __future__ import annotations
import argparse, os
from router.factory import from_env
from nanobot_bridge.agent import make_agent_loop
from pipeline import run_once

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--db", default="otta_min.db")
    args = ap.parse_args()

    router = from_env()
    agent, provider = make_agent_loop()

    out = run_once(args.text, db_path=args.db, router=router, agent=agent, provider=provider)
    print(out)

if __name__ == "__main__":
    main()
