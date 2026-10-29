"""Settings. Secrets come from environment variables (.env), never from source."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def _ids(name: str) -> tuple[int, ...]:
    return tuple(int(x) for x in os.getenv(name, "").replace(" ", "").split(",") if x.isdigit())


@dataclass(frozen=True)
class Settings:
    bot_token: str
    gemini_key: str
    gemini_model: str
    deepseek_key: str
    deepseek_model: str
    anthropic_key: str
    model: str
    admin_ids: tuple[int, ...]
    admin_usernames: tuple[str, ...]
    free_daily: int
    paid_daily: int
    free_max_tokens: int
    paid_max_tokens: int
    price_stars: int
    sub_days: int
    db_path: str
    support_contact: str

    @classmethod
    def load(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        return cls(
            bot_token=token,
            gemini_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip(),
            deepseek_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            anthropic_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5").strip(),
            admin_ids=_ids("ADMIN_IDS"),
            admin_usernames=tuple(x.lstrip("@").lower() for x in os.getenv("ADMIN_USERNAMES", "").replace(" ", "").split(",") if x),
            free_daily=_int("FREE_DAILY", 5),
            paid_daily=_int("PAID_DAILY", 100),
            free_max_tokens=_int("FREE_MAX_TOKENS", 1800),
            paid_max_tokens=min(_int("PAID_MAX_TOKENS", 8000), 8192),          # DeepSeek allows up to 8192 output tokens
            price_stars=_int("PRICE_STARS", 300),
            sub_days=_int("SUB_DAYS", 30),
            db_path=os.getenv("DB_PATH", "omnistudent.db").strip(),
            support_contact=os.getenv("SUPPORT_CONTACT", "").strip(),
        )
