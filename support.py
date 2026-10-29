"""Support desk, user side: a client writes one message, admins get it with reply buttons; replies come back to the client."""
from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import keyboards as kb
from config import Settings
from db import Database
from i18n import labels, t

log = logging.getLogger(__name__)

router = Router(name="support")
router.message.filter(F.chat.type == ChatType.PRIVATE)

MAX_OPEN_PER_USER = 3
CANCEL = labels("cancel_btn")


class Support(StatesGroup):
    waiting = State()


async def admin_chat_ids(db: Database, settings: Settings) -> list[int]:
    ids = list(settings.admin_ids)
    ids += [a["user_id"] for a in await db.admin_rows() if a["user_id"] not in ids]
    return ids


def ticket_buttons(ticket_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"tk:reply:{ticket_id}"),
         InlineKeyboardButton(text="✅ Закрыть", callback_data=f"tk:close:{ticket_id}")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data=f"us:{user_id}")]])


@router.message(Command("support"))
@router.message(F.text.in_(kb.BTN_SUPPORT))
async def open_support(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(Support.waiting)
    await message.answer(t(lang, "support_intro"), reply_markup=kb.cancel_menu(lang))


@router.message(StateFilter(Support.waiting), Command("cancel"))
@router.message(StateFilter(Support.waiting), F.text.in_(CANCEL))
async def cancel_support(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "support_cancel"), reply_markup=kb.main_menu(lang))


@router.message(StateFilter(Support.waiting), F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))
async def other_command(message: Message, state: FSMContext) -> None:
    await state.clear()                       # a command or another menu button leaves the support dialog and runs normally
    raise SkipHandler


@router.message(StateFilter(Support.waiting), ~(F.text.startswith("/") | F.text.in_(kb.MENU_LABELS)))
async def receive_ticket(message: Message, state: FSMContext, bot: Bot, db: Database, settings: Settings, lang: str) -> None:
    text = (message.text or message.caption or "").strip()
    has_media = bool(message.photo or message.document or message.video or message.voice)
    if not text and not has_media:
        await message.answer(t(lang, "support_empty"))
        return
    u = message.from_user
    if await db.open_tickets_of(u.id) >= MAX_OPEN_PER_USER:
        await state.clear()
        await message.answer(t(lang, "support_limit"), reply_markup=kb.main_menu(lang))
        return
    tid = await db.create_ticket(u.id, text or "[media]")
    await state.clear()
    head = (f"🆘 <b>Обращение #{tid}</b>\n"
            f"От: {html.escape(u.full_name)}" + (f" (@{html.escape(u.username)})" if u.username else "") +
            f"\nID: <code>{u.id}</code> · язык: {lang}\n\n{html.escape(text)[:3500]}")
    for admin_id in await admin_chat_ids(db, settings):
        try:
            sent = await bot.send_message(admin_id, head, reply_markup=ticket_buttons(tid, u.id))
            await db.link_ticket_msg(admin_id, sent.message_id, tid)
            if has_media:
                copy = await bot.copy_message(admin_id, message.chat.id, message.message_id)
                await db.link_ticket_msg(admin_id, copy.message_id, tid)
        except Exception:
            log.warning("Could not notify admin %s about ticket %s", admin_id, tid)
    await message.answer(t(lang, "support_sent", id=tid), reply_markup=kb.main_menu(lang))
