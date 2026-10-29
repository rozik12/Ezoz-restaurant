"""Language-model client with conversation memory, plan-dependent limits and retries.

Provider order: Gemini (GEMINI_API_KEY), DeepSeek (DEEPSEEK_API_KEY), Claude (ANTHROPIC_API_KEY); the first key that is set wins."""
from __future__ import annotations

import asyncio
import logging

from config import Settings
from db import Database
from prompts import build_system

log = logging.getLogger(__name__)

HISTORY_MESSAGES = 24            # last 12 exchanges
HISTORY_CHARS = 40_000           # budget for the context sent along with each request
STORED_USER_CHARS = 6_000        # long documents are stored shortened so they do not bloat the history
DEEPSEEK_URL = "https://api.deepseek.com"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class AssistantError(Exception):
    """A failure the user is told about. `key` names the translated message (i18n: err_<key>)."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


class Retry(Exception):
    """Internal: a temporary failure worth another attempt; carries the error key shown if every attempt fails."""


class Assistant:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.s, self.db = settings, db
        self.provider: str | None = None
        self.client = None
        if settings.gemini_key:
            from openai import AsyncOpenAI
            self.provider = "gemini"
            self.client = AsyncOpenAI(api_key=settings.gemini_key, base_url=GEMINI_URL, max_retries=0)
        elif settings.deepseek_key:
            from openai import AsyncOpenAI
            self.provider = "deepseek"
            self.client = AsyncOpenAI(api_key=settings.deepseek_key, base_url=DEEPSEEK_URL, max_retries=0)
        elif settings.anthropic_key:
            import anthropic
            self.provider = "anthropic"
            self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_key, max_retries=0)

    @property
    def ready(self) -> bool:
        return self.client is not None

    async def _context(self, user_id: int) -> list[dict]:
        msgs = await self.db.history(user_id, HISTORY_MESSAGES)
        while msgs and msgs[0]["role"] != "user":          # the first turn must be the user's
            msgs.pop(0)
        total = 0
        kept: list[dict] = []
        for m in reversed(msgs):
            total += len(m["content"])
            if total > HISTORY_CHARS and kept:
                break
            kept.append(m)
        kept.reverse()
        while kept and kept[0]["role"] != "user":
            kept.pop(0)
        return kept

    async def ask(self, user_id: int, text: str, *, mode: str, paid: bool, lang: str = "ru",
                  stored: str | None = None) -> tuple[str, bool]:
        """`text` goes to the model in full; `stored` (shorter) is what is kept in the history."""
        if not self.ready:
            raise AssistantError("not_ready")
        await self.db.add_message(user_id, "user", (stored or text)[:STORED_USER_CHARS])
        history = await self._context(user_id)
        if history:                                         # send the full text of this turn, not the shortened copy
            history[-1] = {"role": "user", "content": text}
        max_tokens = self.s.paid_max_tokens if paid else self.s.free_max_tokens
        try:
            answer, truncated = await self._call(build_system(mode, "paid" if paid else "free", lang), history, max_tokens)
        except Exception:
            await self.db.drop_last_user_message(user_id)
            raise
        await self.db.add_message(user_id, "assistant", answer)
        return answer, truncated

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        """A single stateless request (tools: slides, AI check). Raises AssistantError like ask()."""
        if not self.ready:
            raise AssistantError("not_ready")
        text, _ = await self._call(system, [{"role": "user", "content": user}], max_tokens)
        return text

    # ---------- providers ----------
    async def _once(self, system: str, messages: list[dict], max_tokens: int) -> tuple[str, bool]:
        """One request. Raises Retry for temporary problems and AssistantError for fatal ones."""
        if self.provider in ("deepseek", "gemini"):
            import openai
            gemini = self.provider == "gemini"
            extra = {"reasoning_effort": "none"} if gemini else {}      # thinking tokens would eat the answer's token budget
            try:
                resp = await self.client.chat.completions.create(
                    model=self.s.gemini_model if gemini else self.s.deepseek_model,
                    max_tokens=max_tokens if gemini else min(max_tokens, 8192), temperature=0.7, timeout=240,
                    messages=[{"role": "system", "content": system}, *messages], **extra)
            except openai.RateLimitError as e:
                raise Retry("overloaded") from e
            except openai.APIStatusError as e:
                self._fatal_status(e.status_code, e)
                raise Retry("overloaded") from e
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                raise Retry("connection") from e
            choice = resp.choices[0]
            return (choice.message.content or "").strip(), choice.finish_reason == "length"
        import anthropic
        try:
            resp = await self.client.messages.create(model=self.s.model, max_tokens=max_tokens, system=system,
                                                     messages=messages, timeout=240)
        except anthropic.RateLimitError as e:
            raise Retry("overloaded") from e
        except anthropic.APIStatusError as e:
            self._fatal_status(e.status_code, e)
            raise Retry("overloaded") from e
        except anthropic.APIConnectionError as e:
            raise Retry("connection") from e
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        return text, resp.stop_reason == "max_tokens"

    @staticmethod
    def _fatal_status(code: int, err: Exception) -> None:
        if code in (401, 403):
            log.error("The AI provider rejected the API key (%s)", code)
            raise AssistantError("access") from err
        if code == 402:
            log.error("The AI provider reports an insufficient balance")
            raise AssistantError("balance") from err
        if code in (400, 422):
            log.error("The AI provider rejected the request: %s", err)
            raise AssistantError("bad_request") from err

    async def _call(self, system: str, messages: list[dict], max_tokens: int) -> tuple[str, bool]:
        delay = 2.0
        for attempt in range(3):
            try:
                text, truncated = await self._once(system, messages, max_tokens)
            except Retry as e:
                log.warning("LLM call failed (attempt %d): %s", attempt + 1, e)
                if attempt == 2:
                    raise AssistantError(str(e)) from e
                await asyncio.sleep(delay)
                delay *= 2
                continue
            if not text:
                raise AssistantError("empty")
            return text, truncated
        raise AssistantError("overloaded")
