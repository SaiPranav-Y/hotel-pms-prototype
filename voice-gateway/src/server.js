/**
 * Karivena Voice Gateway — Express Server
 * Handles Twilio webhooks, routes to Ollama, manages call sessions.
 */
const express = require('express');
const config = require('./config/voiceConfig');
const voiceController = require('./controllers/voiceController');

const app = express();

// Parse URL-encoded bodies (Twilio sends form data)
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Request logging
app.use((req, res, next) => {
  if (req.method === 'POST') {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  }
  next();
});

// === VOICE ROUTES ===
app.post('/voice/incoming', voiceController.handleIncoming);
app.post('/voice/process', voiceController.handleProcess);
app.post('/voice/confirm', voiceController.handleConfirm);
app.post('/voice/hangup', voiceController.handleHangup);

// === HEALTH CHECK ===
app.get('/health', (req, res) => {
  const sessionStore = require('./services/sessionStore');
  res.json({
    status: 'ok',
    service: 'karivena-voice-gateway',
    activeCalls: sessionStore.getActiveCount(),
    maxConcurrent: config.maxConcurrentCalls,
    ollamaHost: config.ollama.host,
    model: config.ollama.model,
  });
});

// === START SERVER ===
app.listen(config.port, () => {
  console.log('');
  console.log('='.repeat(60));
  console.log('  Karivena Voice Gateway — Twilio + Ollama');
  console.log('='.repeat(60));
  console.log(`  Server:    http://localhost:${config.port}`);
  console.log(`  Health:    http://localhost:${config.port}/health`);
  console.log(`  Webhook:   ${config.publicUrl}/voice/incoming`);
  console.log(`  Ollama:    ${config.ollama.host} (${config.ollama.model})`);
  console.log(`  Max Calls: ${config.maxConcurrentCalls} concurrent`);
  console.log('');
  console.log('  Configure Twilio Voice Webhook to:');
  console.log(`    POST ${config.publicUrl}/voice/incoming`);
  console.log('='.repeat(60));
  console.log('');
});
