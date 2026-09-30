"""
Role-Based Access Control (RBAC) — 3 roles for the Karivena PMS.

Roles (ascending privilege):
  1. supervisor  — manual walk-in bookings, generate invoices at checkout
  2. admin       — everything supervisor + edit room rates + set seva amounts
  3. super_admin — everything + manage users/roles

Users live in Firestore 'users' collection:
  { "email": "...", "role": "supervisor|admin|super_admin", "name": "...", "active": true }

Auth credentials will be provided later. For now this provides:
  - permission checks (has_permission)
  - user lookup / role assignment
  - a require_role() dependency helper for FastAPI routes
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# === PASSWORD HASHING (stdlib pbkdf2 — no external deps) ===

def hash_password(password: str, salt: str = "") -> str:
    """Return a salted PBKDF2-SHA256 hash string: pbkdf2$<salt>$<hexdigest>."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             salt.encode("utf-8"), 120_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a plaintext password against a stored pbkdf2 hash."""
    try:
        scheme, salt, _ = stored.split("$", 2)
        if scheme != "pbkdf2":
            return False
        return hmac.compare_digest(hash_password(password, salt), stored)
    except Exception:
        return False

# === ROLE DEFINITIONS ===

ROLES = ["supervisor", "admin", "super_admin"]

# Permission matrix — what each role can do
PERMISSIONS = {
    "supervisor": {
        "walk_in_booking",       # create manual bookings for walk-in customers
        "view_bookings",
        "view_calls",
        "generate_invoice",      # generate invoice at checkout / end of stay
        "trigger_checkout",      # start WhatsApp checkout
        "view_customers",
        "view_availability",
    },
    "admin": {
        # inherits all supervisor perms +
        "walk_in_booking", "view_bookings", "view_calls", "generate_invoice",
        "trigger_checkout", "view_customers", "view_availability",
        "edit_rates",            # edit room rates (type x location x season)
        "set_seva_amounts",      # define seva donation amounts
        "edit_gotrams",          # manage approved gotram list
        "view_analytics",
        "manage_campaigns",
        "configure_escalation",
    },
    "super_admin": {
        # full control — computed as ALL permissions below
    },
}

# All known permissions (super_admin gets everything)
ALL_PERMISSIONS = {
    "walk_in_booking", "view_bookings", "view_calls", "generate_invoice",
    "trigger_checkout", "view_customers", "view_availability",
    "edit_rates", "set_seva_amounts", "edit_gotrams", "view_analytics",
    "manage_campaigns", "configure_escalation",
    "manage_users",          # create/edit/delete staff accounts
    "assign_roles",          # change a user's role
    "delete_bookings",
    "system_config",
}
PERMISSIONS["super_admin"] = set(ALL_PERMISSIONS)


# In-memory user cache (synced with Firestore)
_users: dict[str, dict] = {}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    if role not in PERMISSIONS:
        return False
    return permission in PERMISSIONS[role]


def get_role_permissions(role: str) -> list[str]:
    """Get all permissions for a role."""
    return sorted(PERMISSIONS.get(role, set()))


def get_all_roles() -> list[dict]:
    """Return roles with their permission lists (for UI)."""
    return [
        {"role": r, "permissions": get_role_permissions(r), "permission_count": len(PERMISSIONS[r])}
        for r in ROLES
    ]


# === FIREBASE AUTH BRIDGE ===
# The Flutter PMS authenticates via Firebase Auth; the Voice-AI backend reads
# roles from the Firestore `users` collection. To make ONE account work in BOTH
# systems, we provision a Firebase Auth user (credentials) AND a Firestore doc
# (role/profile) with the same email + password.

def upsert_firebase_auth_user(email: str, password: str, name: str = "") -> dict:
    """
    Create or update a Firebase Auth user with the given email + password.
    Returns {"success": bool, "uid": str|None, "created": bool, "error": str|None}.
    Requires the Firebase Admin SDK to be initialised (firebase-key.json).
    """
    email = email.lower().strip()
    try:
        from app.firebase_store import is_firebase_active
        if not is_firebase_active():
            return {"success": False, "uid": None, "created": False,
                    "error": "Firebase not active"}
        from firebase_admin import auth as fb_auth
        try:
            existing = fb_auth.get_user_by_email(email)
            # Update password/name on the existing Auth account
            fb_auth.update_user(existing.uid, password=password,
                                display_name=name or existing.display_name)
            return {"success": True, "uid": existing.uid, "created": False, "error": None}
        except fb_auth.UserNotFoundError:
            created = fb_auth.create_user(email=email, password=password,
                                          display_name=name or None,
                                          email_verified=True)
            return {"success": True, "uid": created.uid, "created": True, "error": None}
    except Exception as e:
        logger.error(f"Firebase Auth upsert failed for {email}: {e}")
        return {"success": False, "uid": None, "created": False, "error": str(e)}


# === USER MANAGEMENT ===

def create_user(email: str, name: str, role: str, created_by: str = "system",
                password: str = "", firebase_auth: bool = True) -> dict:
    """
    Create a staff user with a role (and optional login password).

    When `password` is given and `firebase_auth` is True, ALSO provisions a
    Firebase Auth account with the same email + password — so the SAME account
    logs into both the Flutter PMS (Firebase Auth) and the Voice-AI backend
    (which now verifies against Firebase Auth too). A PBKDF2 hash is still stored
    as a local/offline fallback.
    """
    if role not in ROLES:
        return {"success": False, "error": f"Invalid role. Use: {ROLES}"}

    email = email.lower().strip()
    user = {
        "email": email,
        "name": name,
        "role": role,
        "active": True,
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
    }
    if password:
        user["password_hash"] = hash_password(password)
        user["auth_provider"] = "firebase"  # credentials verified via Firebase Auth

    # Bridge: create the matching Firebase Auth account
    auth_result = {"success": False, "created": False, "error": "skipped"}
    if password and firebase_auth:
        auth_result = upsert_firebase_auth_user(email, password, name)
        if auth_result.get("uid"):
            user["firebase_uid"] = auth_result["uid"]

    _users[email] = user

    # Firestore sync (role/profile source of truth)
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("users").document(email).set(user)
    except Exception:
        pass

    logger.info(f"User created: {email} ({role}) | firebase_auth={auth_result.get('success')}")
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return {"success": True, "user": safe, "firebase_auth": auth_result}


def set_password(email: str, password: str, firebase_auth: bool = True) -> dict:
    """Set / reset a user's login password in BOTH Firebase Auth and Firestore."""
    email = email.lower().strip()
    u = get_user(email)
    if not u:
        return {"success": False, "error": "User not found"}
    u["password_hash"] = hash_password(password)
    _users[email] = u

    # Sync to Firebase Auth so Flutter + Voice-AI stay in step
    auth_result = {"success": False, "error": "skipped"}
    if firebase_auth:
        auth_result = upsert_firebase_auth_user(email, password, u.get("name", ""))
        if auth_result.get("uid"):
            u["firebase_uid"] = auth_result["uid"]

    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            update = {"password_hash": u["password_hash"]}
            if u.get("firebase_uid"):
                update["firebase_uid"] = u["firebase_uid"]
            _db.collection("users").document(email).update(update)
    except Exception:
        pass
    return {"success": True, "firebase_auth": auth_result}


def _verify_firebase_password(email: str, password: str) -> bool | None:
    """
    Verify email + password against Firebase Auth via the Identity Toolkit REST
    API (same credentials the Flutter PMS uses). Returns:
      True  -> verified
      False -> wrong password / disabled
      None  -> could not check (no web API key / network) -> caller falls back
    """
    try:
        from app.config import FIREBASE_WEB_API_KEY
    except Exception:
        FIREBASE_WEB_API_KEY = ""
    if not FIREBASE_WEB_API_KEY:
        return None
    try:
        import httpx
        url = ("https://identitytoolkit.googleapis.com/v1/accounts:"
               f"signInWithPassword?key={FIREBASE_WEB_API_KEY}")
        resp = httpx.post(url, json={
            "email": email, "password": password, "returnSecureToken": True,
        }, timeout=15)
        if resp.status_code == 200:
            return True
        # 400 with INVALID_PASSWORD / EMAIL_NOT_FOUND etc.
        return False
    except Exception as e:
        logger.debug(f"Firebase REST verify unavailable: {e}")
        return None


def authenticate(email: str, password: str) -> dict:
    """
    App-level login for the Voice-AI backend / web dashboard.

    Credential check order (bridge with the Flutter PMS):
      1. Firebase Auth (REST) — the shared source of truth for passwords.
      2. PBKDF2 hash in Firestore — offline / fallback when Firebase Auth
         can't be reached or no web API key is configured.
    Role + profile always come from the Firestore `users` doc.
    """
    email = (email or "").lower().strip()
    u = get_user(email)
    if not u:
        return {"success": False, "error": "Invalid email or password"}
    if not u.get("active", True):
        return {"success": False, "error": "Account is inactive"}

    verified = False
    method = None

    # 1. Firebase Auth (shared with Flutter)
    fb = _verify_firebase_password(email, password)
    if fb is True:
        verified, method = True, "firebase"
    elif fb is False:
        # Firebase reachable and rejected — but still allow PBKDF2 in case the
        # account exists only locally. If a hash exists, check it; else deny.
        pass

    # 2. PBKDF2 fallback
    if not verified:
        stored = u.get("password_hash", "")
        if stored and verify_password(password, stored):
            verified, method = True, "pbkdf2"

    if not verified:
        return {"success": False, "error": "Invalid email or password"}

    return {
        "success": True,
        "email": u["email"],
        "name": u.get("name", ""),
        "role": u.get("role"),
        "permissions": get_role_permissions(u.get("role")),
        "auth_method": method,
    }


def get_user(email: str) -> dict | None:
    """Get a user by email (checks cache, then Firestore)."""
    email = email.lower().strip()
    if email in _users:
        return _users[email]
    # Try Firestore
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            doc = _db.collection("users").document(email).get()
            if doc.exists:
                u = doc.to_dict()
                _users[email] = u
                return u
    except Exception:
        pass
    return None


def get_user_role(email: str) -> str | None:
    """Get a user's role."""
    u = get_user(email)
    return u.get("role") if u else None


def assign_role(email: str, new_role: str) -> dict:
    """Change a user's role (super_admin only — enforced at route level)."""
    if new_role not in ROLES:
        return {"success": False, "error": f"Invalid role. Use: {ROLES}"}
    u = get_user(email)
    if not u:
        return {"success": False, "error": "User not found"}
    u["role"] = new_role
    u["updated_at"] = datetime.now().isoformat()
    _users[email.lower().strip()] = u
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("users").document(email.lower().strip()).update({"role": new_role})
    except Exception:
        pass
    return {"success": True, "user": u}


def get_all_users() -> list[dict]:
    """List all staff users (password hashes stripped)."""
    # Refresh from Firestore
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            for doc in _db.collection("users").stream():
                _users[doc.id] = doc.to_dict()
    except Exception:
        pass
    return [{k: v for k, v in u.items() if k != "password_hash"}
            for u in _users.values()]


def load_users():
    """Load all users from Firestore at startup."""
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            for doc in _db.collection("users").stream():
                _users[doc.id] = doc.to_dict()
            logger.info(f"Loaded {len(_users)} staff users")
    except Exception as e:
        logger.debug(f"User load skipped: {e}")


# === ROUTE GUARD HELPER ===

def check_access(email: str, permission: str) -> tuple[bool, str]:
    """
    Verify a user has a permission. Returns (allowed, reason).
    Used by API routes to gate access.
    """
    if not email:
        return False, "No user identity provided"
    user = get_user(email)
    if not user:
        return False, "User not found"
    if not user.get("active", True):
        return False, "User account is inactive"
    role = user.get("role")
    if has_permission(role, permission):
        return True, "ok"
    return False, f"Role '{role}' lacks permission '{permission}'"


# Load on import
load_users()
