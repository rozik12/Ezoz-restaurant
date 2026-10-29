"""End-to-end check against fake Telegram and fake Claude: python tests/smoke.py"""
import asyncio, io, os, sys, tempfile, time
os.environ.update(BOT_TOKEN="123456:TEST", ANTHROPIC_API_KEY="test", DB_PATH=tempfile.mktemp(suffix=".db"),
                  ADMIN_IDS="900", FREE_DAILY="3", PAID_DAILY="6", PRICE_STARS="300")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, Message, Chat, File
import fmt
from config import Settings
from db import Database
from handlers import router
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
        if name in ("sendMessage", "sendInvoice"):
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
    bot = Bot("123456:TEST", session=Mock()); dp = Dispatcher(storage=MemoryStorage(), db=db, ai=ai, settings=s); dp.include_router(router)
    async def feed(d):
        calls.clear(); await dp.feed_update(bot, Update.model_validate(d, context={"bot": bot})); return list(calls)
    texts = lambda r: [c[1].get("text", "") for c in r if c[0] == "sendMessage"]
    U = 100
    r = await feed(msg(U, "/start")); print("start:", texts(r)[0][:50].replace("\n", " "), "| menu buttons:", len(r[0][1]["reply_markup"]["keyboard"]) * 2)
    r = await feed(msg(U, "✍️ Писать работу")); print("mode intro:", texts(r)[0][:40])
    r = await feed(msg(U, "Курсовая по маркетингу, 30 страниц")); out = texts(r)
    print("answer html:", out[0].replace("\n", " | "))
    c = fake.calls[-1]
    assert "OmniStudent" in c["system"] and "Академический писатель" in c["system"] and "Тариф: бесплатный" in c["system"], "prompt parts"
    assert c["max_tokens"] == s.free_max_tokens and c["messages"][-1]["role"] == "user"
    print("system prompt ok, free max_tokens =", c["max_tokens"])
    r = await feed(msg(U, "А теперь план"))
    assert len(fake.calls[-1]["messages"]) == 3, fake.calls[-1]["messages"]            # user, assistant, user
    print("memory ok: history sent =", len(fake.calls[-1]["messages"]), "messages")
    r = await feed(msg(U, "ДЛИННО")); assert "обрезан" in texts(r)[0] and "/subscribe" in texts(r)[0]; print("truncation note for free plan ok")
    r = await feed(msg(U, "ещё вопрос")); t = texts(r)[0]; print("limit reached:", t[:60]); assert "бесплатные запросы закончились" in t and "inline_keyboard" in r[0][1]["reply_markup"]
    r = await feed(cb(U, "pay")); inv = [c for c in r if c[0] == "sendInvoice"][0][1]
    print("invoice:", inv["currency"], inv["prices"], inv["payload"]); assert inv["currency"] == "XTR" and inv["prices"][0]["amount"] == 300
    pre = {"update_id": 9001, "pre_checkout_query": {"id": "p1", "from": user(U), "currency": "XTR", "total_amount": 300, "invoice_payload": f"sub:{U}"}}
    r = await feed(pre); print("pre-checkout answer:", [c[1]["ok"] for c in r if c[0] == "answerPreCheckoutQuery"])
    bad = dict(pre, update_id=9002); bad["pre_checkout_query"] = dict(pre["pre_checkout_query"], total_amount=1)
    r = await feed(bad); print("wrong amount rejected:", [c[1]["ok"] for c in r if c[0] == "answerPreCheckoutQuery"])
    pay = msg(U, successful_payment={"currency": "XTR", "total_amount": 300, "invoice_payload": f"sub:{U}", "telegram_payment_charge_id": "ch1", "provider_payment_charge_id": "pp"})
    r = await feed(pay); print("paid:", texts(r)[0][:60]); assert await db.is_paid(U)
    await feed(pay); assert len(await db._scalar("SELECT COUNT(*) FROM payments") and [1]) == 1 and await db._scalar("SELECT COUNT(*) FROM payments") == 1, "duplicate payment update must not extend twice"
    r = await feed(msg(U, "после оплаты")); assert fake.calls[-1]["max_tokens"] == s.paid_max_tokens and "Тариф: подписка" in fake.calls[-1]["system"]
    print("paid plan: max_tokens =", fake.calls[-1]["max_tokens"])
    r = await feed(msg(U, "ОШИБКА")); print("API error shown nicely:", texts(r)[0][:70])
    assert len(await db.history(U, 50)) % 2 == 0, "failed question must not stay in history"
    # exam mode, files
    r = await feed(cb(U, "mode:exam")); r = await feed(msg(U, "Начинай, тема: цифровой маркетинг")); assert "Вредный преподаватель" in fake.calls[-1]["system"]; print("exam mode prompt ok")
    doc = msg(U, document={"file_id": "f", "file_unique_id": "u", "file_name": "lecture.txt", "file_size": 100}, caption="Сделай шпаргалку")
    r = await feed(doc); last = fake.calls[-1]["messages"][-1]["content"]; assert "Лекция: интеграл" in last and "Сделай шпаргалку" in last; print("document read ok, sent to model:", last[:50].replace("\n", " "))
    r = await feed(msg(U, document={"file_id": "f", "file_unique_id": "u", "file_name": "photo.png", "file_size": 100})); print("unsupported file:", texts(r)[0][:50])
    # admin
    r = await feed(msg(555, "/stats")); assert not r, "non-admin must get no reply"
    r = await feed(msg(900, "/stats")); print("admin stats:", texts(r)[0].replace("\n", " | "))
    r = await feed(msg(900, "/grant 555 30")); print("grant:", texts(r)[0])
    assert await db.is_paid(555)
    r = await feed(msg(U, "/new")); assert await db.history(U) == []; print("/new clears history ok")
    r = await feed(msg(U, "/paysupport")); print("paysupport:", texts(r)[0][:40])
    print("ALL OK")
async def runner():
    try:
        await main()
    finally:
        await asyncio.sleep(0)
asyncio.run(runner())
