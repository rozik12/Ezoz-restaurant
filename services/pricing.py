"""Banquet price estimate. Example prices: replace with the hall's real price list."""
from __future__ import annotations

from dataclasses import dataclass

PER_GUEST_UZS = {"standard": 250_000, "premium": 380_000, "royal": 560_000}
HALL_FEE_UZS = {"vip": 10_000_000, "terrace": 20_000_000, "ballroom": 35_000_000}
ADDON_UZS = {"show": 20_000_000, "decor": 30_000_000, "music": 15_000_000}

TIER_LABEL = {"standard": "Standard", "premium": "Premium", "royal": "Royal"}
ADDON_LABEL = {"show": "Show program", "decor": "Custom decor", "music": "Live music"}
HALL_LABEL = {"vip": "VIP Hall", "terrace": "Summer Terrace", "ballroom": "Grand Ballroom"}

MIN_GUESTS, MAX_GUESTS = 50, 500


def hall_for(guests: int) -> str:
    return "vip" if guests <= 120 else "terrace" if guests <= 250 else "ballroom"


def fmt_uzs(value: float) -> str:
    return f"{round(value):,}".replace(",", " ") + " UZS"


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
