# E'zoz Tashkent bot (aiogram 3)

Roles are resolved from the sender's Telegram ID on every update:

| Role | Who | Features |
|------|-----|----------|
| Owner | `OWNER_ID` in `config.py` | statistics, add/remove administrators, broadcast, plus all admin features |
| Admin | IDs stored in the `admins` table | new cross-post (Instagram, Facebook, YouTube Shorts), recent leads |
| Guest | everyone else | halls, menu PDF, cost calculator, booking |

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set BOT_TOKEN and ADMIN_CHAT_ID
mkdir assets && cp /path/to/menu.pdf assets/ezoz_menu.pdf
python main.py
```
To get `ADMIN_CHAT_ID`: add the bot to the working group, send any message, and open
`https://api.telegram.org/bot<TOKEN>/getUpdates` to read `chat.id` (negative for groups).

## Layout
```
main.py            dispatcher, middleware, router order
config.py          settings from .env, hardcoded OWNER_ID
db.py              SQLite: users, admins, leads, events
roles.py           Role enum, HasRole filter
states.py          FSM groups (post, booking, calculator, owner)
keyboards.py       all inline/reply keyboards
handlers/          common (start, cancel, fallback), guest, admin, owner
services/          pricing (calculator), social (Meta + YouTube), notify (lead forwarding)
```

## Before going live
- Revoke any token that was ever pasted into a chat (`/revoke` in @BotFather) and put the new one only in `.env`.
- Cross-posting: fill the Meta and YouTube values in `.env`. Meta downloads media from a public HTTPS URL, so
  `MEDIA_DIR` must be served at `PUBLIC_MEDIA_BASE_URL`. Platforms without credentials report "not configured".
- Prices in `services/pricing.py` are examples. Hall descriptions are in `handlers/guest.py`.
- `MemoryStorage` forgets conversations on restart; use `RedisStorage` for production.
- Telegram bots can download files up to 20 MB; for larger videos run a local Bot API server.
