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
BTN_SLIDES = labels("btn_slides")
BTN_DETECT = labels("btn_detect")
BTN_CONVERT = labels("btn_convert")
MENU_LABELS = set().union(*(labels(k) for k in (
    "btn_write", "btn_tech", "btn_edit", "btn_cheat", "btn_sub", "btn_new", "btn_support", "btn_lang",
    "btn_slides", "btn_detect", "btn_convert")))

MODE_TITLES = {
    "general": "Свободный режим", "writer": "Академический писатель", "tech": "Технический эксперт",
    "editor": "Редактор и переводчик", "cheat": "Шпаргалка", "exam": "Вредный преподаватель",
}


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_write")), KeyboardButton(text=t(lang, "btn_tech"))],
                  [KeyboardButton(text=t(lang, "btn_edit")), KeyboardButton(text=t(lang, "btn_cheat"))],
                  [KeyboardButton(text=t(lang, "btn_sub")), KeyboardButton(text=t(lang, "btn_new"))],
                  [KeyboardButton(text=t(lang, "btn_slides")), KeyboardButton(text=t(lang, "btn_convert"))],
                  [KeyboardButton(text=t(lang, "btn_detect"))],
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


def convert_targets(targets: tuple[str, ...]) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text=f"→ {x.upper()}", callback_data=f"cv:{x}") for x in targets]
    return InlineKeyboardMarkup(inline_keyboard=[row[i:i + 3] for i in range(0, len(row), 3)])


def theme_buttons(lang: str, current: str) -> InlineKeyboardMarkup:
    from slides import THEME_ORDER
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, f"theme_{n}"), callback_data=f"th:{n}")
                                                  for n in THEME_ORDER if n != current]])


def subscribe_button(label: str, lang: str = "ru", *, card: bool = False, provider: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data="pay")]]
    if provider:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_provider"), callback_data="payp")])
    if card:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_card_pay"), callback_data="card:info")])
    rows.append([InlineKeyboardButton(text=t(lang, "stars_btn"), callback_data="stars:how")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_paid_button(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "card_paid_btn"), callback_data="card:paid")]])
