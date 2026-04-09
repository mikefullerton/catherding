"""SQLite schema migration and parameterized query helpers."""
import sqlite3
from datetime import datetime

DB_VERSION = 3


def get_db(path: str) -> sqlite3.Connection:
    """Open database, run migrations if needed, return connection."""
    db = sqlite3.connect(path)
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version < DB_VERSION:
        db.executescript("""
            DROP TABLE IF EXISTS sessions;
            DROP TABLE IF EXISTS weekly_usage;
            DROP TABLE IF EXISTS usage;
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                session_name TEXT,
                model_id TEXT NOT NULL,
                model_display TEXT NOT NULL,
                claude_version TEXT,
                cwd TEXT,
                project_dir TEXT,
                transcript_path TEXT,
                context_window_size INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                duration_s INTEGER NOT NULL,
                api_duration_ms INTEGER NOT NULL DEFAULT 0,
                lines_added INTEGER NOT NULL,
                lines_removed INTEGER NOT NULL,
                total_cost_usd TEXT NOT NULL,
                total_input_tokens INTEGER NOT NULL DEFAULT 0,
                total_output_tokens INTEGER NOT NULL DEFAULT 0,
                cache_create_tokens INTEGER NOT NULL DEFAULT 0,
                cache_read_tokens INTEGER NOT NULL DEFAULT 0,
                context_used_pct INTEGER NOT NULL
            );
            CREATE TABLE weekly_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                week_start TEXT NOT NULL,
                elapsed_hours INTEGER NOT NULL,
                day REAL NOT NULL,
                weekly_pct REAL NOT NULL,
                daily_avg_pct REAL NOT NULL,
                five_hour_pct REAL NOT NULL,
                five_hour_resets_at INTEGER,
                seven_day_resets_at INTEGER,
                projected_pct REAL NOT NULL
            );
        """)
        db.execute(f"PRAGMA user_version={DB_VERSION}")
        db.commit()
    return db


def upsert_session(db: sqlite3.Connection, **kw) -> None:
    """Insert or update a session record."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("""
        INSERT INTO sessions (
            session_id, session_name, model_id, model_display, claude_version,
            cwd, project_dir, transcript_path, context_window_size,
            first_seen, last_seen, duration_s, api_duration_ms,
            lines_added, lines_removed, total_cost_usd,
            total_input_tokens, total_output_tokens,
            cache_create_tokens, cache_read_tokens, context_used_pct)
        VALUES (
            :session_id, :session_name, :model_id, :model_display, :claude_version,
            :cwd, :project_dir, :transcript_path, :context_window_size,
            :now, :now, :duration_s, :api_duration_ms,
            :lines_added, :lines_removed, :total_cost_usd,
            :total_input_tokens, :total_output_tokens,
            :cache_create_tokens, :cache_read_tokens, :context_used_pct)
        ON CONFLICT(session_id) DO UPDATE SET
            session_name=:session_name, last_seen=:now,
            duration_s=:duration_s, api_duration_ms=:api_duration_ms,
            lines_added=:lines_added, lines_removed=:lines_removed,
            total_cost_usd=:total_cost_usd,
            total_input_tokens=:total_input_tokens,
            total_output_tokens=:total_output_tokens,
            cache_create_tokens=:cache_create_tokens,
            cache_read_tokens=:cache_read_tokens,
            context_used_pct=:context_used_pct
    """, {**kw, "now": now})
    db.commit()


def append_weekly_usage(db: sqlite3.Connection, **kw) -> None:
    """Append a weekly usage row, skipping if values unchanged from last row."""
    last = db.execute("""
        SELECT weekly_pct, five_hour_pct, projected_pct
        FROM weekly_usage WHERE session_id=:session_id
        ORDER BY id DESC LIMIT 1
    """, {"session_id": kw["session_id"]}).fetchone()

    if last and (last[0] == kw["weekly_pct"] and last[1] == kw["five_hour_pct"]
                 and last[2] == kw["projected_pct"]):
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("""
        INSERT INTO weekly_usage (
            timestamp, session_id, week_start, elapsed_hours, day,
            weekly_pct, daily_avg_pct, five_hour_pct,
            five_hour_resets_at, seven_day_resets_at, projected_pct)
        VALUES (
            :now, :session_id, :week_start, :elapsed_hours, :elapsed_day,
            :weekly_pct, :daily_avg_pct, :five_hour_pct,
            :five_hour_resets_at, :seven_day_resets_at, :projected_pct)
    """, {**kw, "now": now})
    db.commit()
