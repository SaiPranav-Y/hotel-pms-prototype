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


# === USER MANAGEMENT ===

def create_user(email: str, name: str, role: str, created_by: str = "system",
                password: str = "") -> dict:
    """Create a staff user with a role (and optional login password)."""
    if role not in ROLES:
        return {"success": False, "error": f"Invalid role. Use: {ROLES}"}

    user = {
        "email": email.lower().strip(),
        "name": name,
        "role": role,
        "active": True,
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
    }
    if password:
        user["password_hash"] = hash_password(password)
    _users[user["email"]] = user

    # Firebase sync
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("users").document(user["email"]).set(user)
    except Exception:
        pass

    logger.info(f"User created: {email} ({role})")
    # Never return the hash to callers
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return {"success": True, "user": safe}


def set_password(email: str, password: str) -> dict:
    """Set / reset a user's login password."""
    u = get_user(email)
    if not u:
        return {"success": False, "error": "User not found"}
    u["password_hash"] = hash_password(password)
    _users[email.lower().strip()] = u
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("users").document(email.lower().strip()).update(
                {"password_hash": u["password_hash"]})
    except Exception:
        pass
    return {"success": True}


def authenticate(email: str, password: str) -> dict:
    """
    App-level login: verify email + password against the stored hash.
    (Firebase Auth can be used instead in the Flutter app; this supports the
    web dashboard / API and local testing.)
    """
    u = get_user(email)
    if not u:
        return {"success": False, "error": "Invalid email or password"}
    if not u.get("active", True):
        return {"success": False, "error": "Account is inactive"}
    stored = u.get("password_hash", "")
    if not stored or not verify_password(password, stored):
        return {"success": False, "error": "Invalid email or password"}
    return {
        "success": True,
        "email": u["email"],
        "name": u.get("name", ""),
        "role": u.get("role"),
        "permissions": get_role_permissions(u.get("role")),
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
