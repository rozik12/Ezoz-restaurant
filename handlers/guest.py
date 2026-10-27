"""Guest features: halls, menu PDF, step-by-step cost calculator, date booking, contacts."""
from __future__ import annotations

import html
import re
from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, ReplyKeyboardRemove

import keyboards as kb
from config import settings
from db import Database
from handlers.common import show, show_main_menu
from i18n import fmt_date, fmt_date_short, money, t
from services import pricing
from services.notify import notify_staff
from states import BookingStates, CalcStates

router = Router(name="guest")
router.message.filter(F.chat.type == ChatType.PRIVATE)

PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{7,17}\d$")


# =========================== halls ===========================
@router.callback_query(F.data == "g:halls")
async def halls(call: CallbackQuery, lang: str) -> None:
    await show(call, t(lang, "halls_title"), kb.halls_kb(lang))


@router.callback_query(F.data.startswith("g:hall:"))
async def hall_detail(call: CallbackQuery, db: Database, lang: str) -> None:
    key = call.data.split(":")[2]
    if key not in pricing.HALL_UZS_KEYS:
        await call.answer()
        return
    await db.record_event("tour_viewed", call.from_user.id)
    # PLACEHOLDER: send real photos/videos here, e.g. bot.send_media_group(chat_id, [InputMediaPhoto(file_id), ...])
    # with Telegram file_ids you collect once, or link the website's virtual tour (WEBSITE_URL).
    await show(call, t(lang, "hall_card", name=t(lang, f"hall_{key}"), cap=t(lang, f"cap_{key}"),
                       blurb=t(lang, f"blurb_{key}")), kb.hall_detail_kb(lang))


# =========================== menu PDF ===========================
@router.callback_query(F.data == "g:menu")
async def menu_pdf(call: CallbackQuery, db: Database, lang: str) -> None:
    await call.answer()
    path = settings.menu_pdf_path
    if not path.is_file():
        await call.message.answer(t(lang, "menu_missing"), reply_markup=kb.calc_result_kb(lang))
        return
    await db.record_event("menu_downloaded", call.from_user.id)
    await call.message.answer_document(FSInputFile(path, filename="Ezoz_Menu_and_Pricing.pdf"),
                                       caption=t(lang, "menu_caption"))
    await call.message.answer(t(lang, "what_next"), reply_markup=kb.calc_result_kb(lang))


# =========================== calculator ===========================
@router.callback_query(F.data == "g:calc")
async def calc_start(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(CalcStates.guests)
    await state.update_data(calc={})
    await show(call, t(lang, "calc_g", min=pricing.MIN_GUESTS, max=pricing.MAX_GUESTS), kb.guests_kb(lang))


async def _ask_tier(event: Message | CallbackQuery, state: FSMContext, guests: int, lang: str) -> None:
    await state.update_data(calc={"guests": guests, "addons": []})
    await state.set_state(CalcStates.tier)
    await show(event, t(lang, "calc_t", guests=guests), kb.tier_kb(lang))


@router.callback_query(CalcStates.guests, F.data.startswith("calc:g:"))
async def calc_guests_btn(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await _ask_tier(call, state, int(call.data.split(":")[2]), lang)


@router.message(CalcStates.guests, F.text)
async def calc_guests_text(message: Message, state: FSMContext, lang: str) -> None:
    txt = message.text.strip()
    if not txt.isdigit() or not pricing.MIN_GUESTS <= int(txt) <= pricing.MAX_GUESTS:
        await message.answer(t(lang, "calc_g_bad", min=pricing.MIN_GUESTS, max=pricing.MAX_GUESTS))
        return
    await _ask_tier(message, state, int(txt), lang)


@router.callback_query(CalcStates.tier, F.data.startswith("calc:t:"))
async def calc_tier(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    tier = call.data.split(":")[2]
    if tier not in pricing.PER_GUEST_UZS:
        await call.answer()
        return
    calc = (await state.get_data())["calc"] | {"tier": tier}
    await state.update_data(calc=calc)
    await state.set_state(CalcStates.addons)
    await show(call, t(lang, "calc_a"), kb.addons_kb(lang, calc["addons"]))


@router.callback_query(CalcStates.addons, F.data.startswith("calc:a:"))
async def calc_toggle_addon(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    key = call.data.split(":")[2]
    calc = (await state.get_data())["calc"]
    if key in pricing.ADDON_UZS:
        calc["addons"] = [a for a in calc["addons"] if a != key] if key in calc["addons"] else calc["addons"] + [key]
        await state.update_data(calc=calc)
    await show(call, t(lang, "calc_a"), kb.addons_kb(lang, calc["addons"]))


@router.callback_query(CalcStates.addons, F.data == "calc:done")
async def calc_done(call: CallbackQuery, state: FSMContext, db: Database, lang: str) -> None:
    calc = (await state.get_data())["calc"]
    est = pricing.estimate(calc["guests"], calc["tier"], calc["addons"])
    await state.update_data(calc=calc | {"total": est.total})
    await state.set_state(None)          # keep the data so "Book a date" can attach the estimate
    await db.record_event("calc_completed", call.from_user.id)
    lines = [f"{t(lang, 'calc_menu', tier=t(lang, 'tier_' + est.tier), guests=est.guests)}: <b>{money(lang, est.menu)}</b>",
             f"{t(lang, 'calc_hall', hall=t(lang, 'hall_' + est.hall))}: <b>{money(lang, est.hall_fee)}</b>"]
    lines += [f"✨ {t(lang, 'addon_' + a)}: <b>{money(lang, pricing.ADDON_UZS[a])}</b>" for a in est.addons]
    text = "\n".join([
        t(lang, "calc_title"), *lines, "",
        t(lang, "calc_total", total=money(lang, est.total)),
        t(lang, "calc_range", lo=money(lang, est.total * 0.93), hi=money(lang, est.total * 1.07),
          per=money(lang, est.total / est.guests)),
        "", t(lang, "calc_note"),
    ])
    await show(call, text, kb.calc_result_kb(lang))


# =========================== contacts ===========================
@router.callback_query(F.data == "g:contacts")
async def contacts(call: CallbackQuery, lang: str) -> None:
    parts = [t(lang, "contacts_title")]
    if settings.address:
        parts.append(t(lang, "contacts_addr", v=html.escape(settings.address)))
    if settings.phone:
        parts.append(t(lang, "contacts_phone", v=html.escape(settings.phone)))
    parts += ["", t(lang, "contacts_cta")]
    await show(call, "\n".join(parts), kb.contacts_kb(lang))


# =========================== booking ===========================
def parse_date(text: str) -> date | None:
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


@router.callback_query(F.data == "g:book")
async def book_start(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(BookingStates.date)
    await show(call, t(lang, "book_date"), kb.back_home(lang))


@router.callback_query(F.data == "g:book_prefill")
async def book_prefill(call: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    pre = data.get("prefill")
    if not pre:
        await book_start(call, state, lang)
        return
    await state.update_data(event_date=pre["date"], calc=data.get("calc") or {"guests": pre["guests"]})
    await _ask_phone(call, state, lang)


@router.message(BookingStates.date, F.text)
async def book_date(message: Message, state: FSMContext, lang: str) -> None:
    d = parse_date(message.text)
    if d is None:
        await message.answer(t(lang, "book_date_bad"))
        return
    if d < date.today() or (d - date.today()).days > 730:
        await message.answer(t(lang, "book_date_range"))
        return
    await state.update_data(event_date=d.isoformat())
    await _ask_phone(message, state, lang)


async def _ask_phone(event: Message | CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(BookingStates.phone)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer(t(lang, "book_phone"), reply_markup=kb.phone_kb(lang))


@router.message(BookingStates.phone, F.contact)
async def book_phone_contact(message: Message, state: FSMContext, bot: Bot, db: Database, lang: str) -> None:
    if message.contact.user_id != message.from_user.id:
        await message.answer(t(lang, "book_phone_not_own"))
        return
    await _finish_booking(message, state, bot, db, lang, message.contact.phone_number)


@router.message(BookingStates.phone, F.text)
async def book_phone_text(message: Message, state: FSMContext, bot: Bot, db: Database, lang: str) -> None:
    if not PHONE_RE.match(message.text.strip()):
        await message.answer(t(lang, "book_phone_bad"))
        return
    await _finish_booking(message, state, bot, db, lang, message.text.strip())


async def _finish_booking(message: Message, state: FSMContext, bot: Bot, db: Database, lang: str, phone: str) -> None:
    data = await state.get_data()
    calc = data.get("calc") or {}
    user = message.from_user
    event_date = date.fromisoformat(data["event_date"])
    lead_id = await db.add_lead(
        user_id=user.id, name=user.full_name, username=user.username, phone=phone,
        event_date=event_date.isoformat(), guests=calc.get("guests"), tier=calc.get("tier"),
        estimate_uzs=calc.get("total"), lang=lang,
    )

    # Staff notifications are always written in ADMIN_LANG so the working chat reads consistently.
    al = settings.admin_lang
    lines = [t(al, "lead_title", id=lead_id),
             f"👤 <a href=\"tg://user?id={user.id}\">{html.escape(user.full_name)}</a>"
             + (f" (@{html.escape(user.username)})" if user.username else ""),
             f"📞 {html.escape(phone)}",
             f"📅 {fmt_date(al, event_date)}"]
    if calc.get("guests"):
        tier = t(al, "tier_" + calc["tier"]) if calc.get("tier") else t(al, "lead_tier_none")
        lines.append(t(al, "lead_guests", guests=calc["guests"], tier=tier))
    if calc.get("total"):
        lines.append(t(al, "lead_estimate", total=money(al, calc["total"])))
    lines.append(t(al, "lead_lang", code=lang.upper()))
    await notify_staff(bot, db, "\n".join(lines))        # forwarded instantly to the administrators' working chat

    await state.clear()
    await message.answer(t(lang, "book_done", date=fmt_date(lang, event_date), phone=html.escape(phone)),
                         reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message, db, lang)
