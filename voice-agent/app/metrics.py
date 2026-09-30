# -*- coding: utf-8 -*-
"""
Lightweight latency instrumentation (steering §10).

CPU-only Telugu STT/LLM/TTS is slow, so we measure per-stage timing to know
where turns spend their time and to decide when to play a "ఒక్క నిమిషం…" filler.

Usage:
    from app.metrics import timed, Timings

    t = Timings()
    with t.stage("stt"):
        text = stt.transcribe(...)
    with t.stage("dialogue"):
        reply = session.handle(text)
    print(t.summary())          # e.g. "stt=2.13s dialogue=0.04s total=2.17s"

`timed` is a decorator for one-off function timing. Nothing here does I/O or
raises; instrumentation must never break the conversation.
"""

import time
import logging
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class Timings:
    """Accumulates named stage durations for a single turn/call."""

    def __init__(self):
        self._stages: dict[str, float] = {}
        self._t0 = time.perf_counter()

    @contextmanager
    def stage(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self._stages[name] = self._stages.get(name, 0.0) + (time.perf_counter() - start)

    def get(self, name: str) -> float:
        return self._stages.get(name, 0.0)

    @property
    def total(self) -> float:
        return time.perf_counter() - self._t0

    def as_dict(self) -> dict[str, float]:
        d = {k: round(v, 3) for k, v in self._stages.items()}
        d["total"] = round(self.total, 3)
        return d

    def summary(self) -> str:
        parts = [f"{k}={v:.2f}s" for k, v in self._stages.items()]
        parts.append(f"total={self.total:.2f}s")
        return " ".join(parts)


@contextmanager
def measure(name: str = "block"):
    """Standalone timer: `with measure('llm'): ...` logs the duration."""
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info(f"[timing] {name}={time.perf_counter() - start:.3f}s")


def timed(fn):
    """Decorator that logs how long `fn` takes."""
    @wraps(fn)
    def _wrap(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            logger.info(f"[timing] {fn.__name__}={time.perf_counter() - start:.3f}s")
    return _wrap
