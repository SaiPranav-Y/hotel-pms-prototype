/// Karivena Satram reference data — mirrors the backend (voice-ai/app).
///
/// Kept in sync with:
///   - app/allowed_gotrams.json   (approved gotrams)
///   - app/rate_config.json       (room rates per location x type)
///   - app/payments.py            (payment methods + donation categories/amounts)
///
/// The app can override any of these from Firestore at runtime, but these
/// constants provide a correct, offline-safe default so the UI always works.
library;

// ============================================================
//  GOTRAMS (approved community list)
// ============================================================

/// A single approved gotram with its Telugu spelling and alias variants.
class Gotram {
  final String canonical;
  final String telugu;
  final List<String> aliases;

  const Gotram(this.canonical, this.telugu, this.aliases);

  /// All searchable forms (canonical + telugu + aliases), lowercased.
  List<String> get searchForms =>
      [canonical, telugu, ...aliases].map((s) => s.toLowerCase()).toList();
}

/// The 40 approved gotrams derived from the community reference
/// (Brahmanula Illa Perlu Gotramulu, 382 pages).
const List<Gotram> kGotrams = [
  Gotram('Bharadwaja', 'భారద్వాజ', ['Bharadwaj', 'Bharadhwaja', 'Bharadvaja', 'Bhardwaj']),
  Gotram('Kashyapa', 'కాశ్యప', ['Kashyap', 'Kasyapa', 'Kaashyapa']),
  Gotram('Vasishta', 'వాశిష్ఠ', ['Vashishta', 'Vasistha', 'Vashista', 'Vasishtha']),
  Gotram('Vishwamitra', 'విశ్వామిత్ర', ['Vishwamithra', 'Viswamitra', 'Kamakayana']),
  Gotram('Gautama', 'గౌతమ', ['Gautam', 'Gowtama', 'Goutama', 'Gauthama']),
  Gotram('Atreya', 'ఆత్రేయ', ['Atri', 'Aatreya', 'Athreya']),
  Gotram('Bhrigu', 'భృగు', ['Brigu', 'Bhrgu', 'Bhargava']),
  Gotram('Angirasa', 'ఆంగీరస', ['Angiras', 'Aangirasa', 'Angeerasa']),
  Gotram('Agastya', 'అగస్త్య', ['Agasthya', 'Agasti']),
  Gotram('Koundinya', 'కౌండిన్య', ['Kaundinya', 'Kaundilya', 'Koundilya', 'Kondinya']),
  Gotram('Shandilya', 'శాండిల్య', ['Sandilya', 'Saandilya', 'Shaandilya']),
  Gotram('Srivatsa', 'శ్రీవత్స', ['Srivatsava', 'Shrivatsa', 'Srivathsa']),
  Gotram('Harita', 'హారీత', ['Haritha', 'Haarita', 'Harit']),
  Gotram('Gargya', 'గార్గ్య', ['Garga', 'Gaargya', 'Gargeya']),
  Gotram('Koutsa', 'కౌత్స', ['Kutsa', 'Kowtsa', 'Kautsa']),
  Gotram('Jamadagni', 'జామదగ్న్య', ['Jamadagnya', 'Jaamadagnya']),
  Gotram('Kaushika', 'కౌశిక', ['Koushika', 'Kausika', 'Kaushik', 'Koushik']),
  Gotram('Moudgalya', 'మౌద్గల్య', ['Mudgala', 'Moudgala', 'Maudgalya']),
  Gotram('Sankhyayana', 'సాంఖ్యాయన', ['Sankhayana', 'Saankhyaayana']),
  Gotram('Parashara', 'పరాశర', ['Parasara', 'Paraashara', 'Parasharya', 'Parashar']),
  Gotram('Kanva', 'కాణ్వ', ['Kanwa', 'Kaanva', 'Kanvayana']),
  Gotram('Chyavana', 'చ్యవన', ['Chyavan', 'Chyaavana']),
  Gotram('Ambarisha', 'అంబరీష', ['Ambareesha', 'Ambarisa']),
  Gotram('Shaunaka', 'శౌనక', ['Shaunak', 'Saunaka', 'Shounaka']),
  Gotram('Vitahavya', 'వీతహవ్య', ['Vithahavya', 'Veetahavya']),
  Gotram('Barhaspatya', 'బార్హస్పత్య', ['Barhaspathya', 'Bruhaspatya', 'Brihaspatya']),
  Gotram('Archananasa', 'అర్చనానస', ['Archanaanasa', 'Archanasa']),
  Gotram('Poutimasha', 'పౌతిమాష', ['Poutimasa', 'Pautimasha', 'Poothimasha']),
  Gotram('Ashtaka', 'అష్టక', ['Ashtak', 'Astaka']),
  Gotram('Naidhruva', 'నైధ్రువ', ['Naidhruvasa', 'Nydhruva']),
  Gotram('Rathitara', 'రథీతర', ['Rathithara', 'Ratheetara']),
  Gotram('Mandavya', 'మాండవ్య', ['Maandavya', 'Mandavyasa']),
  Gotram('Upamanyu', 'ఉపమన్యు', ['Upamanyusa']),
  Gotram('Dhananjaya', 'ధనంజయ', ['Dhanunjaya', 'Dhananjay']),
  Gotram('Vishnuvardhana', 'విష్ణువర్ధన', ['Vishnuvardhan', 'Vishnuvriddha']),
  Gotram('Sankriti', 'సంకృతి', ['Sankruti', 'Sankrithi']),
  Gotram('Lohita', 'లోహిత', ['Lohitha', 'Lauhita', 'Lohit']),
  Gotram('Vadhula', 'వాధూల', ['Vaadhula', 'Vadhoola', 'Vadula']),
  Gotram('Gopala', 'గోపాల', ['Gopal', 'Gopaala']),
  Gotram('Yaska', 'యాస్క', ['Yaaska', 'Yaskasa']),
];

/// Sorted list of canonical gotram names (for dropdowns).
List<String> get kGotramNames =>
    kGotrams.map((g) => g.canonical).toList()..sort();

String _normGotram(String s) {
  final lower = s.trim().toLowerCase();
  // strip common suffixes + non-letters (keep Telugu + latin)
  final stripped = lower.replaceAll(
      RegExp(r'\s*(gotram|gothram|gotra|gothra)\s*$'), '');
  final buf = StringBuffer();
  for (final ch in stripped.runes) {
    final c = String.fromCharCode(ch);
    final isLatin = ch >= 0x61 && ch <= 0x7a;
    final isTelugu = ch >= 0x0c00 && ch <= 0x0c7f;
    if (isLatin || isTelugu) buf.write(c);
  }
  return buf.toString();
}

/// Match a typed/spoken gotram to its canonical name, or null if not approved.
/// Handles English, Telugu, aliases, and suffix-stripping.
String? matchGotram(String input) {
  if (input.trim().isEmpty) return null;
  final norm = _normGotram(input);
  if (norm.length < 3) return null;
  for (final g in kGotrams) {
    for (final form in g.searchForms) {
      final fnorm = _normGotram(form);
      if (fnorm.isEmpty) continue;
      if (fnorm == norm) return g.canonical;
    }
  }
  // prefix fallback (length-guarded)
  if (norm.length >= 4) {
    for (final g in kGotrams) {
      for (final form in g.searchForms) {
        final fnorm = _normGotram(form);
        if (fnorm.length >= 4 &&
            (fnorm.startsWith(norm) || norm.startsWith(fnorm))) {
          return g.canonical;
        }
      }
    }
  }
  return null;
}

bool isGotramAllowed(String input) => matchGotram(input) != null;

// ============================================================
//  ROOM RATES (per location x room type) — from rate_config.json
// ============================================================

/// Base nightly rate in INR for [location] + [roomType] ("AC" | "Non-AC").
/// Returns 0 if not configured. Tolerant of location display-name variants
/// (e.g. "Srisailam HO", "Tirupati") by matching on the known location key.
int rateFor(String location, String roomType) {
  final isAc = !roomType.toLowerCase().contains('non');
  final table = isAc ? _acRates : _nonAcRates;
  final loc = location.trim().toLowerCase().replaceAll(RegExp(r'[\s_]+'), '_');

  // exact key
  if (table.containsKey(loc)) return table[loc]!;

  // tolerant: match if a known key is contained in the given location
  // ("srisailam_ho" -> "srisailam", "tirupati" -> "tirupathi")
  final bare = loc.replaceAll('_', '');
  for (final key in table.keys) {
    final keyBare = key.replaceAll('_', '');
    if (bare.contains(keyBare) || keyBare.contains(bare)) {
      return table[key]!;
    }
  }
  return 0;
}

const Map<String, int> _acRates = {
  'brundavanam': 1200,
  'kasi': 1800,
  'mahanandi': 1200,
  'tirupathi': 1500,
  'vruddasramam': 1500,
  'rameswaram': 1200,
  'srisailam': 1500,
  'shiridi': 1500,
};

const Map<String, int> _nonAcRates = {
  'mahanandi': 600,
  'naimisaranyam': 700,
  'rameswaram': 700,
  'srisailam': 500,
  'shiridi': 1000,
};

/// Room types offered.
const List<String> kRoomTypes = ['AC', 'Non-AC'];

/// Compute total for a stay (nights x rooms x base rate).
int computeStayTotal({
  required String location,
  required String roomType,
  required DateTime checkIn,
  required DateTime checkOut,
  required int rooms,
}) {
  final nights = checkOut.difference(checkIn).inDays;
  final n = nights < 1 ? 1 : nights;
  return rateFor(location, roomType) * n * (rooms < 1 ? 1 : rooms);
}

// ============================================================
//  PAYMENT METHODS
// ============================================================

class PaymentMethod {
  final String id;
  final String name;
  final bool needsReference;
  final String referenceLabel;
  const PaymentMethod(this.id, this.name, this.needsReference, this.referenceLabel);
}

const List<PaymentMethod> kPaymentMethods = [
  PaymentMethod('cash', 'Cash', false, ''),
  PaymentMethod('card', 'Card (Credit/Debit)', true, 'Card txn / approval code'),
  PaymentMethod('upi', 'UPI', true, 'UPI transaction ID / UTR'),
  PaymentMethod('cheque', 'Cheque', true, 'Cheque number + bank'),
  PaymentMethod('online', 'Online (Razorpay via WhatsApp)', false, ''),
];

// ============================================================
//  DONATIONS (all 80G eligible) — from payments.py
// ============================================================

class DonationOption {
  final String id;
  final String name;
  final int amount; // 0 = donor-defined amount
  final String category;
  final String description;
  const DonationOption(this.id, this.name, this.amount, this.category, this.description);

  bool get isCustomAmount => amount == 0;
}

const Map<String, String> kDonationCategories = {
  'general': 'General Donation',
  'corpus_fund_donation': 'Corpus Fund Donations',
  'corpus_fund_receipt': 'Corpus Fund Receipt',
};

const List<DonationOption> kDonationOptions = [
  // General
  DonationOption('general', 'General Donation', 0, 'general', 'Donate any amount of your choosing'),
  // Corpus Fund Donations
  DonationOption('room_construction', 'Room Construction', 500000, 'corpus_fund_donation', 'Sponsor construction of a room'),
  DonationOption('bhudanam', 'Bhudanam (Land Donation)', 100000, 'corpus_fund_donation', 'Contribution towards land'),
  // Corpus Fund Receipt
  DonationOption('one_day_annadanam', 'One Day Annadhanam', 2000, 'corpus_fund_receipt', 'Sponsor one day of Annadanam'),
  DonationOption('five_day_annadanam', 'Five Day Annadhanam', 15000, 'corpus_fund_receipt', 'Sponsor five days of Annadanam'),
  DonationOption('nityannadanam', 'Nityannadanam', 30000, 'corpus_fund_receipt', 'Perpetual daily Annadanam'),
  DonationOption('marriage_day', 'Marriage Day', 3000, 'corpus_fund_receipt', 'Annadanam on your marriage day'),
  DonationOption('birthday', 'Birthday', 2000, 'corpus_fund_receipt', 'Annadanam on your birthday'),
  DonationOption('special_occasion', 'Special Occasion', 6000, 'corpus_fund_receipt', 'Annadanam for a special occasion'),
  DonationOption('maharaja_poshakulu', 'Maharaja Poshakulu', 100000, 'corpus_fund_receipt', 'Maharaja patron sponsorship'),
  DonationOption('budhana_poshakulu', 'Budhana Poshakulu', 10000, 'corpus_fund_receipt', 'Budhana patron sponsorship'),
  DonationOption('vedanidhi', 'Vedanidhi', 5000, 'corpus_fund_receipt', 'Support Vedic scholars / education'),
  DonationOption('gonidhi', 'Gonidhi (Gau Seva)', 5000, 'corpus_fund_receipt', 'Cow protection contribution'),
];

/// Donation options grouped by category id.
Map<String, List<DonationOption>> get kDonationsByCategory {
  final out = <String, List<DonationOption>>{};
  for (final c in kDonationCategories.keys) {
    out[c] = kDonationOptions.where((o) => o.category == c).toList();
  }
  return out;
}
