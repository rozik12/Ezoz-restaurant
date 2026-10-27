"""Owner-only features: lead statistics, administrator management, broadcast."""
from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from config import OWNER_ID
from db import Database
from handlers.common import show
from roles import HasRole, Role
from states import OwnerStates

log = logging.getLogger(__name__)

router = Router(name="owner")
router.message.filter(F.chat.type == ChatType.PRIVATE, HasRole(Role.OWNER))
router.callback_query.filter(HasRole(Role.OWNER))

_background: set[asyncio.Task] = set()      # keeps references so running broadcasts are not garbage-collected


# =========================== statistics ===========================
@router.callback_query(F.data == "own:stats")
async def stats(call: CallbackQuery, db: Database) -> None:
    s = await db.stats()
    conv = f"{s['leads'] / s['users'] * 100:.1f}%" if s["users"] else "n/a"
    text = (
        "📊 <b>Lead generation</b>\n\n"
        f"👥 Users: <b>{s['users']}</b> (today +{s['users_today']}, 7 days +{s['users_week']}, blocked {s['blocked']})\n"
        f"📅 Booking requests: <b>{s['leads']}</b> (today {s['leads_today']}, 7 days {s['leads_week']})\n"
        f"🎯 Users who booked: <b>{conv}</b>\n\n"
        "<b>Funnel actions</b>\n"
        f"🏛 Hall views: {s['tour_viewed']}\n"
        f"📄 Menu PDF downloads: {s['menu_downloaded']}\n"
        f"🧮 Calculator completions: {s['calc_completed']}\n\n"
        f"🛠 Administrators: {s['admins']}"
    )
    await show(call, text, kb.back_home())


# =========================== administrators ===========================
async def _admins_view(event: Message | CallbackQuery, db: Database, note: str = "") -> None:
    rows = await db.list_admins()
    items = [(r["user_id"], f"@{r['username']}" if r["username"] else (r["full_name"] or str(r["user_id"]))) for r in rows]
    listing = "\n".join(f"• <code>{uid}</code> {html.escape(label)}" for uid, label in items) or "No administrators yet."
    await show(event, f"{note}👥 <b>Administrators</b>\n\n{listing}", kb.admins_kb(items))


@router.callback_query(F.data == "own:admins")
async def admins(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await _admins_view(call, db)


@router.callback_query(F.data == "own:add")
async def add_admin_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OwnerStates.add_admin)
    await show(call, "Send the Telegram ID of the new administrator (digits only).\n"
                     "They can get it by sending /id to this bot.", kb.back_home())


@router.message(OwnerStates.add_admin, F.text)
async def add_admin_id(message: Message, state: FSMContext, bot: Bot, db: Database) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("Digits only, for example <code>123456789</code>.")
        return
    uid = int(raw)
    if uid == OWNER_ID:
        await message.answer("That is the Owner account; it already has full access.")
        return
    await state.clear()
    added = await db.add_admin(uid, OWNER_ID)
    note = f"✅ <code>{uid}</code> is now an administrator.\n\n" if added else f"ℹ️ <code>{uid}</code> was already an administrator.\n\n"
    if added:
        try:
            await bot.send_message(uid, "🛠 You have been added as an E'zoz administrator. Send /start to open your menu.")
        except TelegramAPIError:
            note += "(They have not started the bot yet, so they were not notified.)\n\n"
    await _admins_view(message, db, note)


@router.callback_query(F.data.startswith("own:rm:"))
async def remove_admin(call: CallbackQuery, db: Database) -> None:
    uid = int(call.data.split(":")[2])
    removed = await db.remove_admin(uid)
    await _admins_view(call, db, f"🗑 <code>{uid}</code> removed.\n\n" if removed else "")


# =========================== broadcast ===========================
@router.callback_query(F.data == "own:broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OwnerStates.broadcast)
    await show(call, "📣 <b>Broadcast</b>\n\nSend the message to deliver to all users: text, photo, video or a document "
                     "with caption. It is copied exactly as you send it.", kb.back_home())


@router.message(OwnerStates.broadcast)
async def broadcast_preview(message: Message, state: FSMContext, db: Database) -> None:
    targets = await db.broadcast_targets()
    await state.update_data(src_chat=message.chat.id, src_msg=message.message_id)
    await state.set_state(OwnerStates.broadcast_confirm)
    await message.answer(f"Preview above. It will be sent to <b>{len(targets)}</b> users. Send it?",
                         reply_markup=kb.broadcast_confirm_kb(), reply_to_message_id=message.message_id)


@router.callback_query(OwnerStates.broadcast_confirm, F.data == "own:bc_go")
async def broadcast_go(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database) -> None:
    data = await state.get_data()
    await state.clear()
    await show(call, "📣 Sending started. I will report when it finishes.")
    task = asyncio.create_task(_broadcast(bot, db, call.message.chat.id, data["src_chat"], data["src_msg"]))
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _broadcast(bot: Bot, db: Database, report_to: int, src_chat: int, src_msg: int) -> None:
    sent = blocked = failed = 0
    for uid in await db.broadcast_targets():
        for attempt in range(2):
            try:
                await bot.copy_message(uid, src_chat, src_msg)
                sent += 1
            except TelegramRetryAfter as e:                   # flood control: wait, then retry once
                await asyncio.sleep(e.retry_after + 1)
                continue
            except TelegramForbiddenError:                    # user blocked the bot
                await db.mark_blocked(uid)
                blocked += 1
            except TelegramAPIError:
                log.exception("Broadcast to %s failed", uid)
                failed += 1
            break
        await asyncio.sleep(0.05)                             # about 20 msg/s, under Telegram's 30 msg/s limit
    await bot.send_message(report_to, f"📣 <b>Broadcast finished</b>\n\n✅ Delivered: {sent}\n🚫 Blocked the bot: {blocked}\n⚠️ Failed: {failed}")
