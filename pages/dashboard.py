"""pages/dashboard.py — SIMS Module Selection Portal"""
import streamlit as st
from db.connection import fetchall as _fa, fetchone as _fo
from utils.auth import current_user
from config import MODULES


def show():
    user  = current_user()
    is_sa = user.get("is_super_admin",0)

    st.title("SRGEC — Integrated Inventory & Maintenance System")
    st.markdown("Select a module to manage its inventory, complaints, and maintenance.")

    # Summary
    try:
        total_items = dict(_fo("SELECT COUNT(*) c FROM tbl_items WHERE is_deleted=0") or {"c":0})["c"]
        open_calls  = dict(_fo("SELECT COUNT(*) c FROM tbl_calls WHERE call_status='OPEN'") or {"c":0})["c"]
        users_count = dict(_fo("SELECT COUNT(*) c FROM tbl_users WHERE is_active=1") or {"c":0})["c"]
        m1,m2,m3   = st.columns(3)
        m1.metric("Total Assets (All Modules)", total_items)
        m2.metric("Open Complaints", open_calls)
        m3.metric("Active Users", users_count)
    except Exception: pass

    st.divider()
    st.markdown("### Select Module")

    # Load accessible modules
    if is_sa:
        mods = [dict(r) for r in _fa(
            "SELECT * FROM tbl_modules WHERE is_active=1 ORDER BY sort_order")]
    else:
        mods = [dict(r) for r in _fa("""
            SELECT m.* FROM tbl_modules m
            JOIN tbl_user_module_access a ON a.module_id=m.module_id
            WHERE a.user_id=? AND a.is_active=1 AND m.is_active=1
            ORDER BY m.sort_order
        """,(user.get("user_id"),))]

    if not mods:
        st.warning("No modules assigned. Contact Super Admin."); return

    cols = st.columns(4)
    for idx, mod in enumerate(mods):
        mc   = mod["module_code"]
        info = MODULES.get(mc, {})
        color = mod.get("module_color","#1B4F9A")

        with cols[idx % 4]:
            try:
                mid   = mod["module_id"]
                items = dict(_fo("SELECT COUNT(*) c FROM tbl_items WHERE module_id=? AND is_deleted=0",(mid,)) or {"c":0})["c"]
                calls = dict(_fo("SELECT COUNT(*) c FROM tbl_calls WHERE module_id=? AND call_status='OPEN'",(mid,)) or {"c":0})["c"]
            except: items=0; calls=0

            st.markdown(f"""
            <div style="background:#fff;border:2px solid #E0E0E0;border-radius:12px;
                        padding:14px 10px;text-align:center;margin-bottom:6px;
                        border-top:4px solid {color}">
              <div style="font-size:2rem">{mod['module_icon']}</div>
              <div style="font-weight:800;font-size:0.82rem;color:#0D2B5E;margin:6px 0 2px">
                {mod['module_name']}</div>
              <div style="font-size:0.70rem;color:#666">
                📦 {items} &nbsp;|&nbsp; 🔔 {calls} open</div>
            </div>
            """, unsafe_allow_html=True)

            route_map = {
                "IT":"it","UPS":"ups","ELEC":"elec","CIVIL":"civil",
                "FURN":"furn","STAT":"stat","LCD":"lcd","CCTV":"cctv"
            }
            if st.button(f"Open →", key=f"mod_{mc}", use_container_width=True):
                st.session_state["sims_module"] = mc
                st.session_state["page"] = f"mod_{route_map.get(mc,'it')}"
                st.rerun()

    if is_sa:
        st.divider()
        col1,col2 = st.columns(2)
        if col1.button("⚙️ Super Admin Panel", use_container_width=True, key="dash_sa"):
            st.session_state["page"] = "superadmin"; st.rerun()
