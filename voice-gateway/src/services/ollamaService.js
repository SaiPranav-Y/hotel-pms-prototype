/**
 * Ollama Service — communicates with local Ollama instance.
 * Supports both standard and streaming responses.
 * Handles JSON extraction for booking completion.
 */
const config = require('../config/voiceConfig');
const { buildMessages } = require('../prompts/receptionistPrompt');

/**
 * Send conversation to Ollama and get response.
 * Returns the assistant's text reply.
 */
async function chat(conversationHistory) {
  const messages = buildMessages(conversationHistory);

  try {
    const response = await fetch(`${config.ollama.host}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.ollama.model,
        messages,
        stream: false,
        options: config.ollama.options,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Ollama HTTP ${response.status}: ${err}`);
    }

    const data = await response.json();
    return data.message?.content || '';
  } catch (error) {
    console.error('[Ollama] Error:', error.message);
    throw error;
  }
}

/**
 * Send conversation to Ollama with streaming.
 * Returns the first sentence quickly for TTS, then full response.
 * Callback: onFirstSentence(text) called as soon as first sentence ready.
 */
async function chatStreaming(conversationHistory, onFirstSentence) {
  const messages = buildMessages(conversationHistory);

  try {
    const response = await fetch(`${config.ollama.host}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.ollama.model,
        messages,
        stream: true,
        options: config.ollama.options,
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let firstSentenceSent = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      // Ollama streams JSON lines
      for (const line of chunk.split('\n').filter(l => l.trim())) {
        try {
          const parsed = JSON.parse(line);
          const token = parsed.message?.content || '';
          fullText += token;

          // Send first sentence as soon as we hit a period or question mark
          if (!firstSentenceSent && /[.?!]/.test(fullText)) {
            const firstSentence = fullText.split(/(?<=[.?!])\s/)[0];
            if (onFirstSentence && firstSentence.length > 10) {
              onFirstSentence(firstSentence);
              firstSentenceSent = true;
            }
          }
        } catch (e) {
          // Skip malformed JSON lines
        }
      }
    }

    return fullText.trim();
  } catch (error) {
    console.error('[Ollama] Streaming error:', error.message);
    throw error;
  }
}

/**
 * Try to extract a complete booking JSON from Ollama's response.
 * Returns the parsed object if found, null otherwise.
 */
function extractBookingJSON(text) {
  // Look for JSON with "status":"COMPLETE"
  const jsonMatch = text.match(/\{[^{}]*"status"\s*:\s*"COMPLETE"[^{}]*\}/);
  if (!jsonMatch) return null;

  try {
    const parsed = JSON.parse(jsonMatch[0]);
    // Validate required fields
    if (parsed.guest_name && parsed.check_in && parsed.check_out && parsed.room_type) {
      return parsed;
    }
  } catch (e) {
    // Invalid JSON
  }
  return null;
}

/**
 * Check if Ollama is reachable.
 */
async function healthCheck() {
  try {
    const res = await fetch(`${config.ollama.host}/api/version`);
    if (res.ok) {
      const data = await res.json();
      return { ok: true, version: data.version };
    }
    return { ok: false, error: `HTTP ${res.status}` };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

module.exports = { chat, chatStreaming, extractBookingJSON, healthCheck };
