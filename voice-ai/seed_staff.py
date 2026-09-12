"""
Seed staff accounts for Karivena Satram PMS.

Provisions:
  - 1 Super Admin
  - 3 Admins
  - 5 Supervisors  (adjust SUPERVISOR_COUNT as needed)

Each account gets a strong random password. The plaintext credentials are
written ONCE to `staff_credentials.txt` (gitignored) so you can distribute them
securely, then deleted. Only salted PBKDF2 hashes are stored in Firestore.

Run:  py seed_staff.py            (creates accounts, keeps existing)
      py seed_staff.py --reset    (resets passwords for existing accounts too)

NOTE on Firebase Auth: these records live in the Firestore `users` collection
(email -> {role, name, password_hash, active}). The app/dashboard log in via
roles.authenticate(). If you also want Firebase Auth (for the Flutter app's
FirebaseAuth login), create matching users in the Firebase console / Admin SDK
with the SAME emails + passwords printed below.
"""

import sys
import os
import secrets
import string

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Initialise Firebase FIRST so created users persist to Firestore.
from app.firebase_store import init_firebase, is_firebase_active
init_firebase()

from app import roles

SUPERVISOR_COUNT = 5

# email, display name, role
STAFF = [
    ("superadmin@karivena.org", "Super Administrator", "super_admin"),
    ("admin1@karivena.org", "Admin One", "admin"),
    ("admin2@karivena.org", "Admin Two", "admin"),
    ("admin3@karivena.org", "Admin Three", "admin"),
]
for i in range(1, SUPERVISOR_COUNT + 1):
    STAFF.append((f"supervisor{i}@karivena.org", f"Supervisor {i}", "supervisor"))


def gen_password(n: int = 12) -> str:
    """Readable but strong password: letters+digits+one symbol."""
    alphabet = string.ascii_letters + string.digits
    pwd = "".join(secrets.choice(alphabet) for _ in range(n - 2))
    return pwd + secrets.choice("23456789") + secrets.choice("@#$%&*")


def main():
    reset = "--reset" in sys.argv
    lines = []
    created, updated, skipped = 0, 0, 0

    for email, name, role in STAFF:
        existing = roles.get_user(email)
        password = gen_password()

        if existing and not reset:
            skipped += 1
            print(f"  [skip] {email} already exists (use --reset to set new password)")
            continue

        if existing and reset:
            roles.assign_role(email, role)  # ensure role correct
            res = roles.set_password(email, password)
            fb = res.get("firebase_auth", {}).get("success")
            updated += 1
            print(f"  [reset] {email} ({role}) | firebase_auth={fb}")
        else:
            r = roles.create_user(email=email, name=name, role=role,
                                  created_by="seed_staff", password=password)
            if not r.get("success"):
                print(f"  [FAIL] {email}: {r.get('error')}")
                continue
            fb = r.get("firebase_auth", {})
            note = "ok" if fb.get("success") else f"NO ({fb.get('error')})"
            created += 1
            print(f"  [created] {email} ({role}) | firebase_auth={note}")

        lines.append(f"{role:12} | {email:28} | {password}")

    print(f"\nSummary: {created} created, {updated} reset, {skipped} skipped")

    if lines:
        header = (
            "Karivena Satram — Staff Login Credentials\n"
            "==========================================\n"
            "KEEP THIS FILE SECURE. Delete after distributing.\n"
            "These accounts work in BOTH the Flutter PMS (Firebase Auth) and the\n"
            "Voice-AI backend (verifies via Firebase Auth, PBKDF2 fallback).\n\n"
            f"{'ROLE':12} | {'EMAIL':28} | PASSWORD\n"
            f"{'-'*12}-+-{'-'*28}-+-{'-'*14}\n"
        )
        with open("staff_credentials.txt", "w", encoding="utf-8") as f:
            f.write(header + "\n".join(lines) + "\n")
        print("\nCredentials written to: staff_credentials.txt (gitignored)")
        print("Distribute securely, then delete the file.")


if __name__ == "__main__":
    main()
