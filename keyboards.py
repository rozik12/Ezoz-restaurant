"""All keyboards. Callback data is namespaced: menu:*, lang:*, own:*, adm:*, post:*, g:*, calc:*."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import settings
from i18n import LANG_BUTTON, LANGS, money, t
from roles import Role
from services.pricing import ADDON_UZS, GROUPS, HALL_FEE_UZS, HALL_UZS_KEYS, PER_GUEST_UZS
from services.social import PLATFORMS, VIDEO_ONLY

Row = list[tuple[str, str]]


def _build(rows: list[Row], *, urls: dict[str, str] | None = None) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text=txt, callback_data=data) for txt, data in row] for row in rows]
    for text, url in (urls or {}).items():
        kb.append([InlineKeyboardButton(text=text, url=url)])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def home_row(lang: str) -> Row:
    return [(t(lang, "b_home"), "menu:home")]


def language_kb() -> InlineKeyboardMarkup:
    return _build([[(LANG_BUTTON[code], f"lang:{code}") for code in LANGS]])


def main_menu(role: Role, lang: str) -> InlineKeyboardMarkup:
    if role is Role.OWNER:
        rows = [[(t(lang, "b_stats"), "own:stats"), (t(lang, "b_admins"), "own:admins")],
                [(t(lang, "b_broadcast"), "own:broadcast"), (t(lang, "b_post"), "adm:post")],
                [(t(lang, "b_leads"), "adm:leads"), (t(lang, "b_prices"), "adm:prices")],
                [(t(lang, "b_guest_menu"), "menu:guest"), (t(lang, "b_lang"), "menu:lang")]]
        return _build(rows)
    if role is Role.ADMIN:
        rows = [[(t(lang, "b_post"), "adm:post"), (t(lang, "b_leads"), "adm:leads")],
                [(t(lang, "b_prices"), "adm:prices"), (t(lang, "b_guest_menu"), "menu:guest")],
                [(t(lang, "b_lang"), "menu:lang")]]
        return _build(rows)
    return guest_menu(lang)


def guest_menu(lang: str) -> InlineKeyboardMarkup:
    rows = [[(t(lang, "b_halls"), "g:halls")],
            [(t(lang, "b_menu"), "g:menu")],
            [(t(lang, "b_calc"), "g:calc")],
            [(t(lang, "b_book"), "g:book")],
            [(t(lang, "b_contacts"), "g:contacts"), (t(lang, "b_lang"), "menu:lang")]]
    return _build(rows)


def back_home(lang: str) -> InlineKeyboardMarkup:
    return _build([home_row(lang)])


# ---------------- guest ----------------
def halls_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[(t(lang, f"hall_{k}"), f"g:hall:{k}")] for k in HALL_UZS_KEYS] + [home_row(lang)]
    return _build(rows)


def hall_detail_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[(t(lang, "b_book"), "g:book")], [(t(lang, "b_all_halls"), "g:halls"), home_row(lang)[0]]]
    urls = {t(lang, "b_tour"): settings.website_url} if settings.website_url else None
    return _build(rows, urls=urls)


def guests_kb(lang: str) -> InlineKeyboardMarkup:
    presets = [50, 100, 150, 200, 250, 300, 400, 500]
    rows = [[(str(n), f"calc:g:{n}") for n in presets[i:i + 4]] for i in range(0, len(presets), 4)]
    return _build(rows + [home_row(lang)])


def tier_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[(t(lang, "tier_row", name=t(lang, f"tier_{k}"), price=money(lang, PER_GUEST_UZS[k])), f"calc:t:{k}")]
            for k in PER_GUEST_UZS]
    return _build(rows + [home_row(lang)])


def addons_kb(lang: str, selected: list[str]) -> InlineKeyboardMarkup:
    rows = [[(f"{'✅' if k in selected else '⬜️'} {t(lang, 'addon_' + k)} (+{money(lang, ADDON_UZS[k])})", f"calc:a:{k}")]
            for k in ADDON_UZS]
    rows.append([(t(lang, "b_show_est"), "calc:done")])
    return _build(rows)


def calc_result_kb(lang: str) -> InlineKeyboardMarkup:
    return _build([[(t(lang, "b_book"), "g:book")],
                   [(t(lang, "b_recalc"), "g:calc"), (t(lang, "b_menu_short"), "g:menu")],
                   home_row(lang)])


def prefill_kb(lang: str, label: str) -> InlineKeyboardMarkup:
    return _build([[(label, "g:book_prefill")], home_row(lang)])


def contacts_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[(t(lang, "b_book"), "g:book")], home_row(lang)]
    urls = {}
    if settings.website_url:
        urls[t(lang, "b_open_site")] = settings.website_url
    for name, url in (("Instagram", settings.instagram), ("Telegram", settings.telegram_channel), ("Facebook", settings.facebook)):
        if url:
            urls[name] = url
    return _build(rows, urls=urls)


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "b_share_phone"), request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True, input_field_placeholder=t(lang, "phone_ph"),
    )


# ---------------- admin ----------------
def platforms_kb(lang: str, selected: list[str], kind: str) -> InlineKeyboardMarkup:
    rows = []
    for key, label in PLATFORMS.items():
        locked = key in VIDEO_ONLY and kind != "video"
        mark = "🚫" if locked else "✅" if key in selected else "⬜️"
        rows.append([(f"{mark} {label}", f"post:t:{key}")])
    rows.append([(t(lang, "b_review"), "post:review")])
    rows.append([(t(lang, "b_cancel"), "menu:home")])
    return _build(rows)


def confirm_post_kb(lang: str) -> InlineKeyboardMarkup:
    return _build([[(t(lang, "b_publish"), "post:go")], [(t(lang, "b_back"), "post:back"), (t(lang, "b_cancel"), "menu:home")]])


# ---------------- owner ----------------
def admins_kb(lang: str, admins: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [[(t(lang, "b_remove", who=label), f"own:rm:{uid}")] for uid, label in admins]
    rows += [[(t(lang, "b_add_admin"), "own:add")], home_row(lang)]
    return _build(rows)


def broadcast_confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return _build([[(t(lang, "b_send_all"), "own:bc_go")], [(t(lang, "b_cancel"), "menu:home")]])


# ---------------- prices (admin) ----------------
PRICE_ICON = {"pg": "🍽", "hf": "🏛", "ad": "✨"}


def price_label(lang: str, group: str, key: str) -> str:
    """Translated name of one price line, e.g. 'Premium' or 'Summer Terrace'."""
    return t(lang, {"pg": "tier_", "hf": "hall_", "ad": "addon_"}[group] + key)


def prices_kb(lang: str) -> InlineKeyboardMarkup:
    rows: list[Row] = []
    for group in ("pg", "hf", "ad"):
        order = HALL_UZS_KEYS if group == "hf" else tuple(GROUPS[group])
        for key in order:
            rows.append([(f"{PRICE_ICON[group]} {price_label(lang, group, key)} · {money(lang, GROUPS[group][key])}", f"price:{group}:{key}")])
    return _build(rows + [home_row(lang)])


def price_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return _build([[(t(lang, "b_back"), "adm:prices")]])
