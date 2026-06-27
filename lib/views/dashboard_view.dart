import 'package:flutter/material.dart';

import '../models/reservation.dart';
import '../models/temple.dart';
import '../services/firestore_service.dart';

/// Dashboard home page displaying KPI cards and temple inventory overview.
///
/// All availability values are computed dynamically from the reservations
/// stream — no hardcoded values.
class DashboardView extends StatefulWidget {
  const DashboardView({super.key});

  @override
  State<DashboardView> createState() => _DashboardViewState();
}

class _DashboardViewState extends State<DashboardView> {
  final FirestoreService _firestoreService = FirestoreService();
  late Stream<List<Temple>> _templesStream;
  late Stream<List<Reservation>> _reservationsStream;

  @override
  void initState() {
    super.initState();
    _templesStream = _firestoreService.getTemplesStream();
    _reservationsStream = _firestoreService.getReservationsStream();
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<List<Temple>>(
      stream: _templesStream,
      builder: (context, templesSnapshot) {
        return StreamBuilder<List<Reservation>>(
          stream: _reservationsStream,
          builder: (context, reservationsSnapshot) {
            final temples = templesSnapshot.data ?? [];
            final reservations = reservationsSnapshot.data ?? [];

            // KPI 1: Total Rooms = Sum(total_capacity) from temples
            final totalRooms = temples.fold<int>(
              0,
              (sum, t) => sum + t.totalCapacity,
            );

            // KPI 2: Available Rooms = Sum(available_rooms) from temples
            final availableRooms = temples.fold<int>(
              0,
              (sum, t) => sum + t.availableRooms,
            );

            // Date references for computations
            final now = DateTime.now();

            // KPI 3: Today's Reservations = reservations created today
            final todayReservations = reservations.where((r) {
              return r.createdAt.year == now.year &&
                  r.createdAt.month == now.month &&
                  r.createdAt.day == now.day;
            }).length;

            // KPI 4: Total Reservations = total count of loaded reservations
            final totalReservations = reservations.length;

            // Booking Source Analytics
            final whatsappBookings = reservations
                .where((r) => r.reservationMode == 'WhatsApp Booking')
                .length;
            final voiceBookings = reservations
                .where((r) => r.reservationMode == 'Voice Assistant')
                .length;
            final walkInBookings = reservations
                .where((r) => r.reservationMode == 'Walk-In')
                .length;
            final digitalBookings = whatsappBookings + voiceBookings;

            return SingleChildScrollView(
              padding: const EdgeInsets.all(32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Page title
                  const Text(
                    'Dashboard',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Overview of your property management',
                    style: TextStyle(
                      fontSize: 15,
                      color: Colors.grey.shade500,
                    ),
                  ),
                  const SizedBox(height: 32),

                  // KPI Cards
                  LayoutBuilder(
                    builder: (context, constraints) {
                      return Wrap(
                        spacing: 20,
                        runSpacing: 20,
                        children: [
                          _KpiCard(
                            icon: Icons.hotel_rounded,
                            iconColor: const Color(0xFF4F46E5),
                            iconBgColor: const Color(0xFF4F46E5)
                                .withValues(alpha: 0.1),
                            title: 'Total Rooms',
                            value: totalRooms.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                          _KpiCard(
                            icon: Icons.check_circle_rounded,
                            iconColor: const Color(0xFF10B981),
                            iconBgColor: const Color(0xFF10B981)
                                .withValues(alpha: 0.1),
                            title: 'Available Rooms',
                            value: availableRooms.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                          _KpiCard(
                            icon: Icons.calendar_today_rounded,
                            iconColor: const Color(0xFFF59E0B),
                            iconBgColor: const Color(0xFFF59E0B)
                                .withValues(alpha: 0.1),
                            title: "Today's Reservations",
                            value: todayReservations.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                          _KpiCard(
                            icon: Icons.book_rounded,
                            iconColor: const Color(0xFF8B5CF6),
                            iconBgColor: const Color(0xFF8B5CF6)
                                .withValues(alpha: 0.1),
                            title: 'Total Reservations',
                            value: totalReservations.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                        ],
                      );
                    },
                  ),

                  const SizedBox(height: 40),

                  // Booking Sources section
                  const Text(
                    'Booking Sources',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Reservations grouped by booking channel',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade500,
                    ),
                  ),
                  const SizedBox(height: 20),

                  LayoutBuilder(
                    builder: (context, constraints) {
                      return Wrap(
                        spacing: 20,
                        runSpacing: 20,
                        children: [
                          _KpiCard(
                            icon: Icons.chat_rounded,
                            iconColor: const Color(0xFF10B981),
                            iconBgColor: const Color(0xFF10B981)
                                .withValues(alpha: 0.1),
                            title: 'WhatsApp Booking',
                            value: whatsappBookings.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                          _KpiCard(
                            icon: Icons.call_rounded,
                            iconColor: Colors.blue.shade600,
                            iconBgColor: Colors.blue.shade600
                                .withValues(alpha: 0.1),
                            title: 'Voice Assistant',
                            value: voiceBookings.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                          _KpiCard(
                            icon: Icons.person_rounded,
                            iconColor: const Color(0xFF8B5CF6),
                            iconBgColor: const Color(0xFF8B5CF6)
                                .withValues(alpha: 0.1),
                            title: 'Walk-In',
                            value: walkInBookings.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                          _KpiCard(
                            icon: Icons.devices_rounded,
                            iconColor: const Color(0xFF4F46E5),
                            iconBgColor: const Color(0xFF4F46E5)
                                .withValues(alpha: 0.1),
                            title: 'Total Digital Bookings',
                            value: digitalBookings.toString(),
                            width: _cardWidth(constraints.maxWidth, 4),
                          ),
                        ],
                      );
                    },
                  ),

                  const SizedBox(height: 40),

                  // Temple inventory section
                  const Text(
                    'Temple Inventory',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Room availability across properties',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade500,
                    ),
                  ),
                  const SizedBox(height: 20),

                  if (temples.isEmpty)
                    const Center(child: Text('No properties available.'))
                  else
                    LayoutBuilder(
                      builder: (context, constraints) {
                        return Wrap(
                          spacing: 20,
                          runSpacing: 20,
                          children: temples.map((temple) {
                            return _TempleCard(
                              temple: temple,
                              width: _cardWidth(constraints.maxWidth, 3),
                            );
                          }).toList(),
                        );
                      },
                    ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  double _cardWidth(double maxWidth, int columns) {
    const spacing = 20.0;
    if (maxWidth < 600) return maxWidth;
    if (maxWidth < 900) {
      return (maxWidth - spacing) / 2;
    }
    if (maxWidth < 1200 && columns > 3) {
      return (maxWidth - spacing * 1) / 2;
    }
    return (maxWidth - spacing * (columns - 1)) / columns;
  }
}

class _KpiCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final Color iconBgColor;
  final String title;
  final String value;
  final double width;

  const _KpiCard({
    required this.icon,
    required this.iconColor,
    required this.iconBgColor,
    required this.title,
    required this.value,
    required this.width,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: Card(
        elevation: 2,
        shadowColor: Colors.black.withValues(alpha: 0.06),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: iconBgColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: iconColor, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey.shade600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      value,
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TempleCard extends StatelessWidget {
  final Temple temple;
  final double width;

  const _TempleCard({
    required this.temple,
    required this.width,
  });

  @override
  Widget build(BuildContext context) {
    final occupancyPercent = temple.occupancyPercent;
    final occupancy = temple.occupancyFraction;

    Color progressColor;
    if (occupancyPercent >= 80) {
      progressColor = Colors.red.shade400;
    } else if (occupancyPercent >= 50) {
      progressColor = Colors.orange.shade400;
    } else {
      progressColor = const Color(0xFF10B981);
    }

    return SizedBox(
      width: width,
      child: Card(
        elevation: 2,
        shadowColor: Colors.black.withValues(alpha: 0.06),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF4F46E5).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.temple_buddhist_rounded,
                      color: Color(0xFF4F46E5),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      temple.templeName,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              _InfoRow(
                label: 'Total Capacity',
                value: '${temple.totalCapacity}',
              ),
              const SizedBox(height: 8),
              _InfoRow(
                label: 'Available Rooms',
                value: '${temple.availableRooms}',
                valueColor: const Color(0xFF10B981),
              ),
              const SizedBox(height: 8),
              _InfoRow(
                label: 'Maintenance Rooms',
                value: '${temple.maintenanceRooms}',
                valueColor: const Color(0xFF6366F1),
              ),
              const SizedBox(height: 8),
              _InfoRow(
                label: 'Occupied Rooms',
                value: '${temple.occupiedRooms}',
                valueColor: Colors.orange.shade600,
              ),
              const SizedBox(height: 16),
              Text(
                '$occupancyPercent% Occupied',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: progressColor,
                ),
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: occupancy,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation<Color>(progressColor),
                  minHeight: 6,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 13,
            color: Colors.grey.shade600,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: valueColor ?? const Color(0xFF1E293B),
          ),
        ),
      ],
    );
  }
}
