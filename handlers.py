"""User-facing handlers: language, menu and modes, chat with the assistant, files, Stars subscription."""
from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

import keyboards as kb
from config import Settings
from db import Database
from docs import MAX_FILE_BYTES, UnsupportedFile, extract_text
from fmt import md_to_html, split_markdown
from i18n import DEFAULT_LANG, LANGS, t
from wallet import give_back, spend, spent_line
from llm import Assistant, AssistantError

log = logging.getLogger(__name__)

router = Router(name="main")
router.message.filter(F.chat.type == ChatType.PRIVATE)

MAX_INPUT_CHARS = 12_000
_locks: dict[int, asyncio.Lock] = {}          # one running request per user, so history stays in order

def _lock(user_id: int) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


async def send_answer(message: Message, text: str, footer: str = "") -> None:
    """Sends a long Markdown answer as several HTML messages; falls back to plain text if Telegram rejects the markup.
    `footer` (what the action cost) rides on the last message."""
    chunks = split_markdown(text)
    for i, chunk in enumerate(chunks):
        last = footer if i == len(chunks) - 1 else ""
        try:
            await message.answer(md_to_html(chunk) + (f"\n\n<i>{html.escape(footer)}</i>" if last else ""), parse_mode="HTML",
                                 disable_web_page_preview=True)
        except TelegramBadRequest:
            await message.answer(chunk + (f"\n\n{footer}" if last else ""), parse_mode=None, disable_web_page_preview=True)


# =========================== start, language, help, menu ===========================
@router.message(CommandStart())
async def start(message: Message, db: Database, settings: Settings, lang: str) -> None:
    u = message.from_user
    await db.touch_user(u.id, u.username, u.full_name)
    if await db.get_lang(u.id) is None:                       # first visit: ask for the language
        await message.answer(t(DEFAULT_LANG, "choose_lang"), reply_markup=kb.lang_choice())
        return
    await message.answer(welcome_text(settings, lang), reply_markup=kb.main_menu(lang))


@router.message(Command("lang"))
@router.message(F.text.in_(kb.BTN_LANG))
async def lang_cmd(message: Message) -> None:
    await message.answer(t(DEFAULT_LANG, "choose_lang"), reply_markup=kb.lang_choice())


@router.callback_query(F.data.startswith("lang:"))
async def lang_pick(call: CallbackQuery, db: Database, settings: Settings) -> None:
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
    await call.message.answer(welcome_text(settings, code), reply_markup=kb.main_menu(code))
    await call.message.answer(guide_text(settings, code), reply_markup=kb.main_menu(code))      # what the bot can do, right after the language is chosen


def welcome_text(settings: Settings, lang: str) -> str:
    n = settings.free_actions
    return t(lang, "welcome", pay_intro=t(lang, "intro_free_welcome", free=n) if n > 0 else t(lang, "intro_welcome"))


def guide_text(settings: Settings, lang: str) -> str:
    p, n = settings.prices, settings.free_actions
    return t(lang, "guide", pay_intro=t(lang, "intro_free_guide", free=n) if n > 0 else t(lang, "intro_guide"),
             chat=p["chat"], slides=p["slides"], detect=p["detect"], convert=p["convert"])


@router.message(Command("guide"))
async def guide_cmd(message: Message, settings: Settings, lang: str) -> None:
    await message.answer(guide_text(settings, lang))


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


# =========================== payment questions ===========================
@router.message(Command("paysupport"))
async def pay_support(message: Message, lang: str) -> None:
    await message.answer(t(lang, "paysupport"))


# =========================== the assistant ===========================
async def run_assistant(message: Message, db: Database, ai: Assistant, settings: Settings, text: str, lang: str,
                        stored: str | None = None) -> None:
    uid = message.from_user.id
    lock = _lock(uid)
    if lock.locked():
        await message.answer(t(lang, "busy"))
        return
    async with lock:
        kind = await spend(message, db, settings, uid, "chat", lang)
        if not kind:
            return
        mode = await db.get_mode(uid)
        try:
            async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
                answer, truncated = await ai.ask(uid, text, mode=mode, paid=True, lang=lang, stored=stored)
        except Exception as e:                                # the action did not happen, so the Stars go back
            await give_back(db, settings, uid, "chat", kind)
            if isinstance(e, AssistantError):
                await message.answer(f"⚠️ {t(lang, 'err_' + e.key)}\n{t(lang, 'refunded')}")
            else:
                log.exception("Unexpected error while answering")
                await message.answer(f"{t(lang, 'generic_error')}\n{t(lang, 'refunded')}")
            return
        await db.count_use(uid)
        if truncated:
            answer += t(lang, "truncated")
        await send_answer(message, answer, footer=await spent_line(db, settings, uid, "chat", lang, kind))


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
