"""Admin / SMM workflow: send media + caption, pick platforms, cross-post. Also: recent leads."""
from __future__ import annotations

import html
import logging
import re
import uuid

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from config import OWNER_ID, settings
from db import Database
from handlers.common import show, show_main_menu
from i18n import fmt_date_short, money, t
from roles import HasRole, Role
from services import pricing
from services.social import IG_CAPTION_LIMIT, PLATFORMS, VIDEO_ONLY, LocalMedia, publish_all
from states import PostStates, PriceStates

log = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(F.chat.type == ChatType.PRIVATE, HasRole(Role.OWNER, Role.ADMIN))
router.callback_query.filter(HasRole(Role.OWNER, Role.ADMIN))

# Bots on the public Bot API can download files up to 20 MB. For bigger videos run a local Bot API server.
MAX_MB = 20
MAX_DOWNLOAD_BYTES = MAX_MB * 1024 * 1024


# =========================== new post ===========================
@router.callback_query(F.data == "adm:post")
async def post_start(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await state.set_state(PostStates.media)
    await show(call, t(lang, "post_start", mb=MAX_MB), kb.back_home(lang))


@router.message(PostStates.media, F.photo | F.video)
async def post_media(message: Message, state: FSMContext, lang: str) -> None:
    if message.photo:
        item, kind, suffix = message.photo[-1], "photo", ".jpg"
    else:
        item, kind, suffix = message.video, "video", ".mp4"
    if item.file_size and item.file_size > MAX_DOWNLOAD_BYTES:
        await message.answer(t(lang, "post_big", mb=MAX_MB))
        return
    await state.update_data(file_id=item.file_id, kind=kind, suffix=suffix, targets=[],
                            caption=(message.caption or "").strip())
    if message.caption:
        await _ask_platforms(message, state, lang)
        return
    await state.set_state(PostStates.caption)
    await message.answer(t(lang, "post_caption", kind=t(lang, f"kind_{kind}"), limit=IG_CAPTION_LIMIT))


@router.message(PostStates.media)
async def post_media_wrong(message: Message, lang: str) -> None:
    await message.answer(t(lang, "post_wrong"))


@router.message(PostStates.caption, F.text)
async def post_caption(message: Message, state: FSMContext, lang: str) -> None:
    if len(message.text) > IG_CAPTION_LIMIT:
        await message.answer(t(lang, "post_caption_long", n=len(message.text), limit=IG_CAPTION_LIMIT))
        return
    await state.update_data(caption=message.text.strip())
    await _ask_platforms(message, state, lang)


async def _ask_platforms(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    await state.set_state(PostStates.platforms)
    await message.answer(t(lang, "post_where"), reply_markup=kb.platforms_kb(lang, data["targets"], data["kind"]))


@router.callback_query(PostStates.platforms, F.data.startswith("post:t:"))
async def post_toggle(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    key = call.data.split(":")[2]
    data = await state.get_data()
    if key not in PLATFORMS:
        await call.answer()
        return
    if key in VIDEO_ONLY and data["kind"] != "video":
        await call.answer(t(lang, "post_needs_video", name=PLATFORMS[key]), show_alert=True)
        return
    targets = data["targets"]
    targets = [x for x in targets if x != key] if key in targets else targets + [key]
    await state.update_data(targets=targets)
    await show(call, t(lang, "post_where"), kb.platforms_kb(lang, targets, data["kind"]))


@router.callback_query(PostStates.platforms, F.data == "post:review")
async def post_review(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    if not data["targets"]:
        await call.answer(t(lang, "post_pick_one"), show_alert=True)
        return
    await state.set_state(PostStates.confirm)
    names = ", ".join(PLATFORMS[x] for x in data["targets"])
    caption = html.escape(data["caption"]) if data["caption"] else t(lang, "empty")
    await show(call, t(lang, "post_review", kind=t(lang, f"kind_{data['kind']}"), names=names, caption=caption),
               kb.confirm_post_kb(lang))


@router.callback_query(PostStates.confirm, F.data == "post:back")
async def post_back(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    await state.set_state(PostStates.platforms)
    await show(call, t(lang, "post_where"), kb.platforms_kb(lang, data["targets"], data["kind"]))


@router.callback_query(PostStates.confirm, F.data == "post:go")
async def post_publish(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database, lang: str) -> None:
    data = await state.get_data()
    await state.clear()                                   # prevents a double tap from posting twice
    await show(call, t(lang, "post_working"))

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    local = settings.media_dir / f"src_{uuid.uuid4().hex}{data['suffix']}"
    try:
        await bot.download(data["file_id"], destination=local)
        results = await publish_all(data["targets"], LocalMedia(local, data["kind"]), data["caption"])
    except Exception:
        log.exception("Post workflow failed")
        await call.message.answer(t(lang, "post_dl_fail"))
        await show_main_menu(call.message, db, lang)
        return
    finally:
        local.unlink(missing_ok=True)

    lines = [f"{'✅' if r.ok else '❌'} <b>{r.platform}</b>: {html.escape(r.detail)}" for r in results]
    await call.message.answer(t(lang, "post_done", results="\n".join(lines)), disable_web_page_preview=True)
    await call.message.answer("✦", reply_markup=kb.main_menu(Role.OWNER if call.from_user.id == OWNER_ID else Role.ADMIN, lang))


# =========================== leads ===========================
@router.callback_query(F.data == "adm:leads")
async def recent_leads(call: CallbackQuery, db: Database, lang: str) -> None:
    rows = await db.recent_leads(10)
    if not rows:
        await show(call, t(lang, "leads_empty"), kb.back_home(lang))
        return
    out = []
    for r in rows:
        from datetime import date as _d
        when = fmt_date_short(lang, _d.fromisoformat(r["event_date"]))
        extra = f" · ~{r['guests']}" if r["guests"] else ""
        tier = f" · {t(lang, 'tier_' + r['tier'])}" if r["tier"] else ""
        est = f" · {money(lang, r['estimate_uzs'])}" if r["estimate_uzs"] else ""
        who = html.escape(r["name"] or t(lang, "guest"))
        if r["user_id"] > 0:                      # website leads have user_id 0 and no Telegram profile
            who = f"<a href=\"tg://user?id={r['user_id']}\">{who}</a>"
        out.append(f"<b>#{r['id']}</b> 📅 {when}{extra}{tier}{est}\n{who} · {html.escape(r['phone'])}")
    await show(call, t(lang, "leads_title") + "\n\n".join(out), kb.back_home(lang))


# =========================== prices ===========================
async def _prices_screen(event, lang: str, note: str = "") -> None:
    await show(event, note + t(lang, "prices_title"), kb.prices_kb(lang))


@router.callback_query(F.data == "adm:prices")
async def prices(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await _prices_screen(call, lang)


@router.callback_query(F.data.startswith("price:"))
async def price_pick(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    _, group, key = call.data.split(":")
    if group not in pricing.GROUPS or key not in pricing.GROUPS[group]:
        await call.answer()
        return
    await state.set_state(PriceStates.value)
    await state.update_data(group=group, key=key)
    await show(call, t(lang, "price_prompt", icon=kb.PRICE_ICON[group], name=kb.price_label(lang, group, key),
                       cur=money(lang, pricing.GROUPS[group][key])), kb.price_cancel_kb(lang))


@router.message(PriceStates.value, F.text)
async def price_set(message: Message, state: FSMContext, bot: Bot, db: Database, lang: str) -> None:
    raw = re.sub(r"[\s,._]", "", message.text)           # accept "400 000", "400,000" and "400.000"
    if not raw.isdigit():
        await message.answer(t(lang, "price_bad"))
        return
    data = await state.get_data()
    group, key = data["group"], data["key"]
    lo, hi = pricing.LIMITS[group]
    value = int(raw)
    if not lo <= value <= hi:
        await message.answer(t(lang, "price_range", lo=money(lang, lo), hi=money(lang, hi)))
        return
    old = await pricing.save_price(db, group, key, value)
    await state.clear()
    log.info("Price %s:%s changed %s -> %s by %s", group, key, old, value, message.from_user.id)
    if message.from_user.id != OWNER_ID:                  # the owner always sees who changed what
        owner_lang = await db.get_lang(OWNER_ID) or settings.admin_lang
        who = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        try:
            await bot.send_message(OWNER_ID, t(owner_lang, "price_audit", who=html.escape(who),
                                               name=kb.price_label(owner_lang, group, key), old=money(owner_lang, old),
                                               new=money(owner_lang, value)))
        except Exception:
            log.warning("Could not notify the owner about a price change")
    await _prices_screen(message, lang, t(lang, "price_saved", name=kb.price_label(lang, group, key),
                                          old=money(lang, old), new=money(lang, value)))
