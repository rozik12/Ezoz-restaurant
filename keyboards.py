"""All keyboards. Callback data is namespaced: menu:*, own:*, adm:*, post:*, g:*, calc:*."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import settings
from roles import Role
from services.pricing import (ADDON_LABEL, ADDON_UZS, HALL_LABEL, PER_GUEST_UZS, TIER_LABEL, fmt_uzs)
from services.social import PLATFORMS, VIDEO_ONLY

HOME = ("🏠 Main menu", "menu:home")


def _build(rows: list[list[tuple[str, str]]], *, urls: dict[str, str] | None = None) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows]
    for text, url in (urls or {}).items():
        kb.append([InlineKeyboardButton(text=text, url=url)])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def main_menu(role: Role) -> InlineKeyboardMarkup:
    if role is Role.OWNER:
        rows = [[("📊 Statistics", "own:stats"), ("👥 Administrators", "own:admins")],
                [("📣 Broadcast", "own:broadcast"), ("📝 New post", "adm:post")],
                [("📋 Recent leads", "adm:leads"), ("🏛 Guest menu", "menu:guest")]]
    elif role is Role.ADMIN:
        rows = [[("📝 New post", "adm:post"), ("📋 Recent leads", "adm:leads")],
                [("🏛 Guest menu", "menu:guest")]]
    else:
        return guest_menu()
    return _build(rows)


def guest_menu() -> InlineKeyboardMarkup:
    rows = [[("🏛 Our Halls (Virtual Tour)", "g:halls")],
            [("📄 Banquet Menu & Pricing (PDF)", "g:menu")],
            [("🧮 Cost Calculator", "g:calc")],
            [("📅 Book a Date", "g:book")]]
    return _build(rows)


def back_home() -> InlineKeyboardMarkup:
    return _build([[HOME]])


# ---------------- guest ----------------
def halls_kb() -> InlineKeyboardMarkup:
    rows = [[(label, f"g:hall:{key}")] for key, label in HALL_LABEL.items()] + [[HOME]]
    return _build(rows)


def hall_detail_kb() -> InlineKeyboardMarkup:
    rows = [[("📅 Book a Date", "g:book")], [("⬅️ All halls", "g:halls"), HOME]]
    return _build(rows, urls={"🎥 Open virtual tour": settings.website_url} if settings.website_url else None)


def guests_kb() -> InlineKeyboardMarkup:
    presets = [50, 100, 150, 200, 250, 300, 400, 500]
    rows = [[(str(n), f"calc:g:{n}") for n in presets[i:i + 4]] for i in range(0, len(presets), 4)]
    return _build(rows + [[HOME]])


def tier_kb() -> InlineKeyboardMarkup:
    rows = [[(f"{TIER_LABEL[k]} · {fmt_uzs(PER_GUEST_UZS[k])} / guest", f"calc:t:{k}")] for k in TIER_LABEL]
    return _build(rows + [[HOME]])


def addons_kb(selected: list[str]) -> InlineKeyboardMarkup:
    rows = [[(f"{'✅' if k in selected else '⬜️'} {ADDON_LABEL[k]} (+{fmt_uzs(ADDON_UZS[k])})", f"calc:a:{k}")]
            for k in ADDON_LABEL]
    rows.append([("Show my estimate ➡️", "calc:done")])
    return _build(rows)


def calc_result_kb() -> InlineKeyboardMarkup:
    return _build([[("📅 Book a Date", "g:book")], [("🔁 Recalculate", "g:calc"), ("📄 Menu PDF", "g:menu")], [HOME]])


def prefill_kb(label: str) -> InlineKeyboardMarkup:
    return _build([[(label, "g:book_prefill")], [HOME]])


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Share my phone number", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="or type +998 90 123 45 67",
    )


# ---------------- admin ----------------
def platforms_kb(selected: list[str], kind: str) -> InlineKeyboardMarkup:
    rows = []
    for key, label in PLATFORMS.items():
        locked = key in VIDEO_ONLY and kind != "video"
        mark = "🚫" if locked else "✅" if key in selected else "⬜️"
        rows.append([(f"{mark} {label}", f"post:t:{key}")])
    rows.append([("Review ➡️", "post:review")])
    rows.append([("❌ Cancel", "menu:home")])
    return _build(rows)


def confirm_post_kb() -> InlineKeyboardMarkup:
    return _build([[("🚀 Publish now", "post:go")], [("⬅️ Back", "post:back"), ("❌ Cancel", "menu:home")]])


# ---------------- owner ----------------
def admins_kb(admins: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [[(f"❌ Remove {label}", f"own:rm:{uid}")] for uid, label in admins]
    rows += [[("➕ Add administrator", "own:add")], [HOME]]
    return _build(rows)


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return _build([[("📣 Send to everyone", "own:bc_go")], [("❌ Cancel", "menu:home")]])
