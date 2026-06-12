"""pages/common_notifications.py — Notifications matching IT-IIMS"""
import streamlit as st
import pandas as pd
from db.connection import fetchall as _fa, execute as _ex, fetchone as _fo
from utils.auth import current_user


def show():
    user = current_user()
    uid  = user.get("user_id")
    if not uid: st.error("Not logged in."); return

    # Unread count
    unread = dict(_fo("SELECT COUNT(*) c FROM tbl_notifications WHERE to_user_id=? AND is_read=0",(uid,)) or {"c":0})["c"]

    c1,c2 = st.columns([3,1])
    c1.markdown(f"**{unread} unread** notification(s)")
    if unread and c2.button("✅ Mark All Read", key="notif_mark_all"):
        _ex("UPDATE tbl_notifications SET is_read=1 WHERE to_user_id=?",(uid,))
        st.rerun()

    # Filter tabs
    tab1,tab2 = st.tabs(["🔔 Unread","📋 All Notifications"])

    with tab1:
        rows = [dict(r) for r in _fa("""
            SELECT n.*, m.module_name, u.full_name AS from_name
            FROM tbl_notifications n
            LEFT JOIN tbl_modules m ON m.module_id=n.module_id
            LEFT JOIN tbl_users u ON u.user_id=n.from_user_id
            WHERE n.to_user_id=? AND n.is_read=0
            ORDER BY n.created_at DESC
        """,(uid,))]
        if not rows:
            st.success("No unread notifications.")
        for r in rows:
            priority_icon = "🔴" if r.get("priority")=="HIGH" else "🟡" if r.get("priority")=="URGENT" else "🔵"
            with st.expander(
                f"{priority_icon} {r['title']} — {str(r.get('created_at',''))[:16]}",
                expanded=True
            ):
                if r.get("message"): st.markdown(r["message"])
                if r.get("module_name"): st.caption(f"Module: {r['module_name']}")
                if r.get("from_name"):   st.caption(f"From: {r['from_name']}")
                if st.button("Mark Read", key=f"nr_{r['notif_id']}"):
                    _ex("UPDATE tbl_notifications SET is_read=1 WHERE notif_id=?",(r["notif_id"],))
                    st.rerun()

    with tab2:
        rows = [dict(r) for r in _fa("""
            SELECT n.*, m.module_name, u.full_name AS from_name
            FROM tbl_notifications n
            LEFT JOIN tbl_modules m ON m.module_id=n.module_id
            LEFT JOIN tbl_users u ON u.user_id=n.from_user_id
            WHERE n.to_user_id=?
            ORDER BY n.created_at DESC LIMIT 100
        """,(uid,))]
        if not rows: st.info("No notifications."); return
        df = pd.DataFrame([{
            "Time":str(r.get("created_at",""))[:16],
            "Title":r["title"],
            "Message":(r.get("message","") or "")[:80],
            "Module":r.get("module_name","—"),
            "From":r.get("from_name","—"),
            "Priority":r.get("priority","NORMAL"),
            "Read":"Yes" if r["is_read"] else "No",
        } for r in rows])
        st.dataframe(df, use_container_width=True, hide_index=True)
