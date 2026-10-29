"""Admin tools (Russian): panel, statistics, users, subscriptions, bans, support desk, broadcast, admin list."""
from __future__ import annotations

import asyncio
import html
import logging
import time
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (BotCommand, BotCommandScopeChat, BufferedInputFile, CallbackQuery, FSInputFile, InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup,
                           KeyboardButton, Message, ReplyKeyboardMarkup)

import keyboards as kb
from config import Settings
from db import Database
from access import USER_MODE
from filters import AdminView, RealAdmin
from i18n import DEFAULT_LANG, t
import settings_store as ss

log = logging.getLogger(__name__)

PAGE = 10


router = Router(name="admin")
router.message.filter(F.chat.type == ChatType.PRIVATE, AdminView())
router.callback_query.filter(AdminView())

info = Router(name="info")                          # /id for everybody: the ID and the role the bot assigns to it
info.message.filter(F.chat.type == ChatType.PRIVATE)


@info.message(Command("id"))
async def whoami(message: Message, lang: str, is_admin: bool = False, is_owner: bool = False) -> None:
    role = t(lang, "role_owner" if is_owner else "role_admin" if is_admin else "role_user")
    await message.answer(t(lang, "your_id", id=message.from_user.id) + "\n" + t(lang, "role_line", role=role))


gate = Router(name="admin-gate")                    # /admin works in both views: it brings an administrator back from the user's view
gate.message.filter(F.chat.type == ChatType.PRIVATE, RealAdmin())


class A(StatesGroup):
    reply = State()        # data: ticket_id
    write = State()        # data: uid
    broadcast = State()
    find = State()
    setting = State()      # data: key


def fdate(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d.%m.%Y") if ts else "—"


BTN = {"stats": "📊 Статистика", "report": "📈 Доход", "users": "👥 Пользователи", "top": "🏆 Топ клиентов", "pay": "💳 Оплаты",
       "tickets": "🆘 Обращения", "bc": "📢 Рассылка", "find": "🔎 Найти", "settings": "⚙️ Настройки", "admins": "👮 Админы",
       "asuser": "👤 Как пользователь"}
ADMIN_LABELS = set(BTN.values())


def admin_menu() -> ReplyKeyboardMarkup:
    rows = [["stats", "report"], ["users", "top"], ["pay", "tickets"], ["bc", "find"], ["settings", "admins"], ["asuser"]]
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN[k]) for k in row] for row in rows], resize_keyboard=True,
                               input_field_placeholder="Админка")


def panel() -> Markup:
    return Markup(inline_keyboard=[
        [Btn(text="📊 Статистика", callback_data="adm:stats"), Btn(text="📈 Доход", callback_data="adm:report:7")],
        [Btn(text="👥 Пользователи", callback_data="adm:users:0"), Btn(text="🏆 Топ клиентов", callback_data="adm:top")],
        [Btn(text="💳 Оплаты", callback_data="adm:pay"), Btn(text="🆘 Обращения", callback_data="adm:tickets")],
        [Btn(text="📢 Рассылка", callback_data="adm:bc"), Btn(text="⚙️ Настройки", callback_data="adm:settings")]])


HELP = ("🛠 <b>Админка</b>\n\n"
        "Все разделы в меню внизу. Команды:\n"
        "/stats · /report [дней] · /top · /users [стр] · /user ID или @ник\n"
        "/grant ID звёзды начислить на кошелёк (минус: списать) · /ban ID · /unban ID · /refund ID платёж\n"
        "/payments оплаты картой и последние пополнения · /settings цены и реквизиты\n"
        "/tickets · /reply № текст · /close № · /broadcast\n"
        "/admins · /addadmin ID или @ник · /rmadmin ID (владелец)\n"
        "/backup и /export база и список клиентов (владелец)\n\n"
        "Обращения и чеки приходят сюда сами. «👤 Как пользователь» показывает бота глазами клиента, вернуться: /admin.")


ADMIN_COMMANDS = [("admin", "Админка"), ("stats", "Статистика"), ("report", "Доход за период"), ("top", "Топ клиентов"), ("users", "Пользователи"),
                  ("payments", "Оплаты и чеки"), ("settings", "Цены и реквизиты"), ("tickets", "Обращения"), ("broadcast", "Рассылка"),
                  ("admins", "Админы"), ("backup", "Копия базы"), ("export", "Список клиентов")]


async def show_panel(message: Message) -> None:
    USER_MODE.discard(message.from_user.id)
    try:                                                   # the command list of an administrator shows the admin commands
        await message.bot.set_my_commands([BotCommand(command=c, description=d) for c, d in ADMIN_COMMANDS],
                                          scope=BotCommandScopeChat(chat_id=message.chat.id))
    except TelegramAPIError:
        pass
    await message.answer(HELP, reply_markup=admin_menu())
    await message.answer("⬇️", reply_markup=panel())


@gate.message(Command("admin"))
async def admin_cmd(message: Message) -> None:
    await show_panel(message)


@router.message(Command("start"))
async def admin_start(message: Message) -> None:
    await show_panel(message)


@router.callback_query(F.data == "adm:home")
async def home(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(HELP, reply_markup=panel())


@router.message(F.text == BTN["asuser"])
async def as_user(message: Message, lang: str) -> None:
    from keyboards import main_menu
    USER_MODE.add(message.from_user.id)
    await message.answer("👤 Вы видите бота как обычный пользователь. Вернуться в админку: /admin", reply_markup=main_menu(lang))


@router.message(StateFilter(A.reply, A.write, A.broadcast, A.find, A.setting), F.text.in_(ADMIN_LABELS))
async def leave_state(message: Message, state: FSMContext) -> None:
    await state.clear()                       # a menu tap ends whatever the administrator was typing
    raise SkipHandler


# ---------------- statistics ----------------
async def stats_text(db: Database) -> str:
    s = await db.stats()
    names = {"ru": "рус", "uz": "узб", "en": "англ", "-": "не выбран"}
    langs = ", ".join(f"{names.get(k, k)} {v}" for k, v in sorted(s["langs"].items(), key=lambda x: -x[1])) or "—"
    return (f"📊 <b>Статистика</b>\n\n"
            f"👥 Пользователей всего: <b>{s['users']}</b>\n"
            f"🆕 Новых сегодня: {s['new_today']} · за 7 дней: {s['new_7d']}\n"
            f"🔥 Писали боту сегодня: {s['active_today']} · были за 7 дней: {s['active_7d']}\n"
            f"💬 Запросов сегодня: {s['requests_today']} · всего: {s['requests_total']}\n"
            f"💰 Пополнили кошелёк: {s['payers']} чел. · оплат: {s['payments']} (Stars получено: {s['stars']} ⭐)\n"
            f"👛 Сейчас на кошельках: {s['wallets']} ⭐ · потрачено сегодня: {s['spent_today']} ⭐, всего: {s['spent_total']} ⭐\n"
            f"🧰 Сегодня: слайдов {s['tools_today'].get('slides', 0)} · проверок на ИИ {s['tools_today'].get('detect', 0)} · "
            f"конвертаций {s['tools_today'].get('convert', 0)}\n"
            f"💳 Оплат картой: {s['card_paid']} · ждут проверки: {s['card_pending']}\n"
            f"🆘 Обращения: открытых {s['tickets_open']} из {s['tickets_total']}\n"
            f"🚫 Заблокировано: {s['banned']}\n"
            f"🌐 Языки: {langs}")


@router.message(Command("stats"))
@router.message(F.text == BTN["stats"])
async def stats_cmd(message: Message, db: Database) -> None:
    await message.answer(await stats_text(db), reply_markup=panel())


@router.callback_query(F.data == "adm:stats")
async def stats_btn(call: CallbackQuery, db: Database) -> None:
    await call.answer()
    await call.message.answer(await stats_text(db), reply_markup=panel())


# ---------------- users ----------------
def user_line(u: dict) -> str:
    flags = (f"💰{u['balance']}" if u["balance"] else "") + (" 🚫" if u["banned"] else "")
    nick = f" @{html.escape(u['username'])}" if u["username"] else ""
    return f"• {html.escape(u['name'] or '—')}{nick} · <code>{u['user_id']}</code> · {u['lang'] or '—'} {flags}".rstrip()


async def users_page(db: Database, page: int) -> tuple[str, Markup]:
    total = (await db.stats())["users"]
    rows = await db.recent_users(PAGE, page * PAGE)
    pages = max(1, -(-total // PAGE))
    nav = []
    if page > 0:
        nav.append(Btn(text="◀️", callback_data=f"adm:users:{page - 1}"))
    nav.append(Btn(text=f"{page + 1}/{pages}", callback_data="adm:home"))
    if (page + 1) * PAGE < total:
        nav.append(Btn(text="▶️", callback_data=f"adm:users:{page + 1}"))
    body = "\n".join(user_line(u) for u in rows) or "Пока никого."
    return f"👥 <b>Пользователи: {total}</b> (новые сверху)\n\n{body}", Markup(inline_keyboard=[nav])


@router.message(Command("users"))
async def users_cmd(message: Message, command: CommandObject, db: Database) -> None:
    page = int(command.args) - 1 if command.args and command.args.strip().isdigit() and int(command.args) > 0 else 0
    text, markup = await users_page(db, page)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("adm:users:"))
async def users_btn(call: CallbackQuery, db: Database) -> None:
    text, markup = await users_page(db, int(call.data.split(":")[2]))
    await call.answer()
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


async def card(db: Database, u: dict) -> tuple[str, Markup]:
    text = (f"👤 <b>{html.escape(u['name'] or '—')}</b>" + (f" @{html.escape(u['username'])}" if u["username"] else "") +
            f"\nID: <code>{u['user_id']}</code>\nЯзык: {u['lang'] or '—'} · режим: {kb.MODE_TITLES.get(u['mode'], u['mode'])}\n"
            f"Регистрация: {fdate(u['created'])} · была активность: {fdate(u['last_seen'])}\n"
            f"Запросов всего: {await db.user_requests(u['user_id'])} · сегодня: {await db.used_today(u['user_id'])}\n"
            f"Баланс: {u['balance']} ⭐\n"
            f"Статус: {'🚫 заблокирован' if u['banned'] else '✅ активен'}")
    uid = u["user_id"]
    markup = Markup(inline_keyboard=[
        [Btn(text="+50 ⭐", callback_data=f"ug:{uid}:50"), Btn(text="+100 ⭐", callback_data=f"ug:{uid}:100"),
         Btn(text="−50 ⭐", callback_data=f"ug:{uid}:-50")],
        [Btn(text="✅ Разблокировать" if u["banned"] else "🚫 Заблокировать", callback_data=f"ub:{uid}"),
         Btn(text="✉️ Написать", callback_data=f"um:{uid}")]])
    return text, markup


async def show_user(target: Message, db: Database, query: str) -> None:
    u = await db.find_user(query)
    if not u:
        await target.answer("Пользователь не найден. Он должен хотя бы раз открыть бота.")
        return
    text, markup = await card(db, u)
    await target.answer(text, reply_markup=markup)


@router.message(Command("user"))
async def user_cmd(message: Message, command: CommandObject, db: Database) -> None:
    if not command.args:
        await message.answer("Формат: /user ID или /user @ник")
        return
    await show_user(message, db, command.args)


@router.callback_query(F.data.startswith("us:"))
async def user_btn(call: CallbackQuery, db: Database) -> None:
    await call.answer()
    await show_user(call.message, db, call.data.split(":")[1])


@router.callback_query(F.data == "adm:find")
async def find_btn(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(A.find)
    await call.message.answer("Пришлите ID или @ник пользователя. Отмена: /cancel")


@router.message(StateFilter(A.find), F.text & ~F.text.startswith("/"), ~F.text.in_(ADMIN_LABELS))
async def find_input(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await show_user(message, db, message.text)


# ---------------- subscriptions, bans, refunds ----------------
async def adjust(db: Database, bot: Bot, uid: int, stars: int) -> str:
    """Admin changes a wallet: positive credits Stars, negative takes them (never below zero)."""
    if stars == 0:
        return "Нужно ненулевое число."
    if stars < 0:
        if not await db.charge(uid, -stars, "admin", "debit"):
            return f"У пользователя {uid} на балансе {await db.balance(uid)} ⭐, списать {-stars} нельзя."
        return f"Списано {-stars} ⭐. Баланс {uid}: {await db.balance(uid)} ⭐."
    balance = await db.credit(uid, stars, "admin", "credit")
    lang = await db.get_lang(uid) or DEFAULT_LANG
    try:
        await bot.send_message(uid, t(lang, "granted", n=stars, balance=balance))
    except TelegramAPIError:
        pass
    return f"Начислено {stars} ⭐. Баланс {uid}: {balance} ⭐."


@router.message(Command("grant"))
async def grant(message: Message, command: CommandObject, db: Database, bot: Bot) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        await message.answer("Формат: /grant ID звёзды (например /grant 123456789 100 начислит 100 ⭐, /grant 123456789 -50 спишет 50)")
        return
    await message.answer(await adjust(db, bot, int(parts[0]), int(parts[1])))


@router.callback_query(F.data.startswith("ug:"))
async def grant_btn(call: CallbackQuery, db: Database, bot: Bot) -> None:
    _, uid, stars = call.data.split(":")
    await call.answer(await adjust(db, bot, int(uid), int(stars)), show_alert=True)


async def ban(db: Database, settings: Settings, uid: int, banned: bool) -> str:
    if uid in settings.admin_ids or await db.is_admin(uid):
        return "Администраторов блокировать нельзя."
    if not await db.find_user(str(uid)):
        return "Пользователь не найден."
    await db.set_banned(uid, banned)
    return f"Пользователь {uid} {'заблокирован 🚫' if banned else 'разблокирован ✅'}."


@router.message(Command("ban"))
@router.message(Command("unban"))
async def ban_cmd(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer(f"Формат: /{command.command} ID")
        return
    await message.answer(await ban(db, settings, int(command.args), command.command == "ban"))


@router.callback_query(F.data.startswith("ub:"))
async def ban_btn(call: CallbackQuery, db: Database, settings: Settings) -> None:
    uid = int(call.data.split(":")[1])
    u = await db.find_user(str(uid))
    await call.answer(await ban(db, settings, uid, not (u and u["banned"])), show_alert=True)
    if u:
        text, markup = await card(db, await db.find_user(str(uid)))
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass


@router.message(Command("refund"))
async def refund(message: Message, command: CommandObject, db: Database, bot: Bot) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Формат: /refund ID_пользователя ID_платежа")
        return
    try:
        await bot.refund_star_payment(user_id=int(parts[0]), telegram_payment_charge_id=parts[1])
    except TelegramBadRequest as e:
        await message.answer(f"Не удалось вернуть Stars: {html.escape(str(e))}")
        return
    take = min(await db.payment_stars(parts[1]), await db.balance(int(parts[0])))
    taken = take if take > 0 and await db.charge(int(parts[0]), take, "admin", "refund") else 0        # take back the credited Stars as far as the balance allows
    await message.answer(f"Stars возвращены. С кошелька пользователя списано {taken} ⭐.")


# ---------------- support desk ----------------
async def deliver_reply(bot: Bot, db: Database, ticket_id: int, text: str) -> str:
    tk = await db.get_ticket(ticket_id)
    if not tk:
        return f"Обращение #{ticket_id} не найдено."
    lang = await db.get_lang(tk["user_id"]) or DEFAULT_LANG
    try:
        await bot.send_message(tk["user_id"], t(lang, "support_reply", id=ticket_id, text=html.escape(text)))
    except TelegramForbiddenError:
        return f"Не доставлено: пользователь {tk['user_id']} заблокировал бота."
    except TelegramAPIError as e:
        return f"Не доставлено: {html.escape(str(e))}"
    await db.set_ticket_status(ticket_id, "answered")
    return f"✅ Ответ на обращение #{ticket_id} отправлен."


async def tickets_text(db: Database) -> str:
    rows = await db.open_tickets(10)
    if not rows:
        return "🆘 Открытых обращений нет."
    out = ["🆘 <b>Открытые обращения</b> (старые сверху)\n"]
    for r in rows:
        out.append(f"<b>#{r['id']}</b> · <code>{r['user_id']}</code> · {fdate(r['created'])}\n{html.escape(r['text'][:200])}")
    out.append("\nОтветить: /reply № текст · закрыть: /close №")
    return "\n\n".join(out)


@router.message(Command("tickets"))
@router.message(F.text == BTN["tickets"])
async def tickets_cmd(message: Message, db: Database) -> None:
    await message.answer(await tickets_text(db))


@router.callback_query(F.data == "adm:tickets")
async def tickets_btn(call: CallbackQuery, db: Database) -> None:
    await call.answer()
    await call.message.answer(await tickets_text(db))


@router.message(Command("reply"))
async def reply_cmd(message: Message, command: CommandObject, db: Database, bot: Bot) -> None:
    head, _, body = (command.args or "").partition(" ")
    if not head.lstrip("#").isdigit() or not body.strip():
        await message.answer("Формат: /reply № текст")
        return
    await message.answer(await deliver_reply(bot, db, int(head.lstrip("#")), body.strip()))


@router.message(Command("close"))
async def close_cmd(message: Message, command: CommandObject, db: Database) -> None:
    arg = (command.args or "").lstrip("#")
    if not arg.isdigit() or not await db.get_ticket(int(arg)):
        await message.answer("Формат: /close № (номер обращения)")
        return
    await db.set_ticket_status(int(arg), "closed")
    await message.answer(f"Обращение #{arg} закрыто.")


@router.callback_query(F.data.startswith("tk:close:"))
async def close_btn(call: CallbackQuery, db: Database) -> None:
    tid = int(call.data.split(":")[2])
    await db.set_ticket_status(tid, "closed")
    await call.answer(f"Обращение #{tid} закрыто", show_alert=True)


@router.callback_query(F.data.startswith("tk:reply:"))
async def reply_btn(call: CallbackQuery, state: FSMContext) -> None:
    tid = int(call.data.split(":")[2])
    await state.set_state(A.reply)
    await state.update_data(ticket_id=tid)
    await call.answer()
    await call.message.answer(f"Напишите ответ на обращение #{tid} одним сообщением. Отмена: /cancel")


@router.message(StateFilter(A.reply), F.text & ~F.text.startswith("/"), ~F.text.in_(ADMIN_LABELS))
async def reply_input(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    tid = (await state.get_data()).get("ticket_id")
    await state.clear()
    await message.answer(await deliver_reply(bot, db, tid, message.text))


@router.message(F.reply_to_message, F.text & ~F.text.startswith("/"))
async def swipe_reply(message: Message, db: Database, bot: Bot) -> None:
    tid = await db.ticket_by_msg(message.chat.id, message.reply_to_message.message_id)
    if not tid:
        raise SkipHandler                      # an ordinary reply, not an answer to a ticket
    await message.answer(await deliver_reply(bot, db, tid, message.text))


@router.callback_query(F.data.startswith("um:"))
async def write_btn(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(A.write)
    await state.update_data(uid=int(call.data.split(":")[1]))
    await call.answer()
    await call.message.answer("Напишите сообщение пользователю одним сообщением. Отмена: /cancel")


@router.message(StateFilter(A.write), F.text & ~F.text.startswith("/"), ~F.text.in_(ADMIN_LABELS))
async def write_input(message: Message, state: FSMContext, bot: Bot) -> None:
    uid = (await state.get_data()).get("uid")
    await state.clear()
    try:
        await bot.send_message(uid, f"💬 {html.escape(message.text)}")
        await message.answer("✅ Отправлено.")
    except TelegramAPIError as e:
        await message.answer(f"Не доставлено: {html.escape(str(e))}")


# ---------------- broadcast ----------------
@router.message(Command("broadcast"))
@router.message(F.text == BTN["bc"])
async def broadcast_cmd(message: Message, state: FSMContext) -> None:
    await state.set_state(A.broadcast)
    await message.answer("📢 Пришлите сообщение для рассылки (текст, фото или файл, форматирование сохранится). Отмена: /cancel")


@router.callback_query(F.data == "adm:bc")
async def broadcast_btn(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await broadcast_cmd(call.message, state)


@router.message(StateFilter(A.broadcast), ~F.text.startswith("/"), ~F.text.in_(ADMIN_LABELS))
async def broadcast_preview(message: Message, state: FSMContext, db: Database) -> None:
    n = len(await db.broadcast_ids())
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await message.answer(f"Отправить это сообщение {n} пользователям?", reply_markup=Markup(inline_keyboard=[
        [Btn(text=f"✅ Отправить ({n})", callback_data="bc:go"), Btn(text="✖️ Отмена", callback_data="bc:no")]]),
        reply_to_message_id=message.message_id)


@router.callback_query(F.data == "bc:no")
async def broadcast_no(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer("Отменено")
    await call.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data == "bc:go")
async def broadcast_go(call: CallbackQuery, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    if "message_id" not in data:
        await call.answer("Сообщение не найдено, начните заново: /broadcast", show_alert=True)
        return
    await call.answer("Отправляю…")
    await call.message.edit_reply_markup(reply_markup=None)
    ok = blocked = failed = 0
    for uid in await db.broadcast_ids():
        try:
            await bot.copy_message(uid, data["chat_id"], data["message_id"])
            ok += 1
        except TelegramForbiddenError:
            blocked += 1
        except TelegramAPIError:
            failed += 1
        await asyncio.sleep(0.05)                          # stays well below Telegram's 30 messages/second limit
    await call.message.answer(f"📢 Готово. Доставлено: {ok} · заблокировали бота: {blocked} · ошибок: {failed}")


# ---------------- card payments ----------------
@router.callback_query(F.data.startswith("cp:"))
async def card_decision(call: CallbackQuery, db: Database, settings: Settings, bot: Bot) -> None:
    _, verdict, pid_s = call.data.split(":")
    pid = int(pid_s)
    pay = await db.get_card_payment(pid)
    if not pay:
        await call.answer("Заявка не найдена", show_alert=True)
        return
    approve = verdict == "ok"
    if not await db.decide_card_payment(pid, "approved" if approve else "rejected"):
        await call.answer("Эта заявка уже обработана", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return
    uid = pay["user_id"]
    lang = await db.get_lang(uid) or DEFAULT_LANG
    if approve:
        balance = await db.credit(uid, pay["stars"], "card", f"card:{pid}")
        await db.add_payment(uid, f"card:{pid}", 0, 0)
        text = t(lang, "card_approved", stars=pay["stars"], balance=balance)
    else:
        text = t(lang, "card_rejected")
    try:
        await bot.send_message(uid, text)
        note = ""
    except TelegramAPIError:
        note = " (пользователю не доставлено: он заблокировал бота)"
    await call.answer(("Подтверждено" if approve else "Отклонено") + note, show_alert=bool(note))
    try:
        await call.message.edit_text(call.message.html_text + f"\n\n{'✅ Подтверждено' if approve else '❌ Отклонено'} · {html.escape(call.from_user.full_name)}",
                                     reply_markup=None)
    except TelegramBadRequest:
        pass


# ---------------- menu buttons that need no arguments ----------------
@router.message(F.text == BTN["users"])
async def users_button(message: Message, db: Database) -> None:
    text, markup = await users_page(db, 0)
    await message.answer(text, reply_markup=markup)


@router.message(F.text == BTN["find"])
async def find_button(message: Message, state: FSMContext) -> None:
    await state.set_state(A.find)
    await message.answer("Пришлите ID или @ник пользователя. Отмена: /cancel")


# ---------------- income report ----------------
PERIODS = {1: "24 часа", 7: "7 дней", 30: "30 дней", 0: "всё время"}


async def report_text(db: Database, settings: Settings, days: int) -> str:
    r = await db.report(days)
    uzs_stars = r["card_stars"] + r["uzs_stars"]
    names = {"chat": "вопросы", "slides": "презентации", "detect": "проверки на ИИ", "convert": "конвертации"}
    acts = ", ".join(f"{names.get(k, k)} {v}" for k, v in sorted(r["by_action"].items(), key=lambda x: -x[1])) or "—"
    rate = settings.uzs_per_star
    return (f"📈 <b>Доход за {PERIODS.get(days, f'{days} дн.')}</b>\n\n"
            f"⭐ Пополнено через Telegram Stars: <b>{r['stars_in']} ⭐</b> ({r['stars_payments']} платежей)\n"
            f"💳 Картой и Click/Payme: <b>{uzs_stars} ⭐</b>" + (f" ≈ {uzs_stars * rate:,} сум".replace(",", " ") if rate else "") +
            f" ({r['card_payments']} подтверждено картой)\n"
            f"👥 Платили: {r['payers']} чел.\n\n"
            f"🛒 Потрачено клиентами: <b>{r['spent']} ⭐</b> за {r['actions']} действий\n"
            f"   {acts}\n\n"
            f"🆕 Новых пользователей: {r['new_users']} · были активны: {r['active_users']}")


def period_buttons(current: int) -> Markup:
    return Markup(inline_keyboard=[[Btn(text=("• " if d == current else "") + label, callback_data=f"adm:report:{d}")
                                    for d, label in PERIODS.items()]])


@router.message(Command("report"))
@router.message(F.text == BTN["report"])
async def report_cmd(message: Message, db: Database, settings: Settings, command: CommandObject | None = None) -> None:
    arg = (command.args or "").strip() if command else ""
    days = int(arg) if arg.isdigit() and 0 <= int(arg) <= 3650 else 7
    await message.answer(await report_text(db, settings, days), reply_markup=period_buttons(days))


@router.callback_query(F.data.startswith("adm:report:"))
async def report_btn(call: CallbackQuery, db: Database, settings: Settings) -> None:
    days = int(call.data.split(":")[2])
    await call.answer()
    text = await report_text(db, settings, days)
    try:
        await call.message.edit_text(text, reply_markup=period_buttons(days))
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=period_buttons(days))


# ---------------- best customers ----------------
async def top_text(db: Database) -> str:
    rows = await db.top_spenders(10)
    if not rows:
        return "🏆 Пока никто ничего не тратил."
    lines = [f"{i}. {html.escape(r['name'] or '—')}" + (f" @{html.escape(r['username'])}" if r["username"] else "") +
             f" · <code>{r['user_id']}</code>\n    потратил {r['spent']} ⭐ ({r['actions']} действий) · баланс {r['balance'] or 0} ⭐"
             for i, r in enumerate(rows, 1)]
    return "🏆 <b>Топ клиентов по тратам</b>\n\n" + "\n".join(lines)


@router.message(Command("top"))
@router.message(F.text == BTN["top"])
async def top_cmd(message: Message, db: Database) -> None:
    await message.answer(await top_text(db))


@router.callback_query(F.data == "adm:top")
async def top_btn(call: CallbackQuery, db: Database) -> None:
    await call.answer()
    await call.message.answer(await top_text(db))


# ---------------- payments: receipts waiting for a decision and the latest top-ups ----------------
KIND = {"topup": "Stars", "topup_uzs": "Click/Payme", "card": "карта"}


async def send_payments(target: Message, bot: Bot, db: Database, settings: Settings) -> None:
    pending = await db.pending_card_payments(10)
    if not pending:
        await target.answer("💳 Чеков на проверку нет.")
    for p in pending:
        who = html.escape(p["name"] or "—") + (f" @{html.escape(p['username'])}" if p["username"] else "")
        await target.answer(f"💳 <b>Заявка #{p['id']}</b> · {who} · <code>{p['user_id']}</code>\n"
                            f"{p['stars']} ⭐ = {p['stars'] * settings.uzs_per_star:,} сум".replace(",", " "),
                            reply_markup=Markup(inline_keyboard=[[Btn(text=f"✅ Зачислить {p['stars']} ⭐", callback_data=f"cp:ok:{p['id']}"),
                                                                  Btn(text="❌ Отклонить", callback_data=f"cp:no:{p['id']}")]]))
        if p["chat_id"] and p["msg_id"]:
            try:
                await bot.copy_message(target.chat.id, p["chat_id"], p["msg_id"])
            except TelegramAPIError:
                await target.answer("(чек больше недоступен: пользователь мог удалить сообщение)")
    recent = await db.recent_topups(10)
    if recent:
        lines = [f"• {fdate(r['ts'])} · {html.escape(r['name'] or '—')} · <code>{r['user_id']}</code> · +{r['delta']} ⭐ ({KIND.get(r['kind'], r['kind'])})"
                 for r in recent]
        await target.answer("🧾 <b>Последние пополнения</b>\n" + "\n".join(lines))


@router.message(Command("payments"))
@router.message(F.text == BTN["pay"])
async def payments_cmd(message: Message, bot: Bot, db: Database, settings: Settings) -> None:
    await send_payments(message, bot, db, settings)


@router.callback_query(F.data == "adm:pay")
async def payments_btn(call: CallbackQuery, bot: Bot, db: Database, settings: Settings) -> None:
    await call.answer()
    await send_payments(call.message, bot, db, settings)


# ---------------- settings: prices and payment details, applied at once ----------------
def settings_text(settings: Settings) -> str:
    lines = []
    for f in ss.FIELDS:
        v = ss.get(settings, f.key)
        lines.append(f"• {f.label}: <b>{html.escape(str(v)) if v not in ('', None) else '—'}</b>")
    return "⚙️ <b>Настройки</b>\nИзменения действуют сразу и сохраняются после перезапуска.\n\n" + "\n".join(lines)


def settings_buttons() -> Markup:
    return Markup(inline_keyboard=[[Btn(text=f.label.split(",")[0].split(" (")[0], callback_data=f"set:{f.key}")] for f in ss.FIELDS])


@router.message(Command("settings"))
@router.message(F.text == BTN["settings"])
async def settings_cmd(message: Message, settings: Settings) -> None:
    await message.answer(settings_text(settings), reply_markup=settings_buttons())


@router.callback_query(F.data == "adm:settings")
async def settings_btn(call: CallbackQuery, settings: Settings) -> None:
    await call.answer()
    await call.message.answer(settings_text(settings), reply_markup=settings_buttons())


@router.callback_query(F.data.startswith("set:"))
async def setting_pick(call: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    key = call.data.split(":")[1]
    f = ss.BY_KEY.get(key)
    if not f:
        await call.answer()
        return
    await call.answer()
    await state.set_state(A.setting)
    await state.update_data(key=key)
    cur = ss.get(settings, key)
    hint = "число" if f.kind == "int" else "текст (чтобы очистить, пришлите «-»)"
    await call.message.answer(f"{f.label}\nСейчас: <b>{html.escape(str(cur)) if cur not in ('', None) else '—'}</b>\n"
                              f"Пришлите новое значение: {hint}. Отмена: /cancel")


@router.message(StateFilter(A.setting), F.text & ~F.text.startswith("/"), ~F.text.in_(ADMIN_LABELS))
async def setting_input(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    key = (await state.get_data()).get("key")
    f = ss.BY_KEY.get(key)
    if not f:
        await state.clear()
        return
    try:
        value = ss.parse(f, message.text)
    except ValueError as e:
        await message.answer(f"{e} Попробуйте ещё раз или /cancel.")
        return
    await state.clear()
    await ss.save(db, settings, key, value)
    log.info("Setting %s changed by %s", key, message.from_user.id)
    await message.answer(f"✅ Сохранено.\n\n" + settings_text(settings), reply_markup=settings_buttons())


# ---------------- backup and export (owners only: personal data) ----------------
@router.message(Command("backup"))
async def backup_cmd(message: Message, db: Database, is_owner: bool = False) -> None:
    if not is_owner:
        await message.answer("Резервную копию может скачать только владелец.")
        return
    import os
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "uniprof-backup.db")
    try:
        await db.backup(path)
        await message.answer_document(FSInputFile(path), caption="💾 Копия базы: пользователи, балансы, платежи, обращения. Храните в безопасном месте.")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@router.message(Command("export"))
async def export_cmd(message: Message, db: Database, is_owner: bool = False) -> None:
    if not is_owner:
        await message.answer("Список клиентов может скачать только владелец.")
        return
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "username", "name", "lang", "balance", "spent", "banned", "registered", "last_seen"])
    for u in await db.export_users():
        w.writerow([u["user_id"], u["username"] or "", u["name"] or "", u["lang"] or "", u["balance"], u["spent"], u["banned"],
                    fdate(u["created"]), fdate(u["last_seen"])])
    await message.answer_document(BufferedInputFile(("\ufeff" + buf.getvalue()).encode("utf-8"), filename="clients.csv"),
                                  caption="📥 Список клиентов (CSV, открывается в Excel).")


# ---------------- admins ----------------
async def admins_text(db: Database, settings: Settings) -> str:
    lines = [f"👑 Владелец: <code>{i}</code>" for i in settings.admin_ids]
    lines += [f"👮 <code>{a['user_id']}</code>" + (f" @{html.escape(a['username'])}" if a["username"] else "")
              for a in await db.admin_rows() if a["user_id"] not in settings.admin_ids]
    names = ", ".join("@" + n for n in settings.admin_usernames)
    return "👮 <b>Администраторы</b>\n\n" + "\n".join(lines) + (f"\n\nАвтоназначение по нику: {names}" if names else "")


@router.message(Command("admins"))
@router.message(F.text == BTN["admins"])
async def admins_cmd(message: Message, db: Database, settings: Settings) -> None:
    await message.answer(await admins_text(db, settings))


@router.callback_query(F.data == "adm:admins")
async def admins_btn(call: CallbackQuery, db: Database, settings: Settings) -> None:
    await call.answer()
    await call.message.answer(await admins_text(db, settings))


@router.message(Command("addadmin"))
async def add_admin(message: Message, command: CommandObject, db: Database, is_owner: bool = False) -> None:
    if not is_owner:
        await message.answer("Назначать админов может только владелец.")
        return
    u = await db.find_user(command.args or "")
    if not u:
        await message.answer("Формат: /addadmin ID или @ник. Человек должен сначала открыть бота.")
        return
    await db.add_admin(u["user_id"], u["username"])
    await message.answer(f"👮 {html.escape(u['name'] or '')} теперь администратор.")


@router.message(Command("rmadmin"))
async def rm_admin(message: Message, command: CommandObject, db: Database, settings: Settings, is_owner: bool = False) -> None:
    if not is_owner:
        await message.answer("Снимать админов может только владелец.")
        return
    u = await db.find_user(command.args or "")
    if not u or u["user_id"] in settings.admin_ids:
        await message.answer("Формат: /rmadmin ID или @ник (владельца снять нельзя).")
        return
    await db.remove_admin(u["user_id"])
    await message.answer("Администратор снят. Если у него в настройках указан этот ник, он вернётся при следующем сообщении.")


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@router.message()
async def fallback(message: Message) -> None:
    """Anything else an administrator types: the user features are hidden in this view."""
    await message.answer("Это админка: клиентские функции здесь скрыты. Выберите раздел в меню или откройте /admin. "
                         "Чтобы посмотреть бота как клиент, нажмите «👤 Как пользователь».", reply_markup=admin_menu())
