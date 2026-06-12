"""
reset_password.py — Reset a user's password in SRGEC-SIMS
Run from C:\\SRGEC_SIMS: python reset_password.py
"""
import sqlite3, hashlib

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "db/sims_data.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

username = input("Enter username to reset: ").strip()
new_pwd  = input("Enter new password: ").strip()

user = conn.execute("SELECT user_id, full_name FROM tbl_users WHERE username=?", (username,)).fetchone()
if not user:
    print(f"User '{username}' not found.")
else:
    user = dict(user)
    pwd_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
    conn.execute("UPDATE tbl_users SET password_hash=? WHERE user_id=?", (pwd_hash, user["user_id"]))
    conn.commit()
    print(f"Password updated for {user['full_name']} ({username}).")

conn.close()
