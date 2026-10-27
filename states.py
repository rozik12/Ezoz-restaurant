"""FSM state groups, one per workflow."""
from aiogram.fsm.state import State, StatesGroup


class PostStates(StatesGroup):          # admin: new cross-post
    media = State()
    caption = State()
    platforms = State()
    confirm = State()


class BookingStates(StatesGroup):       # guest: book a date
    date = State()
    phone = State()


class CalcStates(StatesGroup):          # guest: cost calculator
    guests = State()
    tier = State()
    addons = State()


class OwnerStates(StatesGroup):         # owner: admin management and broadcast
    add_admin = State()
    broadcast = State()
    broadcast_confirm = State()
