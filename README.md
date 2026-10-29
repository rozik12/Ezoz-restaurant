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
