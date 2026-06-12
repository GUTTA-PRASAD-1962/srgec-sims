"""pages/common_account.py — Change Password"""
import streamlit as st
import hashlib
from db.connection import execute as _ex, fetchone as _fo
from utils.auth import current_user


def show():
    user = current_user()
    uid  = user.get("user_id")

    st.markdown(f"**Logged in as:** {user.get('full_name','')} ({user.get('username','')})")
    st.markdown(f"**Department:** {user.get('dept_name','—')}")
    st.markdown(f"**Last Login:** {str(user.get('last_login',''))[:16]}")
    st.divider()

    st.subheader("🔑 Change Password")
    with st.form("change_pwd_form"):
        old_p = st.text_input("Current Password *", type="password")
        new_p = st.text_input("New Password *",     type="password")
        cnf_p = st.text_input("Confirm New Password *", type="password")
        submitted = st.form_submit_button("Change Password", type="primary")

    if submitted:
        if not all([old_p, new_p, cnf_p]):
            st.error("All fields are required.")
        elif new_p != cnf_p:
            st.error("New passwords do not match.")
        elif len(new_p) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            u = _fo("SELECT * FROM tbl_users WHERE user_id=? AND password_hash=?",
                    (uid, hashlib.sha256(old_p.encode()).hexdigest()))
            if not u:
                st.error("Current password is incorrect.")
            else:
                _ex("UPDATE tbl_users SET password_hash=? WHERE user_id=?",
                    (hashlib.sha256(new_p.encode()).hexdigest(), uid))
                st.success("Password changed successfully. Please log in again.")
