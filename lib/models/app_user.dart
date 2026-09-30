/// Staff roles for the Karivena PMS, mirroring the backend `roles.py` matrix.
enum StaffRole {
  supervisor,
  admin,
  superAdmin;

  /// Parse a Firestore role string (e.g. "super_admin") into a [StaffRole].
  static StaffRole fromString(String? value) {
    switch ((value ?? '').toLowerCase()) {
      case 'admin':
        return StaffRole.admin;
      case 'super_admin':
      case 'superadmin':
        return StaffRole.superAdmin;
      case 'supervisor':
      default:
        return StaffRole.supervisor;
    }
  }

  /// The canonical string stored in Firestore.
  String get key {
    switch (this) {
      case StaffRole.supervisor:
        return 'supervisor';
      case StaffRole.admin:
        return 'admin';
      case StaffRole.superAdmin:
        return 'super_admin';
    }
  }

  /// Human-readable label for the UI.
  String get label {
    switch (this) {
      case StaffRole.supervisor:
        return 'Supervisor';
      case StaffRole.admin:
        return 'Admin';
      case StaffRole.superAdmin:
        return 'Super Admin';
    }
  }
}

/// Permission keys — mirror the backend PERMISSIONS matrix in `roles.py`.
class Perm {
  static const walkInBooking = 'walk_in_booking';
  static const viewBookings = 'view_bookings';
  static const viewCalls = 'view_calls';
  static const generateInvoice = 'generate_invoice';
  static const triggerCheckout = 'trigger_checkout';
  static const viewCustomers = 'view_customers';
  static const viewAvailability = 'view_availability';
  static const editRates = 'edit_rates';
  static const setSevaAmounts = 'set_seva_amounts';
  static const editGotrams = 'edit_gotrams';
  static const viewAnalytics = 'view_analytics';
  static const manageCampaigns = 'manage_campaigns';
  static const configureEscalation = 'configure_escalation';
  static const manageUsers = 'manage_users';
  static const assignRoles = 'assign_roles';
  static const deleteBookings = 'delete_bookings';
  static const systemConfig = 'system_config';
}

const Set<String> _supervisorPerms = {
  Perm.walkInBooking,
  Perm.viewBookings,
  Perm.viewCalls,
  Perm.generateInvoice,
  Perm.triggerCheckout,
  Perm.viewCustomers,
  Perm.viewAvailability,
};

const Set<String> _adminExtra = {
  Perm.editRates,
  Perm.setSevaAmounts,
  Perm.editGotrams,
  Perm.viewAnalytics,
  Perm.manageCampaigns,
  Perm.configureEscalation,
};

const Set<String> _superAdminExtra = {
  Perm.manageUsers,
  Perm.assignRoles,
  Perm.deleteBookings,
  Perm.systemConfig,
};

/// Resolve the permission set for a role.
Set<String> permissionsFor(StaffRole role) {
  switch (role) {
    case StaffRole.supervisor:
      return _supervisorPerms;
    case StaffRole.admin:
      return {..._supervisorPerms, ..._adminExtra};
    case StaffRole.superAdmin:
      return {..._supervisorPerms, ..._adminExtra, ..._superAdminExtra};
  }
}

/// An authenticated staff member with a role and derived permissions.
class AppUser {
  final String uid;
  final String email;
  final String name;
  final StaffRole role;
  final bool active;

  const AppUser({
    required this.uid,
    required this.email,
    required this.name,
    required this.role,
    this.active = true,
  });

  Set<String> get permissions => permissionsFor(role);

  bool can(String permission) => permissions.contains(permission);

  factory AppUser.fromMap(String uid, String email, Map<String, dynamic> data) {
    return AppUser(
      uid: uid,
      email: (data['email'] ?? email).toString(),
      name: (data['name'] ?? email).toString(),
      role: StaffRole.fromString(data['role'] as String?),
      active: data['active'] as bool? ?? true,
    );
  }
}
