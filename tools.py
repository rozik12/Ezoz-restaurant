"""Free tools: slides (.pptx), AI-likeness check, file converter."""
from __future__ import annotations

import asyncio
import html
import logging
import re

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

import detect
import keyboards as kb
import slides as sl
from config import Settings
from convert import TARGETS, ConvertError, convert, ext_of
from db import Database
from docs import MAX_FILE_BYTES, UnsupportedFile, extract_text
from i18n import labels, t
from llm import Assistant, AssistantError

log = logging.getLogger(__name__)

router = Router(name="tools")
router.message.filter(F.chat.type == ChatType.PRIVATE)

CANCEL = labels("cancel_btn")


class Tool(StatesGroup):
    slides = State()
    detect = State()
    convert = State()


ANY_TOOL = StateFilter(Tool.slides, Tool.detect, Tool.convert)
NOT_MENU = ~(F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))     # the stored FSM state is stale after clear(), so exclude explicitly


async def allowed(db: Database, settings: Settings, uid: int, tool: str, daily: int) -> tuple[bool, int]:
    limit = daily * 3 if await db.is_paid(uid) else daily
    return await db.tool_used_today(uid, tool) < limit, limit


async def input_text(message: Message, bot: Bot, lang: str) -> str | None:
    """Text of the message, or of an attached .txt/.md/.pdf/.docx file; None when there is nothing usable."""
    if message.document:
        if message.document.file_size and message.document.file_size > MAX_FILE_BYTES:
            await message.answer(t(lang, "file_big"))
            return None
        buf = await bot.download(message.document)
        try:
            text, _ = extract_text(message.document.file_name or "file", buf.read())
        except UnsupportedFile:
            await message.answer(t(lang, "file_bad"))
            return None
        return ((message.caption or "") + "\n\n" + text).strip()
    return (message.text or "").strip() or None


# ---------------- entering and leaving ----------------
@router.message(Command("slides"))
@router.message(F.text.in_(kb.BTN_SLIDES))
async def open_slides(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(Tool.slides)
    await message.answer(t(lang, "slides_intro"), reply_markup=kb.cancel_menu(lang))


@router.message(Command("detect"))
@router.message(F.text.in_(kb.BTN_DETECT))
async def open_detect(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(Tool.detect)
    await message.answer(t(lang, "detect_intro", n=detect.MIN_CHARS), reply_markup=kb.cancel_menu(lang))


@router.message(Command("convert"))
@router.message(F.text.in_(kb.BTN_CONVERT))
async def open_convert(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(Tool.convert)
    await message.answer(t(lang, "convert_intro"), reply_markup=kb.cancel_menu(lang))


@router.message(ANY_TOOL, Command("cancel"))
@router.message(ANY_TOOL, F.text.in_(CANCEL))
async def cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "support_cancel"), reply_markup=kb.main_menu(lang))


@router.message(ANY_TOOL, F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))
async def leave(message: Message, state: FSMContext) -> None:
    await state.clear()                       # another command or menu button ends the tool and runs normally
    raise SkipHandler


# ---------------- slides ----------------
@router.message(StateFilter(Tool.slides), NOT_MENU)
async def make_slides(message: Message, state: FSMContext, bot: Bot, db: Database, ai: Assistant, settings: Settings, lang: str) -> None:
    topic = await input_text(message, bot, lang)
    if topic is None:
        return
    if len(topic) < 4:
        await message.answer(t(lang, "slides_short"))
        return
    uid = message.from_user.id
    ok, limit = await allowed(db, settings, uid, "slides", settings.slides_daily)
    if not ok:
        await message.answer(t(lang, "tool_limit", n=limit), reply_markup=kb.main_menu(lang))
        await state.clear()
        return
    m = re.search(r"(\d{1,2})\s*(?:слайд|slayd|slide|sl\b)", topic.lower())
    count = max(5, min(20, int(m.group(1)))) if m else 10
    wait = await message.answer(t(lang, "slides_working"))
    deck = None
    try:
        async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
            for _ in range(2):                                    # one retry when the model's JSON is malformed
                raw = await ai.complete(sl.outline_prompt(lang, count), f"Topic or source material:\n{topic[:12000]}", 4500)
                try:
                    deck = sl.parse_deck(raw)
                    break
                except (ValueError, TypeError):
                    log.warning("Slides: unparsable model output")
            if deck is None:
                raise ValueError("no deck")
            data = await asyncio.to_thread(sl.build_pptx, deck)
    except AssistantError as e:
        await message.answer(f"⚠️ {t(lang, 'err_' + e.key)}")
        return
    except Exception:
        log.exception("Slides failed")
        await message.answer(t(lang, "slides_fail"))
        return
    finally:
        try:
            await wait.delete()
        except TelegramBadRequest:
            pass
    await db.count_tool(uid, "slides")
    name = re.sub(r"[^\w\- ]+", "", deck.title).strip()[:40].replace(" ", "_") or "presentation"
    await message.answer_document(BufferedInputFile(data, filename=f"{name}.pptx"), caption=t(lang, "slides_done", n=len(deck.slides)),
                                  reply_markup=kb.main_menu(lang))
    await state.clear()


# ---------------- AI check ----------------
@router.message(StateFilter(Tool.detect), NOT_MENU)
async def check_ai(message: Message, state: FSMContext, bot: Bot, db: Database, ai: Assistant, settings: Settings, lang: str) -> None:
    text = await input_text(message, bot, lang)
    if text is None:
        return
    if len(text) < detect.MIN_CHARS:
        await message.answer(t(lang, "detect_short", n=detect.MIN_CHARS))
        return
    uid = message.from_user.id
    ok, limit = await allowed(db, settings, uid, "detect", settings.detect_daily)
    if not ok:
        await message.answer(t(lang, "tool_limit", n=limit), reply_markup=kb.main_menu(lang))
        await state.clear()
        return
    text = text[:detect.MAX_CHARS]
    st = detect.stats(text)
    wait = await message.answer(t(lang, "detect_working"))
    try:
        async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
            raw = await ai.complete(detect.prompt(lang, st), text, 1500)
            res = detect.parse(raw)
    except AssistantError as e:
        await message.answer(f"⚠️ {t(lang, 'err_' + e.key)}")
        return
    except Exception:
        log.exception("AI check failed")
        await message.answer(t(lang, "detect_fail"))
        return
    finally:
        try:
            await wait.delete()
        except TelegramBadRequest:
            pass
    await db.count_tool(uid, "detect")
    verdict = t(lang, "verdict_low" if res["p"] < 35 else "verdict_mid" if res["p"] < 70 else "verdict_high")
    parts = [t(lang, "detect_head", p=res["p"], verdict=verdict),
             t(lang, "detect_stats", words=st["words"], sentences=st["sentences"], avg=st["avg_len"], spread=st["len_spread"],
               conn=st["connectors_per_1000"])]
    if res["signals"]:
        parts.append(t(lang, "detect_signals") + "\n" + "\n".join("• " + html.escape(x) for x in res["signals"]))
    if res["fragments"]:
        parts.append(t(lang, "detect_frags") + "\n" + "\n".join(f"«{html.escape(q)}»\n   ↳ {html.escape(r)}" for q, r in res["fragments"]))
    if res["advice"]:
        parts.append(t(lang, "detect_advice") + "\n" + "\n".join("• " + html.escape(x) for x in res["advice"]))
    parts.append(t(lang, "detect_note"))
    await message.answer("\n\n".join(parts), reply_markup=kb.main_menu(lang))
    await state.clear()


# ---------------- converter ----------------
@router.message(StateFilter(Tool.convert), F.document | F.photo)
async def receive_file(message: Message, state: FSMContext, lang: str) -> None:
    if message.photo:
        file_id, name, size = message.photo[-1].file_id, "photo.jpg", message.photo[-1].file_size
    else:
        d = message.document
        file_id, name, size = d.file_id, d.file_name or "file", d.file_size
    if size and size > MAX_FILE_BYTES:
        await message.answer(t(lang, "file_big"))
        return
    targets = TARGETS.get(ext_of(name))
    if not targets:
        await message.answer(t(lang, "conv_err_unsupported"))
        return
    await state.update_data(file_id=file_id, name=name)
    await message.answer(t(lang, "convert_pick", name=html.escape(name)), reply_markup=kb.convert_targets(targets))


@router.callback_query(F.data.startswith("cv:"))
async def do_convert(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database, settings: Settings, lang: str) -> None:
    data = await state.get_data()
    if "file_id" not in data:
        await call.answer(t(lang, "convert_expired"), show_alert=True)
        return
    uid = call.from_user.id
    ok, limit = await allowed(db, settings, uid, "convert", settings.convert_daily)
    if not ok:
        await call.answer(t(lang, "tool_limit", n=limit), show_alert=True)
        return
    await call.answer(t(lang, "convert_working"))
    try:
        buf = await bot.download(data["file_id"])
        name, out = await asyncio.to_thread(convert, data["name"], buf.read(), call.data.split(":")[1])
    except ConvertError as e:
        await call.message.answer(f"⚠️ {t(lang, 'conv_err_' + e.key)}")
        return
    except Exception:
        log.exception("Conversion failed")
        await call.message.answer(f"⚠️ {t(lang, 'convert_fail')}")
        return
    await db.count_tool(uid, "convert")
    await call.message.answer_document(BufferedInputFile(out, filename=name), caption=t(lang, "convert_done", name=html.escape(name)))
