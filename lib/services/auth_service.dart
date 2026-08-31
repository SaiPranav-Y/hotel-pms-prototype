import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

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
class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  /// Emits the current Firebase user (or null) on auth state changes.
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  User? get currentFirebaseUser => _auth.currentUser;

  /// Sign in with email + password, then load the staff profile + role.
  Future<AppUser> signIn(String email, String password) async {
    final trimmed = email.trim().toLowerCase();
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
