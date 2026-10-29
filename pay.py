"""Payment by transfer to an Uzbek card (Uzcard / Humo): the user sends the receipt, an administrator confirms it."""
from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import keyboards as kb
from config import Settings
from db import Database
from i18n import labels, t
from support import admin_chat_ids

log = logging.getLogger(__name__)

router = Router(name="pay")
router.message.filter(F.chat.type == ChatType.PRIVATE)

CANCEL = labels("cancel_btn")
NOT_MENU = ~(F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))


class Pay(StatesGroup):
    receipt = State()


def amount(n: int) -> str:
    return f"{n:,}".replace(",", " ")


@router.callback_query(F.data == "card:info")
async def card_info(call: CallbackQuery, settings: Settings, lang: str) -> None:
    await call.answer()
    if not settings.card_ready:
        return
    holder = t(lang, "card_holder_line", name=html.escape(settings.card_holder)) if settings.card_holder else ""
    await call.message.answer(t(lang, "card_text", amount=amount(settings.price_uzs), days=settings.sub_days,
                                card=html.escape(settings.card_number), holder=holder),
                              reply_markup=kb.card_paid_button(lang))


@router.callback_query(F.data == "card:paid")
async def card_paid(call: CallbackQuery, state: FSMContext, db: Database, settings: Settings, lang: str) -> None:
    await call.answer()
    if not settings.card_ready:
        return
    if await db.pending_card_payments_of(call.from_user.id):
        await call.message.answer(t(lang, "card_pending"))
        return
    await state.set_state(Pay.receipt)
    await call.message.answer(t(lang, "card_send"), reply_markup=kb.cancel_menu(lang))


@router.message(StateFilter(Pay.receipt), Command("cancel"))
@router.message(StateFilter(Pay.receipt), F.text.in_(CANCEL))
async def cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "support_cancel"), reply_markup=kb.main_menu(lang))


@router.message(StateFilter(Pay.receipt), F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))
async def leave(message: Message, state: FSMContext) -> None:
    await state.clear()                      # another command or menu button leaves the dialog and runs normally
    raise SkipHandler


@router.message(StateFilter(Pay.receipt), NOT_MENU)
async def receive(message: Message, state: FSMContext, bot: Bot, db: Database, settings: Settings, lang: str) -> None:
    doc = message.document
    is_receipt = bool(message.photo) or bool(doc and (doc.mime_type or "").startswith(("image/", "application/pdf")))
    if not is_receipt:
        await message.answer(t(lang, "card_need_photo"))
        return
    u = message.from_user
    pid = await db.create_card_payment(u.id)
    await state.clear()
    head = (f"💳 <b>Оплата картой, заявка #{pid}</b>\n"
            f"От: {html.escape(u.full_name)}" + (f" (@{html.escape(u.username)})" if u.username else "") +
            f"\nID: <code>{u.id}</code>\nСумма: {amount(settings.price_uzs)} сум · подписка на {settings.sub_days} дн.\n"
            "Сверьте сумму и получателя в чеке и подтвердите.")
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"✅ Подтвердить (+{settings.sub_days} дн.)", callback_data=f"cp:ok:{pid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"cp:no:{pid}")]])
    for admin_id in await admin_chat_ids(db, settings):
        try:
            await bot.send_message(admin_id, head, reply_markup=markup)
            await bot.copy_message(admin_id, message.chat.id, message.message_id)
        except Exception:
            log.warning("Could not notify admin %s about card payment %s", admin_id, pid)
    await message.answer(t(lang, "card_received", id=pid), reply_markup=kb.main_menu(lang))
