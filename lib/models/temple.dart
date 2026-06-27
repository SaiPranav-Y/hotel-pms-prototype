class Temple {
  final String id;
  final String templeName;
  final int totalCapacity;
  final int availableRooms;
  final int maintenanceRooms;

  const Temple({
    required this.id,
    required this.templeName,
    required this.totalCapacity,
    required this.availableRooms,
    required this.maintenanceRooms,
  });

  /// Occupied = total_capacity - available_rooms - maintenance_rooms
  int get occupiedRooms =>
      (totalCapacity - availableRooms - maintenanceRooms).clamp(0, totalCapacity);

  /// Occupancy percentage based on occupied rooms
  double get occupancyFraction =>
      totalCapacity > 0 ? occupiedRooms / totalCapacity : 0.0;

  int get occupancyPercent => (occupancyFraction * 100).round();

  factory Temple.fromMap(String id, Map<String, dynamic> map) {
    return Temple(
      id: id,
      templeName: map['temple_name'] as String,
      totalCapacity: map['total_capacity'] as int,
      availableRooms: map['available_rooms'] as int,
      maintenanceRooms: (map['maintenance_rooms'] as int?) ?? 0,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'temple_name': templeName,
      'total_capacity': totalCapacity,
      'available_rooms': availableRooms,
      'maintenance_rooms': maintenanceRooms,
    };
  }
}
