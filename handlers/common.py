"""/start, role-based main menu, cancel, and the catch-all fallbacks."""
from __future__ import annotations

import html
from datetime import date

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import keyboards as kb
from db import Database
from roles import Role, resolve_role

router = Router(name="common")
router.message.filter(F.chat.type == ChatType.PRIVATE)

GREETING = {
    Role.OWNER: "👑 <b>Welcome, Owner.</b>\nStatistics, administrators and broadcasts are below.",
    Role.ADMIN: "🛠 <b>Welcome, administrator.</b>\nPublish content or review new booking requests.",
    Role.GUEST: ("✨ <b>E'zoz Tashkent</b>\nCreate the atmosphere of your best moments.\n\n"
                 "Explore our halls, get the menu, estimate your budget or book a date."),
}


async def show(event: Message | CallbackQuery, text: str, markup=None) -> None:
    """Edit the message under a pressed button, or send a new one. Falls back to a new message when the
    old one cannot be edited (for example after sending a document)."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        try:
            await event.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await event.message.answer(text, reply_markup=markup)
    else:
        await event.answer(text, reply_markup=markup)


async def show_main_menu(event: Message | CallbackQuery, db: Database) -> None:
    role = await resolve_role(event.from_user.id, db)
    await show(event, GREETING[role], kb.main_menu(role))


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
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, db: Database) -> None:
    await state.clear()
    role = await resolve_role(message.from_user.id, db)
    await message.answer("·", reply_markup=ReplyKeyboardRemove())  # drops a stale phone-request keyboard
    prefill = _parse_start_payload(command.args) if role is Role.GUEST else None
    if prefill:
        d, g = prefill
        await state.update_data(prefill={"date": d.isoformat(), "guests": g})
        await message.answer(
            f"{GREETING[role]}\n\nWe have your request from the website: <b>{d:%d %b %Y}</b>, about <b>{g}</b> guests.",
            reply_markup=kb.prefill_kb(f"✅ Book {d:%d %b %Y}, ~{g} guests"),
        )
        return
    await message.answer(GREETING[role], reply_markup=kb.main_menu(role))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message, db)


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(f"Your Telegram ID: <code>{message.from_user.id}</code>")


@router.callback_query(F.data == "menu:home")
async def cb_home(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await show_main_menu(call, db)


@router.callback_query(F.data == "menu:guest")
async def cb_guest_menu(call: CallbackQuery) -> None:
    """Lets staff preview exactly what guests see."""
    await show(call, GREETING[Role.GUEST], kb.guest_menu())


# ---- fallbacks: registered last (see main.py) ----
fallback = Router(name="fallback")


@fallback.callback_query()
async def stale_button(call: CallbackQuery) -> None:
    await call.answer("This button is no longer available. Use /start.", show_alert=True)


@fallback.message(F.chat.type == ChatType.PRIVATE)
async def any_message(message: Message, state: FSMContext, db: Database) -> None:
    if await state.get_state():
        await message.answer("I did not understand that. Follow the last question, or send /cancel.")
        return
    await show_main_menu(message, db)
