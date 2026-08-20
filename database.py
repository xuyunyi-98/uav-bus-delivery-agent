"""
SQLite 数据持久化模块
存储历史调度记录，支持回看与对比
"""
import sqlite3, json, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "dispatch_history.db")

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def init_db():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS dispatch_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL, command TEXT NOT NULL,
            weather TEXT NOT NULL, objective TEXT NOT NULL,
            num_tasks INTEGER NOT NULL, num_drones INTEGER NOT NULL,
            num_buses INTEGER NOT NULL, total_time REAL NOT NULL,
            total_cost REAL NOT NULL, total_carbon REAL NOT NULL,
            fitness REAL NOT NULL, weights TEXT NOT NULL,
            depots_json TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS dispatch_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL, task_id INTEGER NOT NULL,
            method TEXT NOT NULL, vehicle_id TEXT NOT NULL,
            depot_id TEXT DEFAULT '', weight REAL DEFAULT 0,
            urgency TEXT DEFAULT '普通', item_type TEXT DEFAULT '常规',
            FOREIGN KEY (run_id) REFERENCES dispatch_runs(id) ON DELETE CASCADE
        );
    """)
    c.commit(); c.close()

init_db()


def save_dispatch(command, weather, objective, num_drones, num_buses,
                  weights, tasks, plan, metrics, score, depots=None):
    c = _conn()
    cur = c.cursor()
    cur.execute("""INSERT INTO dispatch_runs
        (timestamp,command,weather,objective,num_tasks,num_drones,num_buses,
         total_time,total_cost,total_carbon,fitness,weights,depots_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), command, weather,
         objective, len(tasks), num_drones, num_buses,
         metrics["time"], metrics["cost"], metrics["carbon"], score,
         json.dumps(weights, ensure_ascii=False),
         json.dumps(depots or [], ensure_ascii=False)))
    rid = cur.lastrowid
    for item in plan:
        t = next((x for x in tasks if x["id"] == item["task_id"]), {})
        cur.execute("""INSERT INTO dispatch_details
            (run_id,task_id,method,vehicle_id,depot_id,weight,urgency,item_type)
            VALUES(?,?,?,?,?,?,?,?)""",
            (rid, item["task_id"], item["method"],
             item.get("vehicle_id",""), item.get("depot_id",""),
             t.get("weight",0), t.get("urgency","普通"), t.get("item_type","常规")))
    c.commit(); c.close()
    return rid

def get_history(limit=50):
    c = _conn()
    rows = c.execute("SELECT * FROM dispatch_runs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_run_detail(run_id):
    c = _conn()
    rows = c.execute("SELECT * FROM dispatch_details WHERE run_id=? ORDER BY task_id", (run_id,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_run_summary(run_id):
    c = _conn()
    r = c.execute("SELECT * FROM dispatch_runs WHERE id=?", (run_id,)).fetchone()
    c.close()
    return dict(r) if r else None

def compare_runs(a, b):
    r1, r2 = get_run_summary(a), get_run_summary(b)
    if not r1 or not r2: return None
    return {
        "run1": r1, "run2": r2,
        "detail1": get_run_detail(a), "detail2": get_run_detail(b),
        "diff": {
            "time": round(r2["total_time"]-r1["total_time"],2),
            "cost": round(r2["total_cost"]-r1["total_cost"],2),
            "carbon": round(r2["total_carbon"]-r1["total_carbon"],2),
            "fitness": round(r2["fitness"]-r1["fitness"],2),
        }
    }

def delete_run(run_id):
    c = _conn()
    c.execute("DELETE FROM dispatch_runs WHERE id=?", (run_id,))
    c.commit(); c.close()

def delete_runs(run_ids):
    """???????????????"""
    if not run_ids:
        return 0
    c = _conn()
    qmarks = ",".join("?" * len(run_ids))
    cur = c.execute(f"DELETE FROM dispatch_runs WHERE id IN ({qmarks})", tuple(run_ids))
    n = cur.rowcount
    c.commit(); c.close()
    return n

def get_stats():
    c = _conn()
    n = c.execute("SELECT COUNT(*) as cnt FROM dispatch_runs").fetchone()["cnt"]
    if n == 0: c.close(); return {"total_runs": 0}
    s = c.execute("""SELECT COUNT(*) as total_runs,
        ROUND(AVG(total_time),1) as avg_time,
        ROUND(AVG(total_cost),1) as avg_cost,
        ROUND(AVG(total_carbon),1) as avg_carbon,
        ROUND(AVG(fitness),1) as avg_fitness,
        ROUND(MIN(total_cost),1) as min_cost,
        ROUND(MAX(total_cost),1) as max_cost
        FROM dispatch_runs""").fetchone()
    top = c.execute("SELECT objective,COUNT(*) as cnt FROM dispatch_runs GROUP BY objective ORDER BY cnt DESC LIMIT 1").fetchone()
    c.close()
    return dict(s) | {"top_objective": top["objective"] if top else "—"}