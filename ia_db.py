"""
ia_db.py - storage for the RMS Internal Audit Action Tracker (one SQLite file).

Tables: ia_findings, ia_actions, ia_kpis, ia_kpi_log, ia_documents (BLOBs), ia_comments, ia_logs, ia_meta.
Backing up that single file backs up everything (findings, actions, KPI history, documents and comments).

Set the DATABASE_PATH environment variable (e.g. a Railway volume such as /data/ia_tracker.db) so the
data survives redeploys.
"""
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

import ia_core as core
import ia_seed_data as seed

DB_FILE = os.getenv("DATABASE_PATH", "ia_tracker.db")
_db_dir = os.path.dirname(DB_FILE)
if _db_dir and not os.path.exists(_db_dir):
    os.makedirs(_db_dir, exist_ok=True)

MAX_FILE_MB = 100


def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _conn():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now():
    return datetime.now(core.KIGALI).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------------------------
# Schema + seeding
# ---------------------------------------------------------------------------------------------
def init():
    with _conn() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS ia_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, report TEXT, ref TEXT, src_ref TEXT, area TEXT, title TEXT,
            observation TEXT, criteria TEXT, risk TEXT, mgmt_position TEXT, mgmt_comment TEXT, timeline TEXT,
            priority TEXT, flagged_value REAL, flagged_label TEXT, notes TEXT, sort_order REAL,
            created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS ia_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL, seq INTEGER, text TEXT,
            owner TEXT, owner_confirmed INTEGER DEFAULT 0, due_date TEXT, status TEXT DEFAULT 'Not Started',
            pct INTEGER DEFAULT 0, note TEXT, closed_date TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ia_actions_f ON ia_actions(finding_id)")
        c.execute("""CREATE TABLE IF NOT EXISTS ia_kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL, seq INTEGER, name TEXT, unit TEXT,
            baseline REAL, target REAL, current REAL, agg TEXT DEFAULT 'sum', basis TEXT, note TEXT,
            breakdown TEXT, as_of TEXT, updated_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ia_kpis_f ON ia_kpis(finding_id)")
        c.execute("""CREATE TABLE IF NOT EXISTS ia_kpi_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, kpi_id INTEGER NOT NULL, as_of TEXT, value REAL, detail TEXT,
            note TEXT, author TEXT, created_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ia_kpilog_k ON ia_kpi_log(kpi_id)")
        c.execute("""CREATE TABLE IF NOT EXISTS ia_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL, filename TEXT, mime TEXT, size INTEGER,
            sha256 TEXT, note TEXT, data BLOB, uploaded_by TEXT, uploaded_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ia_docs_f ON ia_documents(finding_id)")
        c.execute("""CREATE TABLE IF NOT EXISTS ia_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL, author TEXT, body TEXT, created_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ia_comments_f ON ia_comments(finding_id)")
        c.execute("CREATE TABLE IF NOT EXISTS ia_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, message TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS ia_meta (key TEXT PRIMARY KEY, value TEXT)")


def _migrate_rwf():
    """Existing databases: show currency as 'Rwf' (and B for billions) instead of 'Frw'/'bn'."""
    if get_meta("rwf_migrated") == "1":
        return
    import re
    fix = lambda t: re.sub(r"(Rwf [\d.,]+)bn", r"\1B", t.replace("Frw", "Rwf")) if isinstance(t, str) else t  # noqa: E731
    with _conn() as conn:
        for tbl, cols in (("ia_findings", ["title", "observation", "criteria", "risk", "mgmt_comment", "timeline", "flagged_label", "notes"]),
                          ("ia_actions", ["text", "note"]), ("ia_kpis", ["name", "basis", "note"]), ("ia_comments", ["body"])):
            for r in conn.execute(f"SELECT id, {', '.join(cols)} FROM {tbl}").fetchall():
                new = [fix(r[c]) for c in cols]
                if new != [r[c] for c in cols]:
                    conn.execute(f"UPDATE {tbl} SET {', '.join(c + '=?' for c in cols)} WHERE id=?", new + [r["id"]])
        conn.execute("UPDATE ia_kpis SET unit='Rwf' WHERE unit='Frw'")
    set_meta("rwf_migrated", "1")


def get_meta(key, default=None):
    with _conn() as conn:
        r = conn.execute("SELECT value FROM ia_meta WHERE key=?", (key,)).fetchone()
    return r[0] if r else default


def set_meta(key, value):
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO ia_meta(key, value) VALUES (?, ?)", (key, value))


def seed_if_needed():
    """First run only: load the findings, actions and KPI baselines extracted from the two audit reports."""
    if get_meta("seeded") == "1":
        _migrate_rwf()
        return 0
    with _conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM ia_findings").fetchone()[0] > 0:
            _migrate_rwf()
            set_meta("seeded", "1")
            return 0
    n = 0
    now = _now()
    with _conn() as conn:
        for rkey, rep in seed.REPORTS.items():
            for i, f in enumerate(seed.FINDINGS[rkey], start=1):
                ref = f"{rep['prefix']}{i:02d}"
                cur = conn.execute(
                    """INSERT INTO ia_findings(report, ref, src_ref, area, title, observation, criteria, risk,
                       mgmt_position, mgmt_comment, timeline, priority, flagged_value, flagged_label, notes,
                       sort_order, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (rkey, ref, f["src_ref"], f["area"], f["title"], f["observation"], f["criteria"], f["risk"],
                     f["mgmt_position"], f["mgmt_comment"], f["timeline"], f["priority"], f["flagged_value"],
                     f["flagged_label"], "", i * 10, now, now))
                fid = cur.lastrowid
                n += 1
                for j, a in enumerate(f["actions"], start=1):
                    st = a["status"]
                    conn.execute(
                        """INSERT INTO ia_actions(finding_id, seq, text, owner, owner_confirmed, due_date, status, pct,
                           note, closed_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (fid, j, a["text"], a["owner"], 0, a["due"] or "", st, core.normalise_pct(st, a["pct"]),
                         a["note"], "", now, now))
                for j, k in enumerate(f["kpis"], start=1):
                    kc = conn.execute(
                        """INSERT INTO ia_kpis(finding_id, seq, name, unit, baseline, target, current, agg, basis, note,
                           breakdown, as_of, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (fid, j, k["name"], k["unit"], k["baseline"], k["target"], k["current"], k["agg"], k["basis"],
                         k["note"], json.dumps(k["breakdown"]) if k["breakdown"] else "",
                         (k["series"][-1][0] if k["series"] else rep["baseline_date"]), now))
                    kid = kc.lastrowid
                    if k["series"]:
                        for d, v in k["series"]:
                            conn.execute("INSERT INTO ia_kpi_log(kpi_id, as_of, value, detail, note, author, created_at)"
                                         " VALUES (?,?,?,?,?,?,?)", (kid, d, v, "", "From audit report", "Audit report", now))
                    else:
                        detail = json.dumps({b["label"]: b["baseline"] for b in k["breakdown"]}) if k["breakdown"] else ""
                        conn.execute("INSERT INTO ia_kpi_log(kpi_id, as_of, value, detail, note, author, created_at)"
                                     " VALUES (?,?,?,?,?,?,?)",
                                     (kid, rep["baseline_date"], k["baseline"], detail, "Baseline per audit report",
                                      "Audit report", now))
    set_meta("seeded", "1")
    set_meta("rwf_migrated", "1")
    set_meta("fy_label", "FY 2024–2025")
    log(f"📥 Loaded {n} findings, their actions and KPI baselines from the Regional and Central Warehouse audit reports")
    return n


# ---------------------------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------------------------
def log(message, who=""):
    with _conn() as conn:
        conn.execute("INSERT INTO ia_logs(timestamp, message) VALUES (?, ?)",
                     (_now(), (f"[{who}] " if who else "") + message))


def get_logs(limit=300):
    with _conn() as conn:
        return pd.read_sql("SELECT timestamp, message FROM ia_logs ORDER BY id DESC LIMIT ?", conn, params=(limit,))


# ---------------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------------
def load_findings():
    with _conn() as conn:
        df = pd.read_sql("SELECT * FROM ia_findings ORDER BY report, sort_order, id", conn)
    for col in ("src_ref", "area", "title", "observation", "criteria", "risk", "mgmt_position", "mgmt_comment",
                "timeline", "priority", "flagged_label", "notes"):
        df[col] = df[col].fillna("")
    return df


def load_actions():
    with _conn() as conn:
        df = pd.read_sql("""SELECT a.*, f.report, f.ref, f.title AS finding_title, f.area, f.priority
                            FROM ia_actions a JOIN ia_findings f ON f.id = a.finding_id
                            ORDER BY f.report, f.sort_order, a.seq, a.id""", conn)
    for col in ("text", "owner", "due_date", "status", "note", "closed_date"):
        df[col] = df[col].fillna("")
    df["pct"] = df["pct"].fillna(0).astype(int)
    return df


def load_kpis():
    with _conn() as conn:
        rows = conn.execute("""SELECT k.*, f.report, f.ref, f.title AS finding_title, f.area
                               FROM ia_kpis k JOIN ia_findings f ON f.id = k.finding_id
                               ORDER BY f.report, f.sort_order, k.seq, k.id""").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["breakdown"] = json.loads(d["breakdown"]) if d["breakdown"] else None
        except ValueError:
            d["breakdown"] = None
        out.append(d)
    return out


def kpi_history(kpi_id):
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM ia_kpi_log WHERE kpi_id=? ORDER BY as_of, id", (kpi_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["detail"] = json.loads(d["detail"]) if d["detail"] else None
        except ValueError:
            d["detail"] = None
        out.append(d)
    return out


def docs_summary():
    """{finding_id: [(doc_id, filename, size), ...]}"""
    with _conn() as conn:
        rows = conn.execute("SELECT id, finding_id, filename, size FROM ia_documents ORDER BY id").fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["finding_id"], []).append((r["id"], r["filename"], r["size"]))
    return out


def comments_all():
    with _conn() as conn:
        rows = conn.execute("SELECT finding_id, author, body, created_at FROM ia_comments ORDER BY id").fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["finding_id"], []).append((r["author"], r["body"], r["created_at"]))
    return out


def totals():
    with _conn() as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0] for t, tbl in
                [("findings", "ia_findings"), ("actions", "ia_actions"), ("kpis", "ia_kpis"),
                 ("measurements", "ia_kpi_log"), ("documents", "ia_documents"), ("comments", "ia_comments")]}


# ---------------------------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------------------------
FINDING_FIELDS = ["src_ref", "area", "title", "observation", "criteria", "risk", "mgmt_position", "mgmt_comment",
                  "timeline", "priority", "flagged_label", "notes"]


def update_finding(fid, fields, who=""):
    cols = [k for k in fields if k in FINDING_FIELDS or k == "flagged_value"]
    if not cols:
        return
    with _conn() as conn:
        conn.execute(f"UPDATE ia_findings SET {', '.join(c + '=?' for c in cols)}, updated_at=? WHERE id=?",
                     [fields[c] for c in cols] + [_now(), fid])
        ref = conn.execute("SELECT ref FROM ia_findings WHERE id=?", (fid,)).fetchone()[0]
    log(f"✏️ Updated finding {ref}", who)


def add_finding(report, fields, who=""):
    prefix = seed.REPORTS[report]["prefix"]
    with _conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM ia_findings WHERE report=?", (report,)).fetchone()[0]
        mx = conn.execute("SELECT MAX(sort_order) FROM ia_findings WHERE report=?", (report,)).fetchone()[0] or 0
        existing = {r[0] for r in conn.execute("SELECT ref FROM ia_findings WHERE report=?", (report,))}
        i = n + 1
        while f"{prefix}{i:02d}" in existing:
            i += 1
        ref = f"{prefix}{i:02d}"
        now = _now()
        cur = conn.execute(
            """INSERT INTO ia_findings(report, ref, src_ref, area, title, observation, criteria, risk, mgmt_position,
               mgmt_comment, timeline, priority, flagged_value, flagged_label, notes, sort_order, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (report, ref, fields.get("src_ref", ""), fields.get("area", ""), fields.get("title", ""),
             fields.get("observation", ""), fields.get("criteria", ""), fields.get("risk", ""),
             fields.get("mgmt_position", "No response"), fields.get("mgmt_comment", ""), fields.get("timeline", ""),
             fields.get("priority", "Medium"), fields.get("flagged_value"), fields.get("flagged_label", ""), "",
             mx + 10, now, now))
    log(f"➕ Added finding {ref}: {fields.get('title', '')}", who)
    return cur.lastrowid


# ---------------------------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------------------------
def save_action(action_id, text=None, owner=None, due_date=None, status=None, pct=None, note=None, who=""):
    """Update one action. Only arguments that are not None are changed. Returns True if anything changed."""
    with _conn() as conn:
        cur = conn.execute("""SELECT a.*, f.ref FROM ia_actions a JOIN ia_findings f ON f.id=a.finding_id
                              WHERE a.id=?""", (action_id,)).fetchone()
        if not cur:
            return False
        old = dict(cur)
        new = dict(old)
        if text is not None:
            new["text"] = text
        if owner is not None and owner != old["owner"]:
            new["owner"] = owner
            new["owner_confirmed"] = 1
        if due_date is not None:
            new["due_date"] = core.iso(due_date)
        if status is not None:
            new["status"] = status
        if note is not None:
            new["note"] = note
        new["pct"] = core.normalise_pct(new["status"], old["pct"] if pct is None else pct)
        if new["status"] == core.CL and old["status"] != core.CL:
            new["closed_date"] = core.today().isoformat()
        elif new["status"] != core.CL:
            new["closed_date"] = ""
        keys = ["text", "owner", "owner_confirmed", "due_date", "status", "pct", "note", "closed_date"]
        if all(new[k] == old[k] for k in keys):
            return False
        conn.execute(f"UPDATE ia_actions SET {', '.join(k + '=?' for k in keys)}, updated_at=? WHERE id=?",
                     [new[k] for k in keys] + [_now(), action_id])
    bits = []
    if new["status"] != old["status"]:
        bits.append(f"status {old['status']} → {new['status']}")
    if new["owner"] != old["owner"]:
        bits.append(f"owner → {new['owner'] or '—'}")
    if new["due_date"] != old["due_date"]:
        bits.append(f"due → {core.fmt_date(new['due_date'])}")
    if new["pct"] != old["pct"]:
        bits.append(f"{new['pct']}%")
    if new["note"] != old["note"]:
        bits.append("note updated")
    if new["text"] != old["text"]:
        bits.append("wording edited")
    log(f"✅ {old['ref']} action {old['seq']}: " + ", ".join(bits), who)
    return True


def add_action(finding_id, text, owner="", due_date=None, status=core.NS, who=""):
    with _conn() as conn:
        seq = (conn.execute("SELECT MAX(seq) FROM ia_actions WHERE finding_id=?", (finding_id,)).fetchone()[0] or 0) + 1
        ref = conn.execute("SELECT ref FROM ia_findings WHERE id=?", (finding_id,)).fetchone()[0]
        now = _now()
        conn.execute("""INSERT INTO ia_actions(finding_id, seq, text, owner, owner_confirmed, due_date, status, pct,
                        note, closed_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (finding_id, seq, text, owner, 1 if owner else 0, core.iso(due_date), status,
                      core.normalise_pct(status, 0), "", "", now, now))
    log(f"➕ {ref}: added action {seq}", who)


def delete_action(action_id, who=""):
    with _conn() as conn:
        r = conn.execute("SELECT a.seq, f.ref FROM ia_actions a JOIN ia_findings f ON f.id=a.finding_id WHERE a.id=?",
                         (action_id,)).fetchone()
        conn.execute("DELETE FROM ia_actions WHERE id=?", (action_id,))
    if r:
        log(f"🗑️ {r['ref']}: removed action {r['seq']}", who)


# ---------------------------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------------------------
def record_kpi(kpi_id, current=None, breakdown_current=None, as_of=None, note="", who=""):
    """Record a new measurement. `breakdown_current` = {label: value} for KPIs that have a breakdown."""
    as_of = core.iso(as_of) or core.today().isoformat()
    with _conn() as conn:
        k = conn.execute("""SELECT k.*, f.ref FROM ia_kpis k JOIN ia_findings f ON f.id=k.finding_id WHERE k.id=?""",
                         (kpi_id,)).fetchone()
        if not k:
            return
        bd = json.loads(k["breakdown"]) if k["breakdown"] else None
        detail = ""
        if bd and breakdown_current is not None:
            for b in bd:
                if b["label"] in breakdown_current and breakdown_current[b["label"]] is not None:
                    b["current"] = float(breakdown_current[b["label"]])
            current = core.aggregate([b["current"] for b in bd], k["agg"])
            detail = json.dumps({b["label"]: b["current"] for b in bd})
        if current is None:
            return
        conn.execute("UPDATE ia_kpis SET current=?, breakdown=?, as_of=?, updated_at=? WHERE id=?",
                     (float(current), json.dumps(bd) if bd else "", as_of, _now(), kpi_id))
        conn.execute("INSERT INTO ia_kpi_log(kpi_id, as_of, value, detail, note, author, created_at) VALUES (?,?,?,?,?,?,?)",
                     (kpi_id, as_of, float(current), detail, note, who, _now()))
    log(f"🎯 {k['ref']} KPI “{k['name']}”: {core.fmt_value(current, k['unit'])} as of {core.fmt_date(as_of)}", who)


def update_kpi_definition(kpi_id, target="__keep__", name=None, basis=None, note=None, who=""):
    with _conn() as conn:
        k = conn.execute("""SELECT k.*, f.ref FROM ia_kpis k JOIN ia_findings f ON f.id=k.finding_id WHERE k.id=?""",
                         (kpi_id,)).fetchone()
        if not k:
            return
        sets, vals = [], []
        if target != "__keep__":
            sets.append("target=?")
            vals.append(None if target is None else float(target))
        for col, v in (("name", name), ("basis", basis), ("note", note)):
            if v is not None:
                sets.append(f"{col}=?")
                vals.append(v)
        if not sets:
            return
        conn.execute(f"UPDATE ia_kpis SET {', '.join(sets)}, updated_at=? WHERE id=?", vals + [_now(), kpi_id])
    log(f"🎯 {k['ref']} KPI “{k['name']}”: definition updated", who)


def delete_kpi_measurement(log_id, who=""):
    """Remove one measurement and re-sync the KPI's current value to its latest remaining measurement."""
    with _conn() as conn:
        r = conn.execute("SELECT kpi_id FROM ia_kpi_log WHERE id=?", (log_id,)).fetchone()
        if not r:
            return
        kid = r["kpi_id"]
        conn.execute("DELETE FROM ia_kpi_log WHERE id=?", (log_id,))
        last = conn.execute("SELECT * FROM ia_kpi_log WHERE kpi_id=? ORDER BY as_of DESC, id DESC LIMIT 1", (kid,)).fetchone()
        k = conn.execute("SELECT * FROM ia_kpis WHERE id=?", (kid,)).fetchone()
        if last:
            bd = json.loads(k["breakdown"]) if k["breakdown"] else None
            det = json.loads(last["detail"]) if last["detail"] else None
            if bd and det:
                for b in bd:
                    if b["label"] in det:
                        b["current"] = det[b["label"]]
            conn.execute("UPDATE ia_kpis SET current=?, breakdown=?, as_of=? WHERE id=?",
                         (last["value"], json.dumps(bd) if bd else "", last["as_of"], kid))
    log("🗑️ Removed a KPI measurement", who)


# ---------------------------------------------------------------------------------------------
# Documents + comments
# ---------------------------------------------------------------------------------------------
def add_document(finding_id, filename, mime, data, note="", who=""):
    sha = hashlib.sha256(data).hexdigest()
    with _conn() as conn:
        ref = conn.execute("SELECT ref FROM ia_findings WHERE id=?", (finding_id,)).fetchone()[0]
        conn.execute("""INSERT INTO ia_documents(finding_id, filename, mime, size, sha256, note, data, uploaded_by, uploaded_at)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                     (finding_id, filename, mime, len(data), sha, note, data, who, _now()))
    log(f"📎 {ref}: attached “{filename}”", who)


def list_documents(finding_id):
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, filename, mime, size, note, uploaded_by, uploaded_at FROM ia_documents WHERE finding_id=? ORDER BY id",
            (finding_id,))]


def get_document(doc_id):
    with _conn() as conn:
        r = conn.execute("SELECT * FROM ia_documents WHERE id=?", (doc_id,)).fetchone()
    return dict(r) if r else None


def delete_document(doc_id, who=""):
    with _conn() as conn:
        r = conn.execute("SELECT filename FROM ia_documents WHERE id=?", (doc_id,)).fetchone()
        conn.execute("DELETE FROM ia_documents WHERE id=?", (doc_id,))
    if r:
        log(f"🗑️ Removed attachment “{r['filename']}”", who)


def add_comment(finding_id, author, body):
    with _conn() as conn:
        ref = conn.execute("SELECT ref FROM ia_findings WHERE id=?", (finding_id,)).fetchone()[0]
        conn.execute("INSERT INTO ia_comments(finding_id, author, body, created_at) VALUES (?,?,?,?)",
                     (finding_id, author or "Anonymous", body, _now()))
    log(f"💬 {ref}: comment added", author)


def list_comments(finding_id):
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, author, body, created_at FROM ia_comments WHERE finding_id=? ORDER BY id", (finding_id,))]


def read_db_bytes():
    with open(DB_FILE, "rb") as f:
        return f.read()
