import 'package:flutter/material.dart';

import '../models/temple.dart';
import '../services/firestore_service.dart';

/// Modal dialog for editing temple capacity, availability, and maintenance values.
///
/// Pre-populates fields with the current [Temple] values and validates
/// that all fields are integers in range [0, 10000] with
/// `available_rooms + maintenance_rooms <= total_capacity`.
class UpdateInventoryDialog extends StatefulWidget {
  final Temple temple;

  const UpdateInventoryDialog({super.key, required this.temple});

  @override
  State<UpdateInventoryDialog> createState() => _UpdateInventoryDialogState();
}

class _UpdateInventoryDialogState extends State<UpdateInventoryDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _totalCapacityController;
  late final TextEditingController _availableRoomsController;
  late final TextEditingController _maintenanceRoomsController;
  final FirestoreService _firestoreService = FirestoreService();

  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _totalCapacityController =
        TextEditingController(text: widget.temple.totalCapacity.toString());
    _availableRoomsController =
        TextEditingController(text: widget.temple.availableRooms.toString());
    _maintenanceRoomsController =
        TextEditingController(text: widget.temple.maintenanceRooms.toString());
  }

  @override
  void dispose() {
    _totalCapacityController.dispose();
    _availableRoomsController.dispose();
    _maintenanceRoomsController.dispose();
    super.dispose();
  }

  String? _validateTotalCapacity(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Total capacity is required';
    }
    final parsed = int.tryParse(value.trim());
    if (parsed == null) {
      return 'Must be a valid integer';
    }
    if (parsed < 1) {
      return 'Must be at least 1';
    }
    if (parsed > 10000) {
      return 'Must be at most 10,000';
    }
    return null;
  }

  String? _validateAvailableRooms(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Available rooms is required';
    }
    final parsed = int.tryParse(value.trim());
    if (parsed == null) {
      return 'Must be a valid integer';
    }
    if (parsed < 0) {
      return 'Cannot be negative';
    }
    if (parsed > 10000) {
      return 'Must be at most 10,000';
    }
    final totalCapacity =
        int.tryParse(_totalCapacityController.text.trim()) ?? 0;
    final maintenance =
        int.tryParse(_maintenanceRoomsController.text.trim()) ?? 0;
    if (parsed + maintenance > totalCapacity) {
      return 'Available + Maintenance cannot exceed Total Capacity';
    }
    return null;
  }

  String? _validateMaintenanceRooms(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Maintenance rooms is required';
    }
    final parsed = int.tryParse(value.trim());
    if (parsed == null) {
      return 'Must be a valid integer';
    }
    if (parsed < 0) {
      return 'Cannot be negative';
    }
    if (parsed > 10000) {
      return 'Must be at most 10,000';
    }
    final totalCapacity =
        int.tryParse(_totalCapacityController.text.trim()) ?? 0;
    final available =
        int.tryParse(_availableRoomsController.text.trim()) ?? 0;
    if (available + parsed > totalCapacity) {
      return 'Available + Maintenance cannot exceed Total Capacity';
    }
    return null;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final totalCapacity = int.parse(_totalCapacityController.text.trim());
    final availableRooms = int.parse(_availableRoomsController.text.trim());
    final maintenanceRooms = int.parse(_maintenanceRoomsController.text.trim());

    try {
      await _firestoreService.updateTemple(
        widget.temple.id,
        totalCapacity: totalCapacity,
        availableRooms: availableRooms,
        maintenanceRooms: maintenanceRooms,
      );
      if (mounted) {
        Navigator.pop(context);
      }
    } on FirestoreServiceException catch (e) {
      setState(() {
        _errorMessage = e.message;
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'An unexpected error occurred';
        _isSubmitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
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
                    child: const Icon(
                      Icons.edit_rounded,
                      color: Color(0xFF4F46E5),
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Update Inventory',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF1E293B),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          widget.temple.templeName,
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey.shade500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Form
              Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (_errorMessage != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.error_outline_rounded,
                              size: 18,
                              color: Colors.red.shade400,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _errorMessage!,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.red.shade700,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    TextFormField(
                      controller: _totalCapacityController,
                      decoration: const InputDecoration(
                        labelText: 'Total Capacity',
                        prefixIcon: Icon(Icons.meeting_room_outlined),
                      ),
                      keyboardType: TextInputType.number,
                      validator: _validateTotalCapacity,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _availableRoomsController,
                      decoration: const InputDecoration(
                        labelText: 'Available Rooms',
                        prefixIcon: Icon(Icons.check_circle_outline_rounded),
                      ),
                      keyboardType: TextInputType.number,
                      validator: _validateAvailableRooms,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _maintenanceRoomsController,
                      decoration: const InputDecoration(
                        labelText: 'Maintenance Rooms',
                        prefixIcon: Icon(Icons.build_rounded),
                      ),
                      keyboardType: TextInputType.number,
                      validator: _validateMaintenanceRooms,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed:
                        _isSubmitting ? null : () => Navigator.pop(context),
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
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.save_rounded, size: 18),
                    label: const Text('Update'),
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
