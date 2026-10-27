"""Guest features: halls, menu PDF, step-by-step cost calculator, date booking."""
from __future__ import annotations

import html
import re
from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, ReplyKeyboardRemove

import keyboards as kb
from config import settings
from db import Database
from handlers.common import show, show_main_menu
from services import pricing
from states import BookingStates, CalcStates
from services.notify import notify_staff

router = Router(name="guest")
router.message.filter(F.chat.type == ChatType.PRIVATE)

HALLS = {
    "ballroom": ("Grand Ballroom", "200 to 500 guests",
                 "The main hall: chandeliers, a raised presidium for the couple, a wide dance floor and a full show stage."),
    "vip": ("VIP Hall", "50 to 120 guests",
            "A private hall with its own entrance and lounge, for engagements, family evenings and smaller weddings."),
    "terrace": ("Summer Terrace", "80 to 250 guests",
                "An open-air garden terrace under string lights, with a floral ceremony arch and a fire lounge. Summer season."),
}
PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{7,17}\d$")


# =========================== halls ===========================
@router.callback_query(F.data == "g:halls")
async def halls(call: CallbackQuery) -> None:
    await show(call, "🏛 <b>Our halls</b>\nChoose a hall to see details.", kb.halls_kb())


@router.callback_query(F.data.startswith("g:hall:"))
async def hall_detail(call: CallbackQuery, db: Database) -> None:
    key = call.data.split(":")[2]
    if key not in HALLS:
        await call.answer()
        return
    name, cap, blurb = HALLS[key]
    await db.record_event("tour_viewed", call.from_user.id)
    # PLACEHOLDER: send real photos/videos here, e.g. bot.send_media_group(chat_id, [InputMediaPhoto(file_id), ...])
    # using Telegram file_ids you collect once and store, or link the website's virtual tour (WEBSITE_URL).
    await show(call, f"🏛 <b>{name}</b>\n<i>{cap}</i>\n\n{blurb}", kb.hall_detail_kb())


# =========================== menu PDF ===========================
@router.callback_query(F.data == "g:menu")
async def menu_pdf(call: CallbackQuery, db: Database) -> None:
    await call.answer()
    path = settings.menu_pdf_path
    if not path.is_file():
        await call.message.answer("The menu PDF is being updated. Please try again soon, or book a date and a manager will send it.",
                                  reply_markup=kb.guest_menu())
        return
    await db.record_event("menu_downloaded", call.from_user.id)
    await call.message.answer_document(FSInputFile(path, filename="Ezoz_Menu_and_Pricing.pdf"),
                                       caption="📄 E'zoz banquet menu and pricing.")
    await call.message.answer("What next?", reply_markup=kb.calc_result_kb())


# =========================== calculator ===========================
@router.callback_query(F.data == "g:calc")
async def calc_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CalcStates.guests)
    await state.update_data(calc={})
    await show(call, f"🧮 <b>Cost calculator</b>\n\nStep 1 of 3. How many guests?\nPick a number or type any value from "
                     f"{pricing.MIN_GUESTS} to {pricing.MAX_GUESTS}.", kb.guests_kb())


async def _ask_tier(event: Message | CallbackQuery, state: FSMContext, guests: int) -> None:
    await state.update_data(calc={"guests": guests, "addons": []})
    await state.set_state(CalcStates.tier)
    await show(event, f"Step 2 of 3. Choose a menu for <b>{guests}</b> guests:", kb.tier_kb())


@router.callback_query(CalcStates.guests, F.data.startswith("calc:g:"))
async def calc_guests_btn(call: CallbackQuery, state: FSMContext) -> None:
    await _ask_tier(call, state, int(call.data.split(":")[2]))


@router.message(CalcStates.guests, F.text)
async def calc_guests_text(message: Message, state: FSMContext) -> None:
    txt = message.text.strip()
    if not txt.isdigit() or not pricing.MIN_GUESTS <= int(txt) <= pricing.MAX_GUESTS:
        await message.answer(f"Please send a whole number from {pricing.MIN_GUESTS} to {pricing.MAX_GUESTS}.")
        return
    await _ask_tier(message, state, int(txt))


@router.callback_query(CalcStates.tier, F.data.startswith("calc:t:"))
async def calc_tier(call: CallbackQuery, state: FSMContext) -> None:
    tier = call.data.split(":")[2]
    if tier not in pricing.PER_GUEST_UZS:
        await call.answer()
        return
    calc = (await state.get_data())["calc"] | {"tier": tier}
    await state.update_data(calc=calc)
    await state.set_state(CalcStates.addons)
    await show(call, "Step 3 of 3. Add anything extra, then show your estimate:", kb.addons_kb(calc["addons"]))


@router.callback_query(CalcStates.addons, F.data.startswith("calc:a:"))
async def calc_toggle_addon(call: CallbackQuery, state: FSMContext) -> None:
    key = call.data.split(":")[2]
    calc = (await state.get_data())["calc"]
    if key in pricing.ADDON_UZS:
        calc["addons"] = [a for a in calc["addons"] if a != key] if key in calc["addons"] else calc["addons"] + [key]
        await state.update_data(calc=calc)
    await show(call, "Step 3 of 3. Add anything extra, then show your estimate:", kb.addons_kb(calc["addons"]))


@router.callback_query(CalcStates.addons, F.data == "calc:done")
async def calc_done(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    calc = (await state.get_data())["calc"]
    est = pricing.estimate(calc["guests"], calc["tier"], calc["addons"])
    await state.update_data(calc=calc | {"total": est.total})
    await state.set_state(None)          # keep the data so "Book a date" can attach the estimate
    await db.record_event("calc_completed", call.from_user.id)
    lines = [f"Menu · {pricing.TIER_LABEL[est.tier]} × {est.guests}: {pricing.fmt_uzs(est.menu)}",
             f"Hall · {pricing.HALL_LABEL[est.hall]}: {pricing.fmt_uzs(est.hall_fee)}"]
    lines += [f"{pricing.ADDON_LABEL[a]}: {pricing.fmt_uzs(pricing.ADDON_UZS[a])}" for a in est.addons]
    await show(call,
               "🧮 <b>Your estimate</b>\n\n" + "\n".join(lines) +
               f"\n\n💰 <b>About {pricing.fmt_uzs(est.total)}</b>\n"
               f"({pricing.fmt_uzs(est.total * 0.93)} to {pricing.fmt_uzs(est.total * 1.07)}, "
               f"{pricing.fmt_uzs(est.total / est.guests)} per guest)\n\n"
               "<i>Approximate. A manager confirms the final quote after choosing the date and hall.</i>",
               kb.calc_result_kb())


# =========================== booking ===========================
def parse_date(text: str) -> date | None:
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


@router.callback_query(F.data == "g:book")
async def book_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingStates.date)
    await show(call, "📅 <b>Book a date</b>\n\nSend your preferred date as <code>DD.MM.YYYY</code>, for example "
                     "<code>12.09.2026</code>.\nSend /cancel to stop.", kb.back_home())


@router.callback_query(F.data == "g:book_prefill")
async def book_prefill(call: CallbackQuery, state: FSMContext) -> None:
    pre = (await state.get_data()).get("prefill")
    if not pre:
        await book_start(call, state)
        return
    await state.update_data(event_date=pre["date"])
    await state.update_data(calc=(await state.get_data()).get("calc") or {"guests": pre["guests"]})
    await _ask_phone(call, state)


@router.message(BookingStates.date, F.text)
async def book_date(message: Message, state: FSMContext) -> None:
    d = parse_date(message.text)
    if d is None:
        await message.answer("I could not read that date. Please use <code>DD.MM.YYYY</code>.")
        return
    if d < date.today() or (d - date.today()).days > 730:
        await message.answer("Please choose a date from today up to two years ahead.")
        return
    await state.update_data(event_date=d.isoformat())
    await _ask_phone(message, state)


async def _ask_phone(event: Message | CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingStates.phone)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer("Thank you. Now share your phone number so a manager can call you.",
                     reply_markup=kb.phone_kb())


@router.message(BookingStates.phone, F.contact)
async def book_phone_contact(message: Message, state: FSMContext, bot: Bot, db: Database) -> None:
    if message.contact.user_id != message.from_user.id:
        await message.answer("Please share your own number using the button, or type it.")
        return
    await _finish_booking(message, state, bot, db, message.contact.phone_number)


@router.message(BookingStates.phone, F.text)
async def book_phone_text(message: Message, state: FSMContext, bot: Bot, db: Database) -> None:
    if not PHONE_RE.match(message.text.strip()):
        await message.answer("That does not look like a phone number. Example: <code>+998 90 123 45 67</code>")
        return
    await _finish_booking(message, state, bot, db, message.text.strip())


async def _finish_booking(message: Message, state: FSMContext, bot: Bot, db: Database, phone: str) -> None:
    data = await state.get_data()
    calc = data.get("calc") or {}
    user = message.from_user
    event_date = date.fromisoformat(data["event_date"])
    lead_id = await db.add_lead(
        user_id=user.id, name=user.full_name, username=user.username, phone=phone,
        event_date=event_date.isoformat(), guests=calc.get("guests"), tier=calc.get("tier"),
        estimate_uzs=calc.get("total"),
    )
    lines = [f"🔔 <b>New booking request #{lead_id}</b>",
             f"👤 <a href=\"tg://user?id={user.id}\">{html.escape(user.full_name)}</a>"
             + (f" (@{html.escape(user.username)})" if user.username else ""),
             f"📞 {html.escape(phone)}",
             f"📅 {event_date:%a, %d %b %Y}"]
    if calc.get("guests"):
        tier = pricing.TIER_LABEL.get(calc.get("tier", ""), "not chosen")
        lines.append(f"👥 About {calc['guests']} guests · menu: {tier}")
    if calc.get("total"):
        lines.append(f"💰 Estimate: {pricing.fmt_uzs(calc['total'])}")
    await notify_staff(bot, db, "\n".join(lines))        # forwarded instantly to the administrators' working chat

    await state.clear()
    await message.answer("✅ <b>Request received.</b>\nA manager will contact you shortly to confirm the date.",
                         reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message, db)
