"""Wallet in Telegram Stars: balance, top-up of any amount (Stars invoice, Click/Payme, card transfer), charging for actions."""
from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message,
                           PreCheckoutQuery)

import keyboards as kb
from filters import NotAdminView
from config import Settings
from db import Database
from i18n import DEFAULT_LANG, labels, t
from support import admin_chat_ids

log = logging.getLogger(__name__)

router = Router(name="wallet")
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.message.filter(NotAdminView())
router.callback_query.filter(NotAdminView())

CANCEL = labels("cancel_btn")
NOT_MENU = ~(F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))     # the stored FSM state is stale after clear(), so exclude explicitly


class Wallet(StatesGroup):
    amount = State()        # data: method = xtr | card | payp
    receipt = State()       # data: stars


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


# ---------------------------------------------------------------- charging, used by the other routers
async def spend(target: Message, db: Database, settings: Settings, uid: int, action: str, lang: str) -> str | None:
    """Pays for one action: a free action while the user has any left, then the wallet.
    Returns "free" or "paid", or None after offering the top-up when the balance is short."""
    if await db.use_free(uid, settings.free_actions):
        return "free"
    price = settings.prices[action]
    if price <= 0 or await db.charge(uid, price, "charge", action):
        return "paid"
    bal = await db.balance(uid)
    await target.answer(t(lang, "need_funds", price=price, balance=bal), reply_markup=kb.topup_markup(lang, settings, missing=price - bal))
    return None


async def give_back(db: Database, settings: Settings, uid: int, action: str, kind: str = "paid") -> None:
    """Returns what an action that failed had cost."""
    if kind == "free":
        await db.return_free(uid)
    elif settings.prices[action] > 0:
        await db.credit(uid, settings.prices[action], "refund", action)


async def spent_line(db: Database, settings: Settings, uid: int, action: str, lang: str, kind: str = "paid") -> str:
    if kind == "free":
        return t(lang, "free_line", left=max(0, settings.free_actions - await db.free_used(uid)))
    price = settings.prices[action]
    return t(lang, "spent_line", n=price, balance=await db.balance(uid)) if price > 0 else ""


# ---------------------------------------------------------------- the wallet screen
@router.message(Command("wallet"))
@router.message(Command("balance"))
@router.message(Command("subscribe"))
@router.message(F.text.in_(kb.BTN_SUB))
async def wallet(message: Message, state: FSMContext, db: Database, settings: Settings, lang: str) -> None:
    await state.clear()
    bal = await db.balance(message.from_user.id)
    p = settings.prices
    left = max(0, settings.free_actions - await db.free_used(message.from_user.id))
    free_line = t(lang, "wallet_free_line", free=left) if settings.free_actions > 0 else ""
    await message.answer(t(lang, "wallet_text", balance=bal, n=bal // p["chat"] if p["chat"] else bal, free_line=free_line,
                           chat=p["chat"], paper=p["paper"], slides=p["slides"], detect=p["detect"], convert=p["convert"]),
                         reply_markup=kb.topup_markup(lang, settings))


@router.message(Command("stars"))
async def stars_howto(message: Message, lang: str) -> None:
    await message.answer(t(lang, "stars_howto"))


@router.callback_query(F.data == "stars:how")
async def stars_howto_btn(call: CallbackQuery, lang: str) -> None:
    await call.answer()
    await call.message.answer(t(lang, "stars_howto"))


# ---------------------------------------------------------------- top-up with Stars
async def stars_invoice(target: Message, settings: Settings, uid: int, lang: str, n: int) -> None:
    await target.answer_invoice(
        title=t(lang, "top_title", n=n), description=t(lang, "top_desc"), payload=f"top:{uid}", currency="XTR",
        prices=[LabeledPrice(label=t(lang, "top_label", n=n), amount=n)], provider_token="")


async def provider_invoice(target: Message, settings: Settings, uid: int, lang: str, n: int) -> None:
    """Click / Payme through a Telegram payment provider: billed in so'm, amounts in tiyin."""
    await target.answer_invoice(
        title=t(lang, "top_title", n=n), description=t(lang, "top_desc"), payload=f"topu:{uid}:{n}", currency="UZS",
        provider_token=settings.provider_token,
        prices=[LabeledPrice(label=t(lang, "top_label", n=n), amount=n * settings.uzs_per_star * 100)])


@router.callback_query(F.data.regexp(r"^top:\d+$"))
async def top_preset(call: CallbackQuery, settings: Settings, lang: str) -> None:
    n = int(call.data.split(":")[1])
    await call.answer()
    if 1 <= n <= settings.topup_max:
        await stars_invoice(call.message, settings, call.from_user.id, lang, n)


@router.callback_query(F.data.in_({"top:custom", "topm:card", "topm:payp"}))
async def ask_amount(call: CallbackQuery, state: FSMContext, settings: Settings, lang: str) -> None:
    method = {"top:custom": "xtr", "topm:card": "card", "topm:payp": "payp"}[call.data]
    await call.answer()
    if (method == "card" and not settings.card_ready) or (method == "payp" and not settings.provider_ready):
        return
    await state.set_state(Wallet.amount)
    await state.update_data(method=method)
    key = "top_ask" if method == "xtr" else "card_ask"
    await call.message.answer(t(lang, key, max=settings.topup_max, rate=fmt(settings.uzs_per_star)), reply_markup=kb.cancel_menu(lang))


@router.message(StateFilter(Wallet.amount, Wallet.receipt), Command("cancel"))
@router.message(StateFilter(Wallet.amount, Wallet.receipt), F.text.in_(CANCEL))
async def cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "support_cancel"), reply_markup=kb.main_menu(lang))


@router.message(StateFilter(Wallet.amount, Wallet.receipt), F.text.startswith("/") | F.text.in_(kb.MENU_LABELS))
async def leave(message: Message, state: FSMContext) -> None:
    await state.clear()                      # another command or menu button leaves the dialog and runs normally
    raise SkipHandler


@router.message(StateFilter(Wallet.amount), NOT_MENU)
async def got_amount(message: Message, state: FSMContext, settings: Settings, lang: str) -> None:
    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit() or not 1 <= int(raw) <= settings.topup_max:
        await message.answer(t(lang, "top_bad", max=settings.topup_max))
        return
    n = int(raw)
    method = (await state.get_data()).get("method", "xtr")
    await state.clear()
    uid = message.from_user.id
    if method == "payp" and settings.provider_ready:
        await message.answer("👇", reply_markup=kb.main_menu(lang))
        await provider_invoice(message, settings, uid, lang, n)
    elif method == "card" and settings.card_ready:
        holder = t(lang, "card_holder_line", name=html.escape(settings.card_holder)) if settings.card_holder else ""
        await message.answer(t(lang, "card_text", amount=fmt(n * settings.uzs_per_star), stars=n, card=html.escape(settings.card_number), holder=holder),
                             reply_markup=kb.card_paid_button(lang, n))
        await message.answer("👇", reply_markup=kb.main_menu(lang))
    else:
        await message.answer("👇", reply_markup=kb.main_menu(lang))
        await stars_invoice(message, settings, uid, lang, n)


def parse_payload(payload: str) -> tuple[str, int, int] | None:
    """('top', uid, 0) for Stars, ('topu', uid, stars) for so'm; None when malformed."""
    parts = payload.split(":")
    try:
        if parts[0] == "top" and len(parts) == 2:
            return "top", int(parts[1]), 0
        if parts[0] == "topu" and len(parts) == 3:
            return "topu", int(parts[1]), int(parts[2])
    except ValueError:
        pass
    return None


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, settings: Settings, db: Database) -> None:
    info = parse_payload(query.invoice_payload)
    ok = False
    if info and info[1] == query.from_user.id:
        kind, _, stars = info
        if kind == "top":
            ok = query.currency == "XTR" and 1 <= query.total_amount <= settings.topup_max
        else:
            ok = (query.currency == "UZS" and settings.provider_ready and 1 <= stars <= settings.topup_max
                  and query.total_amount == stars * settings.uzs_per_star * 100)
    lang = await db.get_lang(query.from_user.id) or DEFAULT_LANG
    await query.answer(ok=ok, error_message=None if ok else t(lang, "bad_invoice"))


@router.message(F.successful_payment)
async def paid(message: Message, db: Database, settings: Settings, lang: str) -> None:
    p = message.successful_payment
    info = parse_payload(p.invoice_payload)
    if not info or info[1] != message.from_user.id or await db.payment_exists(p.telegram_payment_charge_id):    # Telegram may redeliver
        return
    stars = p.total_amount if info[0] == "top" else info[2]
    await db.add_payment(message.from_user.id, p.telegram_payment_charge_id, p.total_amount if info[0] == "top" else 0, 0)
    balance = await db.credit(message.from_user.id, stars, "topup" if info[0] == "top" else "topup_uzs", p.telegram_payment_charge_id)
    log.info("Wallet top-up by %s: %s Stars (%s)", message.from_user.id, stars, p.currency)
    await message.answer(t(lang, "top_ok", n=stars, balance=balance), reply_markup=kb.main_menu(lang))


# ---------------------------------------------------------------- top-up by card transfer: the receipt goes to the administrators
@router.callback_query(F.data.regexp(r"^card:paid:\d+$"))
async def card_paid(call: CallbackQuery, state: FSMContext, db: Database, settings: Settings, lang: str) -> None:
    await call.answer()
    stars = int(call.data.split(":")[2])
    if not settings.card_ready or not 1 <= stars <= settings.topup_max:
        return
    if await db.pending_card_payments_of(call.from_user.id):
        await call.message.answer(t(lang, "card_pending"))
        return
    await state.set_state(Wallet.receipt)
    await state.update_data(stars=stars)
    await call.message.answer(t(lang, "card_send"), reply_markup=kb.cancel_menu(lang))


@router.message(StateFilter(Wallet.receipt), NOT_MENU)
async def receipt(message: Message, state: FSMContext, bot: Bot, db: Database, settings: Settings, lang: str) -> None:
    doc = message.document
    if not (message.photo or (doc and (doc.mime_type or "").startswith(("image/", "application/pdf")))):
        await message.answer(t(lang, "card_need_photo"))
        return
    stars = int((await state.get_data()).get("stars", 0))
    await state.clear()
    if not stars:
        return
    u = message.from_user
    pid = await db.create_card_payment(u.id, stars, message.chat.id, message.message_id)
    head = (f"💳 <b>Пополнение картой, заявка #{pid}</b>\n"
            f"От: {html.escape(u.full_name)}" + (f" (@{html.escape(u.username)})" if u.username else "") +
            f"\nID: <code>{u.id}</code>\nСумма: {fmt(stars * settings.uzs_per_star)} сум → {stars} ⭐\n"
            "Сверьте сумму и получателя в чеке и подтвердите.")
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"✅ Зачислить {stars} ⭐", callback_data=f"cp:ok:{pid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"cp:no:{pid}")]])
    for admin_id in await admin_chat_ids(db, settings):
        try:
            await bot.send_message(admin_id, head, reply_markup=markup)
            await bot.copy_message(admin_id, message.chat.id, message.message_id)
        except Exception:
            log.warning("Could not notify admin %s about card payment %s", admin_id, pid)
    await message.answer(t(lang, "card_received", id=pid), reply_markup=kb.main_menu(lang))
