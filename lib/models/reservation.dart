/// Represents a guest reservation with check-in/check-out dates and room count.
class Reservation {
  final String id;
  final String customerName;
  final String customerPhone;
  final int customerAge;
  final String templeName;
  final String roomType;
  final DateTime checkIn;
  final DateTime checkOut;
  final int noOfRooms;
  final String reservationStatus;
  final String reservationMode;
  final DateTime createdAt;

  const Reservation({
    required this.id,
    required this.customerName,
    required this.customerPhone,
    required this.customerAge,
    required this.templeName,
    required this.roomType,
    required this.checkIn,
    required this.checkOut,
    required this.noOfRooms,
    required this.reservationStatus,
    required this.reservationMode,
    required this.createdAt,
  });

  /// Display-friendly room type; defaults to "Standard Room" if empty.
  String get displayRoomType =>
      roomType.isEmpty ? 'Standard Room' : roomType;

  factory Reservation.fromMap(String id, Map<String, dynamic> map) {
    return Reservation(
      id: id,
      customerName: map['customer_name'] as String,
      customerPhone: _parsePhone(map['customer_phone'] ?? map['phone_number']),
      customerAge: _parseInt(map['customer_age']),
      templeName: (map['temple_name'] as String?) ?? '',
      roomType: (map['room_type'] as String?) ?? '',
      checkIn: _parseDate(map['check_in'] ?? map['from_date']),
      checkOut: _parseDate(map['check_out'] ?? map['to_date']),
      noOfRooms: _parseRooms(map['no_of_rooms'], map['number_of_rooms']),
      reservationStatus:
          (map['reservation_status'] as String?) ?? 'Waiting for Approval',
      reservationMode:
          (map['reservation_mode'] as String?) ?? 'Walk-In',
      createdAt: _parseDate(map['created_at']),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'customer_name': customerName,
      'customer_phone': customerPhone,
      'customer_age': customerAge,
      'temple_name': templeName,
      'room_type': roomType,
      'check_in': checkIn.toIso8601String(),
      'check_out': checkOut.toIso8601String(),
      'no_of_rooms': noOfRooms,
      'reservation_status': reservationStatus,
      'reservation_mode': reservationMode,
      'created_at': createdAt.toIso8601String(),
    };
  }

  /// Returns true if this reservation overlaps with the given date range.
  bool overlaps(DateTime rangeStart, DateTime rangeEnd) {
    return checkIn.isBefore(rangeEnd) && rangeStart.isBefore(checkOut);
  }

  static DateTime _parseDate(dynamic field) {
    if (field == null) return DateTime.now();
    if (field is DateTime) return field;
    if (field is String) {
      final iso = DateTime.tryParse(field);
      if (iso != null) return iso;

      final parts = field.split('/');
      if (parts.length == 3) {
        final day = int.tryParse(parts[0]);
        final month = int.tryParse(parts[1]);
        final year = int.tryParse(parts[2]);
        if (day != null && month != null && year != null) {
          return DateTime(year, month, day);
        }
      }

      if (parts.length == 3) {
        final month = int.tryParse(parts[0]);
        final day = int.tryParse(parts[1]);
        final year = int.tryParse(parts[2]);
        if (day != null && month != null && year != null &&
            day <= 31 && month <= 12) {
          return DateTime(year, month, day);
        }
      }

      return DateTime.now();
    }
    try {
      return (field as dynamic).toDate() as DateTime;
    } catch (_) {
      return DateTime.now();
    }
  }

  static int _parseInt(dynamic field) {
    if (field == null) return 0;
    if (field is int) return field;
    if (field is double) return field.toInt();
    if (field is String) return int.tryParse(field) ?? 0;
    return 0;
  }

  static String _parsePhone(dynamic field) {
    if (field == null) return '';
    if (field is String) return field;
    if (field is int) return field.toString();
    if (field is double) return field.toInt().toString();
    return field.toString();
  }

  static int _parseRooms(dynamic noOfRooms, dynamic numberOfRooms) {
    final primary = _parseInt(noOfRooms);
    if (primary > 0) return primary;
    final fallback = _parseInt(numberOfRooms);
    if (fallback > 0) return fallback;
    return 1;
  }
}
