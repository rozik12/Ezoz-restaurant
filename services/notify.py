"""Delivery of lead notifications to the administrators' working chat."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from config import OWNER_ID, settings
from db import Database

log = logging.getLogger(__name__)


async def notify_staff(bot: Bot, db: Database, text: str) -> None:
    """Send to ADMIN_CHAT_ID when set. If it is unset or delivery fails, fall back to every staff member
    privately so that a lead is never lost."""
    if settings.admin_chat_id:
        try:
            await bot.send_message(settings.admin_chat_id, text)
            return
        except TelegramAPIError:
            log.exception("Could not post to ADMIN_CHAT_ID, falling back to private messages")
    for uid in {OWNER_ID, *await db.admin_ids()}:
        try:
            await bot.send_message(uid, text)
        except TelegramAPIError:
            log.warning("Could not notify %s", uid)
