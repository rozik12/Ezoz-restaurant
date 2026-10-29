"""Self-check for AI-like writing: simple text statistics plus a model's reading. An orientation, not proof."""
from __future__ import annotations

import json
import re
import statistics

MIN_CHARS = 300
MAX_CHARS = 12_000

# connectors that machine-written essays overuse (ru / en / uz)
CONNECTORS = (
    "кроме того", "таким образом", "в заключение", "стоит отметить", "необходимо отметить", "важно отметить", "более того",
    "в целом", "следует отметить", "в современном мире", "играет важную роль", "в данной работе",
    "furthermore", "moreover", "in conclusion", "it is important to note", "additionally", "in today's", "plays a crucial role",
    "bundan tashqari", "shunday qilib", "xulosa qilib", "ta'kidlash joizki", "muhim rol o'ynaydi",
)


def stats(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if len(s.split()) >= 2]
    words = re.findall(r"[\w'’-]+", text.lower())
    lens = [len(s.split()) for s in sentences]
    openers = [" ".join(s.lower().split()[:2]) for s in sentences]
    low = text.lower()
    connectors = sum(low.count(c) for c in CONNECTORS)
    return {
        "words": len(words),
        "sentences": len(sentences),
        "avg_len": round(statistics.mean(lens), 1) if lens else 0,
        "len_spread": round(statistics.pstdev(lens), 1) if len(lens) > 1 else 0,          # low spread = monotone rhythm
        "diversity": round(len(set(words)) / len(words), 2) if words else 0,
        "connectors_per_1000": round(connectors * 1000 / max(len(words), 1), 1),
        "repeated_openers": len(openers) - len(set(openers)),
    }


def prompt(lang: str, st: dict) -> str:
    names = {"ru": "Russian", "uz": "Uzbek (Latin script)", "en": "English"}
    return (
        "You are an editor who judges whether a student text reads as machine-written. Reply with ONE JSON object only, no code fences:\n"
        '{"ai_probability": int 0-100, "signals": [str], "fragments": [{"quote": str, "reason": str}], "advice": [str]}\n'
        "ai_probability is your honest estimate; do not exaggerate in either direction, and say a low number when the text has "
        "specific details, uneven rhythm and a personal voice. signals: 2-4 short observations (generic phrasing, uniform sentence length, "
        "empty connectors, no concrete facts, and so on). fragments: up to 4 short exact quotes (max 140 characters each) that sound most "
        "generic, with the reason. advice: 2-4 tips for making the text genuinely the author's own: add own examples, data, "
        "course materials, opinion, and check every fact. "
        f"Local statistics for context: {json.dumps(st)}. Write signals, reasons and advice in {names.get(lang, 'Russian')}.")


def parse(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON")
    d = json.loads(m.group(0))
    p = int(float(d.get("ai_probability", 0)))
    return {
        "p": max(0, min(100, p)),
        "signals": [str(x) for x in d.get("signals", [])][:4],
        "fragments": [(str(f.get("quote", ""))[:160], str(f.get("reason", ""))[:200])
                      for f in d.get("fragments", []) if isinstance(f, dict) and f.get("quote")][:4],
        "advice": [str(x) for x in d.get("advice", [])][:4],
    }
