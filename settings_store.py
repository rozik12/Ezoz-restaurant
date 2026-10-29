"""Settings an administrator can change from the bot. Values live in the database and override the environment at start-up."""
from __future__ import annotations

from dataclasses import dataclass

from config import Settings
from db import Database


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str                       # "int" or "str"
    low: int = 0
    high: int = 10_000_000


FIELDS = (
    Field("price_chat", "Цена вопроса ассистенту, ⭐", "int", 0, 100_000),
    Field("price_slides", "Цена презентации, ⭐", "int", 0, 100_000),
    Field("price_detect", "Цена проверки на ИИ, ⭐", "int", 0, 100_000),
    Field("price_convert", "Цена конвертации, ⭐", "int", 0, 100_000),
    Field("free_actions", "Бесплатных действий новичку", "int", 0, 1000),
    Field("welcome_bonus", "Приветственный бонус, ⭐", "int", 0, 100_000),
    Field("uzs_per_star", "Цена 1 ⭐ в сумах (для карты и Click/Payme)", "int", 0, 10_000_000),
    Field("card_number", "Номер карты для переводов", "str"),
    Field("card_holder", "Получатель карты", "str"),
)
BY_KEY = {f.key: f for f in FIELDS}


def get(settings: Settings, key: str):
    return settings.prices[key[6:]] if key.startswith("price_") else getattr(settings, key)


def apply(settings: Settings, key: str, value) -> None:
    if key.startswith("price_"):
        settings.prices[key[6:]] = value
    else:
        setattr(settings, key, value)


def parse(field: Field, raw: str):
    """Returns the value, or raises ValueError with a message for the administrator."""
    raw = raw.strip()
    if field.kind == "int":
        raw = raw.replace(" ", "")
        if not raw.isdigit() or not field.low <= int(raw) <= field.high:
            raise ValueError(f"Нужно целое число от {field.low} до {field.high}.")
        return int(raw)
    if raw in ("-", "—", "0"):
        return ""
    if len(raw) > 60 or "\n" in raw:
        raise ValueError("Слишком длинно: до 60 знаков в одну строку. Чтобы очистить поле, пришлите «-».")
    return raw


async def load(db: Database, settings: Settings) -> None:
    for f in FIELDS:
        stored = await db.get_kv("set:" + f.key)
        if stored is not None:
            apply(settings, f.key, int(stored) if f.kind == "int" else stored)


async def save(db: Database, settings: Settings, key: str, value) -> None:
    await db.set_kv("set:" + key, str(value))
    apply(settings, key, value)
