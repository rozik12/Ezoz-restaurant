"""Banquet price estimate. The values below are the defaults; administrators change them in the bot and the
changes are stored in the database (key "prices") and applied in place, so every importer sees them at once."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

PER_GUEST_UZS = {"standard": 250_000, "premium": 380_000, "royal": 560_000}
HALL_FEE_UZS = {"vip": 10_000_000, "terrace": 20_000_000, "ballroom": 35_000_000}
ADDON_UZS = {"show": 20_000_000, "decor": 30_000_000, "music": 15_000_000}

HALL_UZS_KEYS = ("ballroom", "vip", "terrace")

# Editable groups: pg = menu per guest, hf = hall fee, ad = add-ons. Values are whole UZS.
GROUPS = {"pg": PER_GUEST_UZS, "hf": HALL_FEE_UZS, "ad": ADDON_UZS}
LIMITS = {"pg": (10_000, 5_000_000), "hf": (0, 1_000_000_000), "ad": (0, 1_000_000_000)}
_DEFAULTS = {g: dict(d) for g, d in GROUPS.items()}


def snapshot() -> dict:
    """Current prices in the shape the website expects."""
    return {"perGuest": dict(PER_GUEST_UZS), "hallFee": dict(HALL_FEE_UZS), "addons": dict(ADDON_UZS)}


async def load_prices(db) -> None:
    """Apply saved prices over the defaults. Bad or unknown entries are ignored."""
    raw = await db.get_kv("prices")
    if not raw:
        return
    try:
        saved = json.loads(raw)
        for g, table in GROUPS.items():
            lo, hi = LIMITS[g]
            for key, value in (saved.get(g) or {}).items():
                if key in table and isinstance(value, int) and lo <= value <= hi:
                    table[key] = value
    except (ValueError, AttributeError):
        log.exception("Saved prices are unreadable, using defaults")


async def save_price(db, group: str, key: str, value: int) -> int:
    """Validate, apply and persist one price. Returns the previous value."""
    if group not in GROUPS or key not in GROUPS[group]:
        raise KeyError(f"{group}:{key}")
    lo, hi = LIMITS[group]
    if not lo <= value <= hi:
        raise ValueError("out of range")
    old = GROUPS[group][key]
    GROUPS[group][key] = value
    await db.set_kv("prices", json.dumps({g: dict(t) for g, t in GROUPS.items()}))
    return old

MIN_GUESTS, MAX_GUESTS = 50, 500


def hall_for(guests: int) -> str:
    return "vip" if guests <= 120 else "terrace" if guests <= 250 else "ballroom"


@dataclass(frozen=True)
class Estimate:
    guests: int
    tier: str
    addons: tuple[str, ...]
    hall: str
    menu: int
    hall_fee: int
    extras: int

    @property
    def total(self) -> int:
        return self.menu + self.hall_fee + self.extras


def estimate(guests: int, tier: str, addons: list[str] | tuple[str, ...]) -> Estimate:
    hall = hall_for(guests)
    return Estimate(
        guests=guests,
        tier=tier,
        addons=tuple(addons),
        hall=hall,
        menu=guests * PER_GUEST_UZS[tier],
        hall_fee=HALL_FEE_UZS[hall],
        extras=sum(ADDON_UZS[a] for a in addons),
    )
