import 'dart:convert';

import 'package:http/http.dart' as http;

/// Thin client for the Karivena voice-ai FastAPI backend.
///
/// Base URL is configurable at build/run time:
///   flutter run --dart-define=API_BASE_URL=http://localhost:8000
/// Defaults to http://localhost:8000 for local development.
///
/// Permission-gated routes expect the acting user's email in the
/// `X-User-Email` header (set [actingEmail]).
class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Email of the signed-in staff user (sent as X-User-Email for RBAC).
  final String? actingEmail;

  const ApiService({this.actingEmail});

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (actingEmail != null && actingEmail!.isNotEmpty)
          'X-User-Email': actingEmail!,
      };

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  /// Create a donation payment link. Returns the payment record (incl. `link`).
  /// [sevaId] selects a predefined seva; [customAmount] overrides / sets amount
  /// (required for General donation).
  Future<Map<String, dynamic>> createDonation({
    required String customerName,
    required String customerPhone,
    required String sevaId,
    int customAmount = 0,
    bool sendWhatsapp = false,
  }) async {
    // Seva-based donation (predefined or custom amount, 80G eligible)
    final resp = await http
        .post(
          _uri('/api/payments/seva'),
          headers: _headers,
          body: jsonEncode({
            'customer_name': customerName,
            'customer_phone': customerPhone,
            'seva_id': sevaId,
            'custom_amount': customAmount,
          }),
        )
        .timeout(const Duration(seconds: 20));
    return _decode(resp);
  }

  /// Fetch grouped donation options from the backend (source of truth).
  Future<Map<String, dynamic>> getDonationsGrouped() async {
    final resp = await http
        .get(_uri('/api/donations/grouped'), headers: _headers)
        .timeout(const Duration(seconds: 15));
    return _decode(resp);
  }

  /// List accepted payment methods.
  Future<Map<String, dynamic>> getPaymentMethods() async {
    final resp = await http
        .get(_uri('/api/payments/methods'), headers: _headers)
        .timeout(const Duration(seconds: 15));
    return _decode(resp);
  }

  /// Mark a payment paid (fires receipt + 80G automation on the backend).
  Future<Map<String, dynamic>> markPaid(String paymentId) async {
    final resp = await http
        .post(_uri('/api/payments/$paymentId/paid'), headers: _headers)
        .timeout(const Duration(seconds: 20));
    return _decode(resp);
  }

  Map<String, dynamic> _decode(http.Response resp) {
    try {
      final data = jsonDecode(resp.body);
      if (data is Map<String, dynamic>) return data;
      return {'success': false, 'error': 'Unexpected response'};
    } catch (_) {
      return {
        'success': false,
        'error': 'HTTP ${resp.statusCode}',
      };
    }
  }
}
