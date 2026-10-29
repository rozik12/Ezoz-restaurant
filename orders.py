"""Order wizards: a written work (type, topic, language, length, standard, requirements) and a presentation (topic, slide count, purpose, style),
plus "My works". Every step has buttons, nothing has to be typed unless it is the topic."""
from __future__ import annotations

import asyncio
import html
import logging
import re
import time

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup, Message
from aiogram.utils.chat_action import ChatActionSender

import keyboards as kb
import papers
import slides as sl
import tools
from config import Settings
from db import Database
from filters import NotAdminView
from i18n import LANGS, labels, t
from llm import Assistant, AssistantError
from wallet import give_back, spend, spent_line

log = logging.getLogger(__name__)

router = Router(name="orders")
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.message.filter(NotAdminView())
router.callback_query.filter(NotAdminView())

CANCEL = labels("cancel_btn")
NOT_MENU = ~(F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))     # the stored FSM state is stale after clear(), so exclude explicitly
KIND_EMOJI = {"course": "📘", "referat": "📄", "essay": "📝", "report": "🎤", "practice": "🏢", "thesis": "🎓"}
PURPOSES = ("defense", "talk", "business", "school")
SLIDE_COUNTS = (5, 8, 10, 12, 15, 20)
_running: set[int] = set()                         # one long job per user at a time


class Paper(StatesGroup):
    topic = State()
    volume = State()
    extra = State()


class SlidesFlow(StatesGroup):
    topic = State()
    count = State()


ANY_ORDER = StateFilter(Paper.topic, Paper.volume, Paper.extra, SlidesFlow.topic, SlidesFlow.count)


def btn(text: str, data: str) -> Btn:
    return Btn(text=text, callback_data=data)


def rows(buttons: list[Btn], per_row: int) -> list[list[Btn]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def pages(words: int) -> int:
    return max(1, round(words / papers.WORDS_PER_PAGE))


async def old(call: CallbackQuery, lang: str) -> None:
    await call.answer(t(lang, "order_old"), show_alert=True)


# ---------------------------------------------------------------- leaving
@router.message(ANY_ORDER, Command("cancel"))
@router.message(ANY_ORDER, F.text.in_(CANCEL))
async def cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "support_cancel"), reply_markup=kb.main_menu(lang))


@router.message(ANY_ORDER, F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))
async def leave(message: Message, state: FSMContext) -> None:
    await state.clear()                       # another command or menu button ends the order and runs normally
    raise SkipHandler


@router.callback_query(F.data == "oc:no")
async def order_cancel(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await call.answer()
    await call.message.answer(t(lang, "support_cancel"), reply_markup=kb.main_menu(lang))


# ================================================================ written works
def kinds_markup(lang: str) -> Markup:
    items = [btn(f"{KIND_EMOJI[k]} {t(lang, 'kind_' + k)}", f"pk:{k}") for k in papers.KINDS]
    return Markup(inline_keyboard=rows(items, 2) + [[btn("💬 " + t(lang, "kind_free"), "pk:free")]])


@router.message(Command("write"))
@router.message(F.text.in_(kb.BTN_WRITE))
async def paper_start(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "paper_start"), reply_markup=kinds_markup(lang))


@router.callback_query(F.data.startswith("pk:"))
async def pick_kind(call: CallbackQuery, state: FSMContext, db: Database, lang: str) -> None:
    kind = call.data.split(":")[1]
    await call.answer()
    if kind == "free":
        await state.clear()
        await db.set_mode(call.from_user.id, "writer")
        await call.message.answer(t(lang, "intro_writer"), reply_markup=kb.main_menu(lang))
        return
    if kind not in papers.KINDS:
        return
    await state.clear()
    await state.update_data(kind=kind)
    await state.set_state(Paper.topic)
    await call.message.answer(t(lang, "paper_topic"), reply_markup=kb.cancel_menu(lang))


@router.message(StateFilter(Paper.topic), F.text, NOT_MENU)
async def got_topic(message: Message, state: FSMContext, lang: str) -> None:
    topic = message.text.strip()
    if len(topic) < 3:
        await message.answer(t(lang, "paper_topic"))
        return
    await state.update_data(topic=topic[:400])
    order = [lang] + [c for c in LANGS if c != lang]
    await message.answer(t(lang, "paper_lang"), reply_markup=Markup(inline_keyboard=[[btn(LANGS[c], f"pl:{c}")] for c in order]))


@router.callback_query(F.data.startswith("pl:"))
async def pick_lang(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    d = await state.get_data()
    code = call.data.split(":")[1]
    if "kind" not in d or "topic" not in d or code not in LANGS:
        await old(call, lang)
        return
    await call.answer()
    await state.update_data(wlang=code)
    presets = papers.KINDS[d["kind"]][2]
    items = [btn(t(lang, "paper_volume_btn", a=a, b=b, p=f"{pages(a)}–{pages(b)}"), f"pv:{a}-{b}") for a, b in presets]
    await call.message.answer(t(lang, "paper_volume", wpp=papers.WORDS_PER_PAGE),
                              reply_markup=Markup(inline_keyboard=[[b] for b in items] + [[btn(t(lang, "btn_custom_volume"), "pv:custom")]]))


async def ask_standard(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(None)
    await target.answer(t(lang, "paper_std"), reply_markup=Markup(inline_keyboard=[[btn(t(lang, f"std_{s}"), f"ps:{s}") for s in ("gost", "apa", "none")]]))


@router.callback_query(F.data.startswith("pv:"))
async def pick_volume(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    d = await state.get_data()
    if "wlang" not in d:
        await old(call, lang)
        return
    await call.answer()
    arg = call.data.split(":")[1]
    if arg == "custom":
        await state.set_state(Paper.volume)
        await call.message.answer(t(lang, "paper_volume", wpp=papers.WORDS_PER_PAGE))
        return
    a, b = (int(x) for x in arg.split("-"))
    await state.update_data(wmin=a, wmax=b)
    await ask_standard(call.message, state, lang)


@router.message(StateFilter(Paper.volume), F.text, NOT_MENU)
async def got_volume(message: Message, state: FSMContext, lang: str) -> None:
    vol = papers.parse_volume(message.text)
    if not vol:
        await message.answer(t(lang, "paper_volume_bad"))
        return
    await state.update_data(wmin=vol[0], wmax=vol[1])
    await ask_standard(message, state, lang)


@router.callback_query(F.data.startswith("ps:"))
async def pick_standard(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    d = await state.get_data()
    std = call.data.split(":")[1]
    if "wmin" not in d or std not in papers.STANDARD:
        await old(call, lang)
        return
    await call.answer()
    await state.update_data(std=std)
    await state.set_state(Paper.extra)
    await call.message.answer(t(lang, "paper_extra"), reply_markup=Markup(inline_keyboard=[[btn(t(lang, "btn_skip"), "px:skip")]]))


async def show_confirm(target: Message, state: FSMContext, db: Database, settings: Settings, uid: int, lang: str) -> None:
    d = await state.get_data()
    await state.set_state(None)
    extra = d.get("extra", "")
    shown = html.escape(extra[:160] + ("…" if len(extra) > 160 else "")) if extra else t(lang, "order_none")
    price = settings.prices["paper"]
    await target.answer(
        t(lang, "paper_confirm", kind=t(lang, "kind_" + d["kind"]), topic=html.escape(d["topic"]), wlang=LANGS[d["wlang"]], wmin=d["wmin"], wmax=d["wmax"],
          pmin=pages(d["wmin"]), pmax=pages(d["wmax"]), std=t(lang, "std_" + d["std"]), extra=shown, price=price, balance=await db.balance(uid)),
        reply_markup=Markup(inline_keyboard=[[btn(t(lang, "btn_go", price=price), "pc:go")],
                                             [btn(t(lang, "btn_edit_order"), "pc:edit"), btn(t(lang, "btn_cancel_order"), "oc:no")]]))


@router.message(StateFilter(Paper.extra), F.text | F.document, NOT_MENU)
async def got_extra(message: Message, state: FSMContext, bot: Bot, db: Database, settings: Settings, lang: str) -> None:
    text = await tools.input_text(message, bot, lang)
    if not text:
        return
    await state.update_data(extra=text[:8000])
    await show_confirm(message, state, db, settings, message.from_user.id, lang)


@router.callback_query(F.data == "px:skip")
async def skip_extra(call: CallbackQuery, state: FSMContext, db: Database, settings: Settings, lang: str) -> None:
    d = await state.get_data()
    if "std" not in d:
        await old(call, lang)
        return
    await call.answer()
    await state.update_data(extra="")
    await show_confirm(call.message, state, db, settings, call.from_user.id, lang)


@router.callback_query(F.data == "pc:edit")
async def confirm_edit(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await call.answer()
    await call.message.answer(t(lang, "paper_start"), reply_markup=kinds_markup(lang))


@router.callback_query(F.data == "pc:go")
async def confirm_go(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database, ai: Assistant, settings: Settings, lang: str) -> None:
    d = await state.get_data()
    if "std" not in d:
        await old(call, lang)
        return
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=None)
    spec = papers.Spec(d["kind"], d["topic"], d["wlang"], d["wmin"], d["wmax"], d["std"], d.get("extra", ""))
    await state.clear()
    await run_paper(call.message, bot, db, ai, settings, call.from_user.id, lang, spec)


async def run_paper(message: Message, bot: Bot, db: Database, ai: Assistant, settings: Settings, uid: int, lang: str, spec: papers.Spec) -> None:
    if uid in _running:
        await message.answer(t(lang, "busy"))
        return
    _running.add(uid)
    try:
        kind = await spend(message, db, settings, uid, "paper", lang)
        if not kind:
            return
        status = await message.answer(t(lang, "paper_p_plan"), reply_markup=kb.main_menu(lang))
        last = {"text": ""}

        async def progress(done: int, total: int, stage: str) -> None:
            text = (t(lang, "paper_p_plan") if stage == "plan" else t(lang, "paper_p_write", done=done, total=total) if stage == "write"
                    else t(lang, "paper_p_expand") if stage == "expand" else t(lang, "paper_p_biblio"))
            if text != last["text"]:
                last["text"] = text
                try:
                    await status.edit_text(text)
                except TelegramBadRequest:
                    pass

        try:
            async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
                title, sections, biblio = await papers.generate(ai, spec, progress)
                data = await asyncio.to_thread(papers.build_docx, spec, title, sections, biblio)
        except Exception as e:
            await give_back(db, settings, uid, "paper", kind)
            if isinstance(e, AssistantError):
                await message.answer(f"⚠️ {t(lang, 'err_' + e.key)}\n{t(lang, 'refunded')}")
            else:
                log.exception("Paper failed")
                await message.answer(f"{t(lang, 'paper_fail')}\n{t(lang, 'refunded')}")
            return
        finally:
            try:
                await status.delete()
            except TelegramBadRequest:
                pass
        words = sum(papers.count_words(s.text) for s in sections)
        note = (t(lang, "range_ok", wmin=spec.wmin, wmax=spec.wmax) if spec.wmin <= words <= spec.wmax * 1.05
                else t(lang, "range_miss", wmin=spec.wmin, wmax=spec.wmax, words=words))
        await db.count_use(uid)
        cost = await spent_line(db, settings, uid, "paper", lang, kind)
        name = re.sub(r"[^\w\- ]+", "", title).strip()[:40].replace(" ", "_") or "work"
        sent = await message.answer_document(
            BufferedInputFile(data, filename=f"{name}.docx"),
            caption=t(lang, "paper_done", words=f"{words:,}".replace(",", " "), pages=pages(words), n=len(sections), range_note=note) + (f"\n<i>{cost}</i>" if cost else ""),
            reply_markup=kb.main_menu(lang))
        if sent.document:
            await db.add_work(uid, "paper", title, sent.document.file_id, words)
    finally:
        _running.discard(uid)


# ================================================================ presentations
@router.message(Command("slides"))
@router.message(F.text.in_(kb.BTN_SLIDES))
async def slides_start(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await state.set_state(SlidesFlow.topic)
    await message.answer(t(lang, "slides_intro"), reply_markup=kb.cancel_menu(lang))


def count_markup(lang: str) -> Markup:
    return Markup(inline_keyboard=rows([btn(str(n), f"sc:{n}") for n in SLIDE_COUNTS], 3) + [[btn(t(lang, "btn_other_number"), "sc:custom")]])


async def ask_purpose(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(None)
    await target.answer(t(lang, "slides_purpose"), reply_markup=Markup(inline_keyboard=rows([btn(t(lang, f"purpose_{p}"), f"sp:{p}") for p in PURPOSES], 2)))


@router.message(StateFilter(SlidesFlow.topic), F.text | F.document, NOT_MENU)
async def slides_topic(message: Message, state: FSMContext, bot: Bot, lang: str) -> None:
    topic = await tools.input_text(message, bot, lang)
    if topic is None:
        return
    if len(topic) < 4:
        await message.answer(t(lang, "slides_short"))
        return
    await state.update_data(topic=topic[:12000])
    m = re.search(r"(\d{1,2})\s*(?:слайд|slayd|slide|sl\b)", topic.lower())
    if m and 3 <= int(m.group(1)) <= 30:                  # the count was already in the message: skip the question
        await state.update_data(count=int(m.group(1)))
        await ask_purpose(message, state, lang)
        return
    await message.answer(t(lang, "slides_count"), reply_markup=count_markup(lang))


@router.callback_query(F.data.startswith("sc:"))
async def slides_count(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    d = await state.get_data()
    if "topic" not in d:
        await old(call, lang)
        return
    await call.answer()
    arg = call.data.split(":")[1]
    if arg == "custom":
        await state.set_state(SlidesFlow.count)
        await call.message.answer(t(lang, "slides_count_bad"))
        return
    await state.update_data(count=int(arg))
    await ask_purpose(call.message, state, lang)


@router.message(StateFilter(SlidesFlow.count), F.text, NOT_MENU)
async def slides_count_input(message: Message, state: FSMContext, lang: str) -> None:
    raw = message.text.strip()
    if not raw.isdigit() or not 3 <= int(raw) <= 30:
        await message.answer(t(lang, "slides_count_bad"))
        return
    await state.update_data(count=int(raw))
    await ask_purpose(message, state, lang)


@router.callback_query(F.data.startswith("sp:"))
async def slides_purpose(call: CallbackQuery, state: FSMContext, db: Database, settings: Settings, lang: str) -> None:
    d = await state.get_data()
    purpose = call.data.split(":")[1]
    if "count" not in d or purpose not in PURPOSES:
        await old(call, lang)
        return
    await call.answer()
    await state.update_data(purpose=purpose)
    topic = d["topic"].replace("\n", " ")
    await call.message.answer(
        t(lang, "slides_style", topic=html.escape(topic[:120] + ("…" if len(topic) > 120 else "")), count=d["count"], purpose=t(lang, f"purpose_{purpose}"),
          price=settings.prices["slides"], balance=await db.balance(call.from_user.id)),
        reply_markup=kb.theme_choice(lang))


@router.callback_query(F.data.startswith("st:"))
async def slides_go(call: CallbackQuery, state: FSMContext, bot: Bot, db: Database, ai: Assistant, settings: Settings, lang: str) -> None:
    d = await state.get_data()
    theme = call.data.split(":")[1]
    if "purpose" not in d or theme not in sl.THEMES:
        await old(call, lang)
        return
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=None)
    await state.clear()
    await run_slides(call.message, bot, db, ai, settings, call.from_user.id, lang, d["topic"], d["count"], d["purpose"], theme)


async def run_slides(message: Message, bot: Bot, db: Database, ai: Assistant, settings: Settings, uid: int, lang: str,
                     topic: str, count: int, purpose: str, theme: str) -> None:
    if uid in _running:
        await message.answer(t(lang, "busy"))
        return
    _running.add(uid)
    try:
        kind = await spend(message, db, settings, uid, "slides", lang)
        if not kind:
            return
        wait = await message.answer(t(lang, "slides_working"), reply_markup=kb.main_menu(lang))
        deck = None
        try:
            async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
                for _ in range(2):                                # one retry when the model's JSON is malformed
                    raw = await ai.complete(sl.outline_prompt(lang, count, purpose), f"Topic or source material:\n{topic[:12000]}", 6000)
                    try:
                        deck = sl.parse_deck(raw)
                        break
                    except (ValueError, TypeError):
                        log.warning("Slides: unparsable model output")
                if deck is None:
                    raise ValueError("no deck")
                try:                                              # second pass: an editor sharpens titles, bullets and notes
                    better = sl.parse_deck(await ai.complete(sl.refine_prompt(lang), sl.deck_to_json(deck), 6000))
                    if len(better.slides) >= len(deck.slides) - 1:
                        deck = better
                except (AssistantError, ValueError, TypeError):
                    log.warning("Slides: refinement skipped")
                data = await asyncio.to_thread(sl.build_pptx, deck, theme, lang)
        except Exception as e:
            await give_back(db, settings, uid, "slides", kind)
            if isinstance(e, AssistantError):
                await message.answer(f"⚠️ {t(lang, 'err_' + e.key)}\n{t(lang, 'refunded')}")
            else:
                log.exception("Slides failed")
                await message.answer(f"{t(lang, 'slides_fail')}\n{t(lang, 'refunded')}")
            return
        finally:
            try:
                await wait.delete()
            except TelegramBadRequest:
                pass
        await db.count_tool(uid, "slides")
        cost = await spent_line(db, settings, uid, "slides", lang, kind)
        name = re.sub(r"[^\w\- ]+", "", deck.title).strip()[:40].replace(" ", "_") or "presentation"
        if len(tools._decks) >= tools.MAX_DECKS:
            tools._decks.pop(next(iter(tools._decks)))
        tools._decks[uid] = (sl.deck_to_json(deck), name)
        sent = await message.answer_document(BufferedInputFile(data, filename=f"{name}.pptx"),
                                             caption=t(lang, "slides_done", n=len(deck.slides)) + (f"\n{cost}" if cost else ""),
                                             reply_markup=kb.theme_buttons(lang, theme))
        await message.answer(t(lang, "slides_restyle"), reply_markup=kb.main_menu(lang))
        if sent.document:
            await db.add_work(uid, "slides", deck.title, sent.document.file_id, len(deck.slides))
    finally:
        _running.discard(uid)


# ================================================================ my works
@router.message(Command("works"))
@router.message(F.text.in_(kb.BTN_WORKS))
async def my_works(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    await state.clear()
    works = await db.recent_works(message.from_user.id, 10)
    if not works:
        await message.answer(t(lang, "works_empty"))
        return
    unit = {"paper": {"ru": "слов", "uz": "so'z", "en": "words"}, "slides": {"ru": "слайдов", "uz": "slayd", "en": "slides"}}
    items = []
    for w in works:
        label = f"{'📄' if w['kind'] == 'paper' else '📊'} {w['title'][:28]} · {w['size']} {unit[w['kind']].get(lang, 'words')} · {time.strftime('%d.%m', time.gmtime(w['created']))}"
        items.append([btn(label, f"wk:{w['id']}")])
    await message.answer(t(lang, "works_title"), reply_markup=Markup(inline_keyboard=items))


@router.callback_query(F.data.startswith("wk:"))
async def download_work(call: CallbackQuery, db: Database, lang: str) -> None:
    w = await db.get_work(int(call.data.split(":")[1]), call.from_user.id)
    if not w:
        await call.answer(t(lang, "works_gone"), show_alert=True)
        return
    await call.answer()
    try:
        await call.message.answer_document(w["file_id"])
    except TelegramBadRequest:
        await call.message.answer(t(lang, "works_gone"))
