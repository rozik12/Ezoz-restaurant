"""Keyboards and the button labels the handlers match on (every language at once)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from i18n import LANGS, labels, t

# button label (any language) -> mode / action
MODE_BUTTONS = {**{x: "tech" for x in labels("btn_tech")},
                **{x: "editor" for x in labels("btn_edit")}}
BTN_WRITE = labels("btn_write")
BTN_WORKS = labels("btn_works")
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
    "btn_slides", "btn_detect", "btn_convert", "btn_works")))

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
                  [KeyboardButton(text=t(lang, "btn_detect")), KeyboardButton(text=t(lang, "btn_works"))],
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


def topup_markup(lang: str, settings, missing: int | None = None) -> InlineKeyboardMarkup:
    """Top-up choices: the missing amount first (after a refused action), presets, any amount, then the other ways to pay."""
    btn = InlineKeyboardButton
    rows: list[list[InlineKeyboardButton]] = []
    if missing and 1 <= missing <= settings.topup_max:
        rows.append([btn(text=t(lang, "top_missing", n=missing), callback_data=f"top:{missing}")])
    presets = [n for n in settings.topup_presets if n <= settings.topup_max]
    rows += [[btn(text=f"⭐ {n}", callback_data=f"top:{n}") for n in presets[i:i + 3]] for i in range(0, len(presets), 3)]
    rows.append([btn(text=t(lang, "top_other"), callback_data="top:custom")])
    if settings.provider_ready:
        rows.append([btn(text=t(lang, "btn_provider"), callback_data="topm:payp")])
    if settings.card_ready:
        rows.append([btn(text=t(lang, "btn_card_pay"), callback_data="topm:card")])
    rows.append([btn(text=t(lang, "stars_btn"), callback_data="stars:how"), btn(text=t(lang, "btn_refund"), callback_data="rf:info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def theme_choice(lang: str) -> InlineKeyboardMarkup:
    from slides import THEME_ORDER
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, f"theme_{n}"), callback_data=f"st:{n}") for n in THEME_ORDER]])


def card_paid_button(lang: str, stars: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "card_paid_btn"), callback_data=f"card:paid:{stars}")]])
