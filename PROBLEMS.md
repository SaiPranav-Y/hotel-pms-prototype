# KS-PMS — Problems Faced & How to Fix Them

A running log of real issues hit during development and the exact steps that resolved them.
Add new entries at the top so the most recent problems are easiest to find.

---

## [2026-10-02] Voice recording only captured user mic — Kaveri's voice missing

### Symptom
After a call, the saved recording (`.webm` file in `voice-ai/recordings/`) contained only the user's microphone audio. Kaveri's responses were audible during the call but completely absent from the recording.

### Root Cause (3 layers)

**Layer 1 — `edge-tts` was not installed (primary cause)**
`voice-ai/app/local_tts.py` tries three TTS engines in order: Piper → edge-tts → browser fallback.
Piper was not installed. `edge-tts` was also not installed, so `synthesize_speech()` returned `None`.
When `None` is returned, `call_handler.py` sends a `text_response` WebSocket message (no audio bytes).
The browser then used the Web Speech API (`window.speechSynthesis`) to speak Kaveri's lines.

The Web Speech API routes audio directly through the OS audio stack — **it cannot be intercepted,
captured, or routed through the Web Audio API**. No amount of `AudioContext` wiring can fix this
because the audio never enters the browser's Web Audio graph at all.

**Layer 2 — `createMediaElementSource` on a data-URI `<Audio>` element fails silently**
An earlier fix attempted to use `audioCtx.createMediaElementSource(audioElement)` where the element
was constructed as `new Audio('data:audio/mp3;base64,...')`. Chrome throws `NotSupportedError`
for this pattern when the element is not attached to the DOM and has not fully loaded. The error
was swallowed by a `try/catch`, so the audio played through speakers but never entered the mix bus.

**Layer 3 — `AudioContext` suspension between turns**
Chrome can suspend an `AudioContext` between turns if the tab is backgrounded or there is a gap
in audio activity. Calling `decodeAudioData` on a suspended context silently does nothing.

### Fix

**Step 1 — Install edge-tts**
```bash
cd voice-ai
pip install edge-tts
```
Verify it works:
```bash
python -c "
import asyncio, tempfile, os
async def t():
    import edge_tts
    c = edge_tts.Communicate('Test.', voice='en-IN-NeerjaNeural')
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f: p=f.name
    await c.save(p)
    print(os.path.getsize(p), 'bytes')
    os.unlink(p)
asyncio.run(t())
```
Expected output: a non-zero byte count (e.g. `21888 bytes`).

**Step 2 — Replace `<Audio>`-element playback with `AudioBufferSourceNode`**
File: `voice-ai/app/pages/call_page.py`

Instead of creating an `<Audio>` element and trying to wire it into the `AudioContext` after the
fact, decode the base64 mp3 directly into an `AudioBuffer` via `audioCtx.decodeAudioData()` and
play it as a `BufferSourceNode`. This node is connected to both `audioCtx.destination` (speakers)
and `mixDest` (the `MediaStreamDestination` that `MediaRecorder` is listening to), so Kaveri's
audio is captured in the recording automatically.

Key points in the corrected `playAudioBuffer()`:
- Call `await audioCtx.resume()` before decoding to handle any suspended state.
- Use `tmp.buffer.slice(0)` to pass an owned `ArrayBuffer` copy to `decodeAudioData` —
  Chrome transfers (detaches) the buffer it receives, so sharing it causes corruption.
- Connect `src` to BOTH `audioCtx.destination` AND `mixDest` before calling `src.start(0)`.

```js
async function playAudioBuffer(b64) {
    if (audioCtx.state === 'suspended') await audioCtx.resume();
    const bin = atob(b64);
    const tmp = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) tmp[i] = bin.charCodeAt(i);
    const arrayBuf = tmp.buffer.slice(0); // owned copy

    return new Promise(resolve => {
        audioCtx.decodeAudioData(arrayBuf, buf => {
            const src = audioCtx.createBufferSource();
            src.buffer = buf;
            src.connect(audioCtx.destination); // → speakers
            src.connect(mixDest);               // → recording
            src.onended = resolve;
            src.start(0);
        }, e => { console.warn('decode error', e); resolve(); });
    });
}
```

**Step 3 — Record the mix bus, not the raw mic stream**
`MediaRecorder` must be created with `mixDest.stream`, not `micStream`:
```js
rec = new MediaRecorder(mixDest.stream, { mimeType: mt });
```
The mic is routed into `mixDest` via a `MediaStreamSource` node. Kaveri's audio is routed in
via the `BufferSourceNode`. Both end up in the recording.

### Files Changed
- `voice-ai/app/pages/call_page.py` — complete JS rewrite of audio playback and recording
- `edge-tts` added to Python environment (add to `voice-ai/requirements.txt` if not present)

### How to Verify Fix
1. Start the backend: `python run.py`
2. Open `http://localhost:8000` in Chrome
3. Make a short test call
4. End the call — check `voice-ai/recordings/` for the new `.webm` file
5. Play it back — both your voice and Kaveri's responses should be audible

---

## [2026-10-02] `seed_staff.py` shows `firebase_auth=NO (Firebase not active)`

### Symptom
Running `python seed_staff.py --reset` created accounts but each line showed
`firebase_auth=NO (Firebase not active)`. Logging in with the generated credentials failed.

### Root Cause
`firebase-admin` Python package was not installed. The `.env` and `firebase-key.json` were
both present and correct, but there was no package to use them. `init_firebase()` caught the
`ImportError` silently and returned `False`, leaving `is_firebase_active()` as `False`.
Accounts were written only to the in-memory `_users` dict, which is lost when the process exits.

### Fix
```bash
cd voice-ai
pip install firebase-admin
```
Then re-run the seed script:
```bash
python seed_staff.py --reset
```
Expected output: `firebase_auth=True` for every account.

### How to Verify Fix
```bash
python -c "
from app.firebase_store import init_firebase, is_firebase_active
init_firebase()
print('Firebase active:', is_firebase_active())
"
```
Should print `Firebase active: True`.

### Files Changed
- None (package install only). Add `firebase-admin` to `voice-ai/requirements.txt` if missing.

---

*Add new entries above this line. Format: `## [YYYY-MM-DD] Short description`*
