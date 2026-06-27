import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/temple.dart';
import '../models/reservation.dart';

/// Exception thrown by [FirestoreService] when Firestore operations fail.
///
/// Wraps the original platform error for debugging while providing a
/// human-readable [message] for display in the UI layer.
class FirestoreServiceException implements Exception {
  final String message;
  final Object? originalError;

  const FirestoreServiceException(this.message, {this.originalError});

  @override
  String toString() => 'FirestoreServiceException: $message';
}

/// Service class encapsulating all Firestore operations for the dashboard.
///
/// Provides real-time streams for reading data and futures for write operations.
/// All methods throw [FirestoreServiceException] on failure.
class FirestoreService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  /// Returns a real-time stream of all reservations ordered by creation time
  /// (newest first).
  Stream<List<Reservation>> getReservationsStream() {
    try {
      return _firestore
          .collection('reservations')
          .orderBy('created_at', descending: true)
          .snapshots()
          .map((snapshot) => snapshot.docs
              .where((doc) {
                final data = doc.data();
                return data['customer_name'] != null &&
                    data['customer_phone'] != null;
              })
              .map((doc) => Reservation.fromMap(doc.id, doc.data()))
              .toList());
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to get reservations stream',
        originalError: e,
      );
    }
  }

  /// Returns a real-time stream of all temples ordered by name ascending.
  Stream<List<Temple>> getTemplesStream() {
    try {
      return _firestore
          .collection('temples')
          .orderBy('temple_name')
          .snapshots()
          .map((snapshot) => snapshot.docs
              .map((doc) => Temple.fromMap(doc.id, doc.data()))
              .toList());
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to get temples stream',
        originalError: e,
      );
    }
  }

  /// Creates a new reservation document in the `reservations` collection.
  Future<void> addReservation(Reservation reservation) async {
    try {
      final data = reservation.toMap();
      // Use Firestore server timestamp for created_at
      data['created_at'] = FieldValue.serverTimestamp();
      await _firestore.collection('reservations').add(data);
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to add reservation',
        originalError: e,
      );
    }
  }

  /// Updates an existing reservation document by [documentId].
  Future<void> updateReservation(
      String documentId, Reservation reservation) async {
    try {
      final data = reservation.toMap();
      // Preserve the original created_at — do not overwrite
      data.remove('created_at');
      await _firestore.collection('reservations').doc(documentId).update(data);
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to update reservation',
        originalError: e,
      );
    }
  }

  /// Deletes a reservation document by [documentId].
  Future<void> deleteReservation(String documentId) async {
    try {
      await _firestore.collection('reservations').doc(documentId).delete();
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to delete reservation',
        originalError: e,
      );
    }
  }

  /// Updates the capacity fields of an existing temple document.
  Future<void> updateTemple(
    String documentId, {
    required int totalCapacity,
    required int availableRooms,
    required int maintenanceRooms,
  }) async {
    try {
      await _firestore.collection('temples').doc(documentId).update({
        'total_capacity': totalCapacity,
        'available_rooms': availableRooms,
        'maintenance_rooms': maintenanceRooms,
      });
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to update temple',
        originalError: e,
      );
    }
  }

  /// Computes the total number of rooms booked across all reservations that
  /// overlap with the given [checkIn] to [checkOut] date range.
  ///
  /// This is the single source of truth for availability calculation.
  static int computeBookedRooms(
    List<Reservation> reservations,
    DateTime checkIn,
    DateTime checkOut,
  ) {
    int totalBooked = 0;
    for (final reservation in reservations) {
      if (reservation.overlaps(checkIn, checkOut)) {
        totalBooked += reservation.noOfRooms;
      }
    }
    return totalBooked;
  }

  /// Computes booked rooms for a specific temple in the given date range.
  /// Matches by [templeName] (the temple's display name).
  static int computeBookedRoomsForTemple(
    List<Reservation> reservations,
    String templeName,
    DateTime checkIn,
    DateTime checkOut,
  ) {
    int totalBooked = 0;
    for (final reservation in reservations) {
      if (reservation.templeName == templeName &&
          reservation.overlaps(checkIn, checkOut)) {
        totalBooked += reservation.noOfRooms;
      }
    }
    return totalBooked;
  }

  /// Computes real-time available rooms for a given date range.
  ///
  /// [totalRooms] is the system-wide total capacity (sum of all temples).
  /// Returns available = totalRooms - bookedInRange.
  static int computeAvailableRooms(
    List<Reservation> reservations,
    int totalRooms,
    DateTime checkIn,
    DateTime checkOut,
  ) {
    final booked = computeBookedRooms(reservations, checkIn, checkOut);
    return (totalRooms - booked).clamp(0, totalRooms);
  }

  /// Computes available rooms for a specific temple in the given date range.
  /// Matches by [templeName] (the temple's display name).
  static int computeAvailableRoomsForTemple(
    List<Reservation> reservations,
    String templeName,
    int templeCapacity,
    DateTime checkIn,
    DateTime checkOut,
  ) {
    final booked = computeBookedRoomsForTemple(
      reservations,
      templeName,
      checkIn,
      checkOut,
    );
    return (templeCapacity - booked).clamp(0, templeCapacity);
  }
}
