"""
app.py — SRGEC Integrated Inventory & Maintenance System v2
Single Streamlit app serving all 8 modules through a common engine.
"""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="SRGEC — SIMS",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── DB init ───────────────────────────────────────────────────────
from config import DB_PATH
if not Path(DB_PATH).exists():
    from db.schema import init_db
    init_db(DB_PATH)

from utils.auth import is_logged_in, do_login, current_user
from components.header import render_header, render_portal_sidebar


# ── Login page ────────────────────────────────────────────────────
def _login_page():
    render_header(logged_in=False)
    col1,col2,col3 = st.columns([1,1.2,1])
    with col2:
        st.markdown("""
        <div style='background:#F8F9FA;border:2px solid #1B4F9A;border-radius:14px;
                    padding:36px 30px;box-shadow:0 6px 24px rgba(0,0,0,0.1)'>
        <h3 style='color:#0D2B5E;text-align:center;margin-top:0'>
            Login to SRGEC-SIMS</h3>
        """, unsafe_allow_html=True)
        username = st.text_input("Username", key="l_user")
        password = st.text_input("Password", type="password", key="l_pwd")
        if st.button("Login", type="primary", use_container_width=True, key="l_btn"):
            ok, msg = do_login(username.strip(), password)
            if ok: st.rerun()
            else:  st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)


# ── Main routing ──────────────────────────────────────────────────
if not is_logged_in():
    _login_page()
    st.stop()

render_header(logged_in=True)

page = st.session_state.get("page", "dashboard")
mod  = st.session_state.get("sims_module","")

# Show module sidebar if inside a module, else portal sidebar
if mod and page.startswith("mod_"):
    pass  # module_home renders its own sidebar
else:
    render_portal_sidebar()

# Page map
PAGE_MAP = {
    "dashboard":       ("pages.dashboard",        "show"),
    "superadmin":      ("pages.superadmin",       "show"),
    "notifications":   ("pages.common_notifications","show"),
    "change_password": ("pages.common_account",   "show"),
    # Module entries
    "mod_it":          ("pages.mod_it",           "show_module"),
    "mod_ups":         ("pages.mod_ups",          "show_module"),
    "mod_elec":        ("pages.mod_elec",         "show_module"),
    "mod_civil":       ("pages.mod_civil",        "show_module"),
    "mod_furn":        ("pages.mod_furn",         "show_module"),
    "mod_stat":        ("pages.mod_stat",         "show_module"),
    "mod_lcd":         ("pages.mod_lcd",          "show_module"),
    "mod_cctv":        ("pages.mod_cctv",         "show_module"),
}

if page in PAGE_MAP:
    import importlib
    mod_path, fn = PAGE_MAP[page]
    try:
        m = importlib.import_module(mod_path)
        getattr(m, fn)()
    except Exception as exc:
        import traceback
        st.error(f"Page error on `{page}`: {exc}")
        with st.expander("Details"): st.code(traceback.format_exc())
else:
    st.session_state["page"] = "dashboard"
    st.rerun()
