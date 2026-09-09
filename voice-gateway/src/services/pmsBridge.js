/**
 * PMS Bridge — connects voice booking data to Firebase Firestore.
 * Writes to the same 'reservations' collection used by the Flutter PMS app.
 * Schema matches: customer_name, temple_name, room_type, check_in, check_out, etc.
 */
const path = require('path');
const config = require('../config/voiceConfig');

let db = null;
let initialized = false;

/**
 * Initialize Firebase Admin SDK.
 */
function initFirebase() {
  if (initialized) return;

  try {
    const admin = require('firebase-admin');
    const keyPath = path.resolve(__dirname, '../../', config.firebase.keyPath);

    if (!require('fs').existsSync(keyPath)) {
      console.warn('[PMS] Firebase key not found at:', keyPath);
      console.warn('[PMS] Bookings will NOT be saved to Firestore.');
      return;
    }

    const serviceAccount = require(keyPath);
    admin.initializeApp({
      credential: admin.credential.cert(serviceAccount),
      projectId: config.firebase.projectId,
    });

    db = admin.firestore();
    initialized = true;
    console.log('[PMS] Firebase connected:', config.firebase.projectId);
  } catch (error) {
    console.error('[PMS] Firebase init failed:', error.message);
  }
}

/**
 * Create a reservation in Firestore.
 * Uses the SAME schema as the Flutter PMS app.
 */
async function createReservation(bookingData, callerPhone) {
  if (!db) {
    console.warn('[PMS] Firebase not connected — booking not saved');
    return { success: false, error: 'Firebase not connected' };
  }

  try {
    const reservation = {
      customer_name: bookingData.guest_name || '',
      customer_phone: callerPhone || '',
      customer_email: bookingData.email || '',
      customer_age: 0,
      gotram: bookingData.gotram || '',
      temple_name: bookingData.location || '',
      room_type: bookingData.room_type || 'AC',
      check_in: bookingData.check_in || '',
      check_out: bookingData.check_out || '',
      no_of_rooms: bookingData.guests || 1,
      reservation_status: 'CONFIRMED',
      reservation_mode: 'Voice Assistant',
      payment_status: 'pending',
      created_at: new Date().toISOString(),
    };

    const docRef = await db.collection('reservations').add(reservation);
    console.log(`[PMS] Reservation created: ${docRef.id}`);

    return {
      success: true,
      reservationId: docRef.id,
      reservation,
    };
  } catch (error) {
    console.error('[PMS] Create reservation failed:', error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Check room availability at a location for given dates.
 * Queries existing reservations that overlap.
 */
async function checkAvailability(location, checkIn, checkOut) {
  if (!db) return { available: true, message: 'Firebase not connected — assuming available' };

  try {
    const snapshot = await db.collection('reservations')
      .where('temple_name', '==', location)
      .where('reservation_status', '==', 'CONFIRMED')
      .get();

    let overlapping = 0;
    snapshot.forEach(doc => {
      const r = doc.data();
      if (r.check_in < checkOut && r.check_out > checkIn) {
        overlapping += r.no_of_rooms || 1;
      }
    });

    // Simple capacity check (use templates data for real limits)
    const available = overlapping < 50; // Generous threshold
    return { available, bookedRooms: overlapping };
  } catch (error) {
    console.error('[PMS] Availability check failed:', error.message);
    return { available: true, message: 'Check failed — assuming available' };
  }
}

// Initialize on load
initFirebase();

module.exports = { createReservation, checkAvailability, initFirebase };
