"""Keyboards and the button labels the handlers match on (every language at once)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from i18n import LANGS, labels, t

# button label (any language) -> mode / action
MODE_BUTTONS = {**{x: "writer" for x in labels("btn_write")},
                **{x: "tech" for x in labels("btn_tech")},
                **{x: "editor" for x in labels("btn_edit")}}
BTN_CHEAT = labels("btn_cheat")
BTN_SUB = labels("btn_sub")
BTN_NEW = labels("btn_new")
BTN_SUPPORT = labels("btn_support")
BTN_LANG = labels("btn_lang")

MODE_TITLES = {
    "general": "Свободный режим", "writer": "Академический писатель", "tech": "Технический эксперт",
    "editor": "Редактор и переводчик", "cheat": "Шпаргалка", "exam": "Вредный преподаватель",
}


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_write")), KeyboardButton(text=t(lang, "btn_tech"))],
                  [KeyboardButton(text=t(lang, "btn_edit")), KeyboardButton(text=t(lang, "btn_cheat"))],
                  [KeyboardButton(text=t(lang, "btn_sub")), KeyboardButton(text=t(lang, "btn_new"))],
                  [KeyboardButton(text=t(lang, "btn_support")), KeyboardButton(text=t(lang, "btn_lang"))]],
        resize_keyboard=True, input_field_placeholder=t(lang, "placeholder"))


def cancel_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t(lang, "cancel_btn"))]], resize_keyboard=True)


def lang_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
                                                 for code, name in LANGS.items()])


def cheat_choice(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cheat_btn"), callback_data="mode:cheat")],
        [InlineKeyboardButton(text=t(lang, "exam_btn"), callback_data="mode:exam")]])


def subscribe_button(label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="pay")]])
