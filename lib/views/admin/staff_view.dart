import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../../models/app_user.dart';

/// Super Admin view for managing staff accounts and roles.
///
/// Reads/writes the Firestore `users` collection (keyed by lowercased email),
/// matching the backend `roles.py` convention. Creating a login credential in
/// Firebase Auth is a separate step (handled by the auth provider); this screen
/// manages the staff profile + role record that authorization reads from.
class StaffView extends StatelessWidget {
  const StaffView({super.key});

  @override
  Widget build(BuildContext context) {
    final users = FirebaseFirestore.instance.collection('users');
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF8B4513),
        icon: const Icon(Icons.person_add_rounded),
        label: const Text('Add Staff'),
        onPressed: () => _editUser(context, null, null),
      ),
      body: StreamBuilder<QuerySnapshot>(
        stream: users.snapshots(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final docs = snapshot.data?.docs ?? [];
          if (docs.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.group_outlined,
                      size: 48, color: Colors.grey.shade300),
                  const SizedBox(height: 16),
                  const Text('No staff accounts yet',
                      style: TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  Text('Add your first staff member with the button below.',
                      style: TextStyle(color: Colors.grey.shade500)),
                ],
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(24),
            itemCount: docs.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, i) {
              final id = docs[i].id;
              final data = docs[i].data() as Map<String, dynamic>;
              final role = StaffRole.fromString(data['role'] as String?);
              final active = data['active'] as bool? ?? true;
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: const Color(0xFF8B4513),
                    child: Text(
                      (data['name']?.toString() ?? id).isNotEmpty
                          ? (data['name']?.toString() ?? id)[0].toUpperCase()
                          : '?',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                  title: Text(data['name']?.toString() ?? id,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text(id),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF8B4513).withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(role.label,
                            style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: Color(0xFF8B4513))),
                      ),
                      if (!active)
                        const Padding(
                          padding: EdgeInsets.only(left: 8),
                          child: Icon(Icons.block, size: 16, color: Colors.red),
                        ),
                      IconButton(
                        icon: const Icon(Icons.edit_rounded),
                        onPressed: () => _editUser(context, id, data),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _editUser(
      BuildContext context, String? email, Map<String, dynamic>? data) async {
    final isNew = email == null;
    final emailCtrl = TextEditingController(text: email ?? '');
    final nameCtrl =
        TextEditingController(text: data?['name']?.toString() ?? '');
    StaffRole role = StaffRole.fromString(data?['role'] as String?);
    bool active = data?['active'] as bool? ?? true;

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlg) => AlertDialog(
          title: Text(isNew ? 'Add Staff' : 'Edit Staff'),
          content: SizedBox(
            width: 360,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: emailCtrl,
                  enabled: isNew,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'Full name'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<StaffRole>(
                  value: role,
                  decoration: const InputDecoration(labelText: 'Role'),
                  items: StaffRole.values
                      .map((r) => DropdownMenuItem(
                          value: r, child: Text(r.label)))
                      .toList(),
                  onChanged: (r) => setDlg(() => role = r ?? role),
                ),
                const SizedBox(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Active'),
                  value: active,
                  activeColor: const Color(0xFF8B4513),
                  onChanged: (v) => setDlg(() => active = v),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel')),
            FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Save')),
          ],
        ),
      ),
    );

    if (ok == true) {
      final key = (isNew ? emailCtrl.text : email).trim().toLowerCase();
      if (key.isEmpty || !key.contains('@')) return;
      await FirebaseFirestore.instance.collection('users').doc(key).set({
        'email': key,
        'name': nameCtrl.text.trim(),
        'role': role.key,
        'active': active,
        'updated_at': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }
  }
}
