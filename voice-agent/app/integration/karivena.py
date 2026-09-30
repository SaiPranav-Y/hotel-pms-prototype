# -*- coding: utf-8 -*-
"""
Bridge to the live Karivena data layer in `hotel-voice-booking-demo`.

The sibling project owns the real inventory (`room_data.json` — 9 pilgrimage
locations), admin rates (`rate_config.json`), gotram eligibility, payment/
WhatsApp side-effects, and — when Firebase is enabled — the concurrency-safe
Firestore booking that the Flutter PMS also contends on. Rather than duplicate
any of that, we import those modules in-process and call them.

This module does the messy part: locate the demo checkout, put its root on
`sys.path` so `import app.knowledge_base` resolves to the DEMO's `app` package
(not ours), and expose a small, typed surface (`bridge()`) the rest of the
Telugu agent uses. Importing is lazy and cached; failures raise
`KarivenaUnavailable` with a clear message so callers can fall back.

Package-name clash note: both projects use a top-level package called `app`.
We import the demo modules by temporarily making the demo root the FIRST entry
on sys.path and importing the specific submodules we need, then we keep
references to them. Our own `app.*` modules are already imported by the time
this runs, so Python's module cache keeps them distinct as long as we don't
re-import our own `app` afterwards under the shadowed path. To stay safe we
import the demo modules under explicit aliases and never rely on bare `app`.
"""

import contextlib
import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

from app import config

logger = logging.getLogger(__name__)


class KarivenaUnavailable(RuntimeError):
    """Raised when the demo data layer can't be imported."""


class _Bridge:
    """
    Holds references to the demo's live modules plus a snapshot of the demo's
    `app.*` module set. Because both projects use a top-level `app` package,
    every call INTO the demo runs inside `use_demo_app()`, which swaps
    sys.modules so the demo's lazy `from app import validators` etc. resolve to
    the DEMO's package, then restores ours.
    """

    def __init__(self, knowledge_base, rates, vernacular, gotram, firebase_store,
                 demo_modules: dict, demo_root: Path):
        self.kb = knowledge_base
        self.rates = rates
        self.vernacular = vernacular
        self.gotram = gotram
        self.firebase_store = firebase_store
        self._demo_modules = demo_modules      # {'app': ..., 'app.knowledge_base': ...}
        self._demo_root = str(demo_root)

    @contextlib.contextmanager
    def use_demo_app(self):
        """Make the demo's `app` package active for the duration of a call."""
        saved_ours = {k: v for k, v in sys.modules.items()
                      if k == "app" or k.startswith("app.")}
        path_inserted = False
        try:
            if self._demo_root not in sys.path:
                sys.path.insert(0, self._demo_root)
                path_inserted = True
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            sys.modules.update(self._demo_modules)
            yield
            # Re-capture any demo submodules imported lazily during the call so
            # subsequent calls reuse them.
            for k, v in list(sys.modules.items()):
                if k == "app" or k.startswith("app."):
                    self._demo_modules[k] = v
        finally:
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            sys.modules.update(saved_ours)
            if path_inserted:
                try:
                    sys.path.remove(self._demo_root)
                except ValueError:
                    pass

    # --- convenience wrappers over the demo API (run inside use_demo_app) ---
    def firebase_active(self) -> bool:
        try:
            with self.use_demo_app():
                return bool(self.firebase_store.is_firebase_active())
        except Exception:
            return False


_BRIDGE: _Bridge | None = None


def _load_demo_module(demo_root: Path, dotted: str) -> ModuleType:
    """
    Import `app.<sub>` FROM the demo checkout, returned under a private alias so
    it never collides with our own `app.<sub>` in sys.modules.
    """
    rel = dotted.replace(".", "/") + ".py"
    file_path = demo_root / rel
    if not file_path.exists():
        raise KarivenaUnavailable(f"demo module not found: {file_path}")
    alias = f"_karivena_demo_{dotted.replace('.', '_')}"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def bridge() -> _Bridge:
    """
    Return the cached demo bridge, importing the demo modules on first use.

    Strategy: put the demo ROOT on sys.path so the demo's own intra-package
    imports (`from app import validators`, `from app.gotram import ...`) resolve
    to the demo's `app` package. We import the demo's `app` package fresh under
    sys.path[0] = demo_root. Because our process already loaded OUR `app`, we
    save/restore sys.modules['app'] around the demo import so the demo's package
    is used only while wiring the bridge, then our `app` is restored.
    """
    global _BRIDGE
    if _BRIDGE is not None:
        return _BRIDGE

    demo_path = config.KARIVENA_DEMO_PATH
    if not demo_path:
        raise KarivenaUnavailable(
            "hotel-voice-booking-demo not found. Set KARIVENA_DEMO_PATH to its "
            "folder (the one containing app/knowledge_base.py)."
        )
    demo_root = Path(demo_path).resolve()
    if not (demo_root / "app" / "knowledge_base.py").exists():
        raise KarivenaUnavailable(f"knowledge_base.py not under {demo_root}/app")

    # Save our own app.* modules, then let the demo's `app` package take over
    # sys.path[0] while we import the demo modules.
    saved = {k: v for k, v in sys.modules.items()
             if k == "app" or k.startswith("app.")}
    inserted = False
    try:
        if str(demo_root) not in sys.path:
            sys.path.insert(0, str(demo_root))
            inserted = True
        # Drop our app.* so the demo's `app` package loads cleanly.
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]

        kb = importlib.import_module("app.knowledge_base")
        rates = importlib.import_module("app.rates")
        vernacular = importlib.import_module("app.vernacular")
        gotram = importlib.import_module("app.gotram")
        firebase_store = importlib.import_module("app.firebase_store")
        # Eagerly import the demo submodules that knowledge_base.create_booking
        # loads lazily, so they're all captured in the demo snapshot.
        for sub in ("validators", "payments", "whatsapp", "audit"):
            try:
                importlib.import_module(f"app.{sub}")
            except Exception as e:
                logger.info(f"optional demo module app.{sub} not loaded: {e}")
        try:
            firebase_store.init_firebase()  # no-op unless FIREBASE_ENABLED=true
        except Exception as e:
            logger.info(f"Firebase not initialised (fine for local): {e}")

        # Snapshot the demo's app.* module set for use_demo_app().
        demo_modules = {k: v for k, v in sys.modules.items()
                        if k == "app" or k.startswith("app.")}

        _BRIDGE = _Bridge(kb, rates, vernacular, gotram, firebase_store,
                          demo_modules, demo_root)
        logger.info(f"Karivena live data bridge ready (demo at {demo_root}).")
        return _BRIDGE
    except KarivenaUnavailable:
        raise
    except Exception as e:
        raise KarivenaUnavailable(f"failed importing demo modules: {e}") from e
    finally:
        # Restore OUR app.* modules so the rest of the Telugu agent keeps working.
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        sys.modules.update(saved)
        if inserted:
            try:
                sys.path.remove(str(demo_root))
            except ValueError:
                pass


def available() -> bool:
    """True if the demo data layer can be imported (cheap check + cache)."""
    try:
        bridge()
        return True
    except Exception as e:
        logger.info(f"Karivena bridge unavailable: {e}")
        return False
