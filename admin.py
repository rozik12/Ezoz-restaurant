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
from aiogram.filters import BaseFilter, Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup, Message

import keyboards as kb
from config import Settings
from db import Database
from i18n import DEFAULT_LANG, t

log = logging.getLogger(__name__)

PAGE = 10


class IsAdmin(BaseFilter):
    async def __call__(self, event, is_admin: bool = False) -> bool:
        return is_admin


router = Router(name="admin")
router.message.filter(F.chat.type == ChatType.PRIVATE, IsAdmin())
router.callback_query.filter(IsAdmin())


class A(StatesGroup):
    reply = State()        # data: ticket_id
    write = State()        # data: uid
    broadcast = State()
    find = State()


def fdate(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d.%m.%Y") if ts else "—"


def panel() -> Markup:
    return Markup(inline_keyboard=[
        [Btn(text="📊 Статистика", callback_data="adm:stats"), Btn(text="👥 Пользователи", callback_data="adm:users:0")],
        [Btn(text="🆘 Обращения", callback_data="adm:tickets"), Btn(text="📢 Рассылка", callback_data="adm:bc")],
        [Btn(text="🔎 Найти пользователя", callback_data="adm:find"), Btn(text="👮 Админы", callback_data="adm:admins")]])


HELP = ("🛠 <b>Панель администратора</b>\n\n"
        "<b>Команды</b>\n/stats статистика\n/users [стр] список пользователей\n/user ID или @ник карточка\n"
        "/grant ID дни подписка (0 или меньше: отключить)\n/refund ID платёж вернуть Stars\n/ban ID · /unban ID\n"
        "/tickets открытые обращения\n/reply № текст ответить клиенту\n/close № закрыть обращение\n"
        "/broadcast рассылка всем\n/admins список админов\n/addadmin ID или @ник · /rmadmin ID (только владелец)\n\n"
        "Обращения приходят сюда сами. Ответить: кнопка «Ответить» или свайп-ответ на сообщение с обращением.")


@router.message(Command("admin"))
async def admin_cmd(message: Message) -> None:
    await message.answer(HELP, reply_markup=panel())


@router.callback_query(F.data == "adm:home")
async def home(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(HELP, reply_markup=panel())


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
            f"💎 Подписчиков сейчас: {s['paid']} · оплат: {s['payments']} на {s['stars']} ⭐\n"
            f"🧰 Сегодня: слайдов {s['tools_today'].get('slides', 0)} · проверок на ИИ {s['tools_today'].get('detect', 0)} · "
            f"конвертаций {s['tools_today'].get('convert', 0)}\n"
            f"💳 Оплат картой: {s['card_paid']} · ждут проверки: {s['card_pending']}\n"
            f"🆘 Обращения: открытых {s['tickets_open']} из {s['tickets_total']}\n"
            f"🚫 Заблокировано: {s['banned']}\n"
            f"🌐 Языки: {langs}")


@router.message(Command("stats"))
async def stats_cmd(message: Message, db: Database) -> None:
    await message.answer(await stats_text(db), reply_markup=panel())


@router.callback_query(F.data == "adm:stats")
async def stats_btn(call: CallbackQuery, db: Database) -> None:
    await call.answer()
    await call.message.answer(await stats_text(db), reply_markup=panel())


# ---------------- users ----------------
def user_line(u: dict) -> str:
    flags = ("💎" if u["paid_until"] > time.time() else "") + ("🚫" if u["banned"] else "")
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
    paid = u["paid_until"] > time.time()
    text = (f"👤 <b>{html.escape(u['name'] or '—')}</b>" + (f" @{html.escape(u['username'])}" if u["username"] else "") +
            f"\nID: <code>{u['user_id']}</code>\nЯзык: {u['lang'] or '—'} · режим: {kb.MODE_TITLES.get(u['mode'], u['mode'])}\n"
            f"Регистрация: {fdate(u['created'])} · была активность: {fdate(u['last_seen'])}\n"
            f"Запросов всего: {await db.user_requests(u['user_id'])} · сегодня: {await db.used_today(u['user_id'])}\n"
            f"Подписка: {'до ' + fdate(u['paid_until']) if paid else 'нет'}\n"
            f"Статус: {'🚫 заблокирован' if u['banned'] else '✅ активен'}")
    uid = u["user_id"]
    markup = Markup(inline_keyboard=[
        [Btn(text="💎 +30 дней", callback_data=f"ug:{uid}:30"), Btn(text="💎 Отключить", callback_data=f"ug:{uid}:0")],
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


@router.message(StateFilter(A.find), F.text & ~F.text.startswith("/"))
async def find_input(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await show_user(message, db, message.text)


# ---------------- subscriptions, bans, refunds ----------------
async def set_sub(db: Database, bot: Bot, uid: int, days: int) -> str:
    if days <= 0:
        await db.revoke_subscription(uid)
        return f"Подписка пользователя {uid} отключена."
    until = await db.extend_subscription(uid, days)
    lang = await db.get_lang(uid) or DEFAULT_LANG
    try:
        await bot.send_message(uid, t(lang, "granted", until=fdate(until)))
    except TelegramAPIError:
        pass
    return f"Подписка пользователя {uid} продлена до {fdate(until)}."


@router.message(Command("grant"))
async def grant(message: Message, command: CommandObject, db: Database, bot: Bot) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        await message.answer("Формат: /grant ID дни (например /grant 123456789 30; 0 или меньше отключает подписку)")
        return
    await message.answer(await set_sub(db, bot, int(parts[0]), int(parts[1])))


@router.callback_query(F.data.startswith("ug:"))
async def grant_btn(call: CallbackQuery, db: Database, bot: Bot) -> None:
    _, uid, days = call.data.split(":")
    await call.answer(await set_sub(db, bot, int(uid), int(days)), show_alert=True)


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
    await db.revoke_subscription(int(parts[0]))
    await message.answer("Stars возвращены, подписка отключена.")


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


@router.message(StateFilter(A.reply), F.text & ~F.text.startswith("/"))
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


@router.message(StateFilter(A.write), F.text & ~F.text.startswith("/"))
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
async def broadcast_cmd(message: Message, state: FSMContext) -> None:
    await state.set_state(A.broadcast)
    await message.answer("📢 Пришлите сообщение для рассылки (текст, фото или файл, форматирование сохранится). Отмена: /cancel")


@router.callback_query(F.data == "adm:bc")
async def broadcast_btn(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await broadcast_cmd(call.message, state)


@router.message(StateFilter(A.broadcast), ~F.text.startswith("/"))
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
        until = await db.extend_subscription(uid, settings.sub_days)
        await db.add_payment(uid, f"card:{pid}", 0, settings.sub_days)
        text = t(lang, "card_approved", until=fdate(until))
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


# ---------------- admins ----------------
async def admins_text(db: Database, settings: Settings) -> str:
    lines = [f"👑 Владелец: <code>{i}</code>" for i in settings.admin_ids]
    lines += [f"👮 <code>{a['user_id']}</code>" + (f" @{html.escape(a['username'])}" if a["username"] else "")
              for a in await db.admin_rows() if a["user_id"] not in settings.admin_ids]
    names = ", ".join("@" + n for n in settings.admin_usernames)
    return "👮 <b>Администраторы</b>\n\n" + "\n".join(lines) + (f"\n\nАвтоназначение по нику: {names}" if names else "")


@router.message(Command("admins"))
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
