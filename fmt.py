"""Turns the model's Markdown into Telegram-safe HTML and splits long answers into message-sized chunks."""
from __future__ import annotations

import html
import re

FENCE = re.compile(r"```[ \t]*([\w+#.-]*)[ \t]*\n(.*?)```", re.S)
MAX_CHUNK = 3000          # leaves room for HTML escaping and tags under Telegram's 4096-character limit


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    stash: list[str] = []

    def keep(markup: str) -> str:
        stash.append(markup)
        return f"\x00{len(stash) - 1}\x00"

    # tables and inline code are kept verbatim so later rules cannot touch them
    text = re.sub(r"((?:^\|.*(?:\n|$))+)", lambda m: keep(f"<pre>{m.group(1).rstrip()}</pre>\n"), text, flags=re.M)
    text = re.sub(r"`([^`\n]+)`", lambda m: keep(f"<code>{m.group(1)}</code>"), text)
    text = re.sub(r"^[ \t]*[-*•][ \t]+", "• ", text, flags=re.M)
    text = re.sub(r"^#{1,6}[ \t]+(.+)$", r"<b>\1</b>", text, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.S)
    text = re.sub(r"(?<![\*\w])\*(?![\s*])([^*\n]+?)(?<![\s*])\*(?![\*\w])", r"<i>\1</i>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)


def md_to_html(text: str) -> str:
    out, pos = [], 0
    for m in FENCE.finditer(text):
        out.append(_inline(text[pos:m.start()]))
        lang = re.sub(r"[^\w+#.-]", "", m.group(1))
        code = html.escape(m.group(2).rstrip("\n"), quote=False)
        out.append(f'<pre><code class="language-{lang}">{code}</code></pre>' if lang else f"<pre>{code}</pre>")
        pos = m.end()
    out.append(_inline(text[pos:]))
    return "".join(out)


def split_markdown(text: str, limit: int = MAX_CHUNK) -> list[str]:
    """Split on line boundaries; a code block that has to be cut is closed and reopened so every chunk stays valid."""
    chunks: list[str] = []
    cur: list[str] = []
    size = 0
    in_code, lang = False, ""

    def flush() -> None:
        nonlocal cur, size
        body = "\n".join(cur).strip("\n")
        if in_code:
            body += "\n```"
        if body.strip():
            chunks.append(body)
        cur, size = ([f"```{lang}"] if in_code else []), (len(lang) + 3 if in_code else 0)

    for raw in text.replace("\r\n", "\n").split("\n"):
        pieces = [raw[i:i + limit] for i in range(0, len(raw), limit)] or [""]     # an over-long line is cut hard
        for line in pieces:
            if size + len(line) + 1 > limit and cur:
                flush()
            cur.append(line)
            size += len(line) + 1
            if line.lstrip().startswith("```"):
                if in_code:
                    in_code = False
                else:
                    in_code, lang = True, line.lstrip()[3:].strip()
    body = "\n".join(cur).strip("\n")
    if body.strip():
        chunks.append(body)
    return chunks or [""]
