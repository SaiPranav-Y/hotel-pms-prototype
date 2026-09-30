# -*- coding: utf-8 -*-
"""
Ollama-backed LLM provider (local, CPU-friendly).

- Uses /api/chat with `format` = JSON schema for structured NLU (steering §8).
- keep_alive=30m + warm_up() so the model stays loaded between calls.
- Validates NLU output with pydantic; retries once; falls back to unknown.
- rephrase_te() guards output with the Telugu-script check.
"""

import json
import logging

import httpx

from app import config
from app.llm.base import LLMProvider, NLUResult
from app.llm import prompts
from app.nlp_te import normalize as nz

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or config.OLLAMA_MODEL
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self._client = httpx.Client(timeout=config.OLLAMA_TIMEOUT)

    # ---- lifecycle ----
    def warm_up(self) -> None:
        """Load the model into memory with a trivial request."""
        try:
            self._chat(
                [{"role": "user", "content": "ok"}],
                fmt=None, num_predict=1,
            )
            logger.info(f"Ollama warmed up: {self.model}")
        except Exception as e:
            logger.warning(f"Ollama warm-up failed (is it running?): {e}")

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass

    # ---- low-level chat ----
    def _chat(self, messages: list[dict], fmt=None, num_predict: int = 256) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": config.OLLAMA_KEEP_ALIVE,
            "options": {
                "temperature": config.OLLAMA_TEMPERATURE,
                "num_ctx": config.OLLAMA_NUM_CTX,
                "num_predict": num_predict,
            },
        }
        if fmt is not None:
            payload["format"] = fmt
        resp = self._client.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("message") or {}).get("content", "") or ""

    # ---- NLU ----
    def extract_nlu(self, user_text: str, context: dict) -> NLUResult:
        messages = prompts.build_nlu_messages(user_text, context)
        for attempt in (1, 2):
            try:
                raw = self._chat(messages, fmt=prompts.NLU_FORMAT, num_predict=256)
                obj = json.loads(raw)
                return NLUResult.model_validate(obj)
            except Exception as e:
                logger.debug(f"NLU attempt {attempt} failed: {e}")
                if attempt == 1:
                    # Nudge the model to return valid JSON only.
                    messages = messages + [{
                        "role": "user",
                        "content": "Return ONLY the JSON object matching the schema.",
                    }]
                    continue
        logger.info("NLU fell back to 'unknown'.")
        return NLUResult(intent="unknown", confidence=0.0)

    # ---- optional free-form Telugu (FAQ) ----
    def rephrase_te(self, facts: str) -> str | None:
        messages = [
            {"role": "system", "content": prompts.REPHRASE_SYSTEM},
            {"role": "user", "content": facts},
        ]
        try:
            out = self._chat(messages, fmt=None, num_predict=120).strip()
        except Exception as e:
            logger.debug(f"rephrase_te failed: {e}")
            return None
        # Telugu-script guard: discard non-Telugu / mostly-Latin output.
        if not out or not nz.is_telugu(out) or nz.mostly_latin(out):
            logger.info("rephrase_te output failed Telugu guard — discarded.")
            return None
        return out
