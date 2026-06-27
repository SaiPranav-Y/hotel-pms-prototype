import 'package:flutter/material.dart';

import '../models/temple.dart';
import '../services/firestore_service.dart';
import '../widgets/update_inventory_dialog.dart';

/// Displays temples with capacity information in responsive cards.
///
/// All availability values come directly from the temples collection.
/// No reservation data is used for inventory calculations.
class InventoryView extends StatefulWidget {
  const InventoryView({super.key});

  @override
  State<InventoryView> createState() => _InventoryViewState();
}

class _InventoryViewState extends State<InventoryView> {
  final FirestoreService _firestoreService = FirestoreService();
  late Stream<List<Temple>> _templesStream;

  @override
  void initState() {
    super.initState();
    _templesStream = _firestoreService.getTemplesStream();
  }

  void _retry() {
    setState(() {
      _templesStream = _firestoreService.getTemplesStream();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Page header
            const Text(
              'Inventory',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Manage temple room capacity and availability',
              style: TextStyle(
                fontSize: 15,
                color: Colors.grey.shade500,
              ),
            ),
            const SizedBox(height: 28),

            // Temple cards
            Expanded(
              child: StreamBuilder<List<Temple>>(
                stream: _templesStream,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }

                  if (snapshot.hasError) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.error_outline_rounded,
                            size: 56,
                            color: Colors.red.shade300,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Failed to load inventory data.',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: Colors.grey.shade700,
                            ),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: _retry,
                            icon: const Icon(Icons.refresh_rounded, size: 18),
                            label: const Text('Retry'),
                          ),
                        ],
                      ),
                    );
                  }

                  final temples = snapshot.data ?? [];

                  if (temples.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.inventory_2_rounded,
                            size: 56,
                            color: Colors.grey.shade300,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'No properties available',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ],
                      ),
                    );
                  }

                  return LayoutBuilder(
                    builder: (context, constraints) {
                      return SingleChildScrollView(
                        child: Wrap(
                          spacing: 20,
                          runSpacing: 20,
                          children: temples.map((temple) {
                            return _InventoryCard(
                              temple: temple,
                              width: _cardWidth(constraints.maxWidth),
                            );
                          }).toList(),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  double _cardWidth(double maxWidth) {
    const spacing = 20.0;
    if (maxWidth < 600) return maxWidth;
    if (maxWidth < 900) return (maxWidth - spacing) / 2;
    return (maxWidth - spacing * 2) / 3;
  }
}

class _InventoryCard extends StatefulWidget {
  final Temple temple;
  final double width;

  const _InventoryCard({required this.temple, required this.width});

  @override
  State<_InventoryCard> createState() => _InventoryCardState();
}

class _InventoryCardState extends State<_InventoryCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final temple = widget.temple;
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

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: widget.width,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: _isHovered ? 0.08 : 0.04),
              blurRadius: _isHovered ? 16 : 8,
              offset: Offset(0, _isHovered ? 6 : 2),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF4F46E5).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.temple_buddhist_rounded,
                      color: Color(0xFF4F46E5),
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      temple.templeName,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Stats from temple document
              _StatRow(
                label: 'Total Capacity',
                value: '${temple.totalCapacity}',
              ),
              const SizedBox(height: 10),
              _StatRow(
                label: 'Available Rooms',
                value: '${temple.availableRooms}',
                valueColor: const Color(0xFF10B981),
              ),
              const SizedBox(height: 10),
              _StatRow(
                label: 'Maintenance Rooms',
                value: '${temple.maintenanceRooms}',
                valueColor: const Color(0xFF6366F1),
              ),
              const SizedBox(height: 10),
              _StatRow(
                label: 'Occupied Rooms',
                value: '${temple.occupiedRooms}',
                valueColor: Colors.orange.shade600,
              ),
              const SizedBox(height: 18),

              // Occupancy progress
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
              const SizedBox(height: 20),

              // Update button
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (context) =>
                          UpdateInventoryDialog(temple: temple),
                    );
                  },
                  icon: const Icon(Icons.edit_rounded, size: 16),
                  label: const Text('Update Inventory'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF4F46E5),
                    side: const BorderSide(color: Color(0xFF4F46E5)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _StatRow({
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
