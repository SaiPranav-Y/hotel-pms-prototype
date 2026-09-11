import 'dart:convert';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/services.dart';

import '../models/app_user.dart';

/// Exception thrown for authentication / authorization failures.
class AuthException implements Exception {
  final String message;
  const AuthException(this.message);
  @override
  String toString() => message;
}

/// Handles Firebase Authentication and resolves the staff [AppUser] (with role)
/// from the Firestore `users` collection (keyed by lowercased email — matching
/// the backend `roles.py` convention).
///
/// For local testing, a JSON file (`assets/test_credentials.json`) is checked
/// first. If the entered email/password match a test user, an [AppUser] is
/// returned directly, bypassing Firebase. This allows developers to log in
/// without needing real credentials in the Firebase project.
class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  /// Cached list of test users loaded from `assets/test_credentials.json`.
  List<AppUser>? _testUsers;

  /// Emits the current Firebase user (or null) on auth state changes.
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  User? get currentFirebaseUser => _auth.currentUser;

  /// Sign in with email + password, then load the staff profile + role.
  ///
  /// First checks the bundled test credentials JSON. If a match is found,
  /// returns an [AppUser] immediately. Otherwise falls back to Firebase Auth.
  Future<AppUser> signIn(String email, String password) async {
    final trimmed = email.trim().toLowerCase();

    // Check test credentials first.
    final testUser = await _findTestUser(trimmed, password);
    if (testUser != null) {
      return testUser;
    }

    try {
      final cred = await _auth.signInWithEmailAndPassword(
        email: trimmed,
        password: password,
      );
      final user = cred.user;
      if (user == null) {
        throw const AuthException('Sign-in failed. Please try again.');
      }
      return await loadAppUser(user);
    } on FirebaseAuthException catch (e) {
      throw AuthException(_friendlyError(e.code));
    }
  }

  /// Loads the test users from `assets/test_credentials.json` (cached).
  Future<List<AppUser>> _loadTestUsers() async {
    if (_testUsers != null) return _testUsers!;

    final jsonString = await rootBundle.loadString('assets/test_credentials.json');
    final json = jsonDecode(jsonString) as Map<String, dynamic>;
    final users = json['test_users'] as List<dynamic>;

    _testUsers = users.map((u) {
      final data = u as Map<String, dynamic>;
      return AppUser(
        uid: 'test-${data['email']}',
        email: data['email'] as String,
        name: data['name'] as String,
        role: StaffRole.fromString(data['role'] as String?),
        active: data['active'] as bool? ?? true,
      );
    }).toList();

    return _testUsers!;
  }

  /// Looks up a test user by email and password.
  Future<AppUser?> _findTestUser(String email, String password) async {
    final users = await _loadTestUsers();
    for (final u in users) {
      if (u.email.toLowerCase() == email) {
        // The password is stored in JSON but we cannot read it from AppUser.
        // We verify against the JSON file directly.
        final jsonString = await rootBundle.loadString('assets/test_credentials.json');
        final json = jsonDecode(jsonString) as Map<String, dynamic>;
        final testUsers = json['test_users'] as List<dynamic>;
        for (final testUser in testUsers) {
          final data = testUser as Map<String, dynamic>;
          if (data['email'] == u.email && data['password'] == password) {
            return u;
          }
        }
      }
    }
    return null;
  }

  /// Load the staff profile + role for an authenticated Firebase user.
  Future<AppUser> loadAppUser(User user) async {
    final email = (user.email ?? '').toLowerCase();
    final doc = await _firestore.collection('users').doc(email).get();

    if (!doc.exists) {
      // No staff record — deny access (staff must be provisioned by super-admin).
      await signOut();
      throw const AuthException(
        'No staff profile found for this account. Contact your administrator.',
      );
    }

    final data = doc.data() as Map<String, dynamic>;
    final appUser = AppUser.fromMap(user.uid, email, data);

    if (!appUser.active) {
      await signOut();
      throw const AuthException('Your account is inactive. Contact your administrator.');
    }
    return appUser;
  }

  Future<void> signOut() => _auth.signOut();

  String _friendlyError(String code) {
    switch (code) {
      case 'invalid-email':
        return 'That email address looks invalid.';
      case 'user-disabled':
        return 'This account has been disabled.';
      case 'user-not-found':
      case 'wrong-password':
      case 'invalid-credential':
        return 'Incorrect email or password.';
      case 'too-many-requests':
        return 'Too many attempts. Please wait and try again.';
      default:
        return 'Sign-in failed ($code).';
    }
  }
}
