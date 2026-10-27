"""Small HTTP API for the website booking form: POST /api/lead -> saved lead + instant staff notification."""
from __future__ import annotations

import html
import logging
import re
import time
from datetime import date

from aiohttp import web
from aiogram import Bot

from config import settings
from db import Database
from i18n import fmt_date, money, t
from services import pricing
from services.notify import notify_staff

log = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{7,17}\d$")
RATE_WINDOW = 3600
ATTEMPT_LIMIT, SUCCESS_LIMIT = 40, 5        # per IP per hour: attempts include typos, successes are real leads
_attempts: dict[str, list[float]] = {}
_successes: dict[str, list[float]] = {}


def _cors(request: web.Request) -> dict[str, str]:
    origin = request.headers.get("Origin", "").rstrip("/")
    allowed = settings.site_origins
    if "*" in allowed:
        return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"}
    if origin in allowed:
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin", "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"}
    return {}


def _json(request: web.Request, payload: dict, status: int = 200) -> web.Response:
    return web.json_response(payload, status=status, headers=_cors(request))


def _recent(store: dict[str, list[float]], ip: str) -> list[float]:
    now = time.time()
    store[ip] = [h for h in store.get(ip, []) if now - h < RATE_WINDOW]
    return store[ip]


def _rate_limited(ip: str) -> bool:
    if len(_recent(_successes, ip)) >= SUCCESS_LIMIT or len(_recent(_attempts, ip)) >= ATTEMPT_LIMIT:
        return True
    _attempts[ip].append(time.time())
    return False


async def options(request: web.Request) -> web.Response:
    return web.Response(status=204, headers=_cors(request))


async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def post_lead(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    db: Database = request.app["db"]
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (request.remote or "?")
    if _rate_limited(ip):
        return _json(request, {"ok": False, "error": "rate_limited"}, 429)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError
    except Exception:
        return _json(request, {"ok": False, "error": "bad_json"}, 400)
    if str(data.get("website", "")).strip():            # honeypot field: real visitors never fill it in
        return _json(request, {"ok": True})

    name = str(data.get("name", "")).strip()[:80]
    phone = str(data.get("phone", "")).strip()[:30]
    lang = data.get("lang") if data.get("lang") in ("en", "ru", "uz") else "ru"
    try:
        event_date = date.fromisoformat(str(data.get("date", "")))
    except ValueError:
        return _json(request, {"ok": False, "error": "bad_date"}, 400)
    if len(name) < 2:
        return _json(request, {"ok": False, "error": "bad_name"}, 400)
    if not PHONE_RE.match(phone):
        return _json(request, {"ok": False, "error": "bad_phone"}, 400)
    if event_date < date.today() or (event_date - date.today()).days > 730:
        return _json(request, {"ok": False, "error": "bad_date"}, 400)
    guests = data.get("guests")
    guests = int(guests) if str(guests).isdigit() and 1 <= int(guests) <= 2000 else None
    tier = data.get("tier") if data.get("tier") in pricing.PER_GUEST_UZS else None
    est = data.get("estimate")
    est = int(est) if str(est).isdigit() and int(est) < 10**11 else None

    lead_id = await db.add_lead(user_id=0, name=name, username=None, phone=phone, event_date=event_date.isoformat(),
                                guests=guests, tier=tier, estimate_uzs=est, lang=lang)
    al = settings.admin_lang
    lines = [t(al, "lead_title", id=lead_id), f"👤 {html.escape(name)}", f"📞 {html.escape(phone)}",
             f"📅 {fmt_date(al, event_date)}"]
    if guests:
        lines.append(t(al, "lead_guests", guests=guests, tier=t(al, "tier_" + tier) if tier else t(al, "lead_tier_none")))
    if est:
        lines.append(t(al, "lead_estimate", total=money(al, est)))
    lines += [t(al, "lead_lang", code=lang.upper()), t(al, "lead_source_site")]
    await notify_staff(bot, db, "\n".join(lines))
    _successes[ip].append(time.time())
    log.info("Website lead #%s saved", lead_id)
    return _json(request, {"ok": True, "id": lead_id})


def create_app(bot: Bot, db: Database) -> web.Application:
    app = web.Application(client_max_size=16 * 1024)
    app["bot"], app["db"] = bot, db
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/api/lead", post_lead)
    app.router.add_route("OPTIONS", "/api/lead", options)
    return app


async def start_web(bot: Bot, db: Database) -> web.AppRunner | None:
    if not settings.web_port:
        log.info("PORT is not set: website API disabled")
        return None
    runner = web.AppRunner(create_app(bot, db))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", settings.web_port).start()
    log.info("Website API listening on port %s", settings.web_port)
    return runner
