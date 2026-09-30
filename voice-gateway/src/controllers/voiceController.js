/**
 * Voice Controller — handles all Twilio webhook endpoints.
 * Routes: /voice/incoming, /voice/process, /voice/confirm, /voice/hangup
 */
const VoiceResponse = require('twilio').twiml.VoiceResponse;
const config = require('../config/voiceConfig');
const sessionStore = require('../services/sessionStore');
const ollamaService = require('../services/ollamaService');
const pmsBridge = require('../services/pmsBridge');

/**
 * POST /voice/incoming — Twilio calls this when someone dials your number.
 * Returns TwiML: greeting + <Gather> to capture speech.
 */
function handleIncoming(req, res) {
  const callSid = req.body.CallSid;
  const callerNumber = req.body.From || '';
  const twiml = new VoiceResponse();

  console.log(`[CALL] Incoming: ${callSid} from ${callerNumber}`);

  // Concurrency check
  if (!sessionStore.canAcceptCall(config.maxConcurrentCalls)) {
    console.log(`[CALL] Rejected (at capacity): ${callSid}`);
    twiml.say(
      { voice: config.voice.name, language: config.voice.language },
      'Namaste. All our agents are currently busy. Please try again in a few minutes. Thank you.'
    );
    twiml.hangup();
    res.type('text/xml').send(twiml.toString());
    return;
  }

  // Initialize session
  const session = sessionStore.getSession(callSid);
  session.callerNumber = callerNumber;

  // Greeting + Gather
  const gather = twiml.gather({
    input: 'speech',
    action: '/voice/process',
    method: 'POST',
    speechTimeout: config.speech.speechTimeout,
    speechModel: config.speech.speechModel,
    language: config.speech.language,
    timeout: config.speech.timeout,
  });

  gather.say(
    { voice: config.voice.name, language: config.voice.language },
    'Namaste! Thank you for calling Karivena Satram accommodations. This is Kaveri. Which location would you like to book a room at?'
  );

  // If no speech detected, prompt again
  twiml.say(
    { voice: config.voice.name, language: config.voice.language },
    'I could not hear you. Please call again.'
  );
  twiml.hangup();

  res.type('text/xml').send(twiml.toString());
}

/**
 * POST /voice/process — Twilio sends transcribed speech here.
 * Routes to Ollama, checks for booking completion, returns TwiML.
 */
async function handleProcess(req, res) {
  const callSid = req.body.CallSid;
  const speechResult = req.body.SpeechResult || '';
  const twiml = new VoiceResponse();

  console.log(`[STT] ${callSid}: "${speechResult}"`);

  const session = sessionStore.getSession(callSid);

  // Safety: end call if too many turns
  if (session.attempts >= session.maxAttempts) {
    twiml.say(
      { voice: config.voice.name, language: config.voice.language },
      'Thank you for calling. For further assistance, please contact our front desk. Goodbye.'
    );
    twiml.hangup();
    sessionStore.endSession(callSid);
    res.type('text/xml').send(twiml.toString());
    return;
  }

  // Add user message to history
  sessionStore.addMessage(callSid, 'user', speechResult);

  try {
    // Call Ollama
    const response = await ollamaService.chat(session.messages);
    console.log(`[LLM] ${callSid}: "${response.substring(0, 100)}"`);

    // Check if Ollama returned a complete booking JSON
    const bookingData = ollamaService.extractBookingJSON(response);

    if (bookingData) {
      // Booking ready — ask for confirmation
      session.status = 'confirming';
      sessionStore.updateSlots(callSid, bookingData);
      sessionStore.addMessage(callSid, 'assistant', response);

      const confirmText = `Let me confirm your booking. ${bookingData.guest_name}, ` +
        `checking in on ${bookingData.check_in}, checking out on ${bookingData.check_out}, ` +
        `${bookingData.room_type} room at ${bookingData.location} for ${bookingData.guests} guests. ` +
        `Shall I confirm this booking?`;

      const gather = twiml.gather({
        input: 'speech',
        action: '/voice/confirm',
        method: 'POST',
        speechTimeout: config.speech.speechTimeout,
        language: config.speech.language,
        timeout: 8,
      });
      gather.say({ voice: config.voice.name, language: config.voice.language }, confirmText);

    } else {
      // Continue conversation
      sessionStore.addMessage(callSid, 'assistant', response);

      // Clean response for TTS (remove any accidental formatting)
      const cleanResponse = response
        .replace(/\*\*/g, '')
        .replace(/[*#\-•]/g, '')
        .replace(/\s+/g, ' ')
        .trim();

      const gather = twiml.gather({
        input: 'speech',
        action: '/voice/process',
        method: 'POST',
        speechTimeout: config.speech.speechTimeout,
        speechModel: config.speech.speechModel,
        language: config.speech.language,
        timeout: config.speech.timeout,
      });
      gather.say({ voice: config.voice.name, language: config.voice.language }, cleanResponse);

      // Fallback if no speech
      twiml.say(
        { voice: config.voice.name, language: config.voice.language },
        'Are you still there? If you need help, please say something.'
      );
      twiml.redirect('/voice/process');
    }

  } catch (error) {
    console.error(`[ERROR] ${callSid}:`, error.message);

    // Fallback: apologize and ask to repeat
    const gather = twiml.gather({
      input: 'speech',
      action: '/voice/process',
      method: 'POST',
      speechTimeout: config.speech.speechTimeout,
      language: config.speech.language,
      timeout: config.speech.timeout,
    });
    gather.say(
      { voice: config.voice.name, language: config.voice.language },
      'I apologize, I had a brief issue. Could you please repeat that?'
    );
  }

  res.type('text/xml').send(twiml.toString());
}

/**
 * POST /voice/confirm — handles yes/no confirmation of booking.
 */
async function handleConfirm(req, res) {
  const callSid = req.body.CallSid;
  const speechResult = (req.body.SpeechResult || '').toLowerCase();
  const twiml = new VoiceResponse();

  console.log(`[CONFIRM] ${callSid}: "${speechResult}"`);

  const session = sessionStore.getSession(callSid);
  const isYes = /yes|yeah|confirm|correct|right|sure|ok|okay|haan|ha/.test(speechResult);
  const isNo = /no|nah|wrong|cancel|change|nahi/.test(speechResult);

  if (isYes) {
    // Create the booking in Firebase
    const result = await pmsBridge.createReservation(session.slots, session.callerNumber);

    if (result.success) {
      twiml.say(
        { voice: config.voice.name, language: config.voice.language },
        'Your booking is confirmed. We have sent the details to your WhatsApp number. Thank you for choosing Karivena Satram. Have a blessed pilgrimage. Goodbye.'
      );
      sessionStore.completeSession(callSid);
    } else {
      twiml.say(
        { voice: config.voice.name, language: config.voice.language },
        'I apologize, there was an issue saving your booking. Our front desk team will contact you shortly to confirm. Thank you. Goodbye.'
      );
    }
    twiml.hangup();
    sessionStore.endSession(callSid);

  } else if (isNo) {
    // Go back to conversation
    session.status = 'active';
    const gather = twiml.gather({
      input: 'speech',
      action: '/voice/process',
      method: 'POST',
      speechTimeout: config.speech.speechTimeout,
      language: config.speech.language,
      timeout: config.speech.timeout,
    });
    gather.say(
      { voice: config.voice.name, language: config.voice.language },
      'No problem. What would you like to change?'
    );

  } else {
    // Didn't understand — ask again
    const gather = twiml.gather({
      input: 'speech',
      action: '/voice/confirm',
      method: 'POST',
      speechTimeout: config.speech.speechTimeout,
      language: config.speech.language,
      timeout: 8,
    });
    gather.say(
      { voice: config.voice.name, language: config.voice.language },
      'Sorry, I did not catch that. Would you like to confirm this booking? Please say yes or no.'
    );
  }

  res.type('text/xml').send(twiml.toString());
}

/**
 * POST /voice/hangup — Twilio status callback when call ends.
 */
function handleHangup(req, res) {
  const callSid = req.body.CallSid;
  console.log(`[HANGUP] ${callSid}`);
  sessionStore.endSession(callSid);
  res.sendStatus(200);
}

module.exports = { handleIncoming, handleProcess, handleConfirm, handleHangup };
