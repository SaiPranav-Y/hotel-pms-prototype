import 'package:flutter/material.dart';

import '../models/app_user.dart';
import 'admin/rates_view.dart';
import 'admin/staff_view.dart';
import 'dashboard_view.dart';
import 'inventory_view.dart';
import 'reservations_view.dart';

/// The root scaffold managing navigation between the role-appropriate views.
///
/// Navigation items are filtered by the signed-in [user]'s permissions:
///   - Supervisor: Dashboard, Reservations (walk-in booking + checkout), Inventory
///   - Admin: + Rates & Sevas
///   - Super Admin: + Staff management
class DashboardShell extends StatefulWidget {
  final AppUser user;
  final Future<void> Function() onSignOut;

  const DashboardShell({
    super.key,
    required this.user,
    required this.onSignOut,
  });

  @override
  State<DashboardShell> createState() => _DashboardShellState();
}

class _DashboardShellState extends State<DashboardShell> {
  int _selectedIndex = 0;

  /// Build the nav items visible to this user's role.
  List<_NavEntry> get _entries {
    final u = widget.user;
    final entries = <_NavEntry>[
      _NavEntry(
        icon: Icons.dashboard_rounded,
        label: 'Dashboard',
        builder: () => const DashboardView(),
      ),
    ];
    if (u.can(Perm.viewBookings) || u.can(Perm.walkInBooking)) {
      entries.add(_NavEntry(
        icon: Icons.calendar_month_rounded,
        label: 'Reservations',
        builder: () => const ReservationsView(),
      ));
    }
    if (u.can(Perm.viewAvailability)) {
      entries.add(_NavEntry(
        icon: Icons.inventory_2_rounded,
        label: 'Inventory',
        builder: () => const InventoryView(),
      ));
    }
    if (u.can(Perm.editRates) || u.can(Perm.setSevaAmounts)) {
      entries.add(_NavEntry(
        icon: Icons.currency_rupee_rounded,
        label: 'Rates & Sevas',
        builder: () => const RatesView(),
      ));
    }
    if (u.can(Perm.manageUsers)) {
      entries.add(_NavEntry(
        icon: Icons.admin_panel_settings_rounded,
        label: 'Staff',
        builder: () => const StaffView(),
      ));
    }
    return entries;
  }

  @override
  Widget build(BuildContext context) {
    final entries = _entries;
    final safeIndex = _selectedIndex.clamp(0, entries.length - 1);

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: Row(
        children: [
          _Sidebar(
            user: widget.user,
            entries: entries,
            selectedIndex: safeIndex,
            onSelect: (i) => setState(() => _selectedIndex = i),
          ),
          Expanded(
            child: Column(
              children: [
                _TopBar(user: widget.user, onSignOut: widget.onSignOut),
                Expanded(
                  child: IndexedStack(
                    index: safeIndex,
                    children: [for (final e in entries) e.builder()],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  final AppUser user;
  final List<_NavEntry> entries;
  final int selectedIndex;
  final ValueChanged<int> onSelect;

  const _Sidebar({
    required this.user,
    required this.entries,
    required this.selectedIndex,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    const brand = Color(0xFF8B4513);
    return Container(
      width: 260,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(right: BorderSide(color: Color(0xFFE2E8F0), width: 1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: brand.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.temple_hindu_rounded,
                      color: brand, size: 24),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'Karivena Satram',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Role badge
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 20),
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: brand.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.verified_user_rounded,
                      size: 14, color: brand),
                  const SizedBox(width: 6),
                  Text(
                    user.role.label,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: brand,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Column(
              children: List.generate(entries.length, (index) {
                final item = entries[index];
                final isSelected = selectedIndex == index;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Material(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(12),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => onSelect(index),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? brand.withValues(alpha: 0.1)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          children: [
                            Icon(item.icon,
                                size: 20,
                                color: isSelected
                                    ? brand
                                    : const Color(0xFF64748B)),
                            const SizedBox(width: 12),
                            Text(
                              item.label,
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: isSelected
                                    ? FontWeight.w600
                                    : FontWeight.w500,
                                color: isSelected
                                    ? brand
                                    : const Color(0xFF64748B),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Temple Accommodation\nManagement System',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade400,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  final AppUser user;
  final Future<void> Function() onSignOut;

  const _TopBar({required this.user, required this.onSignOut});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 20),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0), width: 1)),
      ),
      child: Row(
        children: [
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Property Management Dashboard',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF1E293B),
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'Temple Accommodation Management System',
                  style: TextStyle(fontSize: 14, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
          ),
          // User menu
          PopupMenuButton<String>(
            offset: const Offset(0, 48),
            onSelected: (v) {
              if (v == 'logout') onSignOut();
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                enabled: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(user.name,
                        style:
                            const TextStyle(fontWeight: FontWeight.w600)),
                    Text(user.email,
                        style: TextStyle(
                            fontSize: 12, color: Colors.grey.shade500)),
                  ],
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout_rounded, size: 18),
                    SizedBox(width: 8),
                    Text('Sign Out'),
                  ],
                ),
              ),
            ],
            child: Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundColor: const Color(0xFF8B4513),
                  child: Text(
                    user.name.isNotEmpty ? user.name[0].toUpperCase() : '?',
                    style: const TextStyle(color: Colors.white),
                  ),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.arrow_drop_down, color: Color(0xFF64748B)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _NavEntry {
  final IconData icon;
  final String label;
  final Widget Function() builder;

  const _NavEntry({
    required this.icon,
    required this.label,
    required this.builder,
  });
}
