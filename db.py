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
CREATE TABLE IF NOT EXISTS tool_usage (
    user_id INTEGER NOT NULL,
    tool    TEXT NOT NULL,
    day     TEXT NOT NULL,
    n       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, tool, day)
);
CREATE TABLE IF NOT EXISTS card_payments (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status  TEXT NOT NULL DEFAULT 'pending',
    created REAL NOT NULL,
    decided REAL
);
CREATE TABLE IF NOT EXISTS admins (
    user_id  INTEGER PRIMARY KEY,
    username TEXT,
    added    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    text     TEXT NOT NULL,
    status   TEXT NOT NULL DEFAULT 'open',
    created  REAL NOT NULL,
    answered REAL
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status, id);
CREATE TABLE IF NOT EXISTS ticket_msgs (
    chat_id   INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    ticket_id INTEGER NOT NULL,
    PRIMARY KEY (chat_id, message_id)
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
        async with self._db.execute("PRAGMA table_info(users)") as cur:
            cols = {r["name"] for r in await cur.fetchall()}
        for col, ddl in (("lang", "TEXT"), ("banned", "INTEGER NOT NULL DEFAULT 0"), ("last_seen", "REAL NOT NULL DEFAULT 0")):
            if col not in cols:                               # upgrade a database created by an older version
                await self._db.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
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
            """INSERT INTO users(user_id, username, name, created, last_seen) VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, name=excluded.name, last_seen=excluded.last_seen""",
            (user_id, username, name, time.time(), time.time()))
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

    async def tool_used_today(self, user_id: int, tool: str) -> int:
        return await self._scalar("SELECT n FROM tool_usage WHERE user_id=? AND tool=? AND day=?", (user_id, tool, today()))

    async def count_tool(self, user_id: int, tool: str) -> None:
        await self.db.execute(
            "INSERT INTO tool_usage(user_id, tool, day, n) VALUES(?,?,?,1) ON CONFLICT(user_id, tool, day) DO UPDATE SET n=n+1",
            (user_id, tool, today()))
        await self.db.commit()

    async def tool_totals_today(self) -> dict[str, int]:
        async with self.db.execute("SELECT tool, SUM(n) AS n FROM tool_usage WHERE day=? GROUP BY tool", (today(),)) as cur:
            return {r["tool"]: r["n"] for r in await cur.fetchall()}

    # ---------- payments ----------
    async def add_payment(self, user_id: int, charge_id: str, stars: int, days: int) -> None:
        await self.db.execute("INSERT INTO payments(user_id, charge_id, stars, days, ts) VALUES(?,?,?,?,?)",
                              (user_id, charge_id, stars, days, time.time()))
        await self.db.commit()

    async def payment_exists(self, charge_id: str) -> bool:
        return bool(await self._scalar("SELECT 1 FROM payments WHERE charge_id=?", (charge_id,)))

    # ---------- language, bans ----------
    async def get_lang(self, user_id: int) -> str | None:
        async with self.db.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row["lang"] if row else None

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self.db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
        await self.db.commit()

    async def is_banned(self, user_id: int) -> bool:
        return bool(await self._scalar("SELECT banned FROM users WHERE user_id=?", (user_id,)))

    async def set_banned(self, user_id: int, banned: bool) -> None:
        await self.db.execute("UPDATE users SET banned=? WHERE user_id=?", (int(banned), user_id))
        await self.db.commit()

    # ---------- admins ----------
    async def is_admin(self, user_id: int) -> bool:
        return bool(await self._scalar("SELECT 1 FROM admins WHERE user_id=?", (user_id,)))

    async def add_admin(self, user_id: int, username: str | None) -> None:
        await self.db.execute(
            "INSERT INTO admins(user_id, username, added) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username",
            (user_id, username, time.time()))
        await self.db.commit()

    async def remove_admin(self, user_id: int) -> None:
        await self.db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await self.db.commit()

    async def admin_rows(self) -> list[dict]:
        async with self.db.execute("SELECT user_id, username FROM admins ORDER BY added") as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ---------- user lookup ----------
    async def find_user(self, query: str) -> dict | None:
        q = query.strip().lstrip("@")
        if q.isdigit():
            sql, arg = "SELECT * FROM users WHERE user_id=?", int(q)
        else:
            sql, arg = "SELECT * FROM users WHERE lower(username)=lower(?)", q
        async with self.db.execute(sql, (arg,)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def recent_users(self, limit: int = 15, offset: int = 0) -> list[dict]:
        async with self.db.execute("SELECT * FROM users ORDER BY created DESC LIMIT ? OFFSET ?", (limit, offset)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def broadcast_ids(self) -> list[int]:
        async with self.db.execute("SELECT user_id FROM users WHERE banned=0") as cur:
            return [r["user_id"] for r in await cur.fetchall()]

    async def user_requests(self, user_id: int) -> int:
        return await self._scalar("SELECT COALESCE(SUM(n),0) FROM usage WHERE user_id=?", (user_id,))

    # ---------- support tickets ----------
    async def create_ticket(self, user_id: int, text: str) -> int:
        cur = await self.db.execute("INSERT INTO tickets(user_id, text, created) VALUES(?,?,?)", (user_id, text, time.time()))
        await self.db.commit()
        return cur.lastrowid

    async def get_ticket(self, ticket_id: int) -> dict | None:
        async with self.db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def open_tickets(self, limit: int = 10) -> list[dict]:
        async with self.db.execute("SELECT * FROM tickets WHERE status='open' ORDER BY id LIMIT ?", (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def open_tickets_of(self, user_id: int) -> int:
        return await self._scalar("SELECT COUNT(*) FROM tickets WHERE user_id=? AND status='open'", (user_id,))

    async def set_ticket_status(self, ticket_id: int, status: str) -> None:
        await self.db.execute("UPDATE tickets SET status=?, answered=? WHERE id=?", (status, time.time(), ticket_id))
        await self.db.commit()

    async def link_ticket_msg(self, chat_id: int, message_id: int, ticket_id: int) -> None:
        await self.db.execute("INSERT OR REPLACE INTO ticket_msgs(chat_id, message_id, ticket_id) VALUES(?,?,?)",
                              (chat_id, message_id, ticket_id))
        await self.db.commit()

    async def ticket_by_msg(self, chat_id: int, message_id: int) -> int | None:
        v = await self._scalar("SELECT ticket_id FROM ticket_msgs WHERE chat_id=? AND message_id=?", (chat_id, message_id))
        return v or None

    # ---------- payments by card transfer ----------
    async def create_card_payment(self, user_id: int) -> int:
        cur = await self.db.execute("INSERT INTO card_payments(user_id, created) VALUES(?,?)", (user_id, time.time()))
        await self.db.commit()
        return cur.lastrowid

    async def get_card_payment(self, pid: int) -> dict | None:
        async with self.db.execute("SELECT * FROM card_payments WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def pending_card_payments_of(self, user_id: int) -> int:
        return await self._scalar("SELECT COUNT(*) FROM card_payments WHERE user_id=? AND status='pending'", (user_id,))

    async def decide_card_payment(self, pid: int, status: str) -> bool:
        """Moves a pending request to approved/rejected; False when it was already decided (two admins, double tap)."""
        cur = await self.db.execute("UPDATE card_payments SET status=?, decided=? WHERE id=? AND status='pending'", (status, time.time(), pid))
        await self.db.commit()
        return cur.rowcount == 1

    # ---------- stats ----------
    async def stats(self) -> dict:
        now = time.time()
        day = now - now % 86400                                  # start of the current UTC day
        d = {
            "users": await self._scalar("SELECT COUNT(*) FROM users"),
            "new_today": await self._scalar("SELECT COUNT(*) FROM users WHERE created>=?", (day,)),
            "new_7d": await self._scalar("SELECT COUNT(*) FROM users WHERE created>=?", (now - 7 * 86400,)),
            "paid": await self._scalar("SELECT COUNT(*) FROM users WHERE paid_until>?", (now,)),
            "banned": await self._scalar("SELECT COUNT(*) FROM users WHERE banned=1"),
            "requests_today": await self._scalar("SELECT COALESCE(SUM(n),0) FROM usage WHERE day=?", (today(),)),
            "requests_total": await self._scalar("SELECT COALESCE(SUM(n),0) FROM usage"),
            "active_today": await self._scalar("SELECT COUNT(*) FROM usage WHERE day=?", (today(),)),
            "active_7d": await self._scalar("SELECT COUNT(*) FROM users WHERE last_seen>=?", (now - 7 * 86400,)),
            "payments": await self._scalar("SELECT COUNT(*) FROM payments"),
            "stars": await self._scalar("SELECT COALESCE(SUM(stars),0) FROM payments"),
            "card_pending": await self._scalar("SELECT COUNT(*) FROM card_payments WHERE status='pending'"),
            "card_paid": await self._scalar("SELECT COUNT(*) FROM card_payments WHERE status='approved'"),
            "tickets_open": await self._scalar("SELECT COUNT(*) FROM tickets WHERE status='open'"),
            "tickets_total": await self._scalar("SELECT COUNT(*) FROM tickets"),
        }
        d["tools_today"] = await self.tool_totals_today()
        async with self.db.execute("SELECT COALESCE(lang,'-') AS l, COUNT(*) AS n FROM users GROUP BY l") as cur:
            d["langs"] = {r["l"]: r["n"] for r in await cur.fetchall()}
        return d
