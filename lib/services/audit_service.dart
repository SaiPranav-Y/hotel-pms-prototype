import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

/// Append-only audit trail for staff actions.
///
/// Every create / update / delete / status change on a reservation writes an
/// immutable entry to the Firestore `audit_logs` collection. Security rules
/// allow create only (no update/delete) and restrict reads to admins.
///
/// Entry schema mirrors the Python `app/audit.py` module so both channels write
/// the same shape.
class AuditService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  static const _sensitiveKeys = {
    'password_hash',
    'transcript',
    'payment_link',
    'donation_link',
  };

  Map<String, dynamic>? _clean(Map<String, dynamic>? state) {
    if (state == null) return null;
    final out = <String, dynamic>{};
    state.forEach((k, v) {
      if (!_sensitiveKeys.contains(k)) out[k] = v;
    });
    return out;
  }

  /// Record an audit entry. Never throws — auditing must not block the action.
  Future<void> log({
    required String entityType,
    required String entityId,
    required String action,
    Map<String, dynamic>? previousState,
    Map<String, dynamic>? newState,
    String source = 'walk_in',
    String notes = '',
  }) async {
    try {
      final actor = _auth.currentUser?.email ?? 'unknown';
      await _firestore.collection('audit_logs').add({
        'entity_type': entityType,
        'entity_id': entityId,
        'action': action,
        'actor': actor,
        'source': source,
        'previous_state': _clean(previousState),
        'new_state': _clean(newState),
        'timestamp': FieldValue.serverTimestamp(),
        'notes': notes,
      });
    } catch (_) {
      // Swallow — never let auditing break the primary operation.
    }
  }
}
