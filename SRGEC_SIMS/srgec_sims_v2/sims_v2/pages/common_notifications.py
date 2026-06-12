"""pages/common_notifications.py"""
import streamlit as st
from utils.auth import current_user
from db.connection import fetchall as _fa, execute as _ex, get_conn

def show():
    user = current_user()
    if "common_notifications" == "common_notifications":
        _notifications(user)
    else:
        _change_password(user)

def _notifications(user):
    st.title("Notifications")
    uid = user.get("user_id")
    rows = [dict(r) for r in _fa("""
        SELECT n.*, u.full_name AS from_name
        FROM tbl_notifications n
        LEFT JOIN tbl_users u ON u.user_id=n.from_user_id
        WHERE n.to_user_id=? ORDER BY n.created_at DESC LIMIT 50
    """,(uid,))]
    unread = [r for r in rows if not r["is_read"]]
    if unread:
        st.warning(f"{len(unread)} unread notification(s)")
        if st.button("Mark all read"):
            _ex("UPDATE tbl_notifications SET is_read=1 WHERE to_user_id=?",(uid,)); st.rerun()
    if not rows: st.info("No notifications."); return
    for n in rows:
        icon = "🔔" if not n["is_read"] else "✅"
        with st.expander(f"{icon} {n['title']} — {str(n.get('created_at',''))[:16]}"):
            st.markdown(n.get("message",""))
            if n.get("from_name"): st.caption(f"From: {n['from_name']}")
            if not n["is_read"]:
                if st.button("Mark read", key=f"mr_{n['notif_id']}"):
                    _ex("UPDATE tbl_notifications SET is_read=1 WHERE notif_id=?",(n["notif_id"],)); st.rerun()

def _change_password(user):
    st.title("Change Password")
    import hashlib
    old_p = st.text_input("Current Password", type="password", key="cp_old")
    new_p = st.text_input("New Password",     type="password", key="cp_new")
    cnf_p = st.text_input("Confirm New",      type="password", key="cp_cnf")
    if st.button("Change Password", type="primary", key="cp_save"):
        if not all([old_p,new_p,cnf_p]): st.error("All fields required."); return
        if new_p != cnf_p: st.error("Passwords do not match."); return
        if len(new_p) < 6: st.error("Minimum 6 characters."); return
        from db.connection import fetchone
        u = fetchone("SELECT * FROM tbl_users WHERE user_id=? AND password_hash=?",
                     (user["user_id"], hashlib.sha256(old_p.encode()).hexdigest()))
        if not u: st.error("Current password incorrect."); return
        _ex("UPDATE tbl_users SET password_hash=? WHERE user_id=?",
            (hashlib.sha256(new_p.encode()).hexdigest(), user["user_id"]))
        st.success("Password changed successfully.")
