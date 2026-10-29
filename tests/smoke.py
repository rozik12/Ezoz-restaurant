"""End-to-end check against fake Telegram and fake Claude: python tests/smoke.py"""
import asyncio, io, os, sys, tempfile, time
os.environ.update(BOT_TOKEN="123456:TEST", ANTHROPIC_API_KEY="test", DB_PATH=tempfile.mktemp(suffix=".db"),
                  ADMIN_IDS="900", ADMIN_USERNAMES="ArtyomGlupech", CARD_NUMBER="8600 1234 5678 9012", CARD_HOLDER="TEST HOLDER", UZS_PER_STAR="1200", FREE_ACTIONS="0", PAYMENT_PROVIDER_TOKEN="123:TEST:abc")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, Message, Chat, File, MessageId
import fmt
from config import Settings
from db import Database
from handlers import router
import admin, support, tools
import wallet as walletmod
from access import Access
from llm import Assistant

# ---------- formatting ----------
h = fmt.md_to_html("## Заголовок\n**жирный** и *курсив*, `код` & <tag>\n- пункт\n```python\nprint('<x>')\n```\n| a | b |\n|---|---|\n| 1 | 2 |")
assert "<b>Заголовок</b>" in h and "<b>жирный</b>" in h and "<i>курсив</i>" in h and "<code>код</code>" in h, h
assert "&lt;tag&gt;" in h and "• пункт" in h and 'class="language-python"' in h and "&lt;x&gt;" in h and "<pre>| a | b |" in h, h
assert "snake_case_word" in fmt.md_to_html("snake_case_word and 2*3*4"), "underscores/stars in words must survive"
long = "\n".join(f"строка {i} " + "слово " * 20 for i in range(400)) + "\n```py\n" + "\n".join(f"x{i}=1" for i in range(900)) + "\n```\nконец"
parts = fmt.split_markdown(long)
assert all(len(p) <= 3100 for p in parts), max(len(p) for p in parts)
assert all(p.count("```") % 2 == 0 for p in parts), "every chunk must close its code fence"
print(f"formatting ok, {len(parts)} chunks for a {len(long)}-character answer")

# ---------- fake Claude ----------
class FakeMessages:
    def __init__(self): self.calls = []
    async def create(self, **kw):
        self.calls.append(kw)
        text = "## План\n**Введение** и *выводы*\n- пункт"
        if "presentation designer" in kw["system"] or "editor of presentation decks" in kw["system"]:
            text = '{"title":"Цифровой маркетинг","subtitle":"Курс","slides":[{"title":"Что это","bullets":["a","b","c"],"notes":"n"},{"title":"Итоги","bullets":["x"]}]}'
        if "machine-written" in kw["system"]:
            text = '{"ai_probability": 74, "signals":["Одинаковый ритм"], "fragments":[{"quote":"Таким образом","reason":"шаблон"}], "advice":["Добавьте примеры"]}'
        if "ОШИБКА" in kw["messages"][-1]["content"]:
            import anthropic
            try:
                import httpx
            except ImportError:
                import httpx2 as httpx
            raise anthropic.RateLimitError("x", response=httpx.Response(429, request=httpx.Request("POST", "http://x")), body=None)
        return NS(content=[NS(type="text", text=text)], stop_reason="max_tokens" if "ДЛИННО" in kw["messages"][-1]["content"] else "end_turn")

# ---------- fake Telegram ----------
calls = []
class Mock(BaseSession):
    async def close(self): pass
    async def stream_content(self, *a, **k): yield "Лекция: интеграл это предел суммы. Формула Ньютона-Лейбница.".encode()
    async def make_request(self, bot, method, timeout=None):
        name = method.__api_method__; calls.append((name, method.model_dump(exclude_none=True)))
        if name == "getFile": return File(file_id="f", file_unique_id="u", file_path="docs/a.txt")
        if name == "copyMessage": return MessageId(message_id=len(calls) + 5000)
        if name in ("sendMessage", "sendInvoice", "sendDocument"):
            return Message(message_id=len(calls), date=int(time.time()), chat=Chat(id=method.chat_id, type="private")).as_(bot)
        return True
n = [0]
def user(uid): return {"id": uid, "is_bot": False, "first_name": f"U{uid}", "username": f"u{uid}"}
def msg(uid, text=None, **extra):
    n[0] += 1
    m = {"message_id": n[0], "date": int(time.time()), "chat": {"id": uid, "type": "private"}, "from": user(uid), **extra}
    if text is not None:
        m["text"] = text
        if text.startswith("/"): m["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    return {"update_id": n[0], "message": m}
def cb(uid, data):
    n[0] += 1
    return {"update_id": n[0], "callback_query": {"id": str(n[0]), "chat_instance": "x", "data": data, "from": user(uid),
            "message": {"message_id": 1, "date": int(time.time()), "chat": {"id": uid, "type": "private"}, "text": "old"}}}

async def main():
    s = Settings.load(); db = Database(s.db_path); await db.connect()
    try:
        await body(s, db)
    finally:
        await db.close()

async def body(s, db):
    ai = Assistant(s, db); fake = FakeMessages(); ai.client = NS(messages=fake)
    bot = Bot("123456:TEST", session=Mock()); dp = Dispatcher(storage=MemoryStorage(), db=db, ai=ai, settings=s)
    acc = Access(db, s); dp.message.outer_middleware(acc); dp.callback_query.outer_middleware(acc)
    dp.include_router(support.router); dp.include_router(admin.router); dp.include_router(tools.router); dp.include_router(walletmod.router); dp.include_router(router)
    async def feed(d):
        calls.clear(); await dp.feed_update(bot, Update.model_validate(d, context={"bot": bot})); return list(calls)
    texts = lambda r: [c[1].get("text", "") for c in r if c[0] == "sendMessage"]
    U = 100
    r = await feed(msg(U, "/start")); assert "inline_keyboard" in r[0][1]["reply_markup"] and len(r[0][1]["reply_markup"]["inline_keyboard"]) == 3
    print("start asks language:", texts(r)[0][:40])
    r = await feed(cb(U, "lang:ru")); welcome = [x for x in texts(r) if "OmniStudent" in x]; assert welcome and len(r[-1][1]["reply_markup"]["keyboard"]) == 6
    print("language ru + welcome ok, menu rows:", len(r[-1][1]["reply_markup"]["keyboard"]))
    guide = [x for x in texts(r) if "Как пользоваться ботом" in x]; assert guide and "{" not in guide[0] and "<b>0</b>" in guide[0] and "50 ⭐" in guide[0]; print("guide sent right after the language choice:", guide[0][:30])
    r = await feed(msg(U, "/guide")); assert "Как пользоваться ботом" in texts(r)[0]
    r = await feed(msg(U, "✍️ Писать работу")); print("mode intro:", texts(r)[0][:40])
    r = await feed(msg(U, "Курсовая по маркетингу, 30 страниц")); out = texts(r)
    assert "Недостаточно звёзд" in out[0], out; mk = r[0][1]["reply_markup"]["inline_keyboard"]
    assert mk[0][0]["callback_data"] == "top:50", mk; print("empty wallet: question refused, top-up offered:", out[0][:60].replace("\n", " "))
    assert not fake.calls, "no model call without Stars"
    assert await db.credit(U, 120, "admin") == 120
    r = await feed(msg(U, "Курсовая по маркетингу, 30 страниц")); out = texts(r)
    print("answer html:", out[0].replace("\n", " | "))
    assert "−50 ⭐ · баланс: 70 ⭐" in out[0], out[0]; assert await db.balance(U) == 70; print("question charged 50, footer shows the balance")
    c = fake.calls[-1]
    assert "OmniStudent" in c["system"] and "Академический писатель" in c["system"] and "Тариф: подписка" in c["system"], "prompt parts"
    assert "интерфейса пользователя: русский" in c["system"]
    assert c["max_tokens"] == s.paid_max_tokens and c["messages"][-1]["role"] == "user"
    print("system prompt ok, max_tokens =", c["max_tokens"])
    r = await feed(msg(U, "А теперь план"))
    assert len(fake.calls[-1]["messages"]) == 3, fake.calls[-1]["messages"]            # user, assistant, user
    print("memory ok: history sent =", len(fake.calls[-1]["messages"]), "messages"); assert await db.balance(U) == 20
    r = await feed(msg(U, "ещё вопрос")); t = texts(r)[0]; assert "Недостаточно звёзд" in t and "действие стоит 50" in t and "баланс" not in t.lower() or "20" in t
    mk = r[0][1]["reply_markup"]["inline_keyboard"]; assert mk[0][0]["callback_data"] == "top:30", mk; print("short balance: offers exactly the missing 30 ⭐")
    # top-up with Stars: any amount
    r = await feed(msg(U, "/wallet")); w = texts(r)[0]; assert "20 ⭐" in w and "50 ⭐" in w; cbs = [b["callback_data"] for row in r[0][1]["reply_markup"]["inline_keyboard"] for b in row]
    assert cbs[:5] == ["top:50", "top:100", "top:250", "top:500", "top:1000"] and "top:custom" in cbs and "topm:card" in cbs and "topm:payp" in cbs and "stars:how" in cbs, cbs; print("wallet screen ok:", cbs)
    r = await feed(cb(U, "top:100")); inv = [c for c in r if c[0] == "sendInvoice"][0][1]
    print("invoice:", inv["currency"], inv["prices"], inv["payload"]); assert inv["currency"] == "XTR" and inv["prices"][0]["amount"] == 100 and inv["payload"] == f"top:{U}"
    r = await feed(cb(U, "top:custom")); r = await feed(msg(U, "abc")); assert "Введите целое число" in texts(r)[0]
    r = await feed(msg(U, "0")); assert "Введите целое число" in texts(r)[0]; r = await feed(msg(U, "10001")); assert "Введите целое число" in texts(r)[0]
    r = await feed(msg(U, "7")); inv = [c for c in r if c[0] == "sendInvoice"][0][1]; assert inv["prices"][0]["amount"] == 7; print("custom amount of 7 Stars accepted (no minimum beyond 1)")
    r = await feed(cb(U, "top:custom")); r = await feed(msg(U, "1")); assert [c for c in r if c[0] == "sendInvoice"][0][1]["prices"][0]["amount"] == 1; print("custom amount of 1 Star accepted")
    pre = lambda uid, amt, payload, cur="XTR", n=[9000]: {"update_id": (n.__setitem__(0, n[0] + 1) or n[0]), "pre_checkout_query": {"id": "p", "from": user(uid), "currency": cur, "total_amount": amt, "invoice_payload": payload}}
    ok = lambda r: [c[1]["ok"] for c in r if c[0] == "answerPreCheckoutQuery"]
    assert ok(await feed(pre(U, 100, f"top:{U}"))) == [True] and ok(await feed(pre(U, 1, f"top:{U}"))) == [True]
    assert ok(await feed(pre(U, 0, f"top:{U}"))) == [False] and ok(await feed(pre(U, 100, f"top:{U + 1}"))) == [False] and ok(await feed(pre(U, 100, "junk"))) == [False]
    print("pre-checkout: any amount from 1 accepted; zero, someone else's payload and junk rejected")
    pay = msg(U, successful_payment={"currency": "XTR", "total_amount": 100, "invoice_payload": f"top:{U}", "telegram_payment_charge_id": "ch1", "provider_payment_charge_id": "pp"})
    r = await feed(pay); print("paid:", texts(r)[0][:60]); assert await db.balance(U) == 120
    await feed(pay); assert await db.balance(U) == 120 and await db._scalar("SELECT COUNT(*) FROM payments") == 1, "duplicate payment update must not credit twice"
    r = await feed(msg(U, "после оплаты")); assert await db.balance(U) == 70; print("paid top-up spent on the next question")
    r = await feed(msg(U, "ДЛИННО")); assert "обрезан" in texts(r)[0]; assert await db.balance(U) == 20; print("truncation note ok")
    await db.credit(U, 100, "admin")
    before = await db.balance(U)
    r = await feed(msg(U, "ОШИБКА")); print("API error shown nicely:", texts(r)[0][:70].replace("\n", " ")); assert "перегружен" in texts(r)[0] and "вернулись" in texts(r)[0]
    assert await db.balance(U) == before, "a failed request must cost nothing"; print("failed request refunded")
    assert len(await db.history(U, 50)) % 2 == 0, "failed question must not stay in history"
    r = await feed(cb(U, "mode:exam")); r = await feed(msg(U, "Начинай, тема: цифровой маркетинг")); assert "Вредный преподаватель" in fake.calls[-1]["system"]; print("exam mode prompt ok")
    doc = msg(U, document={"file_id": "f", "file_unique_id": "u", "file_name": "lecture.txt", "file_size": 100}, caption="Сделай шпаргалку")
    r = await feed(doc); last = fake.calls[-1]["messages"][-1]["content"]; assert "Лекция: интеграл" in last and "Сделай шпаргалку" in last; print("document read ok, sent to model:", last[:50].replace("\n", " "))
    r = await feed(msg(U, document={"file_id": "f", "file_unique_id": "u", "file_name": "photo.png", "file_size": 100})); print("unsupported file:", texts(r)[0][:50])
    r = await feed(msg(U, "/new")); assert await db.history(U) == []; print("/new clears history ok")
    r = await feed(msg(U, "/paysupport")); print("paysupport:", texts(r)[0][:40])

    # ---------- three languages ----------
    V, W = 200, 300
    await feed(msg(V, "/start")); r = await feed(cb(V, "lang:uz")); assert any("Salom" in x for x in texts(r)) and any("Botdan qanday foydalaniladi" in x for x in texts(r)); print("uz welcome + guide ok")
    r = await feed(msg(V, "🆘 Yordam xizmati")); assert "Yordam xizmati" in texts(r)[0]; print("uz support entry ok")
    await feed(msg(V, "/cancel"))
    await db.credit(V, 500, "admin"); await feed(msg(V, "Salom, kurs ishi kerak")); assert "o'zbekcha" in fake.calls[-1]["system"]; print("uz system hint ok")
    await feed(msg(W, "/start")); r = await feed(cb(W, "lang:en")); assert any("Hi! I'm OmniStudent" in x for x in texts(r)) and any("How to use the bot" in x for x in texts(r)); print("en welcome + guide ok")
    r = await feed(msg(W, "🧮 Problems & code")); assert "Technical expert" in texts(r)[0]; print("en mode button ok")
    r = await feed(msg(V, "/wallet")); assert "Sizning hamyoningiz" in texts(r)[0] and "Boshqa summa" in str(r[0][1]["reply_markup"]); print("uz wallet text ok")
    r = await feed(cb(V, "stars:how")); howto = texts(r)[0]; assert "Mening yulduzlarim" in howto; print("stars how-to (uz) ok")
    r = await feed(msg(W, "/stars")); assert "My Stars" in texts(r)[0] and "@PremiumBot" in texts(r)[0]; print("/stars (en) ok")
    r = await feed(msg(V, "🌐 Til")); assert "inline_keyboard" in r[0][1]["reply_markup"]; print("language button ok")

    # ---------- support desk ----------
    r = await feed(msg(W, "/support")); assert "Support" in texts(r)[0]
    r = await feed(msg(W, "My payment did not go through")); assert "Request <b>#1</b>" in texts(r)[-1], texts(r); 
    to_admin = [c for c in r if c[0] == "sendMessage" and c[1]["chat_id"] == 900]; assert to_admin and "Обращение #1" in to_admin[0][1]["text"]
    print("ticket created, admin notified:", to_admin[0][1]["text"].replace("\n", " | ")[:90])
    assert await db.open_tickets_of(W) == 1
    # admin by username becomes admin on first message
    A_ID = 777
    a_msg = msg(A_ID, "/stats"); a_msg["message"]["from"]["username"] = "artyomglupech"
    r = await feed(a_msg); assert await db.is_admin(A_ID); txt = texts(r)[0]; print("username admin:", txt.replace("\n", " | ")[:120])
    assert "Пользователей всего" in txt
    r = await feed(msg(555, "/stats")); assert "Пользователей всего" not in " ".join(texts(r)), "non-admin must not see stats"
    # admin replies through the button and by swipe
    r = await feed(cb(900, "tk:reply:1")); r = await feed(msg(900, "Please retry now, fixed")); 
    out = [c for c in r if c[0] == "sendMessage" and c[1]["chat_id"] == W]; assert out and "Support reply to request #1" in out[0][1]["text"]; print("reply delivered in English:", out[0][1]["text"][:60].replace("\n", " "))
    assert (await db.get_ticket(1))["status"] == "answered"
    r = await feed(msg(W, "/support")); await feed(msg(W, "Second problem"))
    await db.link_ticket_msg(900, 4242, 2)
    r = await feed(msg(900, "Done", reply_to_message={"message_id": 4242, "date": int(time.time()), "chat": {"id": 900, "type": "private"}}))
    assert any(c[0] == "sendMessage" and c[1]["chat_id"] == W and "request #2" in c[1]["text"] for c in r); print("swipe-reply ok")
    r = await feed(msg(900, "/tickets")); print("tickets:", texts(r)[0].replace("\n", " | ")[:70])
    # limit of open tickets
    for i in range(4):
        await feed(msg(W, "/support")); r = await feed(msg(W, f"again {i}"))
    assert await db.open_tickets_of(W) == 3 and "several requests" in texts(r)[-1]; print("open-ticket limit ok")

    # ---------- free tools ----------
    T = 400
    await feed(msg(T, "/start")); await feed(cb(T, "lang:en")); await db.credit(T, 250, "admin")
    r = await feed(msg(T, "📊 Slides")); assert "Free slides" in texts(r)[0]
    r = await feed(msg(T, "Digital marketing, 8 slides")); docs_out = [c for c in r if c[0] == "sendDocument"]
    assert docs_out and docs_out[0][1]["caption"].startswith("✅ Done: 2 slides"), r; print("slides ok:", docs_out[0][1]["caption"])
    assert any("exactly 8 content slides" in c["system"] and "English" in c["system"] for c in fake.calls[-3:])
    r = await feed(cb(T, "th:dark")); d = [c for c in r if c[0] == "sendDocument"]; assert d, r; print("restyle ok")
    assert sum(1 for c in fake.calls if "editor of presentation decks" in c["system"]) >= 1; print("refine pass ran")
    r = await feed(msg(T, "🕵️ AI check")); assert "AI check" in texts(r)[0]
    r = await feed(msg(T, "short text")); assert "at least" in texts(r)[0]
    r = await feed(msg(T, "Таким образом, это очень длинный текст. " * 20)); rep = texts(r)[-1]
    assert "74%" in rep and "Одинаковый ритм" in rep and "Таким образом" in rep and "approximate" in rep; print("ai check ok:", rep.replace("\n", " | ")[:110])
    r = await feed(msg(T, "🔁 Converter")); assert "File converter" in texts(r)[0]
    r = await feed(msg(T, document={"file_id": "f", "file_unique_id": "u", "file_name": "notes.txt", "file_size": 100}))
    kbd = r[-1][1]["reply_markup"]["inline_keyboard"]; print("convert targets:", [b["text"] for row in kbd for b in row]); assert any(b["callback_data"] == "cv:pdf" for row in kbd for b in row)
    r = await feed(cb(T, "cv:pdf")); d = [c for c in r if c[0] == "sendDocument"]; assert d and d[0][1]["caption"].startswith("✅ Done: notes.pdf"); print("convert ok:", d[0][1]["caption"])
    r = await feed(msg(T, document={"file_id": "f", "file_unique_id": "u", "file_name": "a.zip", "file_size": 100})); assert "not supported" in texts(r)[0]
    r = await feed(msg(T, "/cancel")); assert await db.tool_used_today(T, "slides") == 1 and await db.balance(T) == 250 - 50 - 50 - 50, await db.balance(T)
    print("slides, AI check and conversion each cost 50:", await db.balance(T), "left")
    r = await feed(msg(T, "📊 Slides")); r = await feed(msg(T, "🧮 Problems & code")); assert "Technical expert" in texts(r)[0]; print("menu button leaves a tool ok")
    await db.charge(T, 50, "admin"); assert await db.balance(T) == 50
    await feed(msg(T, "📊 Slides")); r = await feed(msg(T, "Another topic")); assert await db.balance(T) == 0 and any(c[0] == "sendDocument" for c in r)
    await feed(msg(T, "📊 Slides")); r = await feed(msg(T, "One more topic")); assert "Not enough Stars" in texts(r)[0], texts(r); print("tool refused with an empty wallet:", texts(r)[0][:50])

    # ---------- Uzbek cards: transfer + receipt, and Click/Payme provider ----------
    P = 500
    await feed(msg(P, "/start")); await feed(cb(P, "lang:uz"))
    r = await feed(cb(P, "topm:card")); assert "1 ⭐ = 1 200 so'm" in texts(r)[0]; print("card top-up asks the amount (uz):", texts(r)[0][:50])
    r = await feed(msg(P, "x")); assert "butun son" in texts(r)[0]
    r = await feed(msg(P, "30")); card_txt = texts(r)[0]; assert "8600 1234 5678 9012" in card_txt and "36 000 so'm" in card_txt and "30 ⭐" in card_txt and "TEST HOLDER" in card_txt; print("card instructions ok: 30 ⭐ = 36 000 so'm")
    r = await feed(cb(P, "card:paid:30")); assert "skrinshoti" in texts(r)[0]
    r = await feed(msg(P, "hello")); assert "skrinshoti yoki rasmi kerak" in texts(r)[0]
    r = await feed(msg(P, photo=[{"file_id": "p", "file_unique_id": "pu", "width": 10, "height": 10}]))
    to_adm = [c for c in r if c[0] == "sendMessage" and c[1]["chat_id"] == 900 and "Пополнение картой" in c[1]["text"]]; assert to_adm and any(c[0] == "copyMessage" for c in r) and "30 ⭐" in to_adm[0][1]["text"]
    print("receipt sent to admin:", to_adm[0][1]["text"].replace("\n", " | ")[:90])
    r = await feed(cb(P, "card:paid:30")); assert "tekshiruvda" in texts(r)[0]; print("second request while pending blocked")
    r = await feed(cb(900, "cp:ok:1")); assert await db.balance(P) == 30 and any("30 ⭐" in c[1].get("text", "") for c in r if c[0] == "sendMessage" and c[1]["chat_id"] == P); print("approved -> 30 ⭐ credited, user notified in uz")
    r = await feed(cb(900, "cp:ok:1")); assert await db.balance(P) == 30; print("double approval does not credit twice")
    await feed(cb(P, "topm:card")); await feed(msg(P, "5")); await feed(cb(P, "card:paid:5")); await feed(msg(P, photo=[{"file_id": "p2", "file_unique_id": "pu2", "width": 10, "height": 10}]))
    r = await feed(cb(900, "cp:no:2")); assert any("tasdiqlanmadi" in c[1].get("text", "") for c in r if c[0] == "sendMessage" and c[1]["chat_id"] == P); assert await db.balance(P) == 30; print("rejected ok")
    await feed(cb(P, "topm:payp")); r = await feed(msg(P, "5")); inv = [c for c in r if c[0] == "sendInvoice"][0][1]
    assert inv["currency"] == "UZS" and inv["prices"][0]["amount"] == 5 * 1200 * 100 and inv["payload"] == f"topu:{P}:5" and inv["provider_token"].startswith("123:"); print("provider invoice ok:", inv["currency"], inv["prices"][0]["amount"])
    assert ok(await feed(pre(P, 600000, f"topu:{P}:5", "UZS"))) == [True] and ok(await feed(pre(P, 600000, f"topu:{P}:6", "UZS"))) == [False] and ok(await feed(pre(P, 600000, f"topu:{P}:5", "XTR"))) == [False]
    print("UZS pre-checkout ok")
    pay2 = msg(P, successful_payment={"currency": "UZS", "total_amount": 600000, "invoice_payload": f"topu:{P}:5", "telegram_payment_charge_id": "chu1", "provider_payment_charge_id": "ppu"})
    await feed(pay2); await feed(pay2); assert await db.balance(P) == 35; print("Click/Payme top-up credited 5 ⭐ once")
    r = await feed(msg(900, "/stats")); assert "Пополнили кошелёк" in texts(r)[0]; print("stats:", texts(r)[0].replace("\n", " | ")[:260])

    # ---------- admin tools ----------
    r = await feed(msg(900, "/stats")); print("admin stats:", texts(r)[0].replace("\n", " | "))
    r = await feed(msg(900, "/users")); assert "Пользователи:" in texts(r)[0]; print("users list ok:", texts(r)[0].count("•"), "rows")
    r = await feed(msg(900, "/user @u100")); assert "Запросов всего" in texts(r)[0]; print("user card ok")
    r = await feed(msg(900, "/grant 555 80")); print("grant:", texts(r)[0]); assert await db.balance(555) == 80
    r = await feed(msg(900, "/grant 555 -30")); assert await db.balance(555) == 50; r = await feed(msg(900, "/grant 555 -500")); assert await db.balance(555) == 50 and "нельзя" in texts(r)[0]; print("debit works and cannot go below zero")
    r = await feed(msg(900, f"/ban {V}")); assert "заблокирован" in texts(r)[0]
    r = await feed(msg(V, "hello")); assert "ограничен" in texts(r)[0] or "cheklangan" in texts(r)[0]; print("banned user blocked:", texts(r)[0])
    r = await feed(msg(900, f"/unban {V}")); r = await feed(msg(V, "Salom")); assert "o'zbekcha" in fake.calls[-1]["system"]; print("unban ok")
    r = await feed(msg(900, f"/ban 900")); assert "нельзя" in texts(r)[0]
    r = await feed(msg(777, "/addadmin 100")); assert "только владелец" in texts(r)[0]; print("only owner adds admins ok")
    r = await feed(msg(900, "/addadmin 100")); assert await db.is_admin(100); r = await feed(msg(900, "/rmadmin 100")); assert not await db.is_admin(100)
    await feed(msg(900, "/broadcast")); r = await feed(msg(900, "Всем привет, обновление бота")); assert "Отправить это сообщение" in texts(r)[0]
    r = await feed(cb(900, "bc:go")); done = [x for x in texts(r) if "Готово" in x]; assert done; print("broadcast:", done[0])
    sent = [c for c in r if c[0] == "copyMessage"]; assert len(sent) >= 4 and all(c[1]["from_chat_id"] == 900 for c in sent)
    r = await feed(msg(900, "/admins")); assert "artyomglupech" in texts(r)[0] or "777" in texts(r)[0]; print("admins list ok")
    # ---------- three free actions, then the wallet ----------
    object.__setattr__(s, "free_actions", 3)                      # the rest of the run assumed a paid-only wallet
    F = 600
    r = await feed(msg(F, "/start")); await feed(cb(F, "lang:ru"))
    r = await feed(msg(F, "/start")); assert any("Бесплатных действий для начала: <b>3</b>" in x for x in texts(r)); print("welcome mentions the 3 free actions")
    r = await feed(msg(F, "/wallet")); assert "Бесплатных действий осталось: <b>3</b>" in texts(r)[0]
    r = await feed(msg(F, "Первый вопрос")); assert "🎁 бесплатное действие, осталось: 2" in texts(r)[0] and await db.balance(F) == 0; print("1st action free:", texts(r)[0][-45:].replace("\n", " "))
    before = await db.free_used(F); r = await feed(msg(F, "ОШИБКА")); assert await db.free_used(F) == before, "a failed free action must stay available"; print("failed free action is given back")
    r = await feed(msg(F, "Второй вопрос")); assert "осталось: 1" in texts(r)[0]
    await feed(msg(F, "📊 Слайды")); r = await feed(msg(F, "Цифровой маркетинг")); assert any(c[0] == "sendDocument" and "осталось: 0" in c[1]["caption"] for c in r); print("3rd action (slides) free too")
    r = await feed(msg(F, "Четвёртый вопрос")); assert "Недостаточно звёзд" in texts(r)[0] and await db.balance(F) == 0; print("4th action needs Stars:", texts(r)[0][:40])
    await db.credit(F, 50, "admin"); r = await feed(msg(F, "Четвёртый вопрос")); assert "−50 ⭐ · баланс: 0 ⭐" in texts(r)[0]; print("paid from the wallet after the free ones")
    print("ALL OK")
async def runner():
    try:
        await main()
    finally:
        await asyncio.sleep(0)
asyncio.run(runner())
