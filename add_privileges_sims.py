"""
add_privileges_sims.py — one-time migration for SRGEC-SIMS
Adds tbl_role_module_privileges and tbl_user_module_privileges tables.
Run once: python add_privileges_sims.py
"""
import sqlite3
from pathlib import Path

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "db/sims_data.db"

conn = sqlite3.connect(DB_PATH)
conn.executescript("""
CREATE TABLE IF NOT EXISTS tbl_role_module_privileges (
    rpriv_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    module_code TEXT NOT NULL,
    role_name   TEXT NOT NULL,
    sub_module  TEXT NOT NULL,
    can_view    INTEGER DEFAULT 1,
    can_add     INTEGER DEFAULT 0,
    can_edit    INTEGER DEFAULT 0,
    can_delete  INTEGER DEFAULT 0,
    can_approve INTEGER DEFAULT 0,
    is_visible  INTEGER DEFAULT 1,
    updated_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(module_code, role_name, sub_module)
);

CREATE TABLE IF NOT EXISTS tbl_user_module_privileges (
    upriv_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    module_code TEXT NOT NULL,
    sub_module  TEXT NOT NULL,
    can_view    INTEGER DEFAULT 1,
    can_add     INTEGER DEFAULT 0,
    can_edit    INTEGER DEFAULT 0,
    can_delete  INTEGER DEFAULT 0,
    can_approve INTEGER DEFAULT 0,
    is_visible  INTEGER DEFAULT 1,
    granted_by  INTEGER,
    updated_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(user_id, module_code, sub_module)
);
""")
conn.commit()
conn.close()
print("Tables created successfully.")
print("Now open SRGEC-SIMS → any module → Administration → Role & Privileges")
print("Click 'Apply Default Role Privileges' to set up default access.")
