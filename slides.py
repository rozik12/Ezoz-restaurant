"""Presentations: the model plans the deck as JSON (narrative, layouts, speaker notes), python-pptx draws it in a chosen style."""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field

LANG_NAME = {"ru": "Russian", "uz": "Uzbek (Latin script)", "en": "English"}
LAYOUTS = ("bullets", "two_col", "steps", "cards", "quote", "section")
LABELS = {                                    # words the code adds itself: agenda, closing
    "agenda": {"ru": "План", "uz": "Reja", "en": "Agenda"},
    "thanks": {"ru": "Спасибо за внимание", "uz": "E'tiboringiz uchun rahmat", "en": "Thank you"},
    "questions": {"ru": "Вопросы?", "uz": "Savollar?", "en": "Questions?"},
}

# name -> palette (RGB): bg paper, ink text, muted, accent, accent2, card, dark (title/section background), on_dark text
THEMES = {
    "modern": dict(bg=(0xF6, 0xF7, 0xF9), ink=(0x1B, 0x25, 0x33), muted=(0x6B, 0x75, 0x85), accent=(0x1F, 0x9D, 0x8B),
                   accent2=(0xF2, 0xA6, 0x3B), card=(0xFF, 0xFF, 0xFF), dark=(0x14, 0x23, 0x3F), on_dark=(0xFF, 0xFF, 0xFF),
                   sub=(0xC9, 0xD6, 0xE8), head="Calibri", body="Calibri"),
    "classic": dict(bg=(0xFB, 0xF8, 0xF1), ink=(0x2B, 0x22, 0x1E), muted=(0x7A, 0x6E, 0x66), accent=(0x8C, 0x2F, 0x39),
                    accent2=(0xB8, 0x92, 0x4A), card=(0xFF, 0xFF, 0xFF), dark=(0x3A, 0x1F, 0x24), on_dark=(0xFB, 0xF3, 0xE4),
                    sub=(0xE0, 0xC9, 0xA6), head="Georgia", body="Calibri"),
    "dark": dict(bg=(0x16, 0x19, 0x20), ink=(0xEC, 0xEF, 0xF4), muted=(0x97, 0xA1, 0xB0), accent=(0xFF, 0xB4, 0x2E),
                 accent2=(0x4F, 0xC3, 0xF7), card=(0x22, 0x27, 0x31), dark=(0x0D, 0x0F, 0x14), on_dark=(0xFF, 0xFF, 0xFF),
                 sub=(0xAE, 0xB8, 0xC8), head="Calibri", body="Calibri"),
}
THEME_ORDER = ("modern", "classic", "dark")


@dataclass
class Slide:
    title: str
    bullets: list[str] = field(default_factory=list)
    notes: str = ""
    layout: str = "bullets"
    left: tuple[str, list[str]] = ("", field(default_factory=list))
    right: tuple[str, list[str]] = ("", field(default_factory=list))
    items: list[tuple[str, str]] = field(default_factory=list)       # steps / cards: (title, text)
    quote: str = ""


@dataclass
class Deck:
    title: str
    subtitle: str
    slides: list[Slide]


# ---------------------------------------------------------------- planning
def outline_prompt(lang: str, count: int) -> str:
    return (
        "You are a presentation designer and speaking coach preparing a deck for a student who must present it live. "
        "Reply with ONE JSON object and nothing else (no code fences):\n"
        '{"title": str, "subtitle": str, "slides": [ {"layout": "bullets"|"two_col"|"steps"|"cards"|"quote"|"section", "title": str, '
        '"bullets": [str], "left": {"heading": str, "bullets": [str]}, "right": {"heading": str, "bullets": [str]}, '
        '"items": [{"title": str, "text": str}], "quote": str, "notes": str} ] }\n\n'
        f"Plan exactly {count} content slides (a title slide, an agenda and a closing slide are added automatically).\n"
        "STORY: open with why the topic matters or a concrete problem, move through logically ordered ideas, end with conclusions the audience can remember. "
        "One idea per slide.\n"
        "TITLES: each title states the takeaway of the slide in at most 9 words (\"Chatbots cut response time\", not \"Chatbots\").\n"
        "LAYOUTS (vary them; never use the same layout more than twice in a row):\n"
        "- bullets: 3-5 bullets, each at most 14 words, concrete and informative, no filler, no repeating the title.\n"
        "- two_col: comparison, pros and cons, before and after. Fill left and right (heading + 2-4 bullets each).\n"
        "- steps: a process or timeline, 3-5 items, each with a short title (max 4 words) and one sentence.\n"
        "- cards: 3-4 parallel concepts, each with a short title and one or two sentences (max 25 words).\n"
        "- quote: one key idea or definition as a short statement in 'quote' (max 25 words), used at most once.\n"
        "- section: a divider between big parts, only for decks with 10+ slides; just a title and optional one-line 'quote' subtitle.\n"
        "The last content slide must be a conclusion (bullets or cards).\n"
        "NOTES: for every slide write 3-4 natural spoken sentences the student can say, adding explanation and an example beyond the slide text.\n"
        "ACCURACY: never invent statistics, studies, quotes or bibliographic sources. Use only well-established facts; when unsure, describe the idea without numbers. "
        "If the user supplied source material, stay faithful to it.\n"
        f"Write everything in {LANG_NAME.get(lang, 'Russian')} unless the topic text is clearly in another language.")


def refine_prompt(lang: str) -> str:
    return (
        "You are a strict editor of presentation decks. You receive a deck as JSON. Return the improved deck as ONE JSON object with the same schema, "
        "no code fences. Improve: vague or repetitive bullets (make them specific), titles that are labels instead of takeaways, slides with a weak idea, "
        "monotone layouts (use two_col, steps, cards where the content fits), notes that merely repeat the slide. "
        "Keep the number of slides, the topic and the language; never add invented statistics, studies or sources; remove any you find. "
        f"Language: {LANG_NAME.get(lang, 'Russian')} unless the deck is clearly in another language.")


def _strs(v, n: int) -> list[str]:
    return [str(x).strip() for x in (v if isinstance(v, list) else []) if str(x).strip()][:n]


def _items(v) -> list[tuple[str, str]]:
    out = []
    for it in v if isinstance(v, list) else []:
        if isinstance(it, dict) and (it.get("title") or it.get("text")):
            title = re.sub(r"^\s*\d+\s*[.):]\s*", "", str(it.get("title", "")).strip())      # the badge already shows the number
            out.append((title[:60], str(it.get("text", "")).strip()[:220]))
    return out[:5]


def _col(v) -> tuple[str, list[str]]:
    if isinstance(v, dict):
        return str(v.get("heading", "")).strip()[:60], _strs(v.get("bullets"), 5)
    return "", []


def parse_deck(raw: str) -> Deck:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON")
    data = json.loads(m.group(0))
    slides: list[Slide] = []
    for s in data.get("slides", []):
        if not isinstance(s, dict):
            continue
        title = str(s.get("title", "")).strip()
        if not title:
            continue
        sl = Slide(title[:120], _strs(s.get("bullets"), 6), str(s.get("notes", "")).strip(),
                   str(s.get("layout", "bullets")).strip().lower(), _col(s.get("left")), _col(s.get("right")),
                   _items(s.get("items")), str(s.get("quote", "")).strip()[:300])
        if sl.layout not in LAYOUTS:
            sl.layout = "bullets"
        # fall back to plain bullets when a layout lacks its content
        if sl.layout == "two_col" and not (sl.left[1] and sl.right[1]):
            sl.layout = "bullets"
        elif sl.layout in ("steps", "cards") and len(sl.items) < 3:
            sl.layout = "bullets"
        elif sl.layout == "quote" and not sl.quote:
            sl.layout = "bullets"
        if sl.layout == "bullets" and not sl.bullets:                 # rebuild bullets from whatever the model gave
            sl.bullets = (sl.left[1] + sl.right[1]) or [f"{a}: {b}" if a and b else (a or b) for a, b in sl.items] or ([sl.quote] if sl.quote else [])
        slides.append(sl)
    if not slides:
        raise ValueError("no slides")
    return Deck(str(data.get("title", "")).strip()[:150] or slides[0].title, str(data.get("subtitle", "")).strip()[:200], slides)


def deck_to_json(deck: Deck) -> str:
    def col(c):
        return {"heading": c[0], "bullets": c[1]}
    return json.dumps({"title": deck.title, "subtitle": deck.subtitle, "slides": [
        {"layout": s.layout, "title": s.title, "bullets": s.bullets, "left": col(s.left), "right": col(s.right),
         "items": [{"title": a, "text": b} for a, b in s.items], "quote": s.quote, "notes": s.notes} for s in deck.slides]}, ensure_ascii=False)


# ---------------------------------------------------------------- drawing
def build_pptx(deck: Deck, theme: str = "modern", lang: str = "en") -> bytes:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches, Pt

    th = THEMES.get(theme, THEMES["modern"])
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    W, H = 13.333, 7.5
    rgb = lambda c: RGBColor(*c)
    lab = lambda k: LABELS[k].get(lang, LABELS[k]["en"])

    def shape(s, kind, x, y, w, h, color, radius=None, line=None):
        sh = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(color)
        if line:
            sh.line.color.rgb = rgb(line)
            sh.line.width = Pt(0.75)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = radius
        return sh

    def rect(s, x, y, w, h, color, **kw):
        return shape(s, MSO_SHAPE.RECTANGLE, x, y, w, h, color, **kw)

    def card(s, x, y, w, h, color=None, radius=0.06):
        return shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, color or th["card"], radius=radius, line=(0xDD, 0xE1, 0xE8) if theme != "dark" else (0x33, 0x3A, 0x46))

    def text(s, x, y, w, h, value, size, color, *, bold=False, italic=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             font=None, spacing=None):
        box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.05)
        tf.margin_top = tf.margin_bottom = Inches(0.03)
        p = tf.paragraphs[0]
        p.alignment = align
        if spacing:
            p.line_spacing = spacing
        run = p.add_run()
        run.text = value
        f = run.font
        f.size, f.bold, f.italic, f.name = Pt(size), bold, italic, font or th["body"]
        f.color.rgb = rgb(color)
        return box

    def size_for(value: str, big: int, small: int, per_line: int) -> int:
        n = len(value)
        return big if n <= per_line else max(small, int(big - (n - per_line) / per_line * (big - small)))

    def title_size(value: str, big: int, small: int, per_line: int) -> int:
        size = size_for(value, big, small, per_line)
        longest = max((len(w) for w in value.split()), default=0)
        return max(small - 1, size - 4) if longest > 16 else size              # one long word must not be cut in the middle

    def base(title: str, number: int, total: int):
        s = prs.slides.add_slide(blank)
        rect(s, 0, 0, W, H, th["bg"])
        rect(s, 0, 0, W, 0.14, th["accent"])
        text(s, 0.7, 0.45, 11.9, 1.2, title, size_for(title, 32, 24, 48), th["ink"], bold=True, anchor=MSO_ANCHOR.MIDDLE, font=th["head"])
        rect(s, 0.75, 1.72, 1.1, 0.07, th["accent2"])
        text(s, 0.7, 6.95, 8.0, 0.35, deck.title[:70], 11, th["muted"])
        text(s, 11.6, 6.95, 1.1, 0.35, f"{number} / {total}", 11, th["muted"], align=PP_ALIGN.RIGHT)
        return s

    def dark_slide():
        s = prs.slides.add_slide(blank)
        rect(s, 0, 0, W, H, th["dark"])
        shape(s, MSO_SHAPE.OVAL, 9.6, -1.6, 5.6, 5.6, th["accent"]).fill.fore_color.brightness = -0.35
        shape(s, MSO_SHAPE.OVAL, 11.2, 4.6, 3.6, 3.6, th["accent2"]).fill.fore_color.brightness = -0.45
        return s

    # ---- layouts
    def lay_bullets(s, sl):
        n = len(sl.bullets)
        top, avail = 2.15, 4.6
        gap = 0.18
        h = min(1.05, (avail - gap * (n - 1)) / max(n, 1))
        for i, b in enumerate(sl.bullets):
            y = top + i * (h + gap)
            card(s, 0.75, y, 11.85, h, radius=0.12)
            rect(s, 0.75, y + 0.12, 0.09, h - 0.24, th["accent"])
            text(s, 1.05, y, 11.4, h, b, size_for(b, 22, 16, 80), th["ink"], anchor=MSO_ANCHOR.MIDDLE)

    def lay_two_col(s, sl):
        for k, (heading, bullets) in enumerate((sl.left, sl.right)):
            x = 0.75 + k * 6.05
            card(s, x, 2.15, 5.8, 4.55, radius=0.04)
            shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.15, 5.8, 0.75, th["accent"] if k == 0 else th["accent2"], radius=0.2)
            text(s, x + 0.25, 2.15, 5.3, 0.75, heading or ("A", "B")[k], 20, th["on_dark"] if k == 0 or theme != "classic" else th["dark"],
                 bold=True, anchor=MSO_ANCHOR.MIDDLE, font=th["head"])
            gapy = 3.1
            step = min(1.0, 3.5 / max(len(bullets), 1))
            for i, b in enumerate(bullets):
                text(s, x + 0.3, gapy + i * step, 5.2, step, "•  " + b, size_for(b, 20, 15, 42), th["ink"], anchor=MSO_ANCHOR.TOP)

    def lay_steps(s, sl):
        n = len(sl.items)
        w = (11.85 - 0.3 * (n - 1)) / n
        rect(s, 0.9, 3.0, 11.5, 0.05, th["muted"])
        for i, (title, body) in enumerate(sl.items):
            x = 0.75 + i * (w + 0.3)
            c = shape(s, MSO_SHAPE.OVAL, x + w / 2 - 0.45, 2.55, 0.9, 0.9, th["accent"])
            tf = c.text_frame
            tf.text = str(i + 1)
            r = tf.paragraphs[0].runs[0]
            r.font.size, r.font.bold, r.font.name = Pt(24), True, th["head"]
            r.font.color.rgb = rgb(th["on_dark"] if theme != "dark" else th["dark"])
            tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            text(s, x, 3.65, w, 0.9, title, title_size(title, 20, 15, 13), th["ink"], bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                 font=th["head"])
            text(s, x + 0.05, 4.65, w - 0.1, 2.1, body, size_for(body, 18, 14, 90), th["muted"] if theme != "dark" else th["sub"], align=PP_ALIGN.CENTER)

    def lay_cards(s, sl):
        n = len(sl.items)
        cols = 2 if n == 4 else n
        rows = 2 if n == 4 else 1
        w = (11.85 - 0.3 * (cols - 1)) / cols
        h = 3.9 if rows == 1 else (4.55 - 0.3) / 2
        for i, (title, body) in enumerate(sl.items):
            x, y = 0.75 + (i % cols) * (w + 0.3), 2.15 + (i // cols) * (h + 0.3)
            card(s, x, y, w, h, radius=0.05)
            rect(s, x, y, w, 0.12, th["accent"] if i % 2 == 0 else th["accent2"])
            text(s, x + 0.25, y + 0.3, w - 0.5, 0.8, title, title_size(title, 22 if rows == 1 else 20, 15, 15), th["ink"], bold=True,
                 anchor=MSO_ANCHOR.MIDDLE, font=th["head"])
            text(s, x + 0.25, y + 1.2, w - 0.5, h - 1.35, body, size_for(body, 20 if rows == 1 else 17, 15, 110 if rows == 1 else 130),
                 th["muted"] if theme != "dark" else th["sub"])

    def lay_quote(s, sl):
        text(s, 0.9, 2.0, 2.0, 1.6, "“", 120, th["accent"], bold=True, font=th["head"])
        text(s, 1.7, 2.7, 10.0, 3.0, sl.quote, size_for(sl.quote, 34, 24, 70), th["ink"], italic=True, anchor=MSO_ANCHOR.MIDDLE, font=th["head"])
        rect(s, 1.75, 5.9, 1.2, 0.07, th["accent2"])

    total = len(deck.slides) + 3                                    # title + agenda + closing are added
    # title slide
    s = dark_slide()
    rect(s, 0.9, 3.55, 1.7, 0.09, th["accent2"])
    text(s, 0.9, 1.1, 9.0, 2.4, deck.title, size_for(deck.title, 46, 30, 40), th["on_dark"], bold=True, anchor=MSO_ANCHOR.BOTTOM, font=th["head"])
    if deck.subtitle:
        text(s, 0.9, 3.8, 8.6, 1.5, deck.subtitle, 22, th["sub"])

    # agenda from the slide titles (skip dividers)
    items = [sl.title for sl in deck.slides if sl.layout != "section"]
    if len(items) >= 4:
        agenda = items if len(items) <= 8 else [sl.title for sl in deck.slides if sl.layout == "section"] or items[:8]
        s = base(lab("agenda"), 2, total)
        n = len(agenda)
        cols = 2 if n > 4 else 1
        per = -(-n // cols)
        for i, a in enumerate(agenda):
            cx, cy = 0.9 + (i // per) * 6.0, 2.2 + (i % per) * (4.5 / per)
            c = shape(s, MSO_SHAPE.OVAL, cx, cy + 0.05, 0.55, 0.55, th["accent"] if i % 2 == 0 else th["accent2"])
            c.text_frame.text = str(i + 1)
            r = c.text_frame.paragraphs[0].runs[0]
            r.font.size, r.font.bold, r.font.name = Pt(16), True, th["head"]
            r.font.color.rgb = rgb(th["dark"] if theme in ("dark", "classic") and i % 2 else th["on_dark"] if theme != "dark" else th["dark"])
            c.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            c.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            text(s, cx + 0.75, cy, 5.0 if cols == 2 else 10.5, 0.7, a, size_for(a, 24, 17, 30), th["ink"], anchor=MSO_ANCHOR.MIDDLE)
        offset = 3
    else:
        offset = 2

    for i, sl in enumerate(deck.slides):
        number = i + offset
        if sl.layout == "section":
            s = dark_slide()
            text(s, 0.9, 2.3, 9.5, 2.0, sl.title, size_for(sl.title, 44, 30, 36), th["on_dark"], bold=True, anchor=MSO_ANCHOR.BOTTOM, font=th["head"])
            rect(s, 0.9, 4.5, 1.7, 0.09, th["accent2"])
            if sl.quote:
                text(s, 0.9, 4.8, 8.5, 1.2, sl.quote, 20, th["sub"])
        else:
            s = base(sl.title, number, total)
            {"two_col": lay_two_col, "steps": lay_steps, "cards": lay_cards, "quote": lay_quote}.get(sl.layout, lay_bullets)(s, sl)
        if sl.notes:
            s.notes_slide.notes_text_frame.text = sl.notes

    # closing slide
    s = dark_slide()
    text(s, 0.9, 2.2, 10.0, 1.6, lab("thanks"), 48, th["on_dark"], bold=True, anchor=MSO_ANCHOR.BOTTOM, font=th["head"])
    rect(s, 0.9, 4.0, 1.7, 0.09, th["accent2"])
    text(s, 0.9, 4.3, 9.0, 1.0, lab("questions"), 28, th["sub"])

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
