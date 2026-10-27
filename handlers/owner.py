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
from i18n import t
from roles import HasRole, Role
from states import OwnerStates

log = logging.getLogger(__name__)

router = Router(name="owner")
router.message.filter(F.chat.type == ChatType.PRIVATE, HasRole(Role.OWNER))
router.callback_query.filter(HasRole(Role.OWNER))

_background: set[asyncio.Task] = set()      # keeps references so running broadcasts are not garbage-collected


# =========================== statistics ===========================
@router.callback_query(F.data == "own:stats")
async def stats(call: CallbackQuery, db: Database, lang: str) -> None:
    s = await db.stats()
    conv = f"{s['leads'] / s['users'] * 100:.1f}%" if s["users"] else "–"
    await show(call, t(lang, "stats", conv=conv, **s), kb.back_home(lang))


# =========================== administrators ===========================
async def _admins_view(event: Message | CallbackQuery, db: Database, lang: str, note: str = "") -> None:
    rows = await db.list_admins()
    items = [(r["user_id"], f"@{r['username']}" if r["username"] else (r["full_name"] or str(r["user_id"]))) for r in rows]
    listing = "\n".join(f"• <code>{uid}</code> {html.escape(label)}" for uid, label in items) or t(lang, "admins_none")
    await show(event, note + t(lang, "admins_title", list=listing), kb.admins_kb(lang, items))


@router.callback_query(F.data == "own:admins")
async def admins(call: CallbackQuery, state: FSMContext, db: Database, lang: str) -> None:
    await state.clear()
    await _admins_view(call, db, lang)


@router.callback_query(F.data == "own:add")
async def add_admin_start(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerStates.add_admin)
    await show(call, t(lang, "admin_add_prompt"), kb.back_home(lang))


@router.message(OwnerStates.add_admin, F.text)
async def add_admin_id(message: Message, state: FSMContext, bot: Bot, db: Database, lang: str) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(t(lang, "admin_digits"))
        return
    uid = int(raw)
    if uid == OWNER_ID:
        await message.answer(t(lang, "admin_is_owner"))
        return
    await state.clear()
    added = await db.add_admin(uid, OWNER_ID)
    note = t(lang, "admin_added", id=uid) if added else t(lang, "admin_existing", id=uid)
    if added:
        try:
            target_lang = await db.get_lang(uid) or lang
            await bot.send_message(uid, t(target_lang, "admin_welcome_msg"))
        except TelegramAPIError:
            note += t(lang, "admin_not_notified")
    await _admins_view(message, db, lang, note)


@router.callback_query(F.data.startswith("own:rm:"))
async def remove_admin(call: CallbackQuery, db: Database, lang: str) -> None:
    uid = int(call.data.split(":")[2])
    removed = await db.remove_admin(uid)
    await _admins_view(call, db, lang, t(lang, "admin_removed", id=uid) if removed else "")


# =========================== broadcast ===========================
@router.callback_query(F.data == "own:broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(OwnerStates.broadcast)
    await show(call, t(lang, "bc_prompt"), kb.back_home(lang))


@router.message(OwnerStates.broadcast)
async def broadcast_preview(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    targets = await db.broadcast_targets()
    await state.update_data(src_chat=message.chat.id, src_msg=message.message_id)
    await state.set_state(OwnerStates.broadcast_confirm)
    await message.answer(t(lang, "bc_preview", n=len(targets)), reply_markup=kb.broadcast_confirm_kb(lang),
                         reply_to_message_id=message.message_id)


@router.callback_query(OwnerStates.broadcast_confirm, F.data == "own:bc_go")
async def broadcast_go(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database, lang: str) -> None:
    data = await state.get_data()
    await state.clear()
    await show(call, t(lang, "bc_started"))
    task = asyncio.create_task(_broadcast(bot, db, lang, call.message.chat.id, data["src_chat"], data["src_msg"]))
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _broadcast(bot: Bot, db: Database, lang: str, report_to: int, src_chat: int, src_msg: int) -> None:
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
    await bot.send_message(report_to, t(lang, "bc_done", sent=sent, blocked=blocked, failed=failed))
