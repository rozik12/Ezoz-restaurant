"""E'zoz Tashkent bot entry point.  Run:  python main.py"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import settings
from db import Database
from i18n import norm
from bot_profile import setup_bot_profile
from web import start_web
from handlers import admin, common, guest, owner


class UserTrackerMiddleware(BaseMiddleware):
    """Records every private-chat user so the owner can see stats and broadcast to them."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        chat = event.chat if isinstance(event, Message) else (event.message.chat if isinstance(event, CallbackQuery) and event.message else None)
        lang = None
        if user and not user.is_bot and chat is not None and chat.type == ChatType.PRIVATE:
            await self.db.upsert_user(user.id, user.username, user.full_name)
            lang = await self.db.get_lang(user.id)
        data["lang"] = norm(lang)              # handlers receive `lang` by name
        data["lang_set"] = lang is not None    # False until the user has picked a language
        return await handler(event, data)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = Database(settings.db_path)
    await db.connect()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # MemoryStorage loses FSM state on restart. For production use RedisStorage (aiogram.fsm.storage.redis).
    dp = Dispatcher(storage=MemoryStorage(), db=db)           # `db` is injected into handlers and filters by name

    tracker = UserTrackerMiddleware(db)
    dp.message.outer_middleware(tracker)
    dp.callback_query.outer_middleware(tracker)

    # Order matters: commands and /start first, role routers next, the catch-all last.
    dp.include_routers(common.router, owner.router, admin.router, guest.router, common.fallback)

    runner = await start_web(bot, db)           # website booking API (only when PORT is set)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await setup_bot_profile(bot)
        logging.info("Bot started as @%s", (await bot.me()).username)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if runner:
            await runner.cleanup()
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
