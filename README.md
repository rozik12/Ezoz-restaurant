# OmniStudent bot

Academic assistant for students in Telegram (Claude API): coursework and essays, solving problems and code, editing and
translation, study cheat sheets and the "Tough professor" exam simulator. Reads .txt, .md, .pdf and .docx files.
Free plan with a daily limit; subscription paid in Telegram Stars unlocks long answers and a higher limit.

## Run
```bash
pip install -r requirements.txt
cp .env.example .env     # BOT_TOKEN, ANTHROPIC_API_KEY, ADMIN_IDS
python main.py
python tests/smoke.py    # end-to-end check on fake Telegram and fake Claude
```

## Admin commands (ADMIN_IDS only)
`/stats`, `/grant ID DAYS` (grant or extend a subscription), `/refund USER_ID CHARGE_ID` (refund Stars).

## Notes
- The system prompt lives in `prompts.py`; the bot appends only the answer format, the current mode and the plan (free or paid).
- Telegram requires bots that take Stars to answer `/paysupport`; set `SUPPORT_CONTACT` to your contact.
- `MemoryStorage` and SQLite are enough for one instance; keep the database on a persistent volume when deploying.

## Languages, support and admin tools

* The bot speaks Russian, Uzbek and English (`i18n.py`). A new user picks a language on `/start`; `🌐` or `/lang` changes it later.
* **Support:** users tap `🆘 Support` (or `/support`) and write one message. Every administrator receives it with the buttons
  *Reply / Close / Profile*; a swipe-reply to the message also answers the client. Replies come back in the client's language.
* **Admins:** ids in `ADMIN_IDS` are owners; usernames in `ADMIN_USERNAMES` become admins on their first message.
  `/admin` opens the panel: statistics (users, new, active, subscribers, requests, languages, tickets), user list and cards,
  subscription grant/revoke, ban/unban, refunds, tickets, broadcast, admin list. Only owners use `/addadmin` and `/rmadmin`.

## Free tools

* **📊 Slides** (`/slides`): a topic (optionally "12 slides") or a file becomes a ready `.pptx` with speaker notes. No invented sources.
* **🔁 Converter** (`/convert`): .docx, .pdf, .txt, .md, .pptx convert to each other; photos (.jpg, .png) become PDF.
  Headings, paragraphs and lists are kept; complex layout is simplified; scanned PDFs without a text layer are not supported.
* **🕵️ AI check** (`/detect`): an estimate of how machine-like a text reads, with the most generic passages and advice.
  It is an orientation, not proof; real detectors differ.

Daily limits are separate from chat requests (`SLIDES_DAILY`, `DETECT_DAILY`, `CONVERT_DAILY`; subscribers get triple).
