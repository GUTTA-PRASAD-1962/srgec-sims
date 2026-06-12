"""
add_role_privileges.py — one-time migration to add tbl_role_privileges
Run once from C:\SRGEC_SIMS: python add_role_privileges.py
"""
import sqlite3
from pathlib import Path

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "db/sims_data.db"

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS tbl_role_privileges (
        priv_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id  INTEGER NOT NULL,
        role_name  TEXT NOT NULL,
        sub_module TEXT NOT NULL,
        privilege  TEXT NOT NULL
            CHECK(privilege IN ('VIEW','ADD','EDIT','DELETE','APPROVE')),
        is_allowed INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(module_id, role_name, sub_module, privilege)
    )
""")
conn.commit()
conn.close()
print("tbl_role_privileges created successfully.")
print("Restart Streamlit now.")
