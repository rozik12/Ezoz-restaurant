"""Filters on the role the access middleware injects: `is_admin` (real role) and `admin_view` (an admin who is not testing as a user)."""
from aiogram.filters import BaseFilter


class AdminView(BaseFilter):
    async def __call__(self, event, admin_view: bool = False) -> bool:
        return admin_view


class NotAdminView(BaseFilter):
    """Keeps the user-facing routers silent for an administrator working in the admin view."""

    async def __call__(self, event, admin_view: bool = False) -> bool:
        return not admin_view


class RealAdmin(BaseFilter):
    async def __call__(self, event, is_admin: bool = False) -> bool:
        return is_admin
