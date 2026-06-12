"""
pages/module_home.py — Generic module home page with full sidebar navigation.
This is the landing page when any module is opened.
All sub-modules route through here.

Usage:
    from pages.module_home import show
    show(MODULE_CODE)
"""
import streamlit as st
from db.connection import fetchone as _fo, fetchall as _fa
from utils.auth import current_user, require_module_access, get_user_module_role
from config import MODULES


def show(module_code):
    role = require_module_access(module_code)
    user = current_user()
    mod  = _fo("SELECT * FROM tbl_modules WHERE module_code=?", (module_code,))
    if not mod: st.error(f"Module '{module_code}' not found."); return
    mod  = dict(mod); mid = mod["module_id"]

    # Store current module in session
    st.session_state["sims_module"] = module_code

    # Get subpage — default to dashboard
    subpage = st.session_state.get(f"sub_{module_code}", "dashboard")

    # Render module sidebar
    _render_module_sidebar(module_code, mod, role)

    # Route to subpage
    _route(subpage, module_code, mod, role, user)


def _render_module_sidebar(module_code, mod, role):
    """Render module-specific sidebar with all IT-IIMS equivalent sub-modules."""
    mc   = mod["module_code"]
    info = MODULES.get(mc, {})
    color = info.get("color", "#1B4F9A")

    with st.sidebar:
        # Module header
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{color}CC,{color});
                    padding:10px 14px;border-radius:8px;
                    border-bottom:3px solid #F0A500;margin-bottom:12px">
          <p style="color:#FFFFFF;font-weight:900;font-size:0.9rem;margin:0">
            {mod['module_icon']} {mod['module_name']}</p>
          <p style="color:#FFE0B2;font-size:0.72rem;margin:3px 0 0 0">
            Role: {role}</p>
        </div>
        """, unsafe_allow_html=True)

        def nav(label, sub):
            if st.button(label, use_container_width=True, key=f"snb_{mc}_{sub}"):
                st.session_state[f"sub_{mc}"] = sub
                st.rerun()

        def sec(icon, title, color="#F0A500"):
            st.markdown(
                f'<div style="background:linear-gradient(90deg,#0D2B5E,#1B4F9A);'
                f'padding:5px 10px;border-radius:5px;margin:8px 0 3px;'
                f'border-left:3px solid {color}">'
                f'<span style="color:{color};font-size:0.75rem;font-weight:800">'
                f'{icon} {title.upper()}</span></div>',
                unsafe_allow_html=True)

        # Dashboard
        if st.button("🏠  Module Dashboard", type="primary",
                     use_container_width=True, key=f"snb_{mc}_dash"):
            st.session_state[f"sub_{mc}"] = "dashboard"; st.rerun()

        # Back to Portal
        if st.button("◀  Back to Portal", use_container_width=True, key=f"snb_{mc}_back"):
            st.session_state["sims_module"] = ""
            st.session_state["page"] = "dashboard"; st.rerun()

        sec("🔍", "Inventory", "#4FC3F7")
        nav("📋  Asset Search & Edit",   "asset_search")
        nav("📄  Case Sheets",           "case_sheets")

        sec("📊", "Stock Registers", "#81C784")
        nav("🏛  Central Stock",         "central_stock")
        nav("🏢  Department Stock",      "dept_stock")

        sec("🛒", "Procurement", "#FFB74D")
        nav("📤  Forward Procurement",   "proc_forward")
        nav("✅  Pending Approvals",     "proc_approvals")
        nav("✏️  Joint Data Entry",      "proc_entry")
        nav("📋  Procurement Log",       "proc_log")

        sec("🔧", "Complaints", "#EF9A9A")
        nav("🆕  Raise Complaint",       "raise_complaint")
        nav("📥  My Inbox",              "my_inbox")
        nav("📂  Complaint Register",    "complaint_register")
        nav("🔩  Spare Parts Indent",    "spare_indent")
        nav("📄  Closure Report",        "closure_report")

        sec("🔒", "Warranty", "#CE93D8")
        nav("⚠️  Warranty Alerts",       "warranty_alerts")
        nav("📅  Expiring Soon",         "warranty_expiring")

        if mod.get("has_maintenance", 1):
            sec("🛠", "Maintenance", "#80DEEA")
            nav("🔧  Maintenance Sheet",     "maintenance_sheet")
            nav("🚚  Asset Movement",        "asset_movement")
            nav("🏭  Lab Maint. Register",   "lab_maint")

        sec("📈", "Reports", "#A5D6A7")
        nav("📊  Reports & Export",      "reports")

        if role in ("SuperAdmin","SysAdmin","Coordinator"):
            sec("⚙️", "Administration", "#F48FB1")
            nav("👥  User Management",       "admin_users")
            nav("🏫  Dept & Lab Setup",      "admin_depts")
            nav("🏭  Suppliers",             "admin_suppliers")
            nav("📜  Audit Log",             "admin_audit")

        sec("👤", "Account", "#B0BEC5")
        nav("🔔  Notifications",         "notifications")
        nav("🔑  Change Password",       "change_password")


def _route(subpage, module_code, mod, role, user):
    """Route to the correct common engine page based on subpage."""
    mc = module_code

    if subpage == "dashboard":
        _module_dashboard(mod, role)

    # ── Inventory ──────────────────────────────────────────────────
    elif subpage in ("central_stock","dept_stock","asset_search","case_sheets"):
        from pages.common_stock import show as stock_show
        # Map subpage to tab index hint
        tab_hints = {
            "central_stock": 2, "dept_stock": 3,
            "asset_search": 4, "case_sheets": 4
        }
        st.session_state[f"_stock_tab_{mod['module_id']}"] = tab_hints.get(subpage, 0)
        stock_show(mc)

    # ── Procurement ────────────────────────────────────────────────
    elif subpage in ("proc_forward","proc_approvals","proc_entry","proc_log"):
        from pages.common_procurement import show as proc_show
        tab_hints = {
            "proc_forward": 0, "proc_entry": 1,
            "proc_approvals": 2, "proc_log": 3
        }
        st.session_state[f"_proc_tab_{mod['module_id']}"] = tab_hints.get(subpage, 0)
        proc_show(mc)

    # ── Complaints ─────────────────────────────────────────────────
    elif subpage in ("raise_complaint","my_inbox","complaint_register","spare_indent","closure_report"):
        from pages.common_inbox import show as inbox_show
        tab_hints = {
            "my_inbox": 0, "raise_complaint": 1,
            "complaint_register": 2, "spare_indent": 3
        }
        st.session_state[f"_inbox_tab_{mod['module_id']}"] = tab_hints.get(subpage, 0)
        inbox_show(mc)

    # ── Warranty ───────────────────────────────────────────────────
    elif subpage in ("warranty_alerts","warranty_expiring"):
        from pages.common_warranty import show as warr_show
        warr_show(mc)

    # ── Maintenance ────────────────────────────────────────────────
    elif subpage in ("maintenance_sheet","asset_movement","lab_maint"):
        from pages.common_maintenance import show as maint_show
        maint_show(mc)

    # ── Reports ────────────────────────────────────────────────────
    elif subpage == "reports":
        from pages.common_reports import show as rep_show
        rep_show(mc)

    # ── Administration ─────────────────────────────────────────────
    elif subpage in ("admin_users","admin_depts","admin_suppliers","admin_audit"):
        from pages.common_admin import show as adm_show
        adm_show(mc)

    # ── Account ────────────────────────────────────────────────────
    elif subpage == "notifications":
        from pages.common_notifications import show as notif_show
        notif_show()

    elif subpage == "change_password":
        from pages.common_account import show as acct_show
        acct_show()

    else:
        _module_dashboard(mod, role)


def _module_dashboard(mod, role):
    """Module-specific dashboard with metrics."""
    mid = mod["module_id"]
    mc  = mod["module_code"]

    st.title(f"{mod['module_icon']} {mod['module_name']} — Dashboard")
    st.caption(f"Your role: **{role}**")

    # Metrics
    try:
        total   = dict(_fo("SELECT COUNT(*) c FROM tbl_items WHERE module_id=? AND is_deleted=0",(mid,)) or {"c":0})["c"]
        central = dict(_fo("SELECT COUNT(*) c FROM tbl_items WHERE module_id=? AND dept_id IS NULL AND is_deleted=0",(mid,)) or {"c":0})["c"]
        open_c  = dict(_fo("SELECT COUNT(*) c FROM tbl_calls WHERE module_id=? AND call_status='OPEN'",(mid,)) or {"c":0})["c"]
        working = dict(_fo("SELECT COUNT(*) c FROM tbl_items WHERE module_id=? AND item_status='WORKING' AND is_deleted=0",(mid,)) or {"c":0})["c"]
        faulty  = total - working

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Total Assets",   total)
        m2.metric("Central Stock",  central)
        m3.metric("Open Complaints",open_c)
        m4.metric("Working",        working)
        m5.metric("Faulty",         faulty)
    except Exception: pass

    st.divider()

    # Quick actions
    user = current_user()
    col1,col2,col3 = st.columns(3)

    with col1:
        st.markdown("#### Quick Actions")
        if st.button("➕ New Asset Entry",   use_container_width=True, key=f"{mid}_qa1"):
            st.session_state[f"sub_{mc}"] = "central_stock"; st.rerun()
        if st.button("📥 My Inbox",          use_container_width=True, key=f"{mid}_qa2"):
            st.session_state[f"sub_{mc}"] = "my_inbox"; st.rerun()
        if st.button("🆕 Raise Complaint",   use_container_width=True, key=f"{mid}_qa3"):
            st.session_state[f"sub_{mc}"] = "raise_complaint"; st.rerun()

    with col2:
        st.markdown("#### Recent Complaints")
        try:
            calls = [dict(r) for r in _fa("""
                SELECT c.call_number, c.call_status, c.created_at,
                       i.unique_item_id, d.dept_name
                FROM tbl_calls c
                LEFT JOIN tbl_items i ON i.item_id=c.item_id
                LEFT JOIN tbl_departments d ON d.dept_id=c.dept_id
                WHERE c.module_id=? ORDER BY c.created_at DESC LIMIT 5
            """,(mid,))]
            for c in calls:
                st.markdown(
                    f"**{c['call_number']}** `{c['call_status']}`  \n"
                    f"{c.get('unique_item_id','—')} | {c.get('dept_name','—')}"
                )
        except Exception: pass

    with col3:
        st.markdown("#### Warranty Expiring (30 days)")
        try:
            from datetime import date, timedelta
            threshold = str(date.today() + timedelta(days=30))
            today     = str(date.today())
            expiring  = [dict(r) for r in _fa("""
                SELECT i.unique_item_id, i.description, i.warranty_to
                FROM tbl_items i
                WHERE i.module_id=? AND i.is_deleted=0
                  AND i.warranty_to >= ? AND i.warranty_to <= ?
                ORDER BY i.warranty_to ASC LIMIT 5
            """,(mid,today,threshold))]
            if expiring:
                for e in expiring:
                    st.warning(f"`{e['unique_item_id']}` — expires {e['warranty_to'][:10]}")
            else:
                st.success("No warranties expiring in 30 days.")
        except Exception: pass
