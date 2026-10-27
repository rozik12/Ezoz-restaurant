"""SQLite storage: users, administrators, leads and funnel events."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    full_name  TEXT,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    blocked    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admins (
    user_id  INTEGER PRIMARY KEY,
    added_by INTEGER NOT NULL,
    added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leads (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    name         TEXT,
    username     TEXT,
    phone        TEXT NOT NULL,
    event_date   TEXT NOT NULL,
    guests       INTEGER,
    tier         TEXT,
    estimate_uzs INTEGER,
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    kind    TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    ts      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Database.connect() was not called"
        return self._db

    async def _one(self, sql: str, args: tuple = ()) -> Any:
        async with self.db.execute(sql, args) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    # ---------- users ----------
    async def upsert_user(self, user_id: int, username: str | None, full_name: str) -> None:
        now = _now().isoformat()
        await self.db.execute(
            """INSERT INTO users(user_id, username, full_name, first_seen, last_seen)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 username=excluded.username, full_name=excluded.full_name,
                 last_seen=excluded.last_seen, blocked=0""",
            (user_id, username, full_name, now, now),
        )
        await self.db.commit()

    async def broadcast_targets(self) -> list[int]:
        async with self.db.execute("SELECT user_id FROM users WHERE blocked=0") as cur:
            return [r[0] for r in await cur.fetchall()]

    async def mark_blocked(self, user_id: int) -> None:
        await self.db.execute("UPDATE users SET blocked=1 WHERE user_id=?", (user_id,))
        await self.db.commit()

    # ---------- admins ----------
    async def is_admin(self, user_id: int) -> bool:
        return bool(await self._one("SELECT 1 FROM admins WHERE user_id=?", (user_id,)))

    async def add_admin(self, user_id: int, added_by: int) -> bool:
        """Returns False when the id was already an administrator."""
        if await self.is_admin(user_id):
            return False
        await self.db.execute(
            "INSERT INTO admins(user_id, added_by, added_at) VALUES(?,?,?)",
            (user_id, added_by, _now().isoformat()),
        )
        await self.db.commit()
        return True

    async def remove_admin(self, user_id: int) -> bool:
        cur = await self.db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await self.db.commit()
        return cur.rowcount > 0

    async def list_admins(self) -> list[aiosqlite.Row]:
        async with self.db.execute(
            """SELECT a.user_id, u.username, u.full_name
               FROM admins a LEFT JOIN users u ON u.user_id=a.user_id
               ORDER BY a.added_at"""
        ) as cur:
            return list(await cur.fetchall())

    async def admin_ids(self) -> list[int]:
        async with self.db.execute("SELECT user_id FROM admins") as cur:
            return [r[0] for r in await cur.fetchall()]

    # ---------- leads & events ----------
    async def add_lead(self, **f: Any) -> int:
        cur = await self.db.execute(
            """INSERT INTO leads(user_id,name,username,phone,event_date,guests,tier,estimate_uzs,created_at)
               VALUES(:user_id,:name,:username,:phone,:event_date,:guests,:tier,:estimate_uzs,:created_at)""",
            {**f, "created_at": _now().isoformat()},
        )
        await self.db.commit()
        return cur.lastrowid

    async def recent_leads(self, limit: int = 10) -> list[aiosqlite.Row]:
        async with self.db.execute("SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)) as cur:
            return list(await cur.fetchall())

    async def record_event(self, kind: str, user_id: int) -> None:
        await self.db.execute(
            "INSERT INTO events(kind,user_id,ts) VALUES(?,?,?)", (kind, user_id, _now().isoformat())
        )
        await self.db.commit()

    async def stats(self) -> dict[str, int]:
        day = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        today, week = day.isoformat(), (day - timedelta(days=6)).isoformat()
        out = {
            "users": await self._one("SELECT COUNT(*) FROM users"),
            "users_today": await self._one("SELECT COUNT(*) FROM users WHERE first_seen>=?", (today,)),
            "users_week": await self._one("SELECT COUNT(*) FROM users WHERE first_seen>=?", (week,)),
            "blocked": await self._one("SELECT COUNT(*) FROM users WHERE blocked=1"),
            "leads": await self._one("SELECT COUNT(*) FROM leads"),
            "leads_today": await self._one("SELECT COUNT(*) FROM leads WHERE created_at>=?", (today,)),
            "leads_week": await self._one("SELECT COUNT(*) FROM leads WHERE created_at>=?", (week,)),
            "admins": await self._one("SELECT COUNT(*) FROM admins"),
        }
        for kind in ("tour_viewed", "menu_downloaded", "calc_completed"):
            out[kind] = await self._one("SELECT COUNT(*) FROM events WHERE kind=?", (kind,))
        return out
