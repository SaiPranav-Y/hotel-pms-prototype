import 'package:flutter/material.dart';

import '../models/reservation.dart';
import '../services/firestore_service.dart';
import '../widgets/add_walk_in_guest_modal.dart';

/// Displays reservations with real-time updates from Firestore.
class ReservationsView extends StatefulWidget {
  const ReservationsView({super.key});

  @override
  State<ReservationsView> createState() => _ReservationsViewState();
}

class _ReservationsViewState extends State<ReservationsView> {
  final FirestoreService _firestoreService = FirestoreService();
  final TextEditingController _searchController = TextEditingController();
  late Stream<List<Reservation>> _stream;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _stream = _firestoreService.getReservationsStream();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _retry() {
    setState(() {
      _stream = _firestoreService.getReservationsStream();
    });
  }

  bool _matchesSearch(Reservation r, String query) {
    final q = query.toLowerCase();
    return r.customerName.toLowerCase().contains(q) ||
        r.customerPhone.toLowerCase().contains(q) ||
        r.templeName.toLowerCase().contains(q) ||
        r.displayRoomType.toLowerCase().contains(q) ||
        r.reservationStatus.toLowerCase().contains(q);
  }

  void _openEditDialog(Reservation reservation) {
    showDialog(
      context: context,
      builder: (context) => ReservationDialog(
        mode: ReservationDialogMode.edit,
        existingReservation: reservation,
      ),
    );
  }

  void _openDeleteDialog(Reservation reservation) {
    showDialog(
      context: context,
      builder: (context) => _DeleteConfirmationDialog(reservation: reservation),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          showDialog(
            context: context,
            builder: (context) => const ReservationDialog(
              mode: ReservationDialogMode.add,
            ),
          );
        },
        icon: const Icon(Icons.person_add_rounded),
        label: const Text(
          'Add Walk-In Guest',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Reservations',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Manage guest bookings in real time',
              style: TextStyle(fontSize: 15, color: Colors.grey.shade500),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _searchController,
              maxLength: 100,
              decoration: InputDecoration(
                hintText:
                    'Search by name, phone, temple, room type, or status...',
                hintStyle: TextStyle(color: Colors.grey.shade400),
                prefixIcon:
                    Icon(Icons.search_rounded, color: Colors.grey.shade400),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: Icon(Icons.close_rounded,
                            color: Colors.grey.shade500),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                counterText: '',
              ),
              onChanged: (v) => setState(() => _searchQuery = v),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: StreamBuilder<List<Reservation>>(
                stream: _stream,
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.error_outline_rounded,
                              size: 56, color: Colors.red.shade300),
                          const SizedBox(height: 16),
                          Text('Failed to load reservations',
                              style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.grey.shade700)),
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

                  if (!snapshot.hasData) {
                    return const Center(child: CircularProgressIndicator());
                  }

                  final reservations = snapshot.data!;
                  if (reservations.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.calendar_today_rounded,
                              size: 56, color: Colors.grey.shade300),
                          const SizedBox(height: 16),
                          Text('No reservations currently exist.',
                              style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                  color: Colors.grey.shade600)),
                        ],
                      ),
                    );
                  }

                  final filtered = _searchQuery.isEmpty
                      ? reservations
                      : reservations
                          .where((r) => _matchesSearch(r, _searchQuery))
                          .toList();

                  if (filtered.isEmpty && _searchQuery.isNotEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.search_off_rounded,
                              size: 56, color: Colors.grey.shade300),
                          const SizedBox(height: 16),
                          Text('No reservations match the search query.',
                              style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                  color: Colors.grey.shade600)),
                        ],
                      ),
                    );
                  }

                  return ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (context, index) {
                      return _ReservationCard(
                        reservation: filtered[index],
                        onEdit: () => _openEditDialog(filtered[index]),
                        onDelete: () => _openDeleteDialog(filtered[index]),
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
}

// ─── Reservation Card ────────────────────────────────────────────────────────

class _ReservationCard extends StatefulWidget {
  final Reservation reservation;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  const _ReservationCard({
    required this.reservation,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  State<_ReservationCard> createState() => _ReservationCardState();
}

class _ReservationCardState extends State<_ReservationCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final r = widget.reservation;
    final checkInStr = _fmtDate(r.checkIn);
    final checkOutStr = _fmtDate(r.checkOut);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: MouseRegion(
        onEnter: (_) => setState(() => _isHovered = true),
        onExit: (_) => setState(() => _isHovered = false),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: _isHovered ? 0.08 : 0.04),
                blurRadius: _isHovered ? 12 : 6,
                offset: Offset(0, _isHovered ? 4 : 2),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Row 1: Avatar + Name, Edit/Delete icons top-right
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: const Color(0xFF4F46E5).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.person_rounded,
                          color: Color(0xFF4F46E5), size: 22),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(r.customerName,
                              style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF1E293B))),
                          if (r.customerAge > 0) ...[
                            const SizedBox(height: 2),
                            Text('Age: ${r.customerAge}',
                                style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.grey.shade500)),
                          ],
                        ],
                      ),
                    ),
                    // Edit/Delete in top-right corner
                    IconButton(
                      onPressed: widget.onEdit,
                      icon: const Icon(Icons.edit_rounded, size: 18),
                      color: const Color(0xFF4F46E5),
                      tooltip: 'Edit',
                      visualDensity: VisualDensity.compact,
                      constraints:
                          const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                    IconButton(
                      onPressed: widget.onDelete,
                      icon: const Icon(Icons.delete_rounded, size: 18),
                      color: Colors.red.shade400,
                      tooltip: 'Delete',
                      visualDensity: VisualDensity.compact,
                      constraints:
                          const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Row 2: Status chip (redesigned, prominent)
                _StatusChip(status: r.reservationStatus),
                const SizedBox(height: 14),

                // Row 3: Info chips
                Wrap(
                  spacing: 12,
                  runSpacing: 8,
                  children: [
                    _IconLabel(
                        icon: Icons.phone_rounded, label: r.customerPhone),
                    if (r.templeName.isNotEmpty)
                      _IconLabel(
                          icon: Icons.temple_buddhist_rounded,
                          label: r.templeName),
                    _IconLabel(
                        icon: Icons.bed_rounded, label: r.displayRoomType),
                    _IconLabel(
                        icon: Icons.meeting_room_rounded,
                        label:
                            '${r.noOfRooms} room${r.noOfRooms > 1 ? 's' : ''}'),
                  ],
                ),
                const SizedBox(height: 12),

                // Row 4: Dates + Mode chip
                Row(
                  children: [
                    _DateChip(
                        icon: Icons.login_rounded,
                        label: 'In: $checkInStr',
                        color: const Color(0xFF10B981)),
                    const SizedBox(width: 10),
                    _DateChip(
                        icon: Icons.logout_rounded,
                        label: 'Out: $checkOutStr',
                        color: Colors.orange.shade600),
                    const Spacer(),
                    _ModeChip(mode: r.reservationMode),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _fmtDate(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
}

// ─── Status Chip (Redesigned) ────────────────────────────────────────────────

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final color = _colorFor(status);
    final icon = _iconFor(status);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            status,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Color _colorFor(String s) {
    switch (s) {
      case 'Waiting for Approval':
        return Colors.orange.shade700;
      case 'Approved - Pending Payment':
        return Colors.blue.shade700;
      case 'Approved & Paid':
      case 'Approved - Paid':
        return const Color(0xFF059669);
      case 'Cancelled':
        return Colors.red.shade600;
      default:
        return Colors.grey.shade600;
    }
  }

  IconData _iconFor(String s) {
    switch (s) {
      case 'Waiting for Approval':
        return Icons.hourglass_top_rounded;
      case 'Approved - Pending Payment':
        return Icons.payment_rounded;
      case 'Approved & Paid':
      case 'Approved - Paid':
        return Icons.check_circle_rounded;
      case 'Cancelled':
        return Icons.cancel_rounded;
      default:
        return Icons.circle;
    }
  }
}

// ─── Mode Chip ───────────────────────────────────────────────────────────────

class _ModeChip extends StatelessWidget {
  final String mode;
  const _ModeChip({required this.mode});

  @override
  Widget build(BuildContext context) {
    final icon = _iconFor(mode);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F7FA),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: Colors.grey.shade600),
          const SizedBox(width: 4),
          Text(mode,
              style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: Colors.grey.shade600)),
        ],
      ),
    );
  }

  IconData _iconFor(String m) {
    switch (m) {
      case 'WhatsApp Booking':
        return Icons.chat_rounded;
      case 'Voice Assistant':
        return Icons.call_rounded;
      case 'Walk-In':
        return Icons.person_rounded;
      default:
        return Icons.help_outline_rounded;
    }
  }
}

// ─── Shared Small Widgets ────────────────────────────────────────────────────

class _IconLabel extends StatelessWidget {
  final IconData icon;
  final String label;
  const _IconLabel({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: Colors.grey.shade400),
        const SizedBox(width: 4),
        Text(label,
            style: TextStyle(fontSize: 13, color: Colors.grey.shade600)),
      ],
    );
  }
}

class _DateChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _DateChip(
      {required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 4),
          Text(label,
              style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w500, color: color)),
        ],
      ),
    );
  }
}

// ─── Delete Confirmation Dialog ──────────────────────────────────────────────

class _DeleteConfirmationDialog extends StatefulWidget {
  final Reservation reservation;
  const _DeleteConfirmationDialog({required this.reservation});

  @override
  State<_DeleteConfirmationDialog> createState() =>
      _DeleteConfirmationDialogState();
}

class _DeleteConfirmationDialogState extends State<_DeleteConfirmationDialog> {
  final FirestoreService _firestoreService = FirestoreService();
  bool _isDeleting = false;

  Future<void> _delete() async {
    setState(() => _isDeleting = true);
    try {
      await _firestoreService.deleteReservation(widget.reservation.id);
      if (mounted) Navigator.pop(context);
    } catch (_) {
      if (mounted) {
        setState(() => _isDeleting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to delete reservation')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.reservation;
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 400),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(Icons.delete_rounded,
                        color: Colors.red.shade500, size: 22),
                  ),
                  const SizedBox(width: 14),
                  const Text(
                    'Delete Reservation?',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Customer: ${r.customerName}',
                style: const TextStyle(fontSize: 14, color: Color(0xFF1E293B)),
              ),
              const SizedBox(height: 4),
              Text(
                'Temple: ${r.templeName}',
                style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
              ),
              const SizedBox(height: 16),
              Text(
                'This action cannot be undone.',
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.red.shade400,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed:
                        _isDeleting ? null : () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 12),
                  FilledButton.icon(
                    onPressed: _isDeleting ? null : _delete,
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.red.shade500,
                    ),
                    icon: _isDeleting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.delete_rounded, size: 18),
                    label: const Text('Delete'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
