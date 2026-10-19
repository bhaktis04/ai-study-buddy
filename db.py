import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime

DB_PATH = "study_buddy.db"

def _conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with closing(_conn()) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            sources TEXT,
            created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            created_at TEXT)""")
        c.commit()

def create_session(title):
    sid = str(uuid.uuid4())
    with closing(_conn()) as c:
        c.execute("INSERT INTO sessions VALUES (?, ?, ?)",
                  (sid, title, datetime.now().isoformat(timespec="seconds")))
        c.commit()
    return sid

def add_message(session_id, role, content, sources=None):
    with closing(_conn()) as c:
        c.execute(
            "INSERT INTO messages (session_id, role, content, sources, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, json.dumps(sources or []),
             datetime.now().isoformat(timespec="seconds")))
        c.commit()

def get_messages(session_id):
    with closing(_conn()) as c:
        rows = c.execute(
            "SELECT role, content, sources FROM messages WHERE session_id=? ORDER BY id",
            (session_id,)).fetchall()
    return [{"role": r, "content": t, "sources": json.loads(s or "[]")} for r, t, s in rows]

def list_sessions():
    with closing(_conn()) as c:
        return c.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC").fetchall()

def delete_session(session_id):
    with closing(_conn()) as c:
        c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        c.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        c.commit()

def save_quiz_result(topic, score, total):
    with closing(_conn()) as c:
        c.execute("INSERT INTO quiz_results (topic, score, total, created_at) VALUES (?, ?, ?, ?)",
                  (topic, score, total, datetime.now().isoformat(timespec="seconds")))
        c.commit()

def get_quiz_results():
    with closing(_conn()) as c:
        return c.execute(
            "SELECT topic, score, total, created_at FROM quiz_results ORDER BY id DESC").fetchall()