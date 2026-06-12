"""
pages/common_admin.py — Administration panel for each module.
Provides: User Management, Dept & Lab Setup, Suppliers, Audit Log

Usage:
    from pages.common_admin import show
    show(MODULE_CODE)
"""
import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
from db.connection import fetchall as _fa, fetchone as _fo, get_conn
from utils.auth import current_user, require_module_access
from utils.helpers import export_df


def show(module_code):
    role = require_module_access(module_code)
    if role not in ("SuperAdmin","SysAdmin","Coordinator"):
        st.error("Administration — SysAdmin / Coordinator only."); return

    user = current_user()
    mod  = _fo("SELECT * FROM tbl_modules WHERE module_code=?", (module_code,))
    if not mod: return
    mod  = dict(mod); mid = mod["module_id"]

    st.title(f"{mod['module_icon']} {mod['module_name']} — Administration")

    tab1,tab2,tab3,tab4 = st.tabs([
        "User Management",
        "Dept & Lab Setup",
        "Suppliers",
        "Audit Log",
    ])
    with tab1: _users(user, role, mod, mid)
    with tab2: _depts(user)
    with tab3: _suppliers(user)
    with tab4: _audit(mid)


# ══ USER MANAGEMENT ═══════════════════════════════════════════════
def _users(user, role, mod, mid):
    st.subheader("User Management")

    # Show users with access to this module
    access = [dict(r) for r in _fa("""
        SELECT u.user_id, u.full_name, u.username, u.employee_id,
               u.email, u.phone, u.is_active, a.role_name, d.dept_name
        FROM tbl_user_module_access a
        JOIN tbl_users u ON u.user_id=a.user_id
        JOIN tbl_modules m ON m.module_id=a.module_id
        LEFT JOIN tbl_departments d ON d.dept_id=u.dept_id
        WHERE m.module_code=? AND a.is_active=1
        ORDER BY u.full_name
    """,(mod["module_code"],))]

    if access:
        df = pd.DataFrame([{
            "Name":u["full_name"],"Username":u["username"],"Emp ID":u["employee_id"],
            "Role":u["role_name"],"Dept":u.get("dept_name","—"),
            "Email":u.get("email","—"),"Phone":u.get("phone","—"),
            "Active":"✅" if u["is_active"] else "❌"
        } for u in access])
        st.dataframe(df,use_container_width=True,hide_index=True)

    st.divider()
    st.markdown("**Create New User & Assign to this Module**")
    u1,u2,u3 = st.columns(3)
    uname = u1.text_input("Username *",key=f"{mid}_nu_user")
    ufull = u2.text_input("Full Name *",key=f"{mid}_nu_full")
    uemp  = u3.text_input("Employee ID *",key=f"{mid}_nu_emp")
    u4,u5,u6 = st.columns(3)
    upwd  = u4.text_input("Password *",type="password",key=f"{mid}_nu_pwd")
    depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
    dm    = {"— No Dept —":None}; dm.update({d["dept_name"]:d["dept_id"] for d in depts})
    udept = u5.selectbox("Department",list(dm.keys()),key=f"{mid}_nu_dept")
    urole = u6.selectbox("Module Role",
        ["SysAdmin","HoD","Coordinator","Technician","Lab-IC","User"],key=f"{mid}_nu_role")
    u7,u8 = st.columns(2)
    uemail= u7.text_input("Email",key=f"{mid}_nu_email")
    uphone= u8.text_input("Phone",key=f"{mid}_nu_phone")

    if st.button("Create User & Grant Access",type="primary",key=f"{mid}_nu_save"):
        if not all([uname,ufull,uemp,upwd]):
            st.error("Username, Full Name, Employee ID and Password are required."); return
        try:
            conn = get_conn()
            uid = conn.execute("""
                INSERT INTO tbl_users
                    (username,password_hash,full_name,employee_id,email,phone,dept_id,is_active,created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """,(uname,hashlib.sha256(upwd.encode()).hexdigest(),ufull,uemp,
                 uemail,uphone,dm[udept],datetime.now().strftime("%Y-%m-%d %H:%M:%S"))).lastrowid
            conn.execute("""
                INSERT OR REPLACE INTO tbl_user_module_access (user_id,module_id,role_name,is_active,granted_at)
                VALUES (?,?,?,1,?)
            """,(uid,mid,urole,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            st.success(f"User '{ufull}' created with role '{urole}'."); st.rerun()
        except Exception as ex: st.error(f"Failed: {ex}")

    st.divider()
    st.markdown("**Grant Module Access to Existing User**")
    all_users = [dict(r) for r in _fa("SELECT user_id,full_name,username FROM tbl_users WHERE is_active=1 ORDER BY full_name")]
    if all_users:
        g1,g2,g3 = st.columns(3)
        sel_u = g1.selectbox("User",
            [f"{u['full_name']} ({u['username']})" for u in all_users],key=f"{mid}_ga_user")
        sel_r = g2.selectbox("Role",
            ["SysAdmin","HoD","Coordinator","Technician","Lab-IC","User"],key=f"{mid}_ga_role")
        if g3.button("Grant Access",key=f"{mid}_ga_save"):
            uid   = all_users[[f"{u['full_name']} ({u['username']})" for u in all_users].index(sel_u)]["user_id"]
            conn  = get_conn()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO tbl_user_module_access
                        (user_id,module_id,role_name,is_active,granted_at)
                    VALUES (?,?,?,1,?)
                """,(uid,mid,sel_r,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit(); st.success("Access granted."); st.rerun()
            except Exception as ex: st.error(str(ex))
            finally: conn.close()

    # DB Backup (SysAdmin/SuperAdmin)
    if role in ("SuperAdmin","SysAdmin"):
        st.divider()
        with st.expander("Database Backup & Statistics"):
            from config import DB_PATH
            from pathlib import Path
            c1,c2 = st.columns(2)
            if c1.button("Download DB Backup",type="primary",key=f"{mid}_db_backup"):
                p = Path(DB_PATH)
                if p.exists():
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(f"Save sims_backup_{ts}.db",p.read_bytes(),
                                       file_name=f"sims_backup_{ts}.db",
                                       mime="application/octet-stream",
                                       key=f"{mid}_db_dl")
                else: st.error("DB file not found.")
            if c2.button("DB Statistics",key=f"{mid}_db_stats"):
                tables = [("tbl_items","Assets"),("tbl_invoices","Invoices"),
                          ("tbl_calls","Complaints"),("tbl_maintenance","Maintenance"),
                          ("tbl_users","Users"),("tbl_departments","Departments")]
                stats  = []
                for tbl,lbl in tables:
                    try:
                        cnt = dict(_fo(f"SELECT COUNT(*) c FROM {tbl}") or {"c":0})["c"]
                        stats.append({"Table":lbl,"Records":cnt})
                    except: pass
                if stats: st.dataframe(pd.DataFrame(stats),use_container_width=True,hide_index=True)


# ══ DEPT & LAB SETUP ══════════════════════════════════════════════
def _depts(user):
    st.subheader("Departments & Locations")
    depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
    if depts:
        st.dataframe(pd.DataFrame([{
            "ID":d["dept_id"],"Name":d["dept_name"],"Code":d["dept_code"]
        } for d in depts]),use_container_width=True,hide_index=True)

    st.divider()
    st.markdown("**Add Department**")
    d1,d2 = st.columns(2)
    dn=d1.text_input("Dept Name *",key="new_dept_n"); dc=d2.text_input("Dept Code *",key="new_dept_c")
    if st.button("Add Dept",key="new_dept_save"):
        if dn and dc:
            conn=get_conn()
            try:
                conn.execute("INSERT INTO tbl_departments (dept_name,dept_code) VALUES (?,?)",(dn,dc.upper()))
                conn.commit(); st.success(f"Dept '{dn}' added."); st.rerun()
            except Exception as ex: st.error(str(ex))
            finally: conn.close()

    st.divider()
    st.markdown("**Add Location (Lab / Room)**")
    depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
    dm    = {d["dept_name"]: d["dept_id"] for d in depts}
    l1,l2,l3,l4 = st.columns(4)
    ld   = l1.selectbox("Department *",list(dm.keys()),key="new_loc_dept")
    ln   = l2.text_input("Location Name *",key="new_loc_n")
    lc   = l3.text_input("Location Code *",key="new_loc_c")
    lt   = l4.selectbox("Type",["LAB","ROOM","FLOOR","BLOCK"],key="new_loc_type")
    if st.button("Add Location",key="new_loc_save"):
        if ln and lc:
            conn=get_conn()
            try:
                conn.execute("INSERT INTO tbl_locations (dept_id,location_name,location_code,location_type) VALUES (?,?,?,?)",
                             (dm[ld],ln,lc.upper(),lt))
                conn.commit(); st.success(f"Location '{ln}' added."); st.rerun()
            except Exception as ex: st.error(str(ex))
            finally: conn.close()

    # Show existing locations
    locs = [dict(r) for r in _fa("""
        SELECT l.*, d.dept_name FROM tbl_locations l
        JOIN tbl_departments d ON d.dept_id=l.dept_id
        WHERE l.is_active=1 ORDER BY d.dept_name, l.location_name
    """)]
    if locs:
        st.divider()
        st.markdown("**Existing Locations:**")
        st.dataframe(pd.DataFrame([{
            "Dept":l["dept_name"],"Location":l["location_name"],
            "Code":l["location_code"],"Type":l["location_type"]
        } for l in locs]),use_container_width=True,hide_index=True)


# ══ SUPPLIERS ════════════════════════════════════════════════════
def _suppliers(user):
    st.subheader("Supplier Management")
    supps = [dict(r) for r in _fa("SELECT * FROM tbl_suppliers WHERE is_active=1 ORDER BY supplier_name")]
    if supps:
        st.dataframe(pd.DataFrame([{
            "ID":s["supplier_id"],"Name":s["supplier_name"],
            "Contact":s.get("contact_person","—"),"Phone":s.get("phone","—"),
            "Email":s.get("email","—"),"Address":s.get("address","—"),
        } for s in supps]),use_container_width=True,hide_index=True)

    st.divider()
    st.markdown("**Add Supplier**")
    s1,s2,s3 = st.columns(3)
    sn=s1.text_input("Supplier Name *",key="new_supp_n")
    sc=s2.text_input("Contact Person",key="new_supp_c")
    sp=s3.text_input("Phone",key="new_supp_p")
    s4,s5 = st.columns(2)
    se=s4.text_input("Email",key="new_supp_e"); sa=s5.text_input("Address",key="new_supp_a")
    if st.button("Add Supplier",type="primary",key="new_supp_save"):
        if sn.strip():
            conn=get_conn()
            try:
                conn.execute("INSERT INTO tbl_suppliers (supplier_name,contact_person,phone,email,address) VALUES (?,?,?,?,?)",
                             (sn.strip(),sc,sp,se,sa))
                conn.commit(); st.success(f"Supplier '{sn}' added."); st.rerun()
            except Exception as ex: st.error(str(ex))
            finally: conn.close()


# ══ AUDIT LOG ════════════════════════════════════════════════════
def _audit(mid):
    st.subheader("Audit Log")
    rows = [dict(r) for r in _fa("""
        SELECT a.*, u.full_name AS user_name
        FROM tbl_audit a
        LEFT JOIN tbl_users u ON u.user_id=a.user_id
        WHERE a.module_id=? ORDER BY a.created_at DESC LIMIT 200
    """,(mid,))]
    if not rows: st.info("No audit records."); return
    df = pd.DataFrame([{
        "Time":str(r.get("created_at",""))[:16],"User":r.get("user_name","—"),
        "Action":r["action"],"Table":r.get("table_name","—"),
        "Details":r.get("details","")[:80],
    } for r in rows])
    st.dataframe(df,use_container_width=True,hide_index=True)
