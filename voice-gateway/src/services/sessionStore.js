/**
 * Session Store — in-memory conversation state per CallSid.
 * Tracks: conversation history, extracted slots, attempt counts.
 */

const sessions = new Map();

/**
 * Create or get a session for a call.
 */
function getSession(callSid) {
  if (!sessions.has(callSid)) {
    sessions.set(callSid, {
      callSid,
      messages: [],
      slots: {
        guest_name: null,
        check_in: null,
        check_out: null,
        room_type: null,
        guests: null,
        whatsapp_number: null,
      },
      status: 'active',         // active | confirming | completed | failed
      attempts: 0,              // number of Ollama turns
      maxAttempts: 15,          // safety: end call after 15 turns
      createdAt: Date.now(),
      callerNumber: null,
    });
  }
  return sessions.get(callSid);
}

/**
 * Add a message to conversation history.
 */
function addMessage(callSid, role, content) {
  const session = getSession(callSid);
  session.messages.push({ role, content });
  session.attempts++;
}

/**
 * Update extracted slots from Ollama JSON output.
 */
function updateSlots(callSid, newSlots) {
  const session = getSession(callSid);
  Object.assign(session.slots, newSlots);
}

/**
 * Check if all required slots are filled.
 */
function allSlotsFilled(callSid) {
  const session = getSession(callSid);
  const { guest_name, check_in, check_out, room_type, guests } = session.slots;
  return !!(guest_name && check_in && check_out && room_type && guests);
}

/**
 * Mark session as complete.
 */
function completeSession(callSid) {
  const session = getSession(callSid);
  session.status = 'completed';
}

/**
 * End and clean up a session.
 */
function endSession(callSid) {
  const session = sessions.get(callSid);
  if (session) {
    session.status = 'ended';
    // Keep for 5 minutes for debugging, then auto-delete
    setTimeout(() => sessions.delete(callSid), 5 * 60 * 1000);
  }
}

/**
 * Get active call count (for concurrency limiting).
 */
function getActiveCount() {
  let count = 0;
  for (const [, session] of sessions) {
    if (session.status === 'active' || session.status === 'confirming') {
      count++;
    }
  }
  return count;
}

/**
 * Check if we can accept a new call (concurrency limit).
 */
function canAcceptCall(maxConcurrent) {
  return getActiveCount() < maxConcurrent;
}

module.exports = {
  getSession,
  addMessage,
  updateSlots,
  allSlotsFilled,
  completeSession,
  endSession,
  getActiveCount,
  canAcceptCall,
};
