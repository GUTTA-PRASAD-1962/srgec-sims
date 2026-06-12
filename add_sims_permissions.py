"""
add_sims_permissions.py — one-time migration for SRGEC-SIMS
Adds tbl_sims_role_permissions table.
Run once: python add_sims_permissions.py
"""
import sqlite3
from pathlib import Path

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "db/sims_data.db"

conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS tbl_sims_role_permissions (
    perm_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    module_code TEXT NOT NULL,
    role_name   TEXT NOT NULL,
    sub_module  TEXT NOT NULL,
    can_view    INTEGER DEFAULT 0,
    can_insert  INTEGER DEFAULT 0,
    can_update  INTEGER DEFAULT 0,
    can_delete  INTEGER DEFAULT 0,
    updated_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(module_code, role_name, sub_module)
)
""")
conn.commit()
conn.close()
print("tbl_sims_role_permissions created.")
print("Open any module → Administration → Role & Privileges")
print("Click 'Apply All Default Permissions' to set up access.")
