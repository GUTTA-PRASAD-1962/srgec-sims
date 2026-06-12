"""
portal.py — SRGEC Integrated Inventory & Maintenance System
Main entry portal — login and module selection
"""
import streamlit as st
import sqlite3, hashlib
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="SRGEC — SIMS",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_PATH = Path("db/sims_data.db")

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def hash_pwd(pwd): return hashlib.sha256(pwd.encode()).hexdigest()

# ── CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding: 1rem 2rem; }
.portal-header {
    background: linear-gradient(135deg, #0D2B5E 0%, #1B4F9A 60%, #2E75B6 100%);
    padding: 20px 30px; border-radius: 12px;
    border-bottom: 4px solid #F0A500; margin-bottom: 24px;
    text-align: center;
}
.portal-header h1 { color: #FFFFFF; font-size: 1.8rem; margin: 0; }
.portal-header h2 { color: #F0A500; font-size: 1.1rem; margin: 4px 0 0 0; }
.portal-header p  { color: #B8D4F5; font-size: 0.8rem; margin: 4px 0 0 0; }
.module-card {
    background: #FFFFFF; border-radius: 12px;
    border: 2px solid #E0E0E0; padding: 20px 16px;
    text-align: center; cursor: pointer;
    transition: all 0.2s ease; height: 160px;
}
.module-card:hover {
    border-color: #1B4F9A;
    box-shadow: 0 4px 16px rgba(27,79,154,0.2);
    transform: translateY(-3px);
}
.module-icon { font-size: 2.4rem; }
.module-name { font-weight: 700; font-size: 0.88rem; margin: 8px 0 4px 0; color: #0D2B5E; }
.module-desc { font-size: 0.72rem; color: #666; }
</style>
""", unsafe_allow_html=True)

# ── Portal Header ─────────────────────────────────────────────────
st.markdown("""
<div class="portal-header">
  <h1>🏛 Seshadri Rao Gudlavalleru Engineering College</h1>
  <h2>INTEGRATED INVENTORY & MAINTENANCE SYSTEM (SIMS)</h2>
  <p>An Autonomous Institute — Permanently Affiliated to JNTUK, Kakinada
  &nbsp;|&nbsp; Gudlavalleru, Krishna District, Andhra Pradesh — 521 356</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────
if "sims_user" not in st.session_state:
    st.session_state.sims_user = None
if "sims_module" not in st.session_state:
    st.session_state.sims_module = None

# ── LOGIN ─────────────────────────────────────────────────────────
if not st.session_state.sims_user:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='background:#F8F9FA;border:1px solid #DEE2E6;
                    border-radius:12px;padding:32px 28px;
                    box-shadow:0 4px 20px rgba(0,0,0,0.08)'>
        <h3 style='color:#0D2B5E;text-align:center;margin-top:0'>🔐 Login to SIMS</h3>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Enter username", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pwd")

        if st.button("Login →", type="primary", use_container_width=True, key="login_btn"):
            if not username or not password:
                st.error("Please enter username and password.")
            elif not DB_PATH.exists():
                st.error("Database not initialized. Run: python setup_sims.py")
            else:
                conn = get_conn()
                user = conn.execute("""
                    SELECT * FROM tbl_users
                    WHERE username=? AND password_hash=? AND is_active=1
                """, (username.strip(), hash_pwd(password))).fetchone()
                conn.close()
                if user:
                    st.session_state.sims_user = dict(user)
                    conn = get_conn()
                    conn.execute("UPDATE tbl_users SET last_login=? WHERE user_id=?",
                                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["user_id"]))
                    conn.commit(); conn.close()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ── MODULE SELECTION ──────────────────────────────────────────────
user = st.session_state.sims_user

# Top bar
tc1, tc2, tc3 = st.columns([3,1,1])
tc1.markdown(
    f"👤 **{user['full_name']}** &nbsp;|&nbsp; "
    f"{'⭐ Super Admin' if user.get('is_super_admin') else 'User'}"
)
if tc2.button("⚙️ Admin Panel", key="admin_btn",
              disabled=not user.get("is_super_admin")):
    st.session_state.sims_module = "ADMIN"
    st.rerun()
if tc3.button("🚪 Logout", key="logout_btn"):
    st.session_state.sims_user   = None
    st.session_state.sims_module = None
    st.rerun()

st.divider()

# Load modules
conn = get_conn()
if user.get("is_super_admin"):
    modules = [dict(r) for r in conn.execute(
        "SELECT * FROM tbl_modules WHERE is_active=1 ORDER BY sort_order"
    ).fetchall()]
else:
    modules = [dict(r) for r in conn.execute("""
        SELECT m.* FROM tbl_modules m
        JOIN tbl_user_module_access a ON a.module_id = m.module_id
        WHERE a.user_id = ? AND a.is_active = 1 AND m.is_active = 1
        ORDER BY m.sort_order
    """, (user["user_id"],)).fetchall()]
conn.close()

if not modules:
    st.warning("No modules assigned to your account. Contact Super Admin.")
    st.stop()

st.markdown("### 📋 Select a Module")

# Display module tiles
cols = st.columns(4)
for idx, mod in enumerate(modules):
    with cols[idx % 4]:
        if st.button(
            f"{mod['module_icon']}\n\n**{mod['module_name']}**",
            key=f"mod_{mod['module_code']}",
            use_container_width=True,
            help=mod.get("description","")
        ):
            st.session_state.sims_module = mod["module_code"]
            st.rerun()

# ── MODULE LAUNCHED ───────────────────────────────────────────────
if st.session_state.sims_module:
    mod_code = st.session_state.sims_module
    st.divider()

    if mod_code == "IT":
        st.info("🔄 Launching IT-IIMS... (redirecting to existing IT-IIMS application)")
        st.markdown(
            "[🚀 Open IT-IIMS](http://localhost:8501)",
            unsafe_allow_html=False
        )
    elif mod_code == "ADMIN":
        _show_admin_panel(user)
    else:
        _show_module(mod_code, user)

def _show_admin_panel(user):
    """SuperAdmin configuration panel."""
    if not user.get("is_super_admin"):
        st.error("Access denied."); return
    st.subheader("⚙️ Super Admin Configuration Panel")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Modules",
        "👥 Users & Access",
        "🔧 Item Types & Fields",
        "⚙️ Workflow Rules",
        "🏢 Departments"
    ])
    with tab1: _admin_modules()
    with tab2: _admin_users()
    with tab3: _admin_fields()
    with tab4: _admin_workflow()
    with tab5: _admin_depts()

def _show_module(mod_code, user):
    """Generic module page — works for any module."""
    conn = get_conn()
    mod = conn.execute(
        "SELECT * FROM tbl_modules WHERE module_code=?", (mod_code,)
    ).fetchone()
    conn.close()
    if not mod:
        st.error(f"Module '{mod_code}' not found."); return
    mod = dict(mod)
    st.markdown(
        f"## {mod['module_icon']} {mod['module_name']}"
    )
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Item Register",
        "🔧 Complaints",
        "📊 Reports",
        "⚙️ Settings",
    ])
    with tab1: st.info("Item Register — coming in Phase 2")
    with tab2: st.info("Complaint System — coming in Phase 2")
    with tab3: st.info("Reports — coming in Phase 2")
    with tab4: st.info("Module Settings — configure via SuperAdmin Panel")

def _admin_modules():
    st.markdown("#### Manage Modules")
    conn = get_conn()
    mods = [dict(r) for r in conn.execute("SELECT * FROM tbl_modules ORDER BY sort_order").fetchall()]
    conn.close()
    import pandas as pd
    df = pd.DataFrame([{
        "Code": m["module_code"], "Name": m["module_name"],
        "Icon": m["module_icon"], "Active": "✅" if m["is_active"] else "❌"
    } for m in mods])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**Add / Edit Module**")
    c1,c2,c3,c4 = st.columns(4)
    mc = c1.text_input("Code (e.g. UPS)", key="am_code")
    mn = c2.text_input("Name", key="am_name")
    mi = c3.text_input("Icon (emoji)", value="📦", key="am_icon")
    mcol = c4.color_picker("Color", value="#1B4F9A", key="am_color")
    if st.button("💾 Save Module", key="am_save"):
        if mc and mn:
            conn = get_conn()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO tbl_modules (module_code,module_name,module_icon,module_color,is_active) VALUES (?,?,?,?,1)",
                    (mc.upper(), mn, mi, mcol))
                conn.commit()
                st.success(f"✅ Module '{mn}' saved.")
                st.rerun()
            except Exception as e: st.error(str(e))
            finally: conn.close()

def _admin_users():
    st.markdown("#### User Management & Module Access")
    conn = get_conn()
    users = [dict(r) for r in conn.execute("""
        SELECT u.user_id, u.full_name, u.username, u.employee_id,
               u.is_super_admin, u.is_active
        FROM tbl_users u ORDER BY u.full_name
    """).fetchall()]
    mods  = [dict(r) for r in conn.execute("SELECT * FROM tbl_modules WHERE is_active=1").fetchall()]
    conn.close()
    import pandas as pd
    df = pd.DataFrame([{
        "ID": u["user_id"], "Name": u["full_name"],
        "Username": u["username"], "Emp ID": u["employee_id"],
        "SuperAdmin": "⭐" if u["is_super_admin"] else "",
        "Active": "✅" if u["is_active"] else "❌"
    } for u in users])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**Create New User**")
    u1,u2,u3 = st.columns(3)
    uname  = u1.text_input("Username *", key="nu_user")
    ufull  = u2.text_input("Full Name *", key="nu_full")
    uemp   = u3.text_input("Employee ID *", key="nu_emp")
    u4,u5  = st.columns(2)
    upwd   = u4.text_input("Password *", type="password", key="nu_pwd")
    uadmin = u5.checkbox("Super Admin", key="nu_admin")
    if st.button("➕ Create User", key="nu_save"):
        if uname and ufull and uemp and upwd:
            conn = get_conn()
            try:
                conn.execute(
                    "INSERT INTO tbl_users (username,password_hash,full_name,employee_id,is_super_admin,is_active,created_at) VALUES (?,?,?,?,?,1,?)",
                    (uname, hash_pwd(upwd), ufull, uemp, 1 if uadmin else 0,
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success(f"✅ User '{ufull}' created.")
                st.rerun()
            except Exception as e: st.error(str(e))
            finally: conn.close()

    st.divider()
    st.markdown("**Grant Module Access**")
    g1,g2,g3,g4 = st.columns(4)
    sel_user = g1.selectbox("User", [f"{u['full_name']} ({u['user_id']})" for u in users], key="ga_user")
    sel_mod  = g2.selectbox("Module", [m["module_name"] for m in mods], key="ga_mod")
    sel_role = g3.selectbox("Role", ["SysAdmin","HoD","Coordinator","Technician","Lab-IC","User"], key="ga_role")
    if g4.button("✅ Grant Access", key="ga_save"):
        uid = int(sel_user.split("(")[-1].rstrip(")"))
        mid = [m["module_id"] for m in mods if m["module_name"]==sel_mod][0]
        conn = get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO tbl_user_module_access (user_id,module_id,role_name,is_active,granted_at) VALUES (?,?,?,1,?)",
                (uid, mid, sel_role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            st.success("✅ Access granted.")
        except Exception as e: st.error(str(e))
        finally: conn.close()

def _admin_fields():
    st.markdown("#### Item Types & Custom Field Definitions")
    conn = get_conn()
    mods  = [dict(r) for r in conn.execute("SELECT * FROM tbl_modules WHERE is_active=1 ORDER BY sort_order").fetchall()]
    conn.close()
    sel_mod = st.selectbox("Select Module", [m["module_name"] for m in mods], key="af_mod")
    mid = [m["module_id"] for m in mods if m["module_name"]==sel_mod][0]
    conn = get_conn()
    types = [dict(r) for r in conn.execute(
        "SELECT * FROM tbl_item_types WHERE module_id=? AND is_active=1", (mid,)).fetchall()]
    conn.close()
    if types:
        sel_type = st.selectbox("Select Item Type", [t["type_name"] for t in types], key="af_type")
        tid = [t["type_id"] for t in types if t["type_name"]==sel_type][0]
        conn = get_conn()
        fields = [dict(r) for r in conn.execute(
            "SELECT * FROM tbl_field_definitions WHERE type_id=? ORDER BY sort_order", (tid,)).fetchall()]
        conn.close()
        if fields:
            import pandas as pd
            df = pd.DataFrame([{
                "Field Name": f["field_name"], "Label": f["field_label"],
                "Type": f["field_type"], "Required": "✅" if f["is_required"] else "",
                "Config": "⚙️" if f["is_config_field"] else ""
            } for f in fields])
            st.dataframe(df, use_container_width=True, hide_index=True)
        st.divider()
        st.markdown("**Add Field**")
        f1,f2,f3,f4 = st.columns(4)
        fn  = f1.text_input("Field Name (key)", key="nf_name")
        fl  = f2.text_input("Display Label", key="nf_label")
        ft  = f3.selectbox("Type", ["text","number","date","dropdown","boolean","textarea"], key="nf_type")
        freq= f4.checkbox("Required", key="nf_req")
        fcfg= st.checkbox("Configuration Field", key="nf_cfg")
        fopts = ""
        if ft == "dropdown":
            fopts = st.text_input("Options (comma separated)", key="nf_opts")
        if st.button("➕ Add Field", key="nf_save"):
            if fn and fl:
                conn = get_conn()
                try:
                    order = len(fields)
                    conn.execute(
                        "INSERT INTO tbl_field_definitions (type_id,field_name,field_label,field_type,is_required,is_config_field,field_options,sort_order) VALUES (?,?,?,?,?,?,?,?)",
                        (tid,fn,fl,ft,1 if freq else 0,1 if fcfg else 0,
                         f'["{fopts}"]' if fopts else None, order))
                    conn.commit()
                    st.success(f"✅ Field '{fl}' added.")
                    st.rerun()
                except Exception as e: st.error(str(e))
                finally: conn.close()

    st.divider()
    st.markdown("**Add New Item Type**")
    it1,it2,it3,it4 = st.columns(4)
    itn = it1.text_input("Type Name", key="nit_name")
    itc = it2.text_input("Type Code (3-4 chars)", key="nit_code")
    itp = it3.text_input("ID Prefix", key="nit_prefix")
    itcfg = it4.checkbox("Has Config Fields", key="nit_cfg")
    if st.button("➕ Add Item Type", key="nit_save"):
        if itn and itc and itp:
            conn = get_conn()
            try:
                conn.execute(
                    "INSERT INTO tbl_item_types (module_id,type_name,type_code,id_prefix,has_config) VALUES (?,?,?,?,?)",
                    (mid, itn, itc.upper(), itp.upper(), 1 if itcfg else 0))
                conn.commit()
                st.success(f"✅ Item type '{itn}' added.")
                st.rerun()
            except Exception as e: st.error(str(e))
            finally: conn.close()

def _admin_workflow():
    st.markdown("#### Workflow Rule Configuration")
    conn = get_conn()
    mods = [dict(r) for r in conn.execute("SELECT * FROM tbl_modules WHERE is_active=1").fetchall()]
    conn.close()
    sel_mod = st.selectbox("Select Module", [m["module_name"] for m in mods], key="wf_mod")
    mid = [m["module_id"] for m in mods if m["module_name"]==sel_mod][0]
    conn = get_conn()
    rules = [dict(r) for r in conn.execute(
        "SELECT * FROM tbl_workflow_rules WHERE module_id=? ORDER BY sort_order", (mid,)).fetchall()]
    conn.close()
    if rules:
        import pandas as pd
        df = pd.DataFrame([{
            "From Status": r["from_status"], "Action": r["action_label"],
            "To Status": r["to_status"], "Allowed Roles": r["allowed_roles"],
            "Active": "✅" if r["is_active"] else "❌"
        } for r in rules])
        st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**Add Workflow Step**")
    w1,w2 = st.columns(2)
    wfrom = w1.text_input("From Status (e.g. OPEN)", key="wf_from")
    wto   = w2.text_input("To Status (e.g. UNDER REVIEW)", key="wf_to")
    w3,w4 = st.columns(2)
    wlabel= w3.text_input("Action Label (e.g. Forward to Coordinator)", key="wf_label")
    wroles= w4.text_input("Allowed Roles (comma separated)", key="wf_roles")
    if st.button("➕ Add Rule", key="wf_save"):
        if wfrom and wto and wlabel and wroles:
            conn = get_conn()
            try:
                conn.execute(
                    "INSERT INTO tbl_workflow_rules (module_id,from_status,to_status,action_label,allowed_roles,sort_order) VALUES (?,?,?,?,?,?)",
                    (mid,wfrom.upper(),wto.upper(),wlabel,wroles,len(rules)))
                conn.commit()
                st.success("✅ Workflow rule added.")
                st.rerun()
            except Exception as e: st.error(str(e))
            finally: conn.close()

def _admin_depts():
    st.markdown("#### Departments & Locations")
    conn = get_conn()
    depts = [dict(r) for r in conn.execute("SELECT * FROM tbl_departments ORDER BY dept_name").fetchall()]
    conn.close()
    import pandas as pd
    if depts:
        st.dataframe(pd.DataFrame([{
            "ID": d["dept_id"], "Name": d["dept_name"],
            "Code": d["dept_code"], "Active": "✅" if d["is_active"] else "❌"
        } for d in depts]), use_container_width=True, hide_index=True)
    st.divider()
    d1,d2 = st.columns(2)
    dname = d1.text_input("Department Name", key="nd_name")
    dcode = d2.text_input("Department Code", key="nd_code")
    if st.button("➕ Add Department", key="nd_save"):
        if dname and dcode:
            conn = get_conn()
            try:
                conn.execute("INSERT INTO tbl_departments (dept_name,dept_code) VALUES (?,?)",
                             (dname, dcode.upper()))
                conn.commit()
                st.success(f"✅ Department '{dname}' added.")
                st.rerun()
            except Exception as e: st.error(str(e))
            finally: conn.close()
