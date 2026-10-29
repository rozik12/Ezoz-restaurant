"""All Telegram handlers: menu and modes, chat with the assistant, files, Stars subscription, admin tools."""
from __future__ import annotations

import asyncio
import html
import logging
import time
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, ReplyKeyboardRemove
from aiogram.utils.chat_action import ChatActionSender

import keyboards as kb
from config import Settings
from db import Database
from docs import MAX_FILE_BYTES, UnsupportedFile, extract_text
from fmt import md_to_html, split_markdown
from llm import Assistant, AssistantError

log = logging.getLogger(__name__)

router = Router(name="main")
router.message.filter(F.chat.type == ChatType.PRIVATE)

MAX_INPUT_CHARS = 12_000
_locks: dict[int, asyncio.Lock] = {}          # one running request per user, so history stays in order

WELCOME = ("👋 <b>Привет! Я OmniStudent</b>, академический помощник для студентов.\n\n"
           "✍️ пишу курсовые, рефераты, эссе и планы работ\n"
           "🧮 решаю задачи и пишу код с пошаговым объяснением\n"
           "📝 редактирую, делаю рерайт и перевожу научные тексты\n"
           "🎓 делаю шпаргалки и устраиваю «Вредного преподавателя» перед защитой\n\n"
           "Выберите режим в меню или просто напишите вопрос. Файлы .txt, .pdf и .docx тоже читаю.")

DEFAULT_FILE_TASK = {
    "cheat": "Сделай из этого материала краткую шпаргалку: определения, формулы, ключевые мысли.",
    "editor": "Проверь текст: исправь ошибки, улучши стиль и логику. Коротко перечисли, что изменил.",
    "exam": "Прочитай работу и начни экзамен: задай первый каверзный вопрос по ней.",
}


def _lock(user_id: int) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _fmt_until(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d.%m.%Y")


async def send_answer(message: Message, text: str) -> None:
    """Sends a long Markdown answer as several HTML messages; falls back to plain text if Telegram rejects the markup."""
    for chunk in split_markdown(text):
        try:
            await message.answer(md_to_html(chunk), parse_mode="HTML", disable_web_page_preview=True)
        except TelegramBadRequest:
            await message.answer(chunk, parse_mode=None, disable_web_page_preview=True)


# =========================== start, help, menu ===========================
@router.message(CommandStart())
async def start(message: Message, db: Database) -> None:
    u = message.from_user
    await db.touch_user(u.id, u.username, u.full_name)
    await message.answer(WELCOME, reply_markup=kb.main_menu())


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(
        "<b>Команды</b>\n/start главное меню\n/new начать новый диалог (забыть контекст)\n"
        "/subscribe подписка за Telegram Stars\n/paysupport вопросы по оплате\n/id ваш Telegram ID\n\n"
        "Совет: чем точнее задача (тема, объём, стандарт оформления, дедлайн), тем лучше результат.")


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>")


@router.message(Command("new"))
@router.message(F.text == kb.BTN_NEW)
async def new_dialog(message: Message, db: Database) -> None:
    await db.clear_history(message.from_user.id)
    await message.answer("🧹 Диалог очищен. Начнём с чистого листа: выберите режим или напишите вопрос.",
                         reply_markup=kb.main_menu())


@router.message(F.text.in_(kb.MODE_BUTTONS))
async def pick_mode(message: Message, db: Database) -> None:
    mode = kb.MODE_BUTTONS[message.text]
    await db.touch_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await db.set_mode(message.from_user.id, mode)
    await message.answer(kb.MODE_INTRO[mode])


@router.message(F.text == kb.BTN_CHEAT)
async def cheat_menu(message: Message) -> None:
    await message.answer("🎓 Что нужно?", reply_markup=kb.cheat_choice())


@router.callback_query(F.data.startswith("mode:"))
async def pick_cheat_mode(call: CallbackQuery, db: Database) -> None:
    mode = call.data.split(":")[1]
    if mode not in ("cheat", "exam"):
        await call.answer()
        return
    await db.touch_user(call.from_user.id, call.from_user.username, call.from_user.full_name)
    await db.set_mode(call.from_user.id, mode)
    await call.answer()
    await call.message.answer(kb.MODE_INTRO[mode])


# =========================== subscription (Telegram Stars) ===========================
async def status_text(db: Database, s: Settings, user_id: int) -> str:
    until = await db.paid_until(user_id)
    if until > time.time():
        return (f"💎 <b>Подписка активна</b> до {_fmt_until(until)}.\n"
                f"Развёрнутые ответы и до {s.paid_daily} запросов в день.")
    left = max(0, s.free_daily - await db.used_today(user_id))
    return (f"🆓 <b>Бесплатный тариф</b>: осталось запросов сегодня: {left} из {s.free_daily}. Ответы компактные.\n\n"
            f"💎 <b>Подписка на {s.sub_days} дней за {s.price_stars} ⭐</b>:\n"
            f"• до {s.paid_daily} запросов в день\n• большие главы курсовых и развёрнутые тексты\n• длинные ответы без обрезки")


@router.message(Command("subscribe"))
@router.message(F.text == kb.BTN_SUB)
async def subscribe(message: Message, db: Database, settings: Settings) -> None:
    await message.answer(await status_text(db, settings, message.from_user.id),
                         reply_markup=kb.subscribe_button(f"⭐ Оплатить {settings.price_stars} Stars"))


async def send_invoice(target: Message, settings: Settings, user_id: int) -> None:
    await target.answer_invoice(
        title=f"OmniStudent: подписка на {settings.sub_days} дней",
        description="Развёрнутые ответы, большие главы работ и до "
                    f"{settings.paid_daily} запросов в день.",
        payload=f"sub:{user_id}", currency="XTR",
        prices=[LabeledPrice(label=f"Подписка {settings.sub_days} дней", amount=settings.price_stars)],
        provider_token="")


@router.callback_query(F.data == "pay")
async def pay_button(call: CallbackQuery, settings: Settings) -> None:
    await call.answer()
    await send_invoice(call.message, settings, call.from_user.id)


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, settings: Settings) -> None:
    ok = query.currency == "XTR" and query.total_amount == settings.price_stars and query.invoice_payload == f"sub:{query.from_user.id}"
    await query.answer(ok=ok, error_message=None if ok else "Счёт устарел. Откройте меню подписки и создайте новый.")


@router.message(F.successful_payment)
async def paid(message: Message, db: Database, settings: Settings) -> None:
    p = message.successful_payment
    if await db.payment_exists(p.telegram_payment_charge_id):            # Telegram may redeliver an update
        return
    await db.touch_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await db.add_payment(message.from_user.id, p.telegram_payment_charge_id, p.total_amount, settings.sub_days)
    until = await db.extend_subscription(message.from_user.id, settings.sub_days)
    log.info("Subscription paid by %s, %s Stars", message.from_user.id, p.total_amount)
    await message.answer(f"✅ <b>Спасибо! Подписка активна до {_fmt_until(until)}.</b>\nТеперь доступны развёрнутые ответы и большие главы.",
                         reply_markup=kb.main_menu())


@router.message(Command("paysupport"))
async def pay_support(message: Message, settings: Settings) -> None:
    contact = f" Напишите: {html.escape(settings.support_contact)}." if settings.support_contact else ""
    await message.answer("💬 <b>Вопросы по оплате.</b> Если оплата прошла, а подписка не включилась, или вы хотите вернуть Stars, "
                         f"сообщите ID платежа из чата с чеком.{contact}")


# =========================== admin ===========================
def _is_admin(message: Message, settings: Settings) -> bool:
    return message.from_user.id in settings.admin_ids


@router.message(Command("stats"))
async def stats(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    s = await db.stats()
    await message.answer(f"📊 Пользователей: {s['users']} (активны сегодня: {s['active_today']})\n"
                         f"Запросов сегодня: {s['requests_today']}\nПодписчиков: {s['paid']}\n"
                         f"Оплат: {s['payments']}, всего {s['stars']} ⭐")


@router.message(Command("grant"))
async def grant(message: Message, command: CommandObject, db: Database, settings: Settings, bot: Bot) -> None:
    if not _is_admin(message, settings):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        await message.answer("Формат: /grant ID дни (например /grant 123456789 30; отрицательные дни ничего не отнимают)")
        return
    uid, days = int(parts[0]), int(parts[1])
    if days <= 0:
        await db.revoke_subscription(uid)
        await message.answer(f"Подписка пользователя {uid} отключена.")
        return
    until = await db.extend_subscription(uid, days)
    await message.answer(f"Подписка пользователя {uid} продлена до {_fmt_until(until)}.")
    try:
        await bot.send_message(uid, f"💎 Вам включена подписка до {_fmt_until(until)}.")
    except Exception:
        pass


@router.message(Command("refund"))
async def refund(message: Message, command: CommandObject, db: Database, settings: Settings, bot: Bot) -> None:
    if not _is_admin(message, settings):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Формат: /refund ID_пользователя ID_платежа")
        return
    try:
        await bot.refund_star_payment(user_id=int(parts[0]), telegram_payment_charge_id=parts[1])
    except TelegramBadRequest as e:
        await message.answer(f"Не удалось вернуть Stars: {html.escape(str(e))}")
        return
    await db.revoke_subscription(int(parts[0]))
    await message.answer("Stars возвращены, подписка отключена.")


# =========================== the assistant ===========================
async def run_assistant(message: Message, db: Database, ai: Assistant, settings: Settings, text: str,
                        stored: str | None = None) -> None:
    uid = message.from_user.id
    await db.touch_user(uid, message.from_user.username, message.from_user.full_name)
    paid = await db.is_paid(uid)
    limit = settings.paid_daily if paid else settings.free_daily
    if await db.used_today(uid) >= limit:
        if paid:
            await message.answer(f"Вы исчерпали дневной лимит ({limit} запросов). Он обновится завтра.")
        else:
            await message.answer(f"На сегодня бесплатные запросы закончились ({limit}). "
                                 f"С подпиской за {settings.price_stars} ⭐ доступно до {settings.paid_daily} запросов в день "
                                 "и большие главы работ. Лимит бесплатного тарифа обновится завтра.",
                                 reply_markup=kb.subscribe_button(f"⭐ Оформить подписку, {settings.price_stars} Stars"))
        return
    lock = _lock(uid)
    if lock.locked():
        await message.answer("Я ещё отвечаю на предыдущий вопрос. Дождитесь ответа, пожалуйста.")
        return
    async with lock:
        mode = await db.get_mode(uid)
        try:
            async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
                answer = await ai.ask(uid, text, mode=mode, paid=paid, stored=stored)
        except AssistantError as e:
            await message.answer(f"⚠️ {html.escape(str(e))}")
            return
        except Exception:
            log.exception("Unexpected error while answering")
            await message.answer("⚠️ Что-то пошло не так. Попробуйте ещё раз через минуту.")
            return
        await db.count_use(uid)
        await send_answer(message, answer)
        if not paid:
            left = max(0, limit - await db.used_today(uid))
            if left == 0:
                await message.answer("Это был последний бесплатный запрос на сегодня.",
                                     reply_markup=kb.subscribe_button(f"⭐ Подписка, {settings.price_stars} Stars"))


@router.message(F.document)
async def on_document(message: Message, bot: Bot, db: Database, ai: Assistant, settings: Settings) -> None:
    doc = message.document
    if doc.file_size and doc.file_size > MAX_FILE_BYTES:
        await message.answer("Файл слишком большой: максимум 10 МБ.")
        return
    name = doc.file_name or "file"
    buf = await bot.download(doc)
    try:
        text, cut = extract_text(name, buf.read())
    except UnsupportedFile as e:
        await message.answer(str(e))
        return
    mode = await db.get_mode(message.from_user.id)
    task = (message.caption or "").strip() or DEFAULT_FILE_TASK.get(mode, "Кратко изложи суть этого материала и предложи, что с ним можно сделать.")
    note = "\n(Файл длинный, прочитаны первые 30 000 знаков.)" if cut else ""
    full = f"{task}\n\n[Файл: {name}]{note}\n{text}"
    stored = f"{task}\n\n[Файл: {name}, {len(text)} знаков]"
    await run_assistant(message, db, ai, settings, full[:MAX_INPUT_CHARS + 30_000], stored=stored)


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, db: Database, ai: Assistant, settings: Settings) -> None:
    if len(message.text) > MAX_INPUT_CHARS:
        await message.answer(f"Сообщение слишком длинное (максимум {MAX_INPUT_CHARS} знаков). "
                             "Пришлите текст файлом (.txt, .pdf, .docx) или разбейте на части.")
        return
    await run_assistant(message, db, ai, settings, message.text)


@router.message()
async def other(message: Message) -> None:
    await message.answer("Я работаю с текстом и файлами .txt, .pdf, .docx. Напишите вопрос или пришлите файл.",
                         reply_markup=kb.main_menu())
