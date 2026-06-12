"""components/header.py — SIMS portal header and sidebar"""
import streamlit as st
from utils.auth import current_user, do_logout, get_user_module_role
from config import APP_TITLE, APP_VERSION, COLLEGE_NAME


def _can_see(user, module_code, sub_module):
    """Check if user can see a sub-module based on privileges."""
    from db.connection import fetchone as _fo
    uid  = user.get("user_id")
    is_sa = user.get("is_super_admin", 0)
    if is_sa: return True

    role = get_user_module_role(module_code)
    if role in ("SuperAdmin", "SysAdmin"): return True

    # User-level override first
    if uid:
        priv = _fo("""
            SELECT is_visible FROM tbl_user_module_privileges
            WHERE user_id=? AND module_code=? AND sub_module=?
        """,(uid, module_code, sub_module))
        if priv is not None:
            return bool(dict(priv)["is_visible"])

    # Role default
    if role:
        priv = _fo("""
            SELECT is_visible FROM tbl_role_module_privileges
            WHERE module_code=? AND role_name=? AND sub_module=?
        """,(module_code, role, sub_module))
        if priv is not None:
            return bool(dict(priv)["is_visible"])

    # No privileges defined — show by default
    return True


def render_header(logged_in=True):
    st.markdown("""
    <style>
    div[data-testid="stSidebarNav"]{display:none!important}
    .block-container{padding-top:0.5rem!important}
    section[data-testid="stSidebar"]{
        min-width:240px!important;max-width:260px!important;
        background:linear-gradient(180deg,#0a1f4e 0%,#0d2b5e 60%,#122d5c 100%)!important}
    section[data-testid="stSidebar"] .stButton>button{
        width:100%;text-align:left;padding:7px 14px;border-radius:6px;
        border:1px solid rgba(255,255,255,0.12);
        background:rgba(255,255,255,0.07)!important;
        color:#FFFFFF!important;font-size:0.81rem;font-weight:600;
        transition:all 0.15s;margin:2px 0}
    section[data-testid="stSidebar"] .stButton>button p{color:#FFFFFF!important}
    section[data-testid="stSidebar"] .stButton>button:hover{
        background:#1B4F9A!important;border-color:#F0A500!important;
        transform:translateX(4px)}
    section[data-testid="stSidebar"] .stButton>button[kind="primary"]{
        background:linear-gradient(90deg,#F0A500,#e09400)!important;
        color:#0D2B5E!important;font-weight:800;border:none}
    section[data-testid="stSidebar"] .stButton>button[kind="primary"] p{
        color:#0D2B5E!important}
    </style>
    """, unsafe_allow_html=True)

    user  = current_user() if logged_in else {}
    name  = user.get("full_name","")
    dept  = user.get("dept_name","") or "All Departments"
    is_sa = user.get("is_super_admin",0)

    badge = ""
    if logged_in and user.get("user_id"):
        try:
            from db.connection import fetchone
            n = dict(fetchone("SELECT COUNT(*) c FROM tbl_notifications WHERE to_user_id=? AND is_read=0",
                              (user["user_id"],)) or {"c":0})["c"]
            if n: badge = f'<span style="background:#dc3545;color:#fff;border-radius:50%;padding:1px 6px;font-size:0.68rem;font-weight:700">{n}</span>'
        except: pass

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D2B5E 0%,#1B4F9A 55%,#2E75B6 100%);
                padding:10px 20px 8px;border-radius:8px;
                border-bottom:4px solid #F0A500;margin-bottom:10px">
      <table width="100%" cellspacing="0" cellpadding="0"><tr>
        <td style="vertical-align:middle">
          <p style="color:#fff;font-size:1.0rem;font-weight:900;margin:0">
            🏛 {COLLEGE_NAME}</p>
          <p style="color:#F0A500;font-size:0.82rem;font-weight:800;margin:2px 0 0 0">
            📋 {APP_TITLE}
            <span style="color:#B8D4F5;font-weight:400;font-size:0.70rem"> ({APP_VERSION})</span>
          </p>
        </td>
        <td style="text-align:right;vertical-align:middle;white-space:nowrap">
          {'<p style="color:#D0E8FF;font-size:0.73rem;margin:0">👤 '+name+' '+ ("⭐" if is_sa else "") +'</p><p style="color:#D0E8FF;font-size:0.73rem;margin:2px 0 0">'+dept+' &nbsp;|&nbsp; 🔔 '+badge+'</p>' if logged_in else ''}
        </td>
      </tr></table>
    </div>
    """, unsafe_allow_html=True)


def render_portal_sidebar():
    """Portal-level sidebar — shown on dashboard/login."""
    user  = current_user()
    is_sa = user.get("is_super_admin",0)

    with st.sidebar:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0D2B5E,#1B4F9A);
                    padding:12px 14px;border-radius:8px;
                    border-bottom:3px solid #F0A500;margin-bottom:14px">
          <p style="color:#F0A500;font-weight:900;font-size:0.85rem;margin:0">
            🏛 SRGEC — SIMS</p>
          <p style="color:#B8D4F5;font-size:0.72rem;margin:3px 0 0 0">{APP_VERSION}</p>
          <hr style="border:none;border-top:1px solid #2E75B6;margin:6px 0"/>
          <p style="color:#fff;font-size:0.78rem;font-weight:700;margin:0">
            👤 {user.get('full_name','')}</p>
          <p style="color:#90CAF9;font-size:0.72rem;margin:2px 0 0 0">
            {user.get('dept_name','') or 'All Departments'}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🏠  Module Portal", type="primary",
                     use_container_width=True, key="sb_portal"):
            st.session_state["page"] = "dashboard"
            st.session_state["sims_module"] = ""
            st.rerun()

        if is_sa:
            st.markdown(
                '<div style="background:linear-gradient(90deg,#0D2B5E,#1B4F9A);'
                'padding:5px 10px;border-radius:5px;margin:8px 0 3px;'
                'border-left:3px solid #F0A500">'
                '<span style="color:#F0A500;font-size:0.75rem;font-weight:800">'
                '⭐ SUPER ADMIN</span></div>',
                unsafe_allow_html=True
            )
            if st.button("⚙️  Super Admin Panel",
                         use_container_width=True, key="sb_sa"):
                st.session_state["page"] = "superadmin"; st.rerun()

        st.markdown(
            '<div style="background:linear-gradient(90deg,#0D2B5E,#1B4F9A);'
            'padding:5px 10px;border-radius:5px;margin:8px 0 3px;'
            'border-left:3px solid #B0BEC5">'
            '<span style="color:#B0BEC5;font-size:0.75rem;font-weight:800">'
            '👤 ACCOUNT</span></div>',
            unsafe_allow_html=True
        )
        if st.button("🔔  Notifications", use_container_width=True, key="sb_notif"):
            st.session_state["page"] = "notifications"; st.rerun()
        if st.button("🔑  Change Password", use_container_width=True, key="sb_pwd"):
            st.session_state["page"] = "change_password"; st.rerun()

        st.markdown("<div style='margin:10px 0 4px'/>", unsafe_allow_html=True)
        if st.button("🚪  Logout", use_container_width=True, key="sb_logout"):
            do_logout()
