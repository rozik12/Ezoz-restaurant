"""Long written works (term paper, essay, report...): plan, section-by-section writing to a required word range, .docx in the usual university layout."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from llm import Assistant, AssistantError

log = logging.getLogger(__name__)

WORDS_PER_PAGE = 250                                   # Times New Roman 14 pt, 1.5 line spacing, A4 (about 1800 characters)
LANG_NAME = {"ru": "Russian", "uz": "Uzbek (Latin script)", "en": "English"}
STANDARD = {
    "gost": "Follow Russian-language academic conventions (GOST style): formal register, impersonal constructions, numbered structure.",
    "apa": "Follow APA conventions: author-date wording, formal register, clear headings.",
    "none": "Use a clean formal academic style.",
}
BIBLIO_TITLE = {"ru": "Список литературы", "uz": "Foydalanilgan adabiyotlar ro'yxati", "en": "References"}
CONTENTS_TITLE = {"ru": "Содержание", "uz": "Mundarija", "en": "Contents"}
FILL_LINES = {
    "ru": ("Выполнил(а):", "Проверил(а):", "Группа:"),
    "uz": ("Bajardi:", "Tekshirdi:", "Guruh:"),
    "en": ("Prepared by:", "Reviewed by:", "Group:"),
}

# kind -> (English name for the prompts, section range, volume presets, has a bibliography, intro/conclusion required)
KINDS = {
    "course": ("term paper (coursework)", (5, 12), [(6000, 8000), (8000, 10000), (10000, 12000)], True),
    "referat": ("referat (academic summary report)", (4, 8), [(1500, 2500), (2500, 4000), (4000, 6000)], True),
    "essay": ("essay", (3, 6), [(500, 800), (800, 1200), (1200, 2000)], False),
    "report": ("report / presentation text", (3, 6), [(600, 1000), (1000, 1500), (1500, 2500)], False),
    "practice": ("internship (practice) report", (5, 9), [(3000, 5000), (5000, 8000), (8000, 10000)], True),
    "thesis": ("chapter of a diploma thesis", (4, 9), [(6000, 8000), (8000, 12000), (12000, 16000)], True),
}


@dataclass
class Spec:
    kind: str
    topic: str
    lang: str
    wmin: int
    wmax: int
    std: str = "none"
    extra: str = ""

    @property
    def target(self) -> int:
        return (self.wmin + self.wmax) // 2


@dataclass
class Section:
    title: str
    goal: str
    words: int
    text: str = ""


def count_words(text: str) -> int:
    return len(re.findall(r"[\w'’-]+", text))


def parse_volume(raw: str) -> tuple[int, int] | None:
    """'5000-6000 words', '25 pages', '3000' -> (min, max) in words; None when it cannot be understood."""
    s = raw.lower().replace("–", "-").replace("—", "-").replace(" ", " ")
    nums = [int(x.replace(" ", "")) for x in re.findall(r"\d[\d ]*\d|\d", s)]
    if not nums or len(nums) > 2:
        return None
    pages = bool(re.search(r"стр|page|bet|лист|\bp\b|pp\b", s)) and not re.search(r"слов|word|so'z|so‘z", s)
    lo, hi = (nums[0], nums[1]) if len(nums) == 2 else (nums[0], int(nums[0] * 1.1))
    if lo > hi:
        lo, hi = hi, lo
    if pages:
        lo, hi = lo * WORDS_PER_PAGE, hi * WORDS_PER_PAGE
    if lo < 200 or hi > 40_000:
        return None
    return lo, hi


# ---------------------------------------------------------------- plan
def plan_prompt(spec: Spec) -> str:
    name, (smin, smax), _, _ = KINDS[spec.kind]
    return (
        f"You plan a {name} for a university student. Reply with ONE JSON object only, no code fences:\n"
        '{"title": str, "sections": [{"title": str, "goal": str, "words": int}]}\n'
        f"The body must total about {spec.target} words (allowed range {spec.wmin}-{spec.wmax}); choose {smin}-{smax} sections whose 'words' add up to that total, "
        "none shorter than 250 words and none longer than 1500. Start with an introduction (relevance, aim, tasks) and end with a conclusion; "
        "for a term paper, thesis chapter or practice report the middle is logically ordered chapters. Section titles are concise academic headings "
        "without numbering. 'goal' is one sentence on what the section must cover so that sections do not overlap. "
        "Do not include the bibliography as a section. If the student gave their own plan or requirements, follow them exactly. "
        f"Write titles and goals in {LANG_NAME.get(spec.lang, 'Russian')}.")


def parse_plan(raw: str, spec: Spec) -> tuple[str, list[Section]]:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON")
    data = json.loads(m.group(0))
    secs = []
    for s in data.get("sections", []):
        if isinstance(s, dict) and str(s.get("title", "")).strip():
            try:
                w = int(float(s.get("words", 0)))
            except (TypeError, ValueError):
                w = 0
            secs.append(Section(str(s["title"]).strip()[:150], str(s.get("goal", "")).strip()[:300], max(w, 0)))
    if len(secs) < 2:
        raise ValueError("plan too short")
    total = sum(s.words for s in secs) or 1
    for s in secs:                                      # scale to the requested total whatever the model summed to
        s.words = max(200, round(s.words * spec.target / total)) if total > 1 else spec.target // len(secs)
    return str(data.get("title", "")).strip()[:200] or spec.topic[:120], secs


# ---------------------------------------------------------------- writing
def section_system(spec: Spec) -> str:
    return (
        "You are an experienced academic writer producing one section of a student's written work. Rules:\n"
        "- Write substantive, specific academic prose in flowing paragraphs: explain, compare, give reasoning and concrete examples; no filler, no repeating the heading, "
        "no summary of what you will do.\n"
        "- Do NOT use markdown, headings or bullet symbols; plain paragraphs separated by a blank line (a numbered list only when the content is truly a list).\n"
        "- Never invent statistics, studies, quotations, laws or bibliographic references. Where a concrete figure or case from the student's own data is needed, "
        "write a short placeholder in square brackets such as [укажите данные] in the work's language instead of guessing.\n"
        f"- {STANDARD.get(spec.std, STANDARD['none'])}\n"
        f"- Language: {LANG_NAME.get(spec.lang, 'Russian')}.\n"
        "- Hit the requested length closely (within about 10%).")


def section_user(spec: Spec, title: str, plan: list[Section], i: int) -> str:
    sec = plan[i]
    outline = "\n".join(f"{n + 1}. {s.title}: {s.goal}" for n, s in enumerate(plan))
    extra = f"\n\nStudent's requirements and source material (follow them):\n{spec.extra}" if spec.extra else ""
    return (f"Work: {KINDS[spec.kind][0]} titled \"{title}\"\nTopic given by the student: {spec.topic}\n\nFull plan:\n{outline}\n\n"
            f"Write ONLY section {i + 1}: \"{sec.title}\" (goal: {sec.goal}).\nTarget length: about {round(sec.words * 1.15)} words.\n"
            f"Stay within this section's goal; other sections cover the rest.{extra}")


async def _retry(coro_factory, tries: int = 3):
    last: Exception | None = None
    for attempt in range(tries):
        try:
            return await coro_factory()
        except AssistantError as e:
            last = e
            if e.key in ("access", "balance", "not_ready"):
                raise
            await asyncio.sleep(2 + 3 * attempt)
    raise last  # type: ignore[misc]


async def write_section(ai: Assistant, spec: Spec, title: str, plan: list[Section], i: int) -> str:
    words = plan[i].words
    text = await _retry(lambda: ai.complete(section_system(spec), section_user(spec, title, plan, i), min(8000, words * 5 + 600)))
    return text.strip()


async def expand_section(ai: Assistant, spec: Spec, sec: Section, need: int) -> str:
    system = section_system(spec)
    user = (f"Here is the section \"{sec.title}\" of the work. Extend it by about {need} words: deepen the explanations, add reasoning, examples and "
            f"transitions, without repeating anything and without placeholders beyond those already present. Return the COMPLETE improved section text only.\n\n{sec.text}")
    return (await _retry(lambda: ai.complete(system, user, min(8000, (sec.words + need) * 5 + 600)))).strip()


async def bibliography(ai: Assistant, spec: Spec, title: str) -> str:
    system = ("You list literature for a student's work. Give 8-12 entries, one per line, numbered, ONLY works you are certain really exist "
              "(standard textbooks, classic monographs, major laws and standards of the relevant country). If unsure about a work, leave it out; "
              "a shorter honest list beats an invented one. Format: "
              + ("GOST R 7.0.100 style" if spec.std == "gost" else "APA 7 style" if spec.std == "apa" else "a clean consistent style")
              + f". Language of the entries follows their originals; no commentary. The student's topic is in {LANG_NAME.get(spec.lang, 'Russian')} context.")
    try:
        return (await _retry(lambda: ai.complete(system, f"Work: {title}\nTopic: {spec.topic}", 1500))).strip()
    except AssistantError:
        return ""


# ---------------------------------------------------------------- the whole job
async def generate(ai: Assistant, spec: Spec, progress=None) -> tuple[str, list[Section], str]:
    """Returns (title, sections with text, bibliography). `progress(done, total, stage)` is awaited as work advances."""
    async def say(done: int, total: int, stage: str) -> None:
        if progress:
            try:
                await progress(done, total, stage)
            except Exception:
                pass

    await say(0, 1, "plan")
    title, plan = "", []
    for _ in range(2):
        raw = await _retry(lambda: ai.complete(plan_prompt(spec), f"Topic: {spec.topic}" + (f"\n\nStudent's requirements:\n{spec.extra}" if spec.extra else ""), 2500))
        try:
            title, plan = parse_plan(raw, spec)
            break
        except (ValueError, TypeError):
            log.warning("Paper: unparsable plan")
    if not plan:
        raise AssistantError("empty")

    done = 0
    sem = asyncio.Semaphore(3)

    async def one(i: int) -> None:
        nonlocal done
        async with sem:
            plan[i].text = await write_section(ai, spec, title, plan, i)
        done += 1
        await say(done, len(plan), "write")

    await say(0, len(plan), "write")
    await asyncio.gather(*(one(i) for i in range(len(plan))))
    if any(not s.text for s in plan):
        raise AssistantError("empty")

    for _ in range(3):                                   # bring a short work up to the required range; models tend to under-deliver length
        total = sum(count_words(s.text) for s in plan)
        if total >= spec.wmin * 1.03:                 # a small margin: Word counts words slightly differently
            break
        await say(len(plan), len(plan), "expand")
        lacking = round((spec.target - total) * 1.25)
        weights = [max(s.words - count_words(s.text), 0) for s in plan]
        if sum(weights) == 0:
            weights = [s.words for s in plan]
        picks = sorted(range(len(plan)), key=lambda i: -weights[i])[:max(2, len(plan) // 2)]
        wsum = sum(weights[i] for i in picks) or 1
        async def grow(i: int) -> None:
            async with sem:
                need = max(100, round(lacking * weights[i] / wsum))
                longer = await expand_section(ai, spec, plan[i], need)
                if count_words(longer) > count_words(plan[i].text):
                    plan[i].text = longer
        await asyncio.gather(*(grow(i) for i in picks))

    biblio = ""
    if KINDS[spec.kind][3]:
        await say(len(plan), len(plan), "biblio")
        biblio = await bibliography(ai, spec, title)
    return title, plan, biblio


# ---------------------------------------------------------------- the document
def build_docx(spec: Spec, title: str, sections: list[Section], biblio: str) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(3), Cm(1), Cm(2), Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Times New Roman", Pt(14)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)

    def heading(text: str, center: bool = False) -> None:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(12), Pt(12)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text.upper() if center else text)
        r.bold = True
        r.font.name, r.font.size = "Times New Roman", Pt(14)
        # outline level so Word's navigation pane and an automatic contents table can use it
        ppr = p._p.get_or_add_pPr()
        lvl = OxmlElement("w:outlineLvl")
        lvl.set(qn("w:val"), "0")
        ppr.append(lvl)

    def body(text: str) -> None:
        for chunk in re.split(r"\n\s*\n", text.strip()):
            chunk = re.sub(r"\s*\n\s*", " ", chunk.strip())
            chunk = re.sub(r"^[#>*\-\s]+", "", chunk) if chunk.startswith(("#", ">")) else chunk
            if chunk:
                p = doc.add_paragraph(chunk.replace("**", ""))
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.first_line_indent = Cm(1.25)

    # title page: blanks for the student to fill in, no personal data
    kind_ru = {"course": "КУРСОВАЯ РАБОТА", "referat": "РЕФЕРАТ", "essay": "ЭССЕ", "report": "ДОКЛАД", "practice": "ОТЧЁТ ПО ПРАКТИКЕ", "thesis": "ДИПЛОМНАЯ РАБОТА"}
    kind_uz = {"course": "KURS ISHI", "referat": "REFERAT", "essay": "ESSE", "report": "MA'RUZA", "practice": "AMALIYOT HISOBOTI", "thesis": "BITIRUV MALAKAVIY ISHI"}
    kind_en = {"course": "TERM PAPER", "referat": "REPORT", "essay": "ESSAY", "report": "REPORT", "practice": "INTERNSHIP REPORT", "thesis": "THESIS"}
    label = {"ru": kind_ru, "uz": kind_uz, "en": kind_en}.get(spec.lang, kind_ru)[spec.kind]
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(label)
    r.bold = True
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    for _ in range(6):
        doc.add_paragraph()
    for line in FILL_LINES.get(spec.lang, FILL_LINES["ru"]):
        p = doc.add_paragraph(f"{line} " + "_" * 28)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p = doc.add_paragraph(str(datetime.now().year))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(60)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    heading(CONTENTS_TITLE.get(spec.lang, "Contents"), center=True)
    for i, s in enumerate(sections, 1):
        doc.add_paragraph(f"{i}. {s.title}")
    if biblio:
        doc.add_paragraph(f"{len(sections) + 1}. {BIBLIO_TITLE.get(spec.lang, 'References')}")
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    for i, s in enumerate(sections, 1):
        heading(f"{i}. {s.title}")
        body(s.text)
    if biblio:
        heading(f"{len(sections) + 1}. {BIBLIO_TITLE.get(spec.lang, 'References')}")
        for line in biblio.splitlines():
            if line.strip():
                doc.add_paragraph(line.strip())

    # page numbers, centered in the footer
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
