"""OmniStudent bot entry point.  Run:  python main.py"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import admin
import wallet
import support
import tools
from access import Access
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
                                   BotCommand(command="guide", description="Инструкция / Yo'riqnoma / Guide"),
                                   BotCommand(command="new", description="Новый диалог"),
                                   BotCommand(command="wallet", description="Кошелёк / Hamyon / Wallet"),
                                   BotCommand(command="stars", description="Как купить Stars / Stars sotib olish / Buy Stars"),
                                   BotCommand(command="slides", description="Слайды / Slaydlar / Slides"),
                                   BotCommand(command="convert", description="Конвертер / Konvertor / Converter"),
                                   BotCommand(command="detect", description="Проверка на ИИ / AI check"),
                                   BotCommand(command="support", description="Поддержка / Yordam / Support"),
                                   BotCommand(command="lang", description="Язык / Til / Language"),
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
    access = Access(db, settings)
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)
    dp.include_router(support.router)          # order matters: support dialog and admin tools come before the catch-all handlers
    dp.include_router(admin.router)
    dp.include_router(tools.router)
    dp.include_router(wallet.router)
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
