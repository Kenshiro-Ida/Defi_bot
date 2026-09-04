"""Deposit storage.

Supports two backends chosen automatically:

* PostgreSQL  -- when DATABASE_URL is set (recommended on Render, since its
  filesystem is ephemeral and a SQLite file would be wiped on redeploy).
* SQLite      -- fallback for local development (file: deposits.db).

Public API:
    init_db()
    insert_deposit(amount, address, tx_hash, from_where, status="sent", telegram_message_id=None, error=None) -> row id
    list_deposits(limit=100, offset=0, from_where=None, address=None) -> list[dict]
    count_deposits(from_where=None, address=None) -> int
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith("postgres")

SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "deposits.db"))

_lock = threading.Lock()

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row

    # Render / Heroku sometimes provide "postgres://"; psycopg wants "postgresql://".
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Postgres helpers ──────────────────────────────────────────────────────
def _pg_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def _pg_init():
    with _pg_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deposits (
                id                   BIGSERIAL PRIMARY KEY,
                amount               TEXT NOT NULL,
                address              TEXT NOT NULL,
                tx_hash              TEXT NOT NULL,
                from_where           TEXT NOT NULL DEFAULT 'website',
                status               TEXT NOT NULL DEFAULT 'sent',
                telegram_message_id  BIGINT,
                error                TEXT,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_address ON deposits (address)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_from_where ON deposits (from_where)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_tx_hash ON deposits (tx_hash)")


# ── SQLite helpers ────────────────────────────────────────────────────────
def _sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_init():
    with _lock, _sqlite_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deposits (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                amount               TEXT NOT NULL,
                address              TEXT NOT NULL,
                tx_hash              TEXT NOT NULL,
                from_where           TEXT NOT NULL DEFAULT 'website',
                status               TEXT NOT NULL DEFAULT 'sent',
                telegram_message_id  INTEGER,
                error                TEXT,
                created_at           TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_address ON deposits (address)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_from_where ON deposits (from_where)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_tx_hash ON deposits (tx_hash)")


# ── Public API ────────────────────────────────────────────────────────────
def init_db():
    if USE_POSTGRES:
        _pg_init()
    else:
        _sqlite_init()


def insert_deposit(amount, address, tx_hash, from_where="website",
                   status="sent", telegram_message_id=None, error=None):
    if USE_POSTGRES:
        with _pg_conn() as conn:
            row = conn.execute(
                """
                INSERT INTO deposits (amount, address, tx_hash, from_where, status, telegram_message_id, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (amount, address, tx_hash, from_where, status, telegram_message_id, error),
            ).fetchone()
            return row["id"]
    else:
        with _lock, _sqlite_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO deposits (amount, address, tx_hash, from_where, status, telegram_message_id, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (amount, address, tx_hash, from_where, status, telegram_message_id, error, _now_iso()),
            )
            return cur.lastrowid


def _build_filters(from_where, address, placeholder):
    clauses, params = [], []
    if from_where:
        clauses.append(f"from_where = {placeholder}")
        params.append(from_where)
    if address:
        clauses.append(f"address = {placeholder}")
        params.append(address)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def list_deposits(limit=100, offset=0, from_where=None, address=None):
    limit = max(1, min(int(limit), 1000))
    offset = max(0, int(offset))
    if USE_POSTGRES:
        where, params = _build_filters(from_where, address, "%s")
        sql = f"SELECT * FROM deposits{where} ORDER BY id DESC LIMIT %s OFFSET %s"
        with _pg_conn() as conn:
            rows = conn.execute(sql, (*params, limit, offset)).fetchall()
            return [_normalize(dict(r)) for r in rows]
    else:
        where, params = _build_filters(from_where, address, "?")
        sql = f"SELECT * FROM deposits{where} ORDER BY id DESC LIMIT ? OFFSET ?"
        with _lock, _sqlite_conn() as conn:
            rows = conn.execute(sql, (*params, limit, offset)).fetchall()
            return [_normalize(dict(r)) for r in rows]


def count_deposits(from_where=None, address=None):
    if USE_POSTGRES:
        where, params = _build_filters(from_where, address, "%s")
        with _pg_conn() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM deposits{where}", tuple(params)).fetchone()
            return int(row["n"])
    else:
        where, params = _build_filters(from_where, address, "?")
        with _lock, _sqlite_conn() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM deposits{where}", tuple(params)).fetchone()
            return int(row["n"])


def _normalize(row):
    """Ensure created_at is a JSON-serializable ISO string."""
    ca = row.get("created_at")
    if isinstance(ca, datetime):
        row["created_at"] = ca.isoformat()
    return row
