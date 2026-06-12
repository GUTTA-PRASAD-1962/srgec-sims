"""
list_users.py — List all users in SRGEC-SIMS database
Run from C:\\SRGEC_SIMS: python list_users.py
"""
import sqlite3
from pathlib import Path

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "db/sims_data.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print(f"{'ID':<4} {'Username':<20} {'Full Name':<25} {'Emp ID':<15} {'SuperAdmin':<10} {'Active'}")
print("-" * 85)

users = conn.execute("""
    SELECT user_id, username, full_name, employee_id, is_super_admin, is_active
    FROM tbl_users ORDER BY user_id
""").fetchall()

for u in users:
    u = dict(u)
    print(f"{u['user_id']:<4} {u['username']:<20} {u['full_name']:<25} "
          f"{u['employee_id']:<15} {'Yes' if u['is_super_admin'] else 'No':<10} "
          f"{'Yes' if u['is_active'] else 'No'}")

print("\n--- Module Access ---")
print(f"{'User':<20} {'Module':<10} {'Role'}")
print("-" * 45)
access = conn.execute("""
    SELECT u.username, m.module_code, a.role_name
    FROM tbl_user_module_access a
    JOIN tbl_users u ON u.user_id=a.user_id
    JOIN tbl_modules m ON m.module_id=a.module_id
    WHERE a.is_active=1
    ORDER BY u.username, m.module_code
""").fetchall()

for a in access:
    a = dict(a)
    print(f"{a['username']:<20} {a['module_code']:<10} {a['role_name']}")

conn.close()

print("\nNote: Passwords are stored as SHA-256 hashes and cannot be retrieved as plain text.")
print("To reset a password, use SuperAdmin Panel -> Users & Access -> create new, or use reset_password.py")
