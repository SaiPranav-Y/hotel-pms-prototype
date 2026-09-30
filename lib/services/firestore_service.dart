import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/temple.dart';
import '../models/reservation.dart';
import 'audit_service.dart';

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

/// Thrown by the atomic booking transaction when capacity would be exceeded on
/// one or more nights of the requested stay.
class RoomUnavailableException implements Exception {
  final String templeName;
  final DateTime date;
  final int available;
  final int requested;

  const RoomUnavailableException(
    this.templeName,
    this.date, {
    required this.available,
    required this.requested,
  });

  String get message =>
      'Only $available room(s) left at $templeName on '
      '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year} '
      '(you requested $requested).';

  @override
  String toString() => 'RoomUnavailableException: $message';
}

/// One page of reservations returned by cursor-based pagination.
class ReservationPage {
  final List<Reservation> reservations;
  final DocumentSnapshot<Map<String, dynamic>>? lastDocument;
  final bool hasMore;

  const ReservationPage({
    required this.reservations,
    required this.lastDocument,
    required this.hasMore,
  });
}

/// Service class encapsulating all Firestore operations for the dashboard.
///
/// Provides real-time streams for reading data and futures for write operations.
/// All methods throw [FirestoreServiceException] on failure.
class FirestoreService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final AuditService _audit = AuditService();

  /// Default page size for reservation reads.
  static const int kReservationsPageSize = 25;

  /// Returns a BOUNDED real-time stream of the most recent reservations
  /// (newest first, capped at [limit]). This replaces the previous unbounded
  /// listener so the dashboard doesn't stream the entire collection. For full
  /// browsing use the paginated [fetchReservationsPage].
  Stream<List<Reservation>> getReservationsStream({int limit = 100}) {
    try {
      return _firestore
          .collection('reservations')
          .orderBy('created_at', descending: true)
          .limit(limit)
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

  /// One page of reservations for cursor-based pagination.
  ///
  /// Pass [startAfter] = the last document of the previous page to fetch the
  /// next page. Returns the mapped reservations plus the raw last document
  /// (use it as the next [startAfter]). Reads are `.get()` (not streamed), so
  /// only [pageSize] docs are billed/transferred per page.
  Future<ReservationPage> fetchReservationsPage({
    DocumentSnapshot<Map<String, dynamic>>? startAfter,
    int pageSize = kReservationsPageSize,
    String? templeName,
    String? status,
  }) async {
    try {
      Query<Map<String, dynamic>> q = _firestore.collection('reservations');
      // Optional server-side filters (backed by composite indexes).
      if (templeName != null && templeName.isNotEmpty) {
        q = q.where('temple_name', isEqualTo: templeName);
      }
      if (status != null && status.isNotEmpty) {
        q = q.where('reservation_status', isEqualTo: status);
      }
      q = q.orderBy('created_at', descending: true).limit(pageSize);
      if (startAfter != null) {
        q = q.startAfterDocument(startAfter);
      }

      final snap = await q.get();
      final docs = snap.docs
          .where((d) =>
              d.data()['customer_name'] != null &&
              d.data()['customer_phone'] != null)
          .toList();

      final items =
          docs.map((d) => Reservation.fromMap(d.id, d.data())).toList();

      return ReservationPage(
        reservations: items,
        lastDocument: snap.docs.isNotEmpty ? snap.docs.last : null,
        hasMore: snap.docs.length == pageSize,
      );
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to fetch reservations page',
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
  ///
  /// NOTE: This is the non-atomic path (kept for edits / back-compat). For NEW
  /// bookings prefer [createReservationAtomic], which prevents double-booking.
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

  // ===========================================================================
  //  CONCURRENCY-SAFE BOOKING
  // ---------------------------------------------------------------------------
  //  Availability is tracked with per-(temple, date) counter documents in the
  //  `availability` collection (id = "<templeKey>__<yyyy-MM-dd>", fields:
  //  { temple_name, date, capacity, booked }). A Firestore TRANSACTION reads
  //  every night's counter, verifies capacity, then writes the reservation and
  //  bumps the counters atomically. Walk-in (Flutter), Voice, and WhatsApp all
  //  contend on the SAME counters, so the last room cannot be double-booked.
  // ===========================================================================

  static String _templeKey(String templeName) =>
      templeName.trim().toLowerCase().replaceAll(RegExp(r'[\s_]+'), '_');

  static String _dateStr(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  static String availabilityDocId(String templeName, DateTime day) =>
      '${_templeKey(templeName)}__${_dateStr(day)}';

  /// The list of night-dates covered by a stay (check-in inclusive, check-out
  /// exclusive) — one counter per night.
  static List<DateTime> nightsOf(DateTime checkIn, DateTime checkOut) {
    final nights = <DateTime>[];
    var cur = DateTime(checkIn.year, checkIn.month, checkIn.day);
    final end = DateTime(checkOut.year, checkOut.month, checkOut.day);
    while (cur.isBefore(end)) {
      nights.add(cur);
      cur = cur.add(const Duration(days: 1));
    }
    if (nights.isEmpty) {
      nights.add(DateTime(checkIn.year, checkIn.month, checkIn.day));
    }
    return nights;
  }

  /// Atomically create a reservation, guaranteeing rooms are available for every
  /// night. Throws [RoomUnavailableException] if capacity would be exceeded,
  /// or [FirestoreServiceException] on other failures.
  ///
  /// [templeCapacity] is the total rooms at the temple (from the `temples`
  /// collection). Returns the new reservation document id.
  Future<String> createReservationAtomic(
    Reservation reservation, {
    required int templeCapacity,
  }) async {
    final nights = nightsOf(reservation.checkIn, reservation.checkOut);
    final rooms = reservation.noOfRooms;

    try {
      return await _firestore.runTransaction<String>((txn) async {
        // 1. READ every night's counter first (transactions require all reads
        //    before any writes).
        final counterRefs = nights
            .map((d) => _firestore
                .collection('availability')
                .doc(availabilityDocId(reservation.templeName, d)))
            .toList();

        final snapshots = <DocumentSnapshot<Map<String, dynamic>>>[];
        for (final ref in counterRefs) {
          snapshots.add(await txn.get(ref));
        }

        // 2. VERIFY capacity on each night.
        for (var i = 0; i < snapshots.length; i++) {
          final data = snapshots[i].data();
          final capacity = (data?['capacity'] as int?) ?? templeCapacity;
          final booked = (data?['booked'] as int?) ?? 0;
          if (booked + rooms > capacity) {
            throw RoomUnavailableException(
              reservation.templeName,
              nights[i],
              available: (capacity - booked).clamp(0, capacity),
              requested: rooms,
            );
          }
        }

        // 3. WRITE the reservation + bump every counter atomically.
        final resRef = _firestore.collection('reservations').doc();
        final data = reservation.toMap();
        data['created_at'] = FieldValue.serverTimestamp();
        txn.set(resRef, data);

        for (var i = 0; i < counterRefs.length; i++) {
          txn.set(
            counterRefs[i],
            {
              'temple_name': reservation.templeName,
              'date': _dateStr(nights[i]),
              'capacity':
                  (snapshots[i].data()?['capacity'] as int?) ?? templeCapacity,
              'booked': FieldValue.increment(rooms),
              'updated_at': FieldValue.serverTimestamp(),
            },
            SetOptions(merge: true),
          );
        }

        return resRef.id;
      });
    } on RoomUnavailableException {
      rethrow;
    } catch (e) {
      throw FirestoreServiceException(
        'Failed to create reservation atomically',
        originalError: e,
      );
    } finally {
      // (audit logged by caller path below)
    }
  }

  /// Create a reservation atomically AND write an audit entry. Preferred entry
  /// point for the walk-in flow.
  Future<String> createReservationAudited(
    Reservation reservation, {
    required int templeCapacity,
    String source = 'walk_in',
  }) async {
    final id = await createReservationAtomic(reservation,
        templeCapacity: templeCapacity);
    await _audit.log(
      entityType: 'reservation',
      entityId: id,
      action: 'create',
      newState: reservation.toMap(),
      source: source,
    );
    return id;
  }

  /// Release the per-night counters for a reservation (call on cancel/delete).
  Future<void> releaseReservationCounters(Reservation reservation) async {
    final nights = nightsOf(reservation.checkIn, reservation.checkOut);
    final rooms = reservation.noOfRooms;
    try {
      await _firestore.runTransaction((txn) async {
        final refs = nights
            .map((d) => _firestore
                .collection('availability')
                .doc(availabilityDocId(reservation.templeName, d)))
            .toList();
        final snaps = <DocumentSnapshot<Map<String, dynamic>>>[];
        for (final r in refs) {
          snaps.add(await txn.get(r));
        }
        for (var i = 0; i < refs.length; i++) {
          if (!snaps[i].exists) continue;
          final booked = (snaps[i].data()?['booked'] as int?) ?? 0;
          final next = (booked - rooms).clamp(0, 1 << 30);
          txn.update(refs[i], {
            'booked': next,
            'updated_at': FieldValue.serverTimestamp(),
          });
        }
      });
    } catch (_) {
      // Non-fatal: counters can be reconciled; don't block the cancel.
    }
  }

  /// Updates an existing reservation document by [documentId].
  Future<void> updateReservation(
      String documentId, Reservation reservation) async {
    try {
      final ref = _firestore.collection('reservations').doc(documentId);
      // Capture previous state for the audit trail.
      final before = (await ref.get()).data();
      final data = reservation.toMap();
      // Preserve the original created_at — do not overwrite
      data.remove('created_at');
      await ref.update(data);
      await _audit.log(
        entityType: 'reservation',
        entityId: documentId,
        action: 'update',
        previousState: before,
        newState: data,
      );
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
      final ref = _firestore.collection('reservations').doc(documentId);
      final before = (await ref.get()).data();
      await ref.delete();
      await _audit.log(
        entityType: 'reservation',
        entityId: documentId,
        action: 'delete',
        previousState: before,
      );
      // Free availability counters for the deleted booking (best effort).
      if (before != null) {
        try {
          await releaseReservationCounters(
              Reservation.fromMap(documentId, before));
        } catch (_) {}
      }
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
