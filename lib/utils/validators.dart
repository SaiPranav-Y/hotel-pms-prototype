/// Shared input validation + sanitization for the Flutter PMS.
///
/// Mirrors the backend `app/validators.py` rules so the walk-in form and the
/// voice/WhatsApp channels accept/reject the same inputs. Use these in
/// `TextFormField.validator` and sanitize before writing to Firestore.
class Validators {
  static final RegExp _emailRe = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
  static final RegExp _controlRe = RegExp(r'[\x00-\x1f\x7f]');
  // Letters (incl. Telugu block), space, dot, apostrophe, hyphen.
  static final RegExp _nameDisallowed =
      RegExp(r"[^A-Za-z\u0C00-\u0C7F .'\-]");

  /// Trim, collapse whitespace, strip control chars, cap length.
  static String sanitizeText(String? value, {int maxLen = 200}) {
    if (value == null) return '';
    var s = value.replaceAll(_controlRe, '').trim();
    s = s.replaceAll(RegExp(r'\s+'), ' ');
    return s.length > maxLen ? s.substring(0, maxLen) : s;
  }

  /// Sanitize a person/place name (allowed chars only).
  static String sanitizeName(String? value, {int maxLen = 100}) {
    return sanitizeText(value, maxLen: maxLen).replaceAll(_nameDisallowed, '').trim();
  }

  /// Digits only from a phone string.
  static String _digits(String v) => v.replaceAll(RegExp(r'[^\d]'), '');

  /// Normalise an Indian mobile to +91XXXXXXXXXX when possible.
  static String normalizePhone(String? value) {
    if (value == null || value.isEmpty) return '';
    var d = _digits(value);
    if (d.length == 12 && d.startsWith('91')) d = d.substring(2);
    if (d.length == 11 && d.startsWith('0')) d = d.substring(1);
    if (d.length == 10 && '6789'.contains(d[0])) return '+91$d';
    return d.isEmpty ? '' : '+$d';
  }

  // ── Form validators (return null when valid) ──────────────────────────────

  static String? name(String? value) {
    final s = sanitizeName(value);
    if (s.isEmpty) return 'Name is required';
    if (s.length < 2) return 'Enter a valid name';
    return null;
  }

  static String? email(String? value) {
    final s = (value ?? '').trim();
    if (s.isEmpty) return 'Email is required';
    if (!_emailRe.hasMatch(s)) return 'Enter a valid email address';
    return null;
  }

  static String? phone(String? value) {
    if (value == null || value.trim().isEmpty) return 'Phone number is required';
    var d = _digits(value);
    if (d.length == 12 && d.startsWith('91')) d = d.substring(2);
    if (d.length == 11 && d.startsWith('0')) d = d.substring(1);
    if (d.length != 10 || !'6789'.contains(d[0])) {
      return 'Enter a valid 10-digit mobile number';
    }
    return null;
  }

  static String? rooms(String? value) {
    if (value == null || value.trim().isEmpty) return 'Required';
    final n = int.tryParse(value.trim());
    if (n == null || n < 1) return 'Must be at least 1';
    if (n > 100) return 'Must be at most 100';
    return null;
  }

  /// Validate a stay date range. Returns an error string or null.
  static String? stay(DateTime? checkIn, DateTime? checkOut) {
    if (checkIn == null || checkOut == null) {
      return 'Select check-in and check-out dates';
    }
    if (!checkOut.isAfter(checkIn)) return 'Check-out must be after check-in';
    final today = DateTime.now();
    final ci = DateTime(checkIn.year, checkIn.month, checkIn.day);
    final t0 = DateTime(today.year, today.month, today.day);
    if (ci.isBefore(t0)) return 'Check-in cannot be in the past';
    if (checkOut.difference(checkIn).inDays > 60) {
      return 'Stay cannot exceed 60 nights';
    }
    return null;
  }
}
