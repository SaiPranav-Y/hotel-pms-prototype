"""
Call Handler — strict turn-taking, workflow status, customer enrichment.
Integrates with knowledge_base for call logs and profile management.
"""

import asyncio
import base64
import json
import logging
import time
from fastapi import WebSocket, WebSocketDisconnect

from app.ai_engine import ConversationEngine
from app.local_tts import synthesize_speech
from app.recorder import save_recording
from app.knowledge_base import create_call_log, update_call_workflow, get_customer

logger = logging.getLogger(__name__)

active_calls: dict[str, dict] = {}
_call_counter = 0


class CallSession:
    """Single call session with workflow tracking."""

    def __init__(self, websocket: WebSocket, call_id: str):
        self.websocket = websocket
        self.call_id = call_id
        self.ai_engine = ConversationEngine()
        self._call_start_time = time.time()
        self._lock = asyncio.Lock()

    async def start(self):
        """Send greeting, register call as pending."""
        active_calls[self.call_id] = {
            "call_id": self.call_id,
            "status": "connected",
            "workflow_status": "pending",
            "start_time": self._call_start_time,
            "start_time_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
            "transcript": [],
            "gathered_info": {},
            "has_recording": False,
        }

        greeting = self.ai_engine.get_greeting()
        logger.info(f"[{self.call_id}] Kaveri: {greeting}")
        active_calls[self.call_id]["transcript"].append({"role": "kaveri", "text": greeting})
        await self._send_response(greeting)

    async def handle_text_input(self, text: str):
        """Process one utterance. Locked to prevent overlap."""
        if not text.strip():
            return
        if self._lock.locked():
            logger.info(f"[{self.call_id}] Dropping (busy): '{text}'")
            return

        async with self._lock:
            logger.info(f"[{self.call_id}] Guest: '{text}'")
            active_calls[self.call_id]["transcript"].append({"role": "guest", "text": text})

            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.ai_engine.process_input, text
                )
                if response:
                    logger.info(f"[{self.call_id}] Kaveri: '{response}'")
                    active_calls[self.call_id]["transcript"].append({"role": "kaveri", "text": response})
                    active_calls[self.call_id]["gathered_info"] = self.ai_engine.get_gathered_info()
                    await self._send_response(response)
            except Exception as e:
                logger.error(f"[{self.call_id}] Error: {e}")
                await self._send_response("I apologize, could you please repeat that?")

    async def handle_recording(self, audio_data: bytes, mime_type: str):
        """Save recording."""
        try:
            recording_info = save_recording(self.call_id, audio_data, mime_type)
            active_calls[self.call_id]["has_recording"] = True
            active_calls[self.call_id]["recording_filename"] = recording_info["filename"]
            logger.info(f"[{self.call_id}] Recording saved ({len(audio_data)} bytes)")
        except Exception as e:
            logger.error(f"[{self.call_id}] Recording error: {e}")

    async def _send_response(self, text: str):
        """Send TTS audio or text fallback."""
        try:
            audio_data = await synthesize_speech(text)
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode("ascii")
                await self.websocket.send_json({
                    "type": "audio_response",
                    "text": text,
                    "audio": audio_b64,
                })
            else:
                await self.websocket.send_json({"type": "text_response", "text": text})
        except Exception as e:
            logger.error(f"[{self.call_id}] Send error: {e}")

    async def cleanup(self):
        """End call — create call log, run intelligence analysis, determine workflow."""
        duration = time.time() - self._call_start_time
        gathered = self.ai_engine.get_gathered_info()
        transcript = active_calls.get(self.call_id, {}).get("transcript", [])

        # Run conversation intelligence (async in background)
        analysis = {}
        try:
            from app.intelligence import analyze_call
            analysis = await asyncio.get_event_loop().run_in_executor(
                None, analyze_call, transcript, gathered
            )
        except Exception as e:
            logger.error(f"[{self.call_id}] Intelligence error: {e}")

        # Determine workflow status
        has_booking = "customer_name" in gathered and "check_in" in gathered
        escalation_triggered = gathered.get("_escalation_triggered", False)
        if escalation_triggered:
            workflow = "needs_review"
        elif has_booking:
            workflow = "completed"
        elif gathered:
            workflow = "needs_review"
        else:
            workflow = "pending"

        # Update active call record
        if self.call_id in active_calls:
            active_calls[self.call_id]["status"] = "ended"
            active_calls[self.call_id]["duration"] = duration
            active_calls[self.call_id]["workflow_status"] = workflow
            active_calls[self.call_id]["gathered_info"] = gathered
            active_calls[self.call_id]["analysis"] = analysis

        # Persist call log
        create_call_log(
            call_id=self.call_id,
            duration=duration,
            transcript=[{"role": t["role"], "text": t["text"]} for t in transcript],
            gathered_info=gathered,
            status=workflow,
        )

        # Enrich contact profile
        try:
            from app.contacts import upsert_contact
            phone = gathered.get("customer_phone", "")
            if phone:
                upsert_contact(
                    phone=phone,
                    name=gathered.get("customer_name", ""),
                    age=gathered.get("customer_age", ""),
                    location=gathered.get("location", ""),
                    call_id=self.call_id,
                    tags=analysis.get("tags", []),
                )
        except Exception:
            pass

        # Create escalation if triggered
        if escalation_triggered:
            try:
                from app.escalation import create_escalation
                create_escalation(
                    call_id=self.call_id,
                    reason=gathered.get("_escalation_reason", "Customer requested"),
                    customer_phone=gathered.get("customer_phone", ""),
                    customer_name=gathered.get("customer_name", ""),
                    transcript_summary=analysis.get("summary", ""),
                )
            except Exception:
                pass

        logger.info(f"[{self.call_id}] Ended ({duration:.0f}s) workflow={workflow} intent={analysis.get('intent','?')}")


async def handle_voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for voice calls."""
    global _call_counter
    await websocket.accept()

    _call_counter += 1
    call_id = f"CALL-{_call_counter:04d}"
    session = CallSession(websocket, call_id)

    try:
        await session.start()

        while True:
            message = await websocket.receive()
            if "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type")
                if msg_type == "transcript":
                    await session.handle_text_input(data.get("text", ""))
                elif msg_type == "recording":
                    audio_b64 = data.get("audio", "")
                    mime_type = data.get("mimeType", "audio/webm")
                    if audio_b64:
                        await session.handle_recording(base64.b64decode(audio_b64), mime_type)
                elif msg_type == "end_call":
                    break

    except WebSocketDisconnect:
        logger.info(f"[{call_id}] Disconnected")
    except Exception as e:
        logger.error(f"[{call_id}] Error: {e}")
    finally:
        await session.cleanup()
