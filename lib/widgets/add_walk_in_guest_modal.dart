import 'package:flutter/material.dart';

import '../constants/karivena_data.dart';
import '../models/reservation.dart';
import '../models/temple.dart';
import '../services/firestore_service.dart';
import '../utils/validators.dart';

/// Dialog mode — determines Add vs Edit behaviour.
enum ReservationDialogMode { add, edit }

/// Reusable dialog for creating and editing reservations.
///
/// In [ReservationDialogMode.add] mode, creates a new document.
/// In [ReservationDialogMode.edit] mode, updates the existing document.
class ReservationDialog extends StatefulWidget {
  final ReservationDialogMode mode;
  final Reservation? existingReservation;

  const ReservationDialog({
    super.key,
    this.mode = ReservationDialogMode.add,
    this.existingReservation,
  });

  @override
  State<ReservationDialog> createState() => _ReservationDialogState();
}

/// Keep the old class name as an alias for backward-compatible usage.
typedef AddWalkInGuestModal = ReservationDialog;

class _ReservationDialogState extends State<ReservationDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _phoneController;
  late final TextEditingController _ageController;
  late final TextEditingController _roomsController;
  late final TextEditingController _gotramController;
  final FocusNode _gotramFocus = FocusNode();
  final FirestoreService _firestoreService = FirestoreService();

  bool _isSubmitting = false;
  bool _isLoadingTemples = true;
  String? _errorMessage;

  DateTime? _checkIn;
  DateTime? _checkOut;
  String? _selectedTempleName;
  String _selectedRoomType = 'AC';
  String _selectedPaymentMethod = 'cash';
  String _selectedStatus = 'Waiting for Approval';
  late final String _reservationMode;
  List<Temple> _temples = [];

  /// Live-computed total for the current selection (nights x rooms x rate).
  int get _computedTotal {
    if (_checkIn == null || _checkOut == null || _selectedTempleName == null) {
      return 0;
    }
    final rooms = int.tryParse(_roomsController.text.trim()) ?? 1;
    return computeStayTotal(
      location: _selectedTempleName!,
      roomType: _selectedRoomType,
      checkIn: _checkIn!,
      checkOut: _checkOut!,
      rooms: rooms,
    );
  }

  int get _nightlyRate =>
      _selectedTempleName == null ? 0 : rateFor(_selectedTempleName!, _selectedRoomType);

  static const _statusOptions = [
    'Waiting for Approval',
    'Approved - Pending Payment',
    'Approved - Paid',
    'Cancelled',
  ];

  bool get _isEditMode => widget.mode == ReservationDialogMode.edit;

  @override
  void initState() {
    super.initState();
    final r = widget.existingReservation;

    _nameController = TextEditingController(text: r?.customerName ?? '');
    _phoneController = TextEditingController(text: r?.customerPhone ?? '');
    _ageController =
        TextEditingController(text: r != null && r.customerAge > 0 ? '${r.customerAge}' : '');
    _roomsController =
        TextEditingController(text: r != null ? '${r.noOfRooms}' : '1');
    _gotramController = TextEditingController(text: r?.gotram ?? '');

    if (r != null) {
      _checkIn = r.checkIn;
      _checkOut = r.checkOut;
      _selectedTempleName = r.templeName.isNotEmpty ? r.templeName : null;
      // Map stored room type onto AC / Non-AC
      _selectedRoomType =
          r.roomType.toLowerCase().contains('non') ? 'Non-AC' : 'AC';
      if (r.paymentMethod.isNotEmpty) _selectedPaymentMethod = r.paymentMethod;
      _selectedStatus = r.reservationStatus;
      _reservationMode = r.reservationMode;
    } else {
      final now = DateTime.now();
      _checkIn = DateTime(now.year, now.month, now.day);
      _checkOut = DateTime(now.year, now.month, now.day + 1);
      _selectedStatus = 'Waiting for Approval';
      _reservationMode = 'Walk-In';
    }

    _loadTemples();
  }

  Future<void> _loadTemples() async {
    try {
      final temples = await _firestoreService.getTemplesStream().first;
      if (mounted) {
        setState(() {
          _temples = temples;
          _isLoadingTemples = false;
          if (_selectedTempleName == null && temples.isNotEmpty) {
            _selectedTempleName = temples.first.templeName;
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoadingTemples = false);
      }
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _ageController.dispose();
    _roomsController.dispose();
    _gotramController.dispose();
    _gotramFocus.dispose();
    super.dispose();
  }

  String? _validateName(String? value) => Validators.name(value);

  String? _validatePhone(String? value) => Validators.phone(value);

  String? _validateRooms(String? value) => Validators.rooms(value);

  String? _validateGotram(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Gotram is required (community eligibility)';
    }
    if (matchGotram(value) == null) {
      return 'Not in the approved gotram list';
    }
    return null;
  }

  Future<void> _pickDate({required bool isCheckIn}) async {
    final now = DateTime.now();
    final initial = isCheckIn
        ? (_checkIn ?? now)
        : (_checkOut ?? now.add(const Duration(days: 1)));

    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 2),
    );

    if (picked != null) {
      setState(() {
        if (isCheckIn) {
          _checkIn = picked;
          if (_checkOut != null && !_checkOut!.isAfter(picked)) {
            _checkOut = picked.add(const Duration(days: 1));
          }
        } else {
          _checkOut = picked;
        }
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    if (_checkIn == null || _checkOut == null) {
      setState(() => _errorMessage = 'Please select check-in and check-out dates.');
      return;
    }
    if (!_checkOut!.isAfter(_checkIn!)) {
      setState(() => _errorMessage = 'Check-out must be after check-in.');
      return;
    }
    if (_selectedTempleName == null || _selectedTempleName!.isEmpty) {
      setState(() => _errorMessage = 'Please select a temple.');
      return;
    }

    // Extra guard on the stay range (defence in depth beyond field validators).
    final stayErr = Validators.stay(_checkIn, _checkOut);
    if (stayErr != null) {
      setState(() => _errorMessage = stayErr);
      return;
    }

    final noOfRooms = int.parse(_roomsController.text.trim());
    final age = int.tryParse(_ageController.text.trim()) ?? 0;
    // Sanitize + normalise inputs before persisting.
    final cleanName = Validators.sanitizeName(_nameController.text);
    final cleanPhone = Validators.normalizePhone(_phoneController.text);
    // Normalise gotram to its canonical approved name
    final canonicalGotram = matchGotram(_gotramController.text) ?? _gotramController.text.trim();

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final reservation = Reservation(
        id: widget.existingReservation?.id ?? '',
        customerName: cleanName,
        customerPhone: cleanPhone,
        customerAge: age,
        gotram: canonicalGotram,
        templeName: _selectedTempleName!,
        roomType: _selectedRoomType,
        checkIn: _checkIn!,
        checkOut: _checkOut!,
        noOfRooms: noOfRooms,
        totalPrice: _computedTotal,
        paymentMethod: _selectedPaymentMethod,
        paymentStatus: widget.existingReservation?.paymentStatus ?? 'pending',
        reservationStatus: _selectedStatus,
        reservationMode: _reservationMode,
        createdAt: widget.existingReservation?.createdAt ?? DateTime.now(),
      );

      if (_isEditMode) {
        await _firestoreService.updateReservation(reservation.id, reservation);
      } else {
        // Concurrency-safe create: atomically verifies availability + books,
        // preventing double-booking of the last room across all channels.
        final capacity = _capacityForSelectedTemple();
        await _firestoreService.createReservationAudited(
          reservation,
          templeCapacity: capacity,
          source: 'walk_in',
        );
      }

      if (mounted) Navigator.pop(context);
    } on RoomUnavailableException catch (e) {
      setState(() => _errorMessage = e.message);
    } on FirestoreServiceException catch (e) {
      setState(() => _errorMessage = e.message);
    } catch (e) {
      setState(() =>
          _errorMessage = 'Could not save. Check your connection and try again.');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  /// Total room capacity for the currently selected temple (0 if unknown).
  int _capacityForSelectedTemple() {
    for (final t in _temples) {
      if (t.templeName == _selectedTempleName) return t.totalCapacity;
    }
    return 0;
  }

  String _formatDate(DateTime? date) {
    if (date == null) return 'Select date';
    return '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 500),
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
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
                      child: Icon(
                        _isEditMode ? Icons.edit_rounded : Icons.person_add_rounded,
                        color: const Color(0xFF4F46E5),
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Text(
                      _isEditMode ? 'Edit Reservation' : 'Add Walk-In Guest',
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _isEditMode
                      ? 'Update reservation details'
                      : 'Create a new reservation for a walk-in guest',
                  style: TextStyle(fontSize: 14, color: Colors.grey.shade500),
                ),

                // Mode chip (read-only, shown in edit mode)
                if (_isEditMode) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text('Mode: ', style: TextStyle(fontSize: 13, color: Colors.grey.shade600)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF5F7FA),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.grey.shade200),
                        ),
                        child: Text(_reservationMode,
                            style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                      ),
                    ],
                  ),
                ],

                const SizedBox(height: 20),

                // Form
                Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Name
                      TextFormField(
                        controller: _nameController,
                        maxLength: 100,
                        decoration: const InputDecoration(
                          labelText: 'Customer Name',
                          hintText: 'Enter guest name',
                          prefixIcon: Icon(Icons.person_outline_rounded),
                          counterText: '',
                        ),
                        validator: _validateName,
                        textInputAction: TextInputAction.next,
                      ),
                      const SizedBox(height: 14),

                      // Phone + Age row
                      Row(
                        children: [
                          Expanded(
                            flex: 3,
                            child: TextFormField(
                              controller: _phoneController,
                              maxLength: 20,
                              decoration: const InputDecoration(
                                labelText: 'Phone',
                                prefixIcon: Icon(Icons.phone_outlined),
                                counterText: '',
                              ),
                              validator: _validatePhone,
                              textInputAction: TextInputAction.next,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            flex: 1,
                            child: TextFormField(
                              controller: _ageController,
                              decoration: const InputDecoration(
                                labelText: 'Age',
                              ),
                              keyboardType: TextInputType.number,
                              textInputAction: TextInputAction.next,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      // Gotram (mandatory — approved-list autocomplete)
                      RawAutocomplete<String>(
                        textEditingController: _gotramController,
                        focusNode: _gotramFocus,
                        optionsBuilder: (TextEditingValue v) {
                          final q = v.text.trim().toLowerCase();
                          if (q.isEmpty) return kGotramNames;
                          return kGotramNames
                              .where((g) => g.toLowerCase().contains(q));
                        },
                        fieldViewBuilder:
                            (context, textCtrl, focusNode, onSubmit) {
                          return TextFormField(
                            controller: textCtrl,
                            focusNode: focusNode,
                            decoration: const InputDecoration(
                              labelText: 'Gotram (required)',
                              hintText: 'Start typing… e.g. Bharadwaja',
                              prefixIcon: Icon(Icons.account_balance_rounded),
                            ),
                            validator: _validateGotram,
                          );
                        },
                        optionsViewBuilder: (context, onSelected, options) {
                          return Align(
                            alignment: Alignment.topLeft,
                            child: Material(
                              elevation: 4,
                              borderRadius: BorderRadius.circular(8),
                              child: ConstrainedBox(
                                constraints: const BoxConstraints(
                                    maxHeight: 220, maxWidth: 400),
                                child: ListView(
                                  padding: EdgeInsets.zero,
                                  shrinkWrap: true,
                                  children: options
                                      .map((o) => ListTile(
                                            dense: true,
                                            title: Text(o),
                                            onTap: () => onSelected(o),
                                          ))
                                      .toList(),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                      const SizedBox(height: 14),

                      // Temple selector
                      if (_isLoadingTemples)
                        const Center(
                          child: Padding(
                            padding: EdgeInsets.all(8),
                            child: SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2)),
                          ),
                        )
                      else
                        DropdownButtonFormField<String>(
                          initialValue: _selectedTempleName,
                          decoration: const InputDecoration(
                            labelText: 'Temple',
                            prefixIcon: Icon(Icons.temple_buddhist_rounded),
                          ),
                          items: _temples
                              .map((t) => DropdownMenuItem(
                                  value: t.templeName, child: Text(t.templeName)))
                              .toList(),
                          onChanged: (v) => setState(() => _selectedTempleName = v),
                          validator: (v) =>
                              (v == null || v.isEmpty) ? 'Select a temple' : null,
                        ),
                      const SizedBox(height: 14),

                      // Room type (AC / Non-AC) + live rate
                      DropdownButtonFormField<String>(
                        initialValue: _selectedRoomType,
                        decoration: const InputDecoration(
                          labelText: 'Room Type',
                          prefixIcon: Icon(Icons.bed_rounded),
                        ),
                        items: kRoomTypes
                            .map((t) =>
                                DropdownMenuItem(value: t, child: Text(t)))
                            .toList(),
                        onChanged: (v) =>
                            setState(() => _selectedRoomType = v ?? 'AC'),
                      ),
                      const SizedBox(height: 6),
                      _RateHint(
                        nightly: _nightlyRate,
                        total: _computedTotal,
                      ),
                      const SizedBox(height: 14),

                      // Date pickers
                      Row(
                        children: [
                          Expanded(
                            child: _DatePickerField(
                              label: 'Check-in',
                              value: _formatDate(_checkIn),
                              icon: Icons.login_rounded,
                              onTap: () => _pickDate(isCheckIn: true),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _DatePickerField(
                              label: 'Check-out',
                              value: _formatDate(_checkOut),
                              icon: Icons.logout_rounded,
                              onTap: () => _pickDate(isCheckIn: false),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      // Rooms
                      TextFormField(
                        controller: _roomsController,
                        decoration: const InputDecoration(
                          labelText: 'Number of Rooms',
                          prefixIcon: Icon(Icons.meeting_room_outlined),
                        ),
                        keyboardType: TextInputType.number,
                        validator: _validateRooms,
                        onChanged: (_) => setState(() {}),
                      ),
                      const SizedBox(height: 14),

                      // Payment method
                      DropdownButtonFormField<String>(
                        initialValue: _selectedPaymentMethod,
                        decoration: const InputDecoration(
                          labelText: 'Payment Method',
                          prefixIcon: Icon(Icons.payments_outlined),
                        ),
                        isExpanded: true,
                        items: kPaymentMethods
                            .map((m) => DropdownMenuItem(
                                value: m.id, child: Text(m.name)))
                            .toList(),
                        onChanged: (v) => setState(
                            () => _selectedPaymentMethod = v ?? 'cash'),
                      ),
                      const SizedBox(height: 14),

                      // Status dropdown (full width to avoid overflow)
                      DropdownButtonFormField<String>(
                        initialValue: _selectedStatus,
                        decoration: const InputDecoration(
                          labelText: 'Reservation Status',
                          prefixIcon: Icon(Icons.flag_rounded),
                        ),
                        isExpanded: true,
                        items: _statusOptions
                            .map((s) =>
                                DropdownMenuItem(value: s, child: Text(s)))
                            .toList(),
                        onChanged: (v) {
                          if (v != null) setState(() => _selectedStatus = v);
                        },
                      ),

                      // Error message
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.error_outline_rounded,
                                  size: 18, color: Colors.red.shade400),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(_errorMessage!,
                                    style: TextStyle(
                                        fontSize: 13,
                                        color: Colors.red.shade700)),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Actions
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: _isSubmitting ? null : () => Navigator.pop(context),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: 12),
                    FilledButton.icon(
                      onPressed: _isSubmitting ? null : _submit,
                      icon: _isSubmitting
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : Icon(
                              _isEditMode ? Icons.save_rounded : Icons.add_rounded,
                              size: 18),
                      label: Text(_isEditMode ? 'Save Changes' : 'Add Guest'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Small inline hint showing the nightly rate and computed stay total.
class _RateHint extends StatelessWidget {
  final int nightly;
  final int total;

  const _RateHint({required this.nightly, required this.total});

  @override
  Widget build(BuildContext context) {
    if (nightly <= 0) {
      return Row(
        children: [
          Icon(Icons.info_outline_rounded, size: 14, color: Colors.grey.shade400),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              'No configured rate for this location/type yet.',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
            ),
          ),
        ],
      );
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF8B4513).withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.currency_rupee_rounded,
              size: 16, color: Color(0xFF8B4513)),
          const SizedBox(width: 6),
          Text('$nightly / night',
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF8B4513))),
          const Spacer(),
          Text('Total: ₹$total',
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF1E293B))),
        ],
      ),
    );
  }
}

class _DatePickerField extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final VoidCallback onTap;

  const _DatePickerField({
    required this.label,
    required this.value,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: Text(value, style: const TextStyle(fontSize: 14)),
      ),
    );
  }
}
