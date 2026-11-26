"""Small SQLite persistence layer using short-lived connections and WAL."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from config import database_path, ist_date


STALE_AUDIO_PRUNE_INTERVAL_SECONDS = 600
_audio_prune_lock = threading.Lock()
_last_audio_prune_at: float | None = None


def _claim_stale_audio_prune() -> bool:
    global _last_audio_prune_at
    now = time.monotonic()
    with _audio_prune_lock:
        if (_last_audio_prune_at is not None
                and now - _last_audio_prune_at < STALE_AUDIO_PRUNE_INTERVAL_SECONDS):
            return False
        _last_audio_prune_at = now
        return True


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        day_index = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_leaderboard_day'"
        ).fetchone()
        if day_index and "deal_id asc" not in str(day_index["sql"]).lower():
            db.execute("DROP INDEX idx_leaderboard_day")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                arena_id TEXT NOT NULL,
                boss_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                date_ist TEXT NOT NULL,
                current_price INTEGER NOT NULL,
                start_price INTEGER NOT NULL,
                patience INTEGER NOT NULL DEFAULT 100,
                turn_number INTEGER NOT NULL DEFAULT 0,
                efficiency REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                condition_id TEXT NOT NULL DEFAULT '',
                challenge_deal_id TEXT,
                modifier_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turns (
                turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(session_id),
                turn_number INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, turn_number)
            );
            CREATE TABLE IF NOT EXISTS session_audio (
                session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
                audio_b64 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE REFERENCES sessions(session_id),
                arena_id TEXT NOT NULL,
                boss_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                date_ist TEXT NOT NULL,
                start_price INTEGER NOT NULL,
                final_price INTEGER NOT NULL,
                limit_price INTEGER NOT NULL,
                direction TEXT NOT NULL,
                efficiency REAL NOT NULL,
                patience INTEGER NOT NULL,
                status TEXT NOT NULL,
                debrief_json TEXT NOT NULL,
                audio_url TEXT,
                rank INTEGER NOT NULL DEFAULT 0,
                percentile REAL NOT NULL DEFAULT 0,
                challenge_deal_id TEXT,
                modifier_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leaderboard (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL UNIQUE REFERENCES deals(deal_id),
                arena_id TEXT NOT NULL,
                date_ist TEXT NOT NULL,
                player_name TEXT NOT NULL,
                boss_name TEXT NOT NULL,
                final_price INTEGER NOT NULL,
                efficiency REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_leaderboard_day
                ON leaderboard(arena_id, date_ist, efficiency DESC, created_at ASC, deal_id ASC);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_all_time
                ON leaderboard(arena_id, efficiency DESC, created_at ASC, deal_id ASC);
            CREATE TABLE IF NOT EXISTS daily_archive (
                date_ist TEXT NOT NULL,
                arena_id TEXT NOT NULL,
                winner_json TEXT NOT NULL,
                archived_at TEXT NOT NULL,
                PRIMARY KEY(date_ist, arena_id)
            );
            """
        )
        db.execute("DELETE FROM leaderboard WHERE deal_id IN (SELECT deal_id FROM deals WHERE status='walked_out')")
        for table, column, ddl in (
            ("sessions", "condition_id", "TEXT NOT NULL DEFAULT ''"),
            ("sessions", "challenge_deal_id", "TEXT"),
            ("sessions", "modifier_id", "TEXT"),
            ("deals", "challenge_deal_id", "TEXT"),
            ("deals", "modifier_id", "TEXT"),
        ):
            cols = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
            if column not in cols:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def get_session(session_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    return row_dict(row)


def create_session(values: dict[str, Any]) -> None:
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
    record = {"patience": 100, "condition_id": "", "challenge_deal_id": None, "modifier_id": None, **values}
    with connect() as db:
        if _claim_stale_audio_prune():
            _prune_stale_session_audio(db, cutoff_iso)
        db.execute(
            """INSERT INTO sessions(session_id,arena_id,boss_id,player_name,date_ist,current_price,
               start_price,patience,turn_number,efficiency,status,condition_id,challenge_deal_id,modifier_id,created_at,updated_at)
               VALUES(:session_id,:arena_id,:boss_id,:player_name,:date_ist,:current_price,
               :start_price,:patience,0,0,'active',:condition_id,:challenge_deal_id,:modifier_id,:created_at,:updated_at)""",
            record,
        )


def record_turn(session_id: str, values: dict[str, Any], session: dict[str, Any]) -> None:
    payload = {key: value for key, value in values.items() if key != "audio_b64"}
    with connect() as db:
        db.execute(
            "INSERT INTO turns(session_id,turn_number,payload_json,created_at) VALUES(?,?,?,?)",
            (session_id, values["turn_number"], json.dumps(payload, ensure_ascii=False), values["created_at"]),
        )
        if values.get("audio_b64"):
            db.execute("INSERT INTO session_audio(session_id,audio_b64) VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET audio_b64=excluded.audio_b64",
                       (session_id, values["audio_b64"]))
        else:
            db.execute("DELETE FROM session_audio WHERE session_id=?", (session_id,))
        db.execute(
            """UPDATE sessions SET current_price=?,patience=?,turn_number=?,efficiency=?,status=?,updated_at=?
               WHERE session_id=?""",
            (session["current_price"], session["patience"], session["turn_number"], session["efficiency"],
             session["status"], session["updated_at"], session_id),
        )


def get_turn(session_id: str, turn_number: int) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute(
            "SELECT payload_json FROM turns WHERE session_id=? AND turn_number=?",
            (session_id, turn_number),
        ).fetchone()
    return json.loads(row["payload_json"]) if row else None


def save_turn_audio_if_latest(session_id: str, turn_number: int, audio_b64: str) -> bool:
    with connect() as db:
        row = db.execute(
            "SELECT turn_number FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        deal = db.execute(
            "SELECT 1 FROM deals WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not row or deal is not None or int(row["turn_number"]) != int(turn_number):
            return False
        db.execute(
            "INSERT INTO session_audio(session_id,audio_b64) VALUES(?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET audio_b64=excluded.audio_b64",
            (session_id, audio_b64),
        )
        return True


def list_turns(session_id: str, include_audio: bool = True) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT payload_json FROM turns WHERE session_id=? ORDER BY turn_number", (session_id,)).fetchall()
        audio_row = (
            db.execute("SELECT audio_b64 FROM session_audio WHERE session_id=?", (session_id,)).fetchone()
            if include_audio else None
        )
    result = [json.loads(row["payload_json"]) for row in rows]
    if result and audio_row:
        result[-1]["audio_b64"] = audio_row["audio_b64"]
    return result


def find_deal_by_session(session_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM deals WHERE session_id=?", (session_id,)).fetchone()
    return row_dict(row)


def find_deal(deal_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,)).fetchone()
    return row_dict(row)


def save_deal(deal: dict[str, Any]) -> None:
    record = {"challenge_deal_id": None, "modifier_id": None, **deal}
    with connect() as db:
        db.execute(
            """INSERT INTO deals(deal_id,session_id,arena_id,boss_id,player_name,date_ist,start_price,
               final_price,limit_price,direction,efficiency,patience,status,debrief_json,audio_url,
               rank,percentile,challenge_deal_id,modifier_id,created_at)
               VALUES(:deal_id,:session_id,:arena_id,:boss_id,:player_name,:date_ist,:start_price,
               :final_price,:limit_price,:direction,:efficiency,:patience,:status,:debrief_json,:audio_url,
               :rank,:percentile,:challenge_deal_id,:modifier_id,:created_at)""",
            record,
        )
        if deal["status"] != "walked_out":
            db.execute(
                """INSERT INTO leaderboard(deal_id,arena_id,date_ist,player_name,boss_name,final_price,efficiency,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (deal["deal_id"], deal["arena_id"], deal["date_ist"], deal["player_name"], deal["boss_name"],
                 deal["final_price"], deal["efficiency"], deal["created_at"]),
            )


def update_deal_rank(deal_id: str, rank: int, percentile: float) -> None:
    with connect() as db:
        db.execute("UPDATE deals SET rank=?,percentile=? WHERE deal_id=?", (rank, percentile, deal_id))


def close_session(session_id: str, status: str, updated_at: str) -> None:
    with connect() as db:
        db.execute("UPDATE sessions SET status=?,updated_at=? WHERE session_id=?", (status, updated_at, session_id))


def clear_session_audio(session_id: str) -> None:
    with connect() as db:
        db.execute("DELETE FROM session_audio WHERE session_id=?", (session_id,))


def _leaderboard_scope(arena_id: str, date_text: str | None) -> tuple[str, tuple[Any, ...]]:
    if arena_id == "daily_market":
        date_text = date_text or ist_date().isoformat()
        return "arena_id=? AND date_ist=?", (arena_id, date_text)
    return "arena_id=?", (arena_id,)


def leaderboard_rows(arena_id: str, date_ist: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    where, scope_params = _leaderboard_scope(arena_id, date_ist)
    with connect() as db:
        rows = db.execute(
            f"""SELECT player_name,boss_name,final_price,efficiency,created_at,deal_id
               FROM leaderboard WHERE {where}
               ORDER BY efficiency DESC,created_at ASC,deal_id ASC LIMIT ?""",
            (*scope_params, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def compute_rank(deal_id: str, arena_id: str, date_ist: str | None = None) -> tuple[int, float]:
    """Compute a deterministic leaderboard rank using bounded-memory SQL counts."""
    where, scope_params = _leaderboard_scope(arena_id, date_ist)
    with connect() as db:
        current = db.execute(
            f"SELECT efficiency,created_at FROM leaderboard WHERE {where} AND deal_id=?",
            (*scope_params, deal_id),
        ).fetchone()
        if current is None:
            return 0, 0.0
        total = int(db.execute(f"SELECT COUNT(*) FROM leaderboard WHERE {where}", scope_params).fetchone()[0])
        ahead = int(db.execute(
            f"""SELECT COUNT(*) FROM leaderboard WHERE {where} AND (
                 efficiency>? OR (efficiency=? AND created_at<?) OR
                 (efficiency=? AND created_at=? AND deal_id<?))""",
            (*scope_params, current["efficiency"], current["efficiency"], current["created_at"],
             current["efficiency"], current["created_at"], deal_id),
        ).fetchone()[0])
    rank = ahead + 1
    percentile = round(max(0.0, 100.0 * (1.0 - (rank - 1) / max(1, total))), 1)
    return rank, percentile


def prune_stale_session_audio(cutoff_iso: str) -> int:
    with connect() as db:
        return _prune_stale_session_audio(db, cutoff_iso)


def _prune_stale_session_audio(connection: sqlite3.Connection, cutoff_iso: str) -> int:
    cursor = connection.execute(
        """DELETE FROM session_audio
           WHERE session_id IN (
             SELECT audio.session_id FROM session_audio AS audio
             LEFT JOIN sessions ON sessions.session_id=audio.session_id
             WHERE sessions.session_id IS NULL OR sessions.updated_at < ?
           )""",
        (cutoff_iso,),
    )
    return max(0, cursor.rowcount)


def archive_day(date_ist: str, arena_ids: list[str], archived_at: str) -> int:
    added = 0
    with connect() as db:
        for arena_id in arena_ids:
            row = db.execute(
                """SELECT player_name,boss_name,final_price,efficiency,created_at,deal_id
                   FROM leaderboard WHERE arena_id=? AND date_ist=?
                   ORDER BY efficiency DESC,created_at ASC,deal_id ASC LIMIT 1""",
                (arena_id, date_ist),
            ).fetchone()
            payload = json.dumps(dict(row) if row else {}, ensure_ascii=False)
            cursor = db.execute(
                "INSERT OR IGNORE INTO daily_archive(date_ist,arena_id,winner_json,archived_at) VALUES(?,?,?,?)",
                (date_ist, arena_id, payload, archived_at),
            )
            added += cursor.rowcount
    return added
