/**
 * Voice Gateway Configuration
 * Loads from .env and provides defaults for all services.
 */
require('dotenv').config();

module.exports = {
  // Server
  port: parseInt(process.env.PORT || '3000', 10),
  publicUrl: process.env.PUBLIC_URL || 'http://localhost:3000',

  // Twilio
  twilio: {
    accountSid: process.env.TWILIO_ACCOUNT_SID || '',
    authToken: process.env.TWILIO_AUTH_TOKEN || '',
    phoneNumber: process.env.TWILIO_PHONE_NUMBER || '',
  },

  // Ollama
  ollama: {
    host: process.env.OLLAMA_HOST || 'http://localhost:11434',
    model: process.env.OLLAMA_MODEL || 'llama3.2',
    // Voice-optimized parameters
    options: {
      temperature: 0.4,
      num_predict: 80,      // Short responses for voice
      num_ctx: 2048,        // Small context for speed
      top_p: 0.8,
      repeat_penalty: 1.1,
    },
  },

  // Firebase
  firebase: {
    keyPath: process.env.FIREBASE_KEY_PATH || 'firebase-key.json',
    projectId: 'hotel-pms-prototype',
  },

  // Concurrency
  maxConcurrentCalls: parseInt(process.env.MAX_CONCURRENT_CALLS || '3', 10),

  // Speech recognition settings
  speech: {
    language: 'en-IN',
    speechTimeout: 'auto',
    speechModel: 'phone_call',
    timeout: 5,  // seconds to wait for speech
  },

  // Voice settings for TTS
  voice: {
    name: 'Polly.Aditi',  // Indian English female voice
    language: 'en-IN',
  },
};
