"""Central configuration. Secrets come from environment variables (.env), never from source."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Hardcoded on purpose: the Owner is the only account that can manage administrators.
OWNER_ID: int = 8219891075


def _int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else None


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_chat_id: int | None
    db_path: str
    menu_pdf_path: Path
    website_url: str
    instagram: str
    telegram_channel: str
    facebook: str
    address: str
    phone: str
    admin_lang: str
    logo_path: Path
    # Meta Graph API
    graph_version: str
    ig_user_id: str
    meta_access_token: str
    fb_page_id: str
    fb_page_token: str
    media_dir: Path
    public_media_base_url: str
    # YouTube Data API
    yt_client_id: str
    yt_client_secret: str
    yt_refresh_token: str

    @classmethod
    def load(cls) -> "Settings":
        token = _str("BOT_TOKEN")
        if not token:
            raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        return cls(
            bot_token=token,
            admin_chat_id=_int("ADMIN_CHAT_ID"),
            db_path=_str("DB_PATH", "ezoz.db"),
            menu_pdf_path=Path(_str("MENU_PDF_PATH", "assets/ezoz_menu.pdf")),
            website_url=_str("WEBSITE_URL"),
            instagram=_str("INSTAGRAM_URL"),
            telegram_channel=_str("TELEGRAM_CHANNEL_URL"),
            facebook=_str("FACEBOOK_URL"),
            address=_str("ADDRESS"),
            phone=_str("PHONE"),
            admin_lang=_str("ADMIN_LANG", "ru"),
            logo_path=Path(_str("LOGO_PATH", "assets/logo.jpg")),
            graph_version=_str("GRAPH_VERSION", "v21.0"),
            ig_user_id=_str("IG_USER_ID"),
            meta_access_token=_str("META_ACCESS_TOKEN"),
            fb_page_id=_str("FB_PAGE_ID"),
            fb_page_token=_str("FB_PAGE_TOKEN"),
            media_dir=Path(_str("MEDIA_DIR", "media_tmp")),
            public_media_base_url=_str("PUBLIC_MEDIA_BASE_URL").rstrip("/"),
            yt_client_id=_str("YT_CLIENT_ID"),
            yt_client_secret=_str("YT_CLIENT_SECRET"),
            yt_refresh_token=_str("YT_REFRESH_TOKEN"),
        )


settings = Settings.load()
