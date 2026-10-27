"""Bot profile text and command menus in all three languages (the profile photo itself is set in @BotFather)."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand

log = logging.getLogger(__name__)

DESCRIPTION = {
    "en": "E'zoz Tashkent banquet hall and restaurant. See our halls, get the menu and prices, estimate your budget and book your date.",
    "ru": "Банкетный зал и ресторан E'zoz в Ташкенте. Смотрите залы, получайте меню и цены, считайте бюджет и бронируйте дату.",
    "uz": "Toshkentdagi E'zoz banket zali va restorani. Zallarni ko'ring, menyu va narxlarni oling, byudjetni hisoblang va sanani band qiling.",
}
SHORT = {
    "en": "Banquet hall in Tashkent: menu, prices, booking",
    "ru": "Банкетный зал в Ташкенте: меню, цены, бронь",
    "uz": "Toshkentdagi banket zali: menyu, narxlar, band qilish",
}
COMMANDS = {
    "en": [("start", "Main menu"), ("language", "Change language"), ("cancel", "Cancel the current action")],
    "ru": [("start", "Главное меню"), ("language", "Сменить язык"), ("cancel", "Отменить действие")],
    "uz": [("start", "Bosh menyu"), ("language", "Tilni o'zgartirish"), ("cancel", "Amalni bekor qilish")],
}


async def setup_bot_profile(bot: Bot) -> None:
    """Best effort: a failure here must never stop the bot from starting."""
    try:
        for code in ("en", "ru", "uz"):
            await bot.set_my_description(DESCRIPTION[code], language_code=code)
            await bot.set_my_short_description(SHORT[code], language_code=code)
            await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS[code]], language_code=code)
        await bot.set_my_description(DESCRIPTION["en"])
        await bot.set_my_short_description(SHORT["en"])
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS["en"]])
    except Exception:
        log.exception("Could not update the bot profile")
