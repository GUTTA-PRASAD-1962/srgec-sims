"""utils/auth.py"""
import streamlit as st
import hashlib
from db.connection import fetchone, execute
from datetime import datetime


def h(pwd): return hashlib.sha256(pwd.encode()).hexdigest()


def is_logged_in():
    return bool(st.session_state.get("sims_user"))


def current_user():
    return st.session_state.get("sims_user", {})


def current_module():
    return st.session_state.get("sims_module", "")


def do_login(username, password):
    if not username or not password:
        return False, "Enter username and password."
    user = fetchone("""
        SELECT u.*, d.dept_name, d.dept_code
        FROM tbl_users u
        LEFT JOIN tbl_departments d ON d.dept_id = u.dept_id
        WHERE u.username=? AND u.password_hash=? AND u.is_active=1
    """, (username.strip(), h(password)))
    if not user:
        return False, "Invalid username or password."
    st.session_state["sims_user"] = dict(user)
    st.session_state["page"] = "dashboard"
    execute("UPDATE tbl_users SET last_login=? WHERE user_id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["user_id"]))
    return True, "OK"


def do_logout():
    st.session_state.clear()
    st.rerun()


def get_user_module_role(module_code):
    user = current_user()
    if user.get("is_super_admin"): return "SuperAdmin"
    row = fetchone("""
        SELECT a.role_name FROM tbl_user_module_access a
        JOIN tbl_modules m ON m.module_id = a.module_id
        WHERE a.user_id=? AND m.module_code=? AND a.is_active=1
    """, (user.get("user_id"), module_code))
    return dict(row)["role_name"] if row else None


def require_module_access(module_code):
    role = get_user_module_role(module_code)
    if not role:
        st.error(f"Access denied — you are not assigned to the {module_code} module.")
        st.stop()
    return role
