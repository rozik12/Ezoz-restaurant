"""/start, language choice, branded main menu (with the logo), cancel, and the catch-all fallbacks."""
from __future__ import annotations

import logging
from datetime import date

from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ContentType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, ReplyKeyboardRemove

import keyboards as kb
from config import settings
from db import Database
from i18n import HDR, LANGS, fmt_date_short, t
from roles import Role, resolve_role

log = logging.getLogger(__name__)

router = Router(name="common")
router.message.filter(F.chat.type == ChatType.PRIVATE)

_logo_file_id: str | None = None      # Telegram caches the upload, so the file is sent only once per run


def _logo():
    """The logo as an InputFile or a cached file_id; None when the file is missing."""
    if _logo_file_id:
        return _logo_file_id
    return FSInputFile(settings.logo_path) if settings.logo_path.is_file() else None


async def _send_branded(message: Message, caption: str, markup) -> None:
    """Send the logo with a caption and buttons; falls back to plain text if the logo is unavailable."""
    global _logo_file_id
    logo = _logo()
    if logo is not None:
        try:
            sent = await message.answer_photo(logo, caption=caption, reply_markup=markup)
            if sent.photo:
                _logo_file_id = sent.photo[-1].file_id
            return
        except TelegramAPIError:
            log.exception("Could not send the logo, falling back to text")
    await message.answer(caption, reply_markup=markup)


async def show(event: Message | CallbackQuery, text: str, markup=None) -> None:
    """Edit the text message under a pressed button, or send a new one. Messages that carry a photo or a
    document cannot be edited into text, so they are replaced instead."""
    if isinstance(event, Message):
        await event.answer(text, reply_markup=markup)
        return
    await event.answer()
    msg = event.message
    if msg.content_type != ContentType.TEXT:
        try:
            await msg.delete()
        except TelegramAPIError:
            pass
        await msg.answer(text, reply_markup=markup)
        return
    try:
        await msg.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            await msg.answer(text, reply_markup=markup)


def greeting(role: Role, lang: str) -> str:
    if role is Role.GUEST:
        return f"{HDR}\n\n<i>{t(lang, 'tag')}</i>\n\n{t(lang, 'welcome_guest')}"
    return f"{HDR}\n\n{t(lang, 'welcome_owner' if role is Role.OWNER else 'welcome_admin')}"


async def show_main_menu(event: Message | CallbackQuery, db: Database, lang: str) -> None:
    role = await resolve_role(event.from_user.id, db)
    message = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
        try:
            await message.delete()
        except TelegramAPIError:
            pass
    await _send_branded(message, greeting(role, lang), kb.main_menu(role, lang))


async def ask_language(message: Message) -> None:
    await _send_branded(message, f"{HDR}\n\n{t('en', 'pick_lang')}", kb.language_kb())


def _parse_start_payload(payload: str | None) -> tuple[date, int] | None:
    """Deep link from the website: /start toy_2026-12-05_200 -> (date, guests)."""
    if not payload or not payload.startswith("toy_"):
        return None
    try:
        _, iso, guests = payload.split("_")
        d, g = date.fromisoformat(iso), int(guests)
    except ValueError:
        return None
    return (d, g) if d >= date.today() and 1 <= g <= 2000 else None


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, db: Database,
                    lang: str, lang_set: bool) -> None:
    await state.clear()
    try:                                                                    # drops a stale phone-request keyboard
        await (await message.answer("✦", reply_markup=ReplyKeyboardRemove())).delete()
    except TelegramAPIError:
        pass
    prefill = _parse_start_payload(command.args)
    if prefill:
        await state.update_data(prefill={"date": prefill[0].isoformat(), "guests": prefill[1]})
    if not lang_set:
        await ask_language(message)
        return
    await _after_language(message, state, db, lang)


async def _after_language(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    role = await resolve_role(message.chat.id, db)
    pre = (await state.get_data()).get("prefill")
    if pre and role is Role.GUEST:
        d = date.fromisoformat(pre["date"])
        label = t(lang, "b_prefill", date=fmt_date_short(lang, d), guests=pre["guests"])
        note = t(lang, "prefill_note", date=fmt_date_short(lang, d), guests=pre["guests"])
        await _send_branded(message, f"{greeting(role, lang)}\n\n{note}", kb.prefill_kb(lang, label))
        return
    await _send_branded(message, greeting(role, lang), kb.main_menu(role, lang))


@router.message(Command("language"))
@router.callback_query(F.data == "menu:lang")
async def choose_language(event: Message | CallbackQuery) -> None:
    message = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
        try:
            await message.delete()
        except TelegramAPIError:
            pass
    await ask_language(message)


@router.callback_query(F.data.startswith("lang:"))
async def set_language(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    code = call.data.split(":")[1]
    if code not in LANGS:
        await call.answer()
        return
    await db.set_lang(call.from_user.id, code)
    await call.answer()
    try:
        await call.message.delete()
    except TelegramAPIError:
        pass
    await _after_language(call.message, state, db, code)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "cancelled"), reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message, db, lang)


@router.message(Command("id"))
async def cmd_id(message: Message, lang: str) -> None:
    await message.answer(t(lang, "your_id", id=message.from_user.id))


@router.callback_query(F.data == "menu:home")
async def cb_home(call: CallbackQuery, state: FSMContext, db: Database, lang: str) -> None:
    await state.clear()
    await show_main_menu(call, db, lang)


@router.callback_query(F.data == "menu:guest")
async def cb_guest_menu(call: CallbackQuery, lang: str) -> None:
    """Lets staff preview exactly what guests see."""
    await show(call, greeting(Role.GUEST, lang), kb.guest_menu(lang))


# ---- fallbacks: registered last (see main.py) ----
fallback = Router(name="fallback")


@fallback.callback_query()
async def stale_button(call: CallbackQuery, lang: str) -> None:
    await call.answer(t(lang, "stale"), show_alert=True)


@fallback.message(F.chat.type == ChatType.PRIVATE)
async def any_message(message: Message, state: FSMContext, db: Database, lang: str, lang_set: bool) -> None:
    if not lang_set:
        await ask_language(message)
    elif await state.get_state():
        await message.answer(t(lang, "not_understood"))
    else:
        await show_main_menu(message, db, lang)
