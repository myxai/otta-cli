from __future__ import annotations
import sqlite3, json, time, uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

@dataclass
class GoldenPlan:
    case_key: str
    version: int
    template_id: str
    plan: Dict[str, Any]
    replayable: int = 1

class Store:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def init(self):
        import pathlib
        schema = pathlib.Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        self.conn.executescript(schema)
        self.conn.commit()
        self._auto_migrate()

    def _auto_migrate(self):
        """检测并补齐 v4 新增列（intent），兼容旧库"""
        cursor = self.conn.execute("PRAGMA table_info(exec_runs)")
        existing = {row["name"] for row in cursor.fetchall()}
        for col, typedef in [("intent", "TEXT NOT NULL DEFAULT ''")]:
            if col not in existing:
                self.conn.execute(f"ALTER TABLE exec_runs ADD COLUMN {col} {typedef}")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def get_golden(self, case_key: str) -> Optional[GoldenPlan]:
        row = self.conn.execute("SELECT * FROM golden_plans WHERE case_key=?", (case_key,)).fetchone()
        if not row:
            return None
        return GoldenPlan(
            case_key=row["case_key"],
            version=int(row["version"]),
            template_id=row["template_id"],
            plan=json.loads(row["plan_json"]),
            replayable=int(row["replayable"]),
        )

    def upsert_golden(self, case_key: str, template_id: str, plan: Dict[str, Any], replayable: int = 1):
        row = self.conn.execute("SELECT version FROM golden_plans WHERE case_key=?", (case_key,)).fetchone()
        if row:
            version = int(row["version"]) + 1
            self.conn.execute(
                "UPDATE golden_plans SET version=?, template_id=?, plan_json=?, replayable=?, last_used_at=? WHERE case_key=?",
                (version, template_id, json.dumps(plan, ensure_ascii=False), replayable, now_iso(), case_key),
            )
        else:
            self.conn.execute(
                "INSERT INTO golden_plans(case_key,version,template_id,plan_json,replayable,created_at,last_used_at) VALUES(?,?,?,?,?,?,?)",
                (case_key, 1, template_id, json.dumps(plan, ensure_ascii=False), replayable, now_iso(), now_iso()),
            )
        self.conn.commit()

    def touch_golden(self, case_key: str):
        self.conn.execute("UPDATE golden_plans SET last_used_at=? WHERE case_key=?", (now_iso(), case_key))
        self.conn.commit()

    def delete_golden(self, case_key: str) -> bool:
        """删除指定的 golden 记录，返回是否成功"""
        cursor = self.conn.execute("DELETE FROM golden_plans WHERE case_key=?", (case_key,))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_all_goldens(self):
        """列出所有 golden 记录"""
        rows = self.conn.execute(
            "SELECT case_key, version, template_id, replayable, created_at, last_used_at FROM golden_plans ORDER BY last_used_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def insert_candidate(self, case_key: str, template_id: str, plan: Dict[str, Any]) -> str:
        cid = uuid.uuid4().hex
        self.conn.execute(
            "INSERT INTO golden_candidates(candidate_id,case_key,template_id,plan_json,status,created_at) VALUES(?,?,?,?,?,?)",
            (cid, case_key, template_id, json.dumps(plan, ensure_ascii=False), "new", now_iso()),
        )
        self.conn.commit()
        return cid

    def update_candidate(self, candidate_id: str, status: str, fail_reason: str = ""):
        self.conn.execute(
            "UPDATE golden_candidates SET status=?, fail_reason=?, tried_at=? WHERE candidate_id=?",
            (status, fail_reason, now_iso(), candidate_id),
        )
        self.conn.commit()

    def log_run(self, case_key: str, route: str, source: str, success: bool,
                latency_ms: int, effective_steps: int, cloud_called: bool,
                fail_stage: str = "", *, intent: str = ""):
        rid = uuid.uuid4().hex
        self.conn.execute(
            "INSERT INTO exec_runs(run_id,case_key,route,source,success,latency_ms,"
            "effective_steps,cloud_called,fail_stage,intent,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (rid, case_key, route, source, 1 if success else 0, latency_ms,
             effective_steps, 1 if cloud_called else 0, fail_stage,
             intent, now_iso()),
        )
        self.conn.commit()


    def update_capability_graph_from_plan(self, plan: Dict[str, Any]):
        """Learn capability chains from an executed plan (steps)."""
        steps = plan.get("steps", [])
        if not isinstance(steps, list) or len(steps) < 2:
            return
        names = []
        for st in steps:
            if not isinstance(st, dict):
                continue
            nm = st.get("capability") or st.get("tool")
            if isinstance(nm, str) and nm:
                names.append(nm)
        if len(names) < 2:
            return
        for a, b in zip(names, names[1:]):
            self._upsert_edge(a, b)

    def _upsert_edge(self, src: str, dst: str):
        row = self.conn.execute("SELECT count FROM capability_edges WHERE src=? AND dst=?", (src, dst)).fetchone()
        if row:
            self.conn.execute(
                "UPDATE capability_edges SET count=?, last_used_at=? WHERE src=? AND dst=?",
                (int(row["count"]) + 1, now_iso(), src, dst),
            )
        else:
            self.conn.execute(
                "INSERT INTO capability_edges(src,dst,count,last_used_at) VALUES(?,?,?,?)",
                (src, dst, 1, now_iso()),
            )
        self.conn.commit()

    def top_edges(self, limit: int = 30):
        rows = self.conn.execute(
            "SELECT src,dst,count,last_used_at FROM capability_edges ORDER BY count DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
