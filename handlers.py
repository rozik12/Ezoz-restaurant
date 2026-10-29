"""User-facing handlers: language, menu and modes, chat with the assistant, files, Stars subscription."""
from __future__ import annotations

import asyncio
import html
import logging
import time
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.chat_action import ChatActionSender

import keyboards as kb
from config import Settings
from db import Database
from docs import MAX_FILE_BYTES, UnsupportedFile, extract_text
from fmt import md_to_html, split_markdown
from i18n import DEFAULT_LANG, LANGS, t
from llm import Assistant, AssistantError

log = logging.getLogger(__name__)

router = Router(name="main")
router.message.filter(F.chat.type == ChatType.PRIVATE)

MAX_INPUT_CHARS = 12_000
_locks: dict[int, asyncio.Lock] = {}          # one running request per user, so history stays in order

def _lock(user_id: int) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _fmt_until(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d.%m.%Y")


async def send_answer(message: Message, text: str) -> None:
    """Sends a long Markdown answer as several HTML messages; falls back to plain text if Telegram rejects the markup."""
    for chunk in split_markdown(text):
        try:
            await message.answer(md_to_html(chunk), parse_mode="HTML", disable_web_page_preview=True)
        except TelegramBadRequest:
            await message.answer(chunk, parse_mode=None, disable_web_page_preview=True)


# =========================== start, language, help, menu ===========================
@router.message(CommandStart())
async def start(message: Message, db: Database, lang: str) -> None:
    u = message.from_user
    await db.touch_user(u.id, u.username, u.full_name)
    if await db.get_lang(u.id) is None:                       # first visit: ask for the language
        await message.answer(t(DEFAULT_LANG, "choose_lang"), reply_markup=kb.lang_choice())
        return
    await message.answer(t(lang, "welcome"), reply_markup=kb.main_menu(lang))


@router.message(Command("lang"))
@router.message(F.text.in_(kb.BTN_LANG))
async def lang_cmd(message: Message) -> None:
    await message.answer(t(DEFAULT_LANG, "choose_lang"), reply_markup=kb.lang_choice())


@router.callback_query(F.data.startswith("lang:"))
async def lang_pick(call: CallbackQuery, db: Database) -> None:
    code = call.data.split(":")[1]
    if code not in LANGS:
        await call.answer()
        return
    await db.touch_user(call.from_user.id, call.from_user.username, call.from_user.full_name)
    await db.set_lang(call.from_user.id, code)
    await call.answer(t(code, "lang_set"))
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    await call.message.answer(t(code, "welcome"), reply_markup=kb.main_menu(code))


@router.message(Command("help"))
async def help_cmd(message: Message, lang: str) -> None:
    await message.answer(t(lang, "help"))


@router.message(Command("id"))
async def my_id(message: Message, lang: str) -> None:
    await message.answer(t(lang, "your_id", id=message.from_user.id))


@router.message(Command("new"))
@router.message(F.text.in_(kb.BTN_NEW))
async def new_dialog(message: Message, db: Database, lang: str) -> None:
    await db.clear_history(message.from_user.id)
    await message.answer(t(lang, "new_done"), reply_markup=kb.main_menu(lang))


@router.message(F.text.in_(kb.MODE_BUTTONS))
async def pick_mode(message: Message, db: Database, lang: str) -> None:
    mode = kb.MODE_BUTTONS[message.text]
    await db.touch_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await db.set_mode(message.from_user.id, mode)
    await message.answer(t(lang, f"intro_{mode}"))


@router.message(F.text.in_(kb.BTN_CHEAT))
async def cheat_menu(message: Message, lang: str) -> None:
    await message.answer(t(lang, "cheat_ask"), reply_markup=kb.cheat_choice(lang))


@router.callback_query(F.data.startswith("mode:"))
async def pick_cheat_mode(call: CallbackQuery, db: Database, lang: str) -> None:
    mode = call.data.split(":")[1]
    if mode not in ("cheat", "exam"):
        await call.answer()
        return
    await db.touch_user(call.from_user.id, call.from_user.username, call.from_user.full_name)
    await db.set_mode(call.from_user.id, mode)
    await call.answer()
    await call.message.answer(t(lang, f"intro_{mode}"))


# =========================== subscription (Telegram Stars) ===========================
async def status_text(db: Database, s: Settings, user_id: int, lang: str) -> str:
    until = await db.paid_until(user_id)
    if until > time.time():
        return t(lang, "sub_active", until=_fmt_until(until), paid=s.paid_daily)
    left = max(0, s.free_daily - await db.used_today(user_id))
    return t(lang, "sub_free", left=left, free=s.free_daily, days=s.sub_days, price=s.price_stars, paid=s.paid_daily)


@router.message(Command("subscribe"))
@router.message(F.text.in_(kb.BTN_SUB))
async def subscribe(message: Message, db: Database, settings: Settings, lang: str) -> None:
    await message.answer(await status_text(db, settings, message.from_user.id, lang),
                         reply_markup=kb.subscribe_button(t(lang, "pay_btn", price=settings.price_stars), lang))


async def send_invoice(target: Message, settings: Settings, user_id: int, lang: str) -> None:
    await target.answer_invoice(
        title=t(lang, "invoice_title", days=settings.sub_days),
        description=t(lang, "invoice_desc", paid=settings.paid_daily),
        payload=f"sub:{user_id}", currency="XTR",
        prices=[LabeledPrice(label=t(lang, "invoice_label", days=settings.sub_days), amount=settings.price_stars)],
        provider_token="")


@router.message(Command("stars"))
async def stars_howto(message: Message, settings: Settings, lang: str) -> None:
    await message.answer(t(lang, "stars_howto", price=settings.price_stars, days=settings.sub_days))


@router.callback_query(F.data == "stars:how")
async def stars_howto_btn(call: CallbackQuery, settings: Settings, lang: str) -> None:
    await call.answer()
    await call.message.answer(t(lang, "stars_howto", price=settings.price_stars, days=settings.sub_days),
                              reply_markup=kb.subscribe_button(t(lang, "pay_btn", price=settings.price_stars), lang))


@router.callback_query(F.data == "pay")
async def pay_button(call: CallbackQuery, settings: Settings, lang: str) -> None:
    await call.answer()
    await send_invoice(call.message, settings, call.from_user.id, lang)


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, settings: Settings, db: Database) -> None:
    ok = query.currency == "XTR" and query.total_amount == settings.price_stars and query.invoice_payload == f"sub:{query.from_user.id}"
    lang = await db.get_lang(query.from_user.id) or DEFAULT_LANG
    await query.answer(ok=ok, error_message=None if ok else t(lang, "bad_invoice"))


@router.message(F.successful_payment)
async def paid(message: Message, db: Database, settings: Settings, lang: str) -> None:
    p = message.successful_payment
    if await db.payment_exists(p.telegram_payment_charge_id):            # Telegram may redeliver an update
        return
    await db.touch_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await db.add_payment(message.from_user.id, p.telegram_payment_charge_id, p.total_amount, settings.sub_days)
    until = await db.extend_subscription(message.from_user.id, settings.sub_days)
    log.info("Subscription paid by %s, %s Stars", message.from_user.id, p.total_amount)
    await message.answer(t(lang, "paid_ok", until=_fmt_until(until)), reply_markup=kb.main_menu(lang))


@router.message(Command("paysupport"))
async def pay_support(message: Message, lang: str) -> None:
    await message.answer(t(lang, "paysupport"))


# =========================== the assistant ===========================
async def run_assistant(message: Message, db: Database, ai: Assistant, settings: Settings, text: str, lang: str,
                        stored: str | None = None) -> None:
    uid = message.from_user.id
    await db.touch_user(uid, message.from_user.username, message.from_user.full_name)
    paid = await db.is_paid(uid)
    limit = settings.paid_daily if paid else settings.free_daily
    if await db.used_today(uid) >= limit:
        if paid:
            await message.answer(t(lang, "limit_paid", n=limit))
        else:
            await message.answer(t(lang, "limit_free", n=limit, price=settings.price_stars, paid=settings.paid_daily),
                                 reply_markup=kb.subscribe_button(t(lang, "pay_btn_sub", price=settings.price_stars), lang))
        return
    lock = _lock(uid)
    if lock.locked():
        await message.answer(t(lang, "busy"))
        return
    async with lock:
        mode = await db.get_mode(uid)
        try:
            async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
                answer, truncated = await ai.ask(uid, text, mode=mode, paid=paid, lang=lang, stored=stored)
        except AssistantError as e:
            await message.answer(f"⚠️ {t(lang, 'err_' + e.key)}")
            return
        except Exception:
            log.exception("Unexpected error while answering")
            await message.answer(t(lang, "generic_error"))
            return
        await db.count_use(uid)
        if truncated:
            answer += t(lang, "truncated", upsell="" if paid else t(lang, "truncated_upsell"))
        await send_answer(message, answer)
        if not paid:
            left = max(0, limit - await db.used_today(uid))
            if left == 0:
                await message.answer(t(lang, "last_free"),
                                     reply_markup=kb.subscribe_button(t(lang, "pay_btn_sub", price=settings.price_stars), lang))


@router.message(F.document)
async def on_document(message: Message, bot: Bot, db: Database, ai: Assistant, settings: Settings, lang: str) -> None:
    doc = message.document
    if doc.file_size and doc.file_size > MAX_FILE_BYTES:
        await message.answer(t(lang, "file_big"))
        return
    name = doc.file_name or "file"
    buf = await bot.download(doc)
    try:
        text, cut = extract_text(name, buf.read())
    except UnsupportedFile:
        await message.answer(t(lang, "file_bad"))
        return
    mode = await db.get_mode(message.from_user.id)
    default = t(lang, f"file_task_{mode}") if mode in ("cheat", "editor", "exam") else t(lang, "file_task_default")
    task = (message.caption or "").strip() or default
    note = t(lang, "file_note") if cut else ""
    full = f"{task}\n\n[File: {name}]{note}\n{text}"
    stored = f"{task}\n\n[File: {name}, {len(text)} chars]"
    await run_assistant(message, db, ai, settings, full[:MAX_INPUT_CHARS + 30_000], lang, stored=stored)


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, db: Database, ai: Assistant, settings: Settings, lang: str) -> None:
    if len(message.text) > MAX_INPUT_CHARS:
        await message.answer(t(lang, "too_long", n=MAX_INPUT_CHARS))
        return
    await run_assistant(message, db, ai, settings, message.text, lang)


@router.message()
async def other(message: Message, lang: str) -> None:
    await message.answer(t(lang, "other"), reply_markup=kb.main_menu(lang))
