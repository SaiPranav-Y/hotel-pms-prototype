import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

/// Admin view for managing room rates (per location x room type) and seva
/// donation amounts. Reads/writes the Firestore `rates` and `sevas`
/// collections — the same source of truth the backend `rates.py` / `payments.py`
/// use. Only reachable by Admin / Super Admin (gated in the shell).
class RatesView extends StatelessWidget {
  const RatesView({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          const Material(
            color: Colors.white,
            child: TabBar(
              labelColor: Color(0xFF8B4513),
              indicatorColor: Color(0xFF8B4513),
              tabs: [
                Tab(text: 'Room Rates'),
                Tab(text: 'Seva Amounts'),
              ],
            ),
          ),
          const Expanded(
            child: TabBarView(
              children: [
                _RatesTab(),
                _SevasTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RatesTab extends StatelessWidget {
  const _RatesTab();

  @override
  Widget build(BuildContext context) {
    final rates = FirebaseFirestore.instance.collection('rates');
    return StreamBuilder<QuerySnapshot>(
      stream: rates.snapshots(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final docs = snapshot.data?.docs ?? [];
        if (docs.isEmpty) {
          return const _EmptyHint(
            icon: Icons.currency_rupee_rounded,
            title: 'No rates configured yet',
            subtitle:
                'Rates load from rate_config.json or can be set here. '
                'Base rate is per night, per room.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(24),
          itemCount: docs.length,
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemBuilder: (context, i) {
            final loc = docs[i].id;
            final data = docs[i].data() as Map<String, dynamic>;
            final ac = (data['ac'] as Map<String, dynamic>?)?['base'] ?? 0;
            final nonac =
                (data['nonac'] as Map<String, dynamic>?)?['base'] ?? 0;
            return Card(
              child: ListTile(
                title: Text(
                  loc.replaceAll('_', ' ').toUpperCase(),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                subtitle: Text('AC: ₹$ac / night   •   Non-AC: ₹$nonac / night'),
                trailing: IconButton(
                  icon: const Icon(Icons.edit_rounded),
                  onPressed: () => _editRate(context, loc, ac, nonac),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _editRate(
      BuildContext context, String loc, dynamic ac, dynamic nonac) async {
    final acCtrl = TextEditingController(text: '$ac');
    final nonacCtrl = TextEditingController(text: '$nonac');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Edit rates — ${loc.replaceAll('_', ' ')}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: acCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'AC base (₹/night)'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: nonacCtrl,
              keyboardType: TextInputType.number,
              decoration:
                  const InputDecoration(labelText: 'Non-AC base (₹/night)'),
            ),
          ],
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
    );
    if (ok == true) {
      await FirebaseFirestore.instance.collection('rates').doc(loc).set({
        'ac': {'base': int.tryParse(acCtrl.text) ?? 0, 'seasons': []},
        'nonac': {'base': int.tryParse(nonacCtrl.text) ?? 0, 'seasons': []},
      }, SetOptions(merge: true));
    }
  }
}

class _SevasTab extends StatelessWidget {
  const _SevasTab();

  @override
  Widget build(BuildContext context) {
    final sevas = FirebaseFirestore.instance.collection('sevas');
    return StreamBuilder<QuerySnapshot>(
      stream: sevas.snapshots(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final docs = snapshot.data?.docs ?? [];
        if (docs.isEmpty) {
          return const _EmptyHint(
            icon: Icons.volunteer_activism_rounded,
            title: 'Using default seva amounts',
            subtitle:
                'Defaults live in the backend. Setting a value here overrides '
                'it. All seva donations are 80G eligible.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(24),
          itemCount: docs.length,
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemBuilder: (context, i) {
            final data = docs[i].data() as Map<String, dynamic>;
            return Card(
              child: ListTile(
                title: Text(data['name']?.toString() ?? docs[i].id,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(data['description']?.toString() ?? ''),
                trailing: Text('₹${data['amount'] ?? 0}',
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, color: Color(0xFF8B4513))),
                onTap: () => _editSeva(context, docs[i].id, data),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _editSeva(
      BuildContext context, String id, Map<String, dynamic> data) async {
    final amtCtrl = TextEditingController(text: '${data['amount'] ?? 0}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Edit — ${data['name'] ?? id}'),
        content: TextField(
          controller: amtCtrl,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Amount (₹)'),
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
    );
    if (ok == true) {
      await FirebaseFirestore.instance.collection('sevas').doc(id).set({
        'amount': int.tryParse(amtCtrl.text) ?? 0,
      }, SetOptions(merge: true));
    }
  }
}

class _EmptyHint extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _EmptyHint({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: Colors.grey.shade300),
            const SizedBox(height: 16),
            Text(title,
                style: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text(subtitle,
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade500)),
          ],
        ),
      ),
    );
  }
}
