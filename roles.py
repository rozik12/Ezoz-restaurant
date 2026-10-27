"""Role resolution. The role is looked up from the Telegram id on every update, so changes apply instantly."""
from __future__ import annotations

from enum import StrEnum

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import OWNER_ID
from db import Database


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    GUEST = "guest"


async def resolve_role(user_id: int, db: Database) -> Role:
    if user_id == OWNER_ID:
        return Role.OWNER
    if await db.is_admin(user_id):
        return Role.ADMIN
    return Role.GUEST


class HasRole(BaseFilter):
    """Passes only when the sender holds one of the given roles. `db` is injected from dispatcher data."""

    def __init__(self, *roles: Role) -> None:
        self.roles = set(roles)

    async def __call__(self, event: Message | CallbackQuery, db: Database) -> bool:
        if event.from_user is None:
            return False
        return await resolve_role(event.from_user.id, db) in self.roles
