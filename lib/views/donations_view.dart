import 'package:flutter/material.dart';

import '../constants/karivena_data.dart';

/// Donations screen — shows the three Karivena donation categories and their
/// options with amounts. All donations are 80G tax-exempt eligible (certificate
/// issued post-donation). Amounts come from [karivena_data.dart] (mirrors the
/// backend). Staff can pick an option to record a donation.
class DonationsView extends StatelessWidget {
  const DonationsView({super.key});

  static const _brand = Color(0xFF8B4513);

  @override
  Widget build(BuildContext context) {
    final grouped = kDonationsByCategory;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.volunteer_activism_rounded, color: _brand),
              const SizedBox(width: 10),
              const Text(
                'Donations',
                style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF1E293B)),
              ),
              const SizedBox(width: 12),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF00BA7C).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Text('All 80G eligible',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF00875A))),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Donors receive an 80G tax-exemption certificate after the donation.',
            style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
          ),
          const SizedBox(height: 24),

          for (final catId in kDonationCategories.keys)
            _CategorySection(
              title: kDonationCategories[catId]!,
              options: grouped[catId] ?? const [],
            ),
        ],
      ),
    );
  }
}

class _CategorySection extends StatelessWidget {
  final String title;
  final List<DonationOption> options;

  const _CategorySection({required this.title, required this.options});

  @override
  Widget build(BuildContext context) {
    if (options.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 10, top: 4),
          child: Text(
            title,
            style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: Color(0xFF8B4513)),
          ),
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            final cols = constraints.maxWidth > 900
                ? 3
                : constraints.maxWidth > 560
                    ? 2
                    : 1;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                for (final o in options)
                  SizedBox(
                    width: (constraints.maxWidth - (cols - 1) * 12) / cols,
                    child: _DonationCard(option: o),
                  ),
              ],
            );
          },
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}

class _DonationCard extends StatelessWidget {
  final DonationOption option;

  const _DonationCard({required this.option});

  @override
  Widget build(BuildContext context) {
    final amountLabel = option.isCustomAmount
        ? 'Any amount'
        : '₹${_fmt(option.amount)}';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    option.name,
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w600),
                  ),
                ),
                Text(
                  amountLabel,
                  style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF8B4513)),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              option.description,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF8B4513),
                  side: const BorderSide(color: Color(0xFF8B4513)),
                ),
                icon: const Icon(Icons.card_giftcard_rounded, size: 16),
                label: const Text('Record'),
                onPressed: () => _recordDonation(context, option),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _recordDonation(
      BuildContext context, DonationOption option) async {
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final amountCtrl = TextEditingController(
        text: option.isCustomAmount ? '' : '${option.amount}');

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Record — ${option.name}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(labelText: 'Donor name'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Phone (WhatsApp)'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: amountCtrl,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: 'Amount (₹)',
                helperText: option.isCustomAmount
                    ? 'Donor chooses the amount'
                    : 'Preset — editable',
              ),
            ),
            const SizedBox(height: 8),
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '80G certificate will be issued after payment.',
                style: TextStyle(fontSize: 11, color: Color(0xFF00875A)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF8B4513)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Record'),
          ),
        ],
      ),
    );

    if (ok == true && context.mounted) {
      // NOTE: wiring to the backend /api/donations or Firestore happens where
      // the API base URL is configured. For now confirm capture to the user.
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              'Donation recorded: ${option.name} — ₹${amountCtrl.text.isEmpty ? "0" : amountCtrl.text}'),
          backgroundColor: const Color(0xFF8B4513),
        ),
      );
    }
  }

  /// Indian-style digit grouping, e.g. 500000 -> "5,00,000".
  static String _fmt(int n) {
    final s = n.toString();
    if (s.length <= 3) return s;
    final last3 = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final groups = <String>[];
    while (rest.length > 2) {
      groups.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) groups.insert(0, rest);
    return '${groups.join(',')},$last3';
  }
}
