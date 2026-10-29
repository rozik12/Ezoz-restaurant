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
    paid_max_tokens: int
    prices: dict
    topup_presets: tuple[int, ...]
    topup_max: int
    welcome_bonus: int
    uzs_per_star: int
    card_number: str
    card_holder: str
    provider_token: str
    db_path: str
    support_contact: str

    @property
    def card_ready(self) -> bool:
        """Payment by transfer to an Uzbek card needs the card and the so'm price of one Star."""
        return bool(self.card_number and self.uzs_per_star)

    @property
    def provider_ready(self) -> bool:
        return bool(self.provider_token and self.uzs_per_star)

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
            paid_max_tokens=min(_int("MAX_TOKENS", 8000), 8192),               # DeepSeek allows up to 8192 output tokens
            prices={k: _int(f"PRICE_{k.upper()}", 50) for k in ("chat", "slides", "detect", "convert")},     # Stars per action
            topup_presets=tuple(int(x) for x in os.getenv("TOPUP_PRESETS", "50,100,250,500,1000").replace(" ", "").split(",") if x.isdigit()),
            topup_max=min(_int("TOPUP_MAX", 10000), 10000),                      # Telegram's ceiling for one Stars invoice
            welcome_bonus=_int("WELCOME_BONUS", 0),
            uzs_per_star=_int("UZS_PER_STAR", 0),
            card_number=os.getenv("CARD_NUMBER", "").strip(),
            card_holder=os.getenv("CARD_HOLDER", "").strip(),
            provider_token=os.getenv("PAYMENT_PROVIDER_TOKEN", "").strip(),
            db_path=os.getenv("DB_PATH", "omnistudent.db").strip(),
            support_contact=os.getenv("SUPPORT_CONTACT", "").strip(),
        )
