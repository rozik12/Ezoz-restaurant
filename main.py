"""OmniStudent bot entry point.  Run:  python main.py"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import Settings
from db import Database
from handlers import router
from llm import Assistant

DESCRIPTION = ("Академический ИИ-помощник для студентов: курсовые, рефераты и эссе, решение задач и код, "
               "рерайт и перевод научных текстов, шпаргалки и «Вредный преподаватель» перед защитой.")
SHORT = "ИИ-помощник студента: работы, задачи, шпаргалки"


async def setup_profile(bot: Bot) -> None:
    """Best effort: a failure here must never stop the bot from starting."""
    try:
        await bot.set_my_description(DESCRIPTION)
        await bot.set_my_short_description(SHORT)
        await bot.set_my_commands([BotCommand(command="start", description="Главное меню"),
                                   BotCommand(command="new", description="Новый диалог"),
                                   BotCommand(command="subscribe", description="Подписка за Stars"),
                                   BotCommand(command="help", description="Помощь"),
                                   BotCommand(command="paysupport", description="Вопросы по оплате")])
    except Exception:
        logging.getLogger(__name__).exception("Could not update the bot profile")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings.load()
    db = Database(settings.db_path)
    await db.connect()
    ai = Assistant(settings, db)
    if not ai.ready:
        logging.warning("No AI key (GEMINI_API_KEY, DEEPSEEK_API_KEY or ANTHROPIC_API_KEY) is set: the bot starts but cannot answer questions yet")

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage(), db=db, ai=ai, settings=settings)     # injected into handlers by name
    dp.include_router(router)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await setup_profile(bot)
        logging.info("Bot started as @%s", (await bot.me()).username)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
