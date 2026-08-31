import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../models/app_user.dart';
import '../services/auth_service.dart';
import 'dashboard_shell.dart';
import 'login_view.dart';

/// Decides whether to show the login screen or the role-based dashboard shell,
/// based on Firebase auth state + the resolved staff [AppUser].
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  final AuthService _auth = AuthService();
  AppUser? _appUser;
  bool _resolving = true;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final fbUser = _auth.currentFirebaseUser;
    if (fbUser != null) {
      try {
        final u = await _auth.loadAppUser(fbUser);
        if (mounted) setState(() => _appUser = u);
      } catch (_) {
        // profile missing / inactive — fall through to login
      }
    }
    if (mounted) setState(() => _resolving = false);
  }

  void _onSignedIn(AppUser user) {
    setState(() => _appUser = user);
  }

  Future<void> _onSignOut() async {
    await _auth.signOut();
    setState(() => _appUser = null);
  }

  @override
  Widget build(BuildContext context) {
    if (_resolving) {
      return const Scaffold(
        backgroundColor: Color(0xFFF5F7FA),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    // React to external sign-outs (e.g. token expiry).
    return StreamBuilder<User?>(
      stream: _auth.authStateChanges,
      builder: (context, snapshot) {
        final signedOut = snapshot.connectionState == ConnectionState.active &&
            snapshot.data == null;
        if (signedOut && _appUser != null) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) setState(() => _appUser = null);
          });
        }

        if (_appUser == null) {
          return LoginView(authService: _auth, onSignedIn: _onSignedIn);
        }
        return DashboardShell(user: _appUser!, onSignOut: _onSignOut);
      },
    );
  }
}
