"""Middleware: registers every sender, promotes configured admins, blocks banned users, injects language and role."""
from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import Settings
from db import Database
from i18n import DEFAULT_LANG, t


USER_MODE: set[int] = set()          # administrators who switched to the ordinary user's view (kept in memory only)


class Access(BaseMiddleware):
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db, self.s = db, settings

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)
        db, s = self.db, self.s
        new = await db.touch_user(user.id, user.username, user.full_name)
        if new and s.welcome_bonus > 0:
            await db.credit(user.id, s.welcome_bonus, "bonus", "welcome")
        owner = user.id in s.admin_ids
        by_name = (user.username or "").lower() in s.admin_usernames        # promoted on first contact, then kept by id
        is_admin = owner or await db.is_admin(user.id)
        if (owner or by_name) and not is_admin:
            await db.add_admin(user.id, user.username)
            is_admin = True
        lang = await db.get_lang(user.id) or DEFAULT_LANG
        if not is_admin and await db.is_banned(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer(t(lang, "banned"), show_alert=True)
            elif isinstance(event, Message):
                await event.answer(t(lang, "banned"))
            return None
        data.update(lang=lang, is_admin=is_admin, is_owner=owner, admin_view=is_admin and user.id not in USER_MODE)
        return await handler(event, data)
