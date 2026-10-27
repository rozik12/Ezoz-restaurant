"""Admin / SMM workflow: send media + caption, pick platforms, cross-post. Also: recent leads."""
from __future__ import annotations

import html
import logging
import uuid
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from config import OWNER_ID, settings
from db import Database
from handlers.common import show, show_main_menu
from roles import HasRole, Role
from services.pricing import TIER_LABEL, fmt_uzs
from services.social import IG_CAPTION_LIMIT, PLATFORMS, VIDEO_ONLY, LocalMedia, publish_all
from states import PostStates

log = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(F.chat.type == ChatType.PRIVATE, HasRole(Role.OWNER, Role.ADMIN))
router.callback_query.filter(HasRole(Role.OWNER, Role.ADMIN))

# Bots on the public Bot API can download files up to 20 MB. For bigger videos run a local Bot API server.
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


# =========================== new post ===========================
@router.callback_query(F.data == "adm:post")
async def post_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PostStates.media)
    await show(call, "📝 <b>New post</b>\n\nSend a <b>photo</b> or a <b>video</b>. "
                     "You can add the caption to it now, or send it in the next step.\n"
                     f"Videos up to {MAX_DOWNLOAD_BYTES // 1024 // 1024} MB. YouTube Shorts needs a vertical video.",
               kb.back_home())


@router.message(PostStates.media, F.photo | F.video)
async def post_media(message: Message, state: FSMContext) -> None:
    if message.photo:
        item, kind, suffix = message.photo[-1], "photo", ".jpg"
    else:
        item, kind, suffix = message.video, "video", ".mp4"
    if item.file_size and item.file_size > MAX_DOWNLOAD_BYTES:
        await message.answer("That file is over 20 MB, which the bot cannot download. Send a smaller one.")
        return
    await state.update_data(file_id=item.file_id, kind=kind, suffix=suffix, targets=[],
                            caption=(message.caption or "").strip())
    if message.caption:
        await _ask_platforms(message, state)
        return
    await state.set_state(PostStates.caption)
    await message.answer(f"Got the {kind}. Now send the <b>caption</b> (up to {IG_CAPTION_LIMIT} characters).")


@router.message(PostStates.media)
async def post_media_wrong(message: Message) -> None:
    await message.answer("Please send a photo or a video, or /cancel.")


@router.message(PostStates.caption, F.text)
async def post_caption(message: Message, state: FSMContext) -> None:
    if len(message.text) > IG_CAPTION_LIMIT:
        await message.answer(f"Caption is {len(message.text)} characters; Instagram allows {IG_CAPTION_LIMIT}. Please shorten it.")
        return
    await state.update_data(caption=message.text.strip())
    await _ask_platforms(message, state)


async def _ask_platforms(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(PostStates.platforms)
    await message.answer("Where should it go? Tap to toggle platforms.",
                         reply_markup=kb.platforms_kb(data["targets"], data["kind"]))


@router.callback_query(PostStates.platforms, F.data.startswith("post:t:"))
async def post_toggle(call: CallbackQuery, state: FSMContext) -> None:
    key = call.data.split(":")[2]
    data = await state.get_data()
    if key not in PLATFORMS:
        await call.answer()
        return
    if key in VIDEO_ONLY and data["kind"] != "video":
        await call.answer(f"{PLATFORMS[key]} needs a video.", show_alert=True)
        return
    targets = data["targets"]
    targets = [t for t in targets if t != key] if key in targets else targets + [key]
    await state.update_data(targets=targets)
    await show(call, "Where should it go? Tap to toggle platforms.", kb.platforms_kb(targets, data["kind"]))


@router.callback_query(PostStates.platforms, F.data == "post:review")
async def post_review(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data["targets"]:
        await call.answer("Choose at least one platform.", show_alert=True)
        return
    await state.set_state(PostStates.confirm)
    names = ", ".join(PLATFORMS[t] for t in data["targets"])
    await show(call, f"<b>Ready to publish</b>\n\nType: {data['kind']}\nPlatforms: {names}\n\n"
                     f"Caption:\n<blockquote>{html.escape(data['caption'] or '(empty)')}</blockquote>",
               kb.confirm_post_kb())


@router.callback_query(PostStates.confirm, F.data == "post:back")
async def post_back(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(PostStates.platforms)
    await show(call, "Where should it go? Tap to toggle platforms.", kb.platforms_kb(data["targets"], data["kind"]))


@router.callback_query(PostStates.confirm, F.data == "post:go")
async def post_publish(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database) -> None:
    data = await state.get_data()
    await state.clear()                                   # prevents a double tap from posting twice
    await show(call, "⏳ Downloading the file and publishing. Videos can take a few minutes...")

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    local = settings.media_dir / f"src_{uuid.uuid4().hex}{data['suffix']}"
    try:
        await bot.download(data["file_id"], destination=local)
        results = await publish_all(data["targets"], LocalMedia(local, data["kind"]), data["caption"])
    except Exception:
        log.exception("Post workflow failed")
        await call.message.answer("❌ Could not download the file from Telegram. Please try again.")
        await show_main_menu(call.message, db)
        return
    finally:
        local.unlink(missing_ok=True)

    lines = [f"{'✅' if r.ok else '❌'} <b>{r.platform}</b>: {html.escape(r.detail)}" for r in results]
    await call.message.answer("<b>Publishing finished</b>\n\n" + "\n".join(lines), disable_web_page_preview=True)
    await call.message.answer("🏠", reply_markup=kb.main_menu(Role.OWNER if call.from_user.id == OWNER_ID else Role.ADMIN))


# =========================== leads ===========================
@router.callback_query(F.data == "adm:leads")
async def recent_leads(call: CallbackQuery, db: Database) -> None:
    rows = await db.recent_leads(10)
    if not rows:
        await show(call, "No booking requests yet.", kb.back_home())
        return
    out = []
    for r in rows:
        extra = f" · ~{r['guests']} guests" if r["guests"] else ""
        est = f" · {fmt_uzs(r['estimate_uzs'])}" if r["estimate_uzs"] else ""
        tier = f" · {TIER_LABEL[r['tier']]}" if r["tier"] in TIER_LABEL else ""
        out.append(f"<b>#{r['id']}</b> {r['event_date']}{extra}{tier}{est}\n"
                   f"<a href=\"tg://user?id={r['user_id']}\">{html.escape(r['name'] or 'guest')}</a> · {html.escape(r['phone'])}")
    await show(call, "📋 <b>Latest requests</b>\n\n" + "\n\n".join(out), kb.back_home())
