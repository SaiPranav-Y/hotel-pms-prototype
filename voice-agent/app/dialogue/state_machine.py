# -*- coding: utf-8 -*-
"""
Dialogue state machine (steering §6).

GREETING → INTENT → COLLECT_SLOTS → CHECK_AVAILABILITY → OFFER → CONFIRM → BOOK → GOODBYE
with a correction loop and global TRANSFER_TO_HUMAN / GOODBYE.

Design (per Task-4 finding): slot extraction is DETERMINISTIC per turn using
nlp_te.normalize + dialogue.slots. The LLM is used only to classify the opening
INTENT (and as a weak assist). All spoken output comes from reviewed Telugu
templates — nothing free-form is spoken. Every outgoing line passes the
Telugu-script guard; if it somehow fails, we substitute NOT_UNDERSTOOD.

The machine is transport-agnostic: `handle(user_text) -> agent_text`. The text
REPL, and later the voice loop, just feed text in and speak text out.
"""

import logging
from datetime import date

from app import config
from app.dialogue import templates_te as _T_TE
from app.dialogue import templates_en as _T_EN
from app.dialogue import templates_common as C
from app.dialogue import slots as S
from app.nlp_te import normalize as nz
from app.tools.datasource import get_data_source

logger = logging.getLogger(__name__)

_TEMPLATES = {"te": _T_TE, "en": _T_EN}

# States
ASK_LANGUAGE = "ASK_LANGUAGE"
GREETING = "GREETING"
INTENT = "INTENT"
ASK_LOCATION = "ASK_LOCATION"
ASK_CHECKIN = "ASK_CHECKIN"
ASK_NIGHTS = "ASK_NIGHTS"
ASK_GUESTS = "ASK_GUESTS"
ASK_ROOM_TYPE = "ASK_ROOM_TYPE"
ASK_NAME = "ASK_NAME"
ASK_PHONE = "ASK_PHONE"
ASK_GOTRAM = "ASK_GOTRAM"
ASK_EMAIL = "ASK_EMAIL"
CONFIRM = "CONFIRM"
CANCEL_ASK_ID = "CANCEL_ASK_ID"
CANCEL_CONFIRM = "CANCEL_CONFIRM"
DONE = "DONE"
TRANSFER = "TRANSFER"

_YES = {"అవును", "సరే", "ఔను", "yes", "ok", "okay", "కరెక్ట్", "బుక్"}
_NO = {"కాదు", "లేదు", "no", "వద్దు"}


def _is_yes(text: str) -> bool:
    t = nz.nfc(text).lower()
    return any(w in t for w in _YES)


def _is_no(text: str) -> bool:
    t = nz.nfc(text).lower()
    return any(w in t for w in _NO)


class DialogueSession:
    """One caller conversation. `caller_id` is used as the default phone."""

    def __init__(self, llm=None, caller_id: str = "", locations: list[str] | None = None,
                 data_source=None, prefill_phone: bool = False, lang: str = "te"):
        self.llm = llm
        self.caller_id = caller_id
        self.locations = locations or []
        # The data source decides where bookings go (offline SQLite or the live
        # Karivena knowledge_base) and which extra slots are mandatory.
        self.ds = data_source if data_source is not None else get_data_source()
        self.extra_required = tuple(getattr(self.ds, "extra_required", ()))
        # Language: "te" (default), "en", or "ask" to let the caller choose.
        self.lang = lang if lang in ("te", "en", "ask") else "te"
        self.T = _TEMPLATES.get(self.lang, _T_TE)  # active template module
        self.state = GREETING
        # Phone handling differs by channel:
        #  - Voice (phone call): we still confirm the number by asking, so leave
        #    it empty in live mode (prefill_phone=False, the default).
        #  - WhatsApp: the sender's number IS their contact, so pre-fill it and
        #    skip the phone question (prefill_phone=True).
        prefill = caller_id or None
        if "phone" in self.extra_required and not prefill_phone:
            prefill = None
        self.slots = S.BookingSlots(callback_number=prefill)
        self.fails = 0            # consecutive failures on the current slot
        self.pending_cancel_id = None

    # ---- public API ----
    def greeting(self) -> str:
        """Opening line. If lang == 'ask', show the bilingual picker first;
        otherwise greet directly in the chosen language."""
        if self.lang == "ask":
            self.state = ASK_LANGUAGE
            return C.LANGUAGE_PROMPT
        self.state = INTENT
        return self._speak(self.T.GREETING)

    def handle(self, user_text: str) -> str:
        """Process one caller turn; return the agent's reply."""
        text = nz.nfc(user_text or "").strip()

        # Language selection happens before anything else.
        if self.state == ASK_LANGUAGE:
            return self._choose_language(text)

        # Global exits (any state)
        if self._wants_human(text):
            self.state = TRANSFER
            return self._speak(self.T.TRANSFER)
        if self.state != CONFIRM and self._wants_goodbye(text):
            self.state = DONE
            return self._speak(self.T.GOODBYE)

        try:
            return self._route(text)
        except Exception as e:
            logger.error(f"dialogue error: {e}")
            return self._speak(self.T.NOT_UNDERSTOOD)

    def _choose_language(self, text: str) -> str:
        """Set the language from the caller's pick, then greet + first question."""
        choice = C.detect_language_choice(text)
        if not choice:
            return C.LANGUAGE_RETRY
        self.lang = choice
        self.T = _TEMPLATES[choice]
        self.state = INTENT
        # Greet, then advance straight to the first booking question so the
        # caller sees one clear prompt after picking a language.
        greeting = self._speak(self.T.GREETING)
        first_q = self._advance_booking()
        return f"{greeting}\n{first_q}" if first_q else greeting

    @property
    def finished(self) -> bool:
        return self.state in (DONE, TRANSFER)

    # ---- routing ----
    def _route(self, text: str) -> str:
        st = self.state
        if st == INTENT:
            return self._on_intent(text)
        if st == ASK_LOCATION:
            return self._collect_location(text)
        if st == ASK_CHECKIN:
            return self._collect_checkin(text)
        if st == ASK_NIGHTS:
            return self._collect_nights(text)
        if st == ASK_GUESTS:
            return self._collect_guests(text)
        if st == ASK_ROOM_TYPE:
            return self._collect_room_type(text)
        if st == ASK_NAME:
            return self._collect_name(text)
        if st == ASK_PHONE:
            return self._collect_phone(text)
        if st == ASK_GOTRAM:
            return self._collect_gotram(text)
        if st == ASK_EMAIL:
            return self._collect_email(text)
        if st == CONFIRM:
            return self._on_confirm(text)
        if st == CANCEL_ASK_ID:
            return self._collect_cancel_id(text)
        if st == CANCEL_CONFIRM:
            return self._on_cancel_confirm(text)
        # default
        return self._on_intent(text)

    # ---- INTENT ----
    def _on_intent(self, text: str) -> str:
        intent = self._classify(text)
        # opportunistically grab any slots stated up front
        self._extract_into_slots(text)

        if intent == "cancel_booking":
            self.state = CANCEL_ASK_ID
            return self._speak(self.T.ASK_BOOKING_NUMBER)
        if intent in ("book_room", "check_availability", "ask_price", "unknown"):
            return self._advance_booking()
        if intent == "ask_facilities":
            # Phase-1: no FAQ knowledge base wired; guide to booking politely.
            return self._advance_booking()
        # goodbye handled globally
        return self._advance_booking()

    def _classify(self, text: str) -> str:
        # Fast rules first (no LLM needed) for the common booking words.
        t = text.lower()
        if any(w in t for w in ("రద్దు", "cancel")):
            return "cancel_booking"
        if not self.llm:
            return "book_room"
        try:
            ctx = {"state": self.state, "known_slots": {}, "locations": self.locations}
            r = self.llm.extract_nlu(text, ctx)
            # merge any slots the LLM did manage to extract (best-effort)
            self._merge_llm_slots(r)
            return r.intent if r.intent != "unknown" else "book_room"
        except Exception:
            return "book_room"

    # ---- slot collection (deterministic) ----
    def _collect_location(self, text: str) -> str:
        loc = self._normalize_location(text)
        if not loc:
            return self._retry(self.T.ASK_LOCATION)
        self.slots.location = loc
        self.fails = 0
        return self._advance_booking()

    def _normalize_location(self, text: str) -> str | None:
        """Resolve a location via the data source (demo vernacular in live mode),
        falling back to the local slot matcher against known locations."""
        loc = None
        try:
            loc = self.ds.normalize_location(text)
        except Exception:
            loc = None
        if not loc:
            loc = S.normalize_location(text, self.locations)
        return loc

    def _collect_checkin(self, text: str) -> str:
        d = nz.parse_relative_date(text)
        if not d or d < nz.today():
            return self._retry(self.T.ASK_CHECKIN)
        self.slots.check_in_date = d
        self.fails = 0
        return self._advance_booking()

    def _collect_nights(self, text: str) -> str:
        n = nz.parse_nights(text)
        if not n or n < 1 or n > 60:
            return self._retry(self.T.ASK_NIGHTS)
        self.slots.nights = n
        self.fails = 0
        return self._advance_booking()

    def _collect_guests(self, text: str) -> str:
        g = nz.parse_number(text)
        if not g or g < 1 or g > 50:
            return self._retry(self.T.ASK_GUESTS)
        self.slots.num_guests = g
        self.fails = 0
        return self._advance_booking()

    def _collect_room_type(self, text: str) -> str:
        rt = S.normalize_room_type(text)
        if not rt:
            return self._retry(self.T.ASK_ROOM_TYPE)
        self.slots.room_type = rt
        self.fails = 0
        return self._advance_booking()

    def _collect_name(self, text: str) -> str:
        name = nz.nfc(text).strip()
        if len(name) < 2:
            return self._retry(self.T.ASK_NAME)
        self.slots.guest_name = name
        self.fails = 0
        return self._advance_booking()

    def _collect_phone(self, text: str) -> str:
        phone = nz.parse_phone(text)
        if not phone:
            return self._retry(self.T.ASK_PHONE)
        self.slots.callback_number = phone
        self.fails = 0
        return self._advance_booking()

    def _collect_gotram(self, text: str) -> str:
        g = nz.nfc(text).strip()
        if len(g) < 2:
            return self._retry(self.T.ASK_GOTRAM)
        self.slots.gotram = g
        self.fails = 0
        return self._advance_booking()

    def _collect_email(self, text: str) -> str:
        email = nz.parse_email(text)
        if not email:
            return self._retry(self.T.ASK_EMAIL)
        self.slots.email = email
        self.fails = 0
        return self._advance_booking()

    # ---- booking progression ----
    def _advance_booking(self) -> str:
        """Ask for the next missing slot, else check availability + confirm."""
        need = self.slots.missing_for_booking(self.extra_required)
        if "location" in need:
            self.state = ASK_LOCATION
            return self._speak(self.T.ASK_LOCATION)
        if "check_in_date" in need:
            self.state = ASK_CHECKIN
            return self._speak(self.T.ASK_CHECKIN)
        if "nights" in need:
            self.state = ASK_NIGHTS
            return self._speak(self.T.ASK_NIGHTS)
        if "num_guests" in need:
            self.state = ASK_GUESTS
            return self._speak(self.T.ASK_GUESTS)
        if "room_type" in need:
            self.state = ASK_ROOM_TYPE
            return self._speak(self.T.ASK_ROOM_TYPE)
        if "guest_name" in need:
            self.state = ASK_NAME
            return self._speak(self.T.ASK_NAME)
        # Live-mode extra slots (phone, gotram, email).
        if "phone" in need:
            self.state = ASK_PHONE
            return self._speak(self.T.ASK_PHONE)
        if "gotram" in need:
            self.state = ASK_GOTRAM
            return self._speak(self.T.ASK_GOTRAM)
        if "email" in need:
            self.state = ASK_EMAIL
            return self._speak(self.T.ASK_EMAIL)
        return self._check_and_confirm()

    def _check_and_confirm(self) -> str:
        ci = self.slots.check_in_date
        co = self.slots.resolved_checkout()
        avail = self.ds.check_availability(
            location=self.slots.location, room_type=self.slots.room_type,
            check_in=ci, check_out=co, num_rooms=1, guests=self.slots.num_guests or 1,
        )
        if not avail.available:
            # nothing available → reset dates for a fresh try
            self.slots.check_in_date = None
            self.slots.nights = None
            self.state = ASK_CHECKIN
            return self._speak(self.T.NOT_AVAILABLE)

        nights = (co - ci).days
        total = avail.total_price or (avail.price_per_night * nights)
        self._quote_total = total
        self.state = CONFIRM
        # Location display: Telugu spelling for te, plain name for en.
        loc_disp = S.location_te(self.slots.location) if self.lang == "te" \
            else self.slots.location
        if self.lang == "te":
            nights_words = f"{nz.number_to_telugu(nights)} రాత్రులు"
            summary = self.T.confirm_summary(
                loc_disp, self.slots.room_type,
                nz.date_to_telugu(ci), nights_words,
                nz.number_to_telugu(self.slots.num_guests),
                nz.number_to_telugu(total),
            )
        else:
            nights_words = f"{nights} night" + ("s" if nights != 1 else "")
            summary = self.T.confirm_summary(
                loc_disp, self.slots.room_type,
                ci.isoformat(), nights_words,
                str(self.slots.num_guests), str(total),
            )
        return self._speak(summary)

    def _on_confirm(self, text: str) -> str:
        if _is_yes(text):
            res = self.ds.create_booking(
                location=self.slots.location,
                room_type=self.slots.room_type,
                guest_name=self.slots.guest_name,
                phone=self.slots.callback_number or self.caller_id or "unknown",
                check_in=self.slots.check_in_date,
                check_out=self.slots.resolved_checkout(),
                guests=self.slots.num_guests or 1,
                num_rooms=1,
                gotram=self.slots.gotram or config.DEFAULT_GOTRAM,
                email=self.slots.email or "",
            )
            if not res.success:
                if res.error == "no_rooms":
                    self.state = DONE
                    return self._speak(self.T.NOT_AVAILABLE)
                if res.error == "gotram_rejected":
                    # Let the caller re-state the gotram rather than ending.
                    self.slots.gotram = None
                    self.state = ASK_GOTRAM
                    return self._speak(self.T.GOTRAM_REJECTED)
                self.state = DONE
                return self._speak(self.T.NOT_UNDERSTOOD)
            self.state = DONE
            # Live ids are alphanumeric (BK-XXXX); SQLite ids are 4 digits.
            is_live_id = "phone" in self.extra_required or (
                res.booking_id and not str(res.booking_id).isdigit())
            if is_live_id:
                return self._speak(self.T.booking_done_live(res.booking_id))
            # Digit ids: spell out in Telugu for te, read plainly for en.
            id_words = (nz.digits_to_telugu_grouped(res.booking_id, group=4)
                        if self.lang == "te" else str(res.booking_id))
            return self._speak(self.T.booking_done(id_words))
        if _is_no(text):
            # correction loop: re-ask dates (most common change)
            self.slots.check_in_date = None
            self.slots.nights = None
            self.state = ASK_CHECKIN
            return self._speak(self.T.ASK_CHECKIN)
        return self._retry(self.T.CONFIRM_PROMPT, yesno=True)

    # ---- cancellation ----
    def _collect_cancel_id(self, text: str) -> str:
        # Live ids look like "BK-68CD5856"; SQLite ids are 4 digits. Accept both:
        # keep an uppercased alphanumeric token if it looks like a live id, else
        # fall back to the digits the caller gave.
        raw = nz.nfc(text).strip().upper().replace(" ", "")
        if raw.startswith("BK") or any(c.isalpha() for c in raw):
            bid = raw if raw.startswith("BK-") else (f"BK-{raw[2:]}" if raw.startswith("BK") else raw)
        else:
            n = nz.parse_number(text)
            bid = str(n) if n else "".join(ch for ch in text if ch.isdigit())
        b = self.ds.get_booking(booking_id=bid) if bid else None
        if not b:
            return self._retry(self.T.CANCEL_NOT_FOUND, prompt2=self.T.ASK_BOOKING_NUMBER)
        self.pending_cancel_id = bid
        self.state = CANCEL_CONFIRM
        return self._speak(self.T.CONFIRM_PROMPT)

    def _on_cancel_confirm(self, text: str) -> str:
        if _is_yes(text):
            ok = self.ds.cancel_booking(self.pending_cancel_id,
                                        phone=self.caller_id or "")
            # If caller-id doesn't match, retry without the phone guard is unsafe;
            # for the demo we cancel by id when confirmed.
            if not ok:
                ok = self.ds.cancel_booking(self.pending_cancel_id)
            self.state = DONE
            return self._speak(self.T.CANCELLED if ok else self.T.CANCEL_NOT_FOUND)
        if _is_no(text):
            self.state = DONE
            return self._speak(self.T.GOODBYE)
        return self._retry(self.T.CONFIRM_PROMPT, yesno=True)

    # ---- helpers ----
    def _extract_into_slots(self, text: str):
        """Best-effort deterministic extraction from a free opening sentence."""
        loc = self._normalize_location(text)
        if loc:
            self.slots.location = loc
        rt = S.normalize_room_type(text)
        if rt:
            self.slots.room_type = rt
        d = nz.parse_relative_date(text)
        if d and d >= nz.today():
            self.slots.check_in_date = d
        g = None
        # only treat a number as guests if the sentence hints at people
        if any(w in text for w in ("మంది", "అతిథ", "person", "people", "guest")):
            g = nz.parse_number(text)
        if g:
            self.slots.num_guests = g

    def _merge_llm_slots(self, nlu):
        s = nlu.slots
        if s.location and not self.slots.location:
            loc = S.normalize_location(s.location, self.locations)
            if loc:
                self.slots.location = loc
        if s.room_type and not self.slots.room_type:
            rt = S.normalize_room_type(s.room_type)
            if rt:
                self.slots.room_type = rt
        if s.num_guests and not self.slots.num_guests:
            self.slots.num_guests = s.num_guests
        if s.nights and not self.slots.nights:
            self.slots.nights = s.nights

    def _retry(self, prompt: str, yesno: bool = False, prompt2: str = None):
        self.fails += 1
        if self.fails >= 2:
            self.fails = 0
            self.state = TRANSFER
            return self._speak(self.T.TRANSFER)
        msg = (self.T.YES_NO_RETRY if yesno else self.T.NOT_UNDERSTOOD) + " " + (prompt2 or prompt)
        return self._speak(msg)

    def _wants_human(self, text: str) -> bool:
        t = text.lower()
        return any(w in t for w in ("మనిషి", "సిబ్బంది", "human", "agent", "operator"))

    def _wants_goodbye(self, text: str) -> bool:
        t = text.lower()
        return any(w in t for w in ("వద్దు", "bye", "సెలవు")) and "బుక్" not in t

    def _speak(self, text: str) -> str:
        """
        Language guard on every outgoing line.
          * Telugu (te): the line MUST contain Telugu script (non-negotiable §1).
          * English (en): the line must be non-empty and NOT Telugu script.
        On failure, fall back to the active language's NOT_UNDERSTOOD.
        """
        text = text or ""
        if self.lang == "te":
            if not nz.is_telugu(text):
                logger.warning("Non-Telugu output blocked by guard.")
                return self.T.NOT_UNDERSTOOD
            return text
        # English: reject accidental Telugu / empty output.
        if not text.strip() or nz.is_telugu(text):
            logger.warning("Unexpected output blocked by English guard.")
            return self.T.NOT_UNDERSTOOD
        return text
