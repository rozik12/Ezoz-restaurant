"""SQLite storage: users and subscriptions, conversation history, daily usage and Stars payments."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    name       TEXT,
    mode       TEXT NOT NULL DEFAULT 'general',
    paid_until REAL NOT NULL DEFAULT 0,
    created    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role    TEXT NOT NULL,
    content TEXT NOT NULL,
    ts      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id);
CREATE TABLE IF NOT EXISTS usage (
    user_id INTEGER NOT NULL,
    day     TEXT NOT NULL,
    n       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
CREATE TABLE IF NOT EXISTS payments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    charge_id TEXT NOT NULL,
    stars     INTEGER NOT NULL,
    days      INTEGER NOT NULL,
    ts        REAL NOT NULL
);
"""


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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

    async def _scalar(self, sql: str, args: tuple = ()):
        async with self.db.execute(sql, args) as cur:
            row = await cur.fetchone()
            return row[0] if row and row[0] is not None else 0

    # ---------- users ----------
    async def touch_user(self, user_id: int, username: str | None, name: str) -> None:
        await self.db.execute(
            """INSERT INTO users(user_id, username, name, created) VALUES(?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, name=excluded.name""",
            (user_id, username, name, time.time()))
        await self.db.commit()

    async def get_mode(self, user_id: int) -> str:
        async with self.db.execute("SELECT mode FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row["mode"] if row else "general"

    async def set_mode(self, user_id: int, mode: str) -> None:
        await self.db.execute("UPDATE users SET mode=? WHERE user_id=?", (mode, user_id))
        await self.db.commit()

    async def paid_until(self, user_id: int) -> float:
        return await self._scalar("SELECT paid_until FROM users WHERE user_id=?", (user_id,))

    async def is_paid(self, user_id: int) -> bool:
        return await self.paid_until(user_id) > time.time()

    async def extend_subscription(self, user_id: int, days: int) -> float:
        """Adds days on top of the remaining time, so paying early never loses what is left."""
        base = max(await self.paid_until(user_id), time.time())
        until = base + days * 86400
        await self.db.execute(                      # also works for a user who has not opened the bot yet
            """INSERT INTO users(user_id, created, paid_until) VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET paid_until=excluded.paid_until""", (user_id, time.time(), until))
        await self.db.commit()
        return until

    async def revoke_subscription(self, user_id: int) -> None:
        await self.db.execute("UPDATE users SET paid_until=0 WHERE user_id=?", (user_id,))
        await self.db.commit()

    # ---------- history ----------
    async def add_message(self, user_id: int, role: str, content: str) -> None:
        await self.db.execute("INSERT INTO messages(user_id, role, content, ts) VALUES(?,?,?,?)",
                              (user_id, role, content, time.time()))
        await self.db.commit()

    async def history(self, user_id: int, limit: int = 24) -> list[dict]:
        async with self.db.execute(
                "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)) as cur:
            rows = await cur.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    async def clear_history(self, user_id: int) -> None:
        await self.db.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        await self.db.commit()

    async def drop_last_user_message(self, user_id: int) -> None:
        """Used when a request fails, so the unanswered question does not stay in the context."""
        await self.db.execute(
            "DELETE FROM messages WHERE id=(SELECT MAX(id) FROM messages WHERE user_id=? AND role='user')", (user_id,))
        await self.db.commit()

    # ---------- usage ----------
    async def used_today(self, user_id: int) -> int:
        return await self._scalar("SELECT n FROM usage WHERE user_id=? AND day=?", (user_id, today()))

    async def count_use(self, user_id: int) -> None:
        await self.db.execute(
            "INSERT INTO usage(user_id, day, n) VALUES(?,?,1) ON CONFLICT(user_id, day) DO UPDATE SET n=n+1",
            (user_id, today()))
        await self.db.commit()

    # ---------- payments ----------
    async def add_payment(self, user_id: int, charge_id: str, stars: int, days: int) -> None:
        await self.db.execute("INSERT INTO payments(user_id, charge_id, stars, days, ts) VALUES(?,?,?,?,?)",
                              (user_id, charge_id, stars, days, time.time()))
        await self.db.commit()

    async def payment_exists(self, charge_id: str) -> bool:
        return bool(await self._scalar("SELECT 1 FROM payments WHERE charge_id=?", (charge_id,)))

    # ---------- stats ----------
    async def stats(self) -> dict[str, int]:
        now = time.time()
        return {
            "users": await self._scalar("SELECT COUNT(*) FROM users"),
            "paid": await self._scalar("SELECT COUNT(*) FROM users WHERE paid_until>?", (now,)),
            "requests_today": await self._scalar("SELECT COALESCE(SUM(n),0) FROM usage WHERE day=?", (today(),)),
            "active_today": await self._scalar("SELECT COUNT(*) FROM usage WHERE day=?", (today(),)),
            "payments": await self._scalar("SELECT COUNT(*) FROM payments"),
            "stars": await self._scalar("SELECT COALESCE(SUM(stars),0) FROM payments"),
        }
