"""pages/common_reports.py — Reports & Export for all modules"""
import streamlit as st
import pandas as pd
from db.connection import fetchall as _fa, fetchone as _fo
from utils.auth import require_module_access
from utils.helpers import format_date, export_df, format_currency


def show(module_code):
    role = require_module_access(module_code)
    mod  = _fo("SELECT * FROM tbl_modules WHERE module_code=?", (module_code,))
    if not mod: return
    mod  = dict(mod); mid = mod["module_id"]
    st.title(f"{mod['module_icon']} {mod['module_name']} — Reports & Export")

    tab1,tab2,tab3,tab4 = st.tabs([
        "Stock Summary",
        "Maintenance Summary",
        "Complaint Register",
        "Asset-wise Report",
    ])
    with tab1: _stock_summary(mod, mid)
    with tab2: _maint_summary(mod, mid)
    with tab3: _complaint_register(mod, mid)
    with tab4: _asset_report(mod, mid)


def _stock_summary(mod, mid):
    st.subheader("Stock Summary")
    rows = [dict(r) for r in _fa("""
        SELECT it.type_name,
               COUNT(*) AS total,
               SUM(CASE WHEN i.dept_id IS NULL THEN 1 ELSE 0 END) AS central,
               SUM(CASE WHEN i.dept_id IS NOT NULL THEN 1 ELSE 0 END) AS issued,
               SUM(CASE WHEN i.item_status='WORKING' THEN 1 ELSE 0 END) AS working,
               SUM(CASE WHEN i.item_status!='WORKING' AND i.item_status!='CONDEMNED'
                        AND i.item_status!='DISPOSED' THEN 1 ELSE 0 END) AS faulty,
               SUM(i.cost_per_unit) AS total_value
        FROM tbl_items i
        JOIN tbl_item_types it ON it.type_id=i.type_id
        WHERE i.module_id=? AND i.is_deleted=0
        GROUP BY i.type_id ORDER BY total DESC
    """,(mid,))]
    if not rows: st.info("No assets."); return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    total_val = sum(r.get("total_value",0) or 0 for r in rows)
    total_assets = sum(r.get("total",0) for r in rows)
    m1,m2,m3 = st.columns(3)
    m1.metric("Total Assets",total_assets)
    m2.metric("Total Value",format_currency(total_val))
    m3.metric("Working",sum(r.get("working",0) for r in rows))
    export_df(df, f"{mod['module_code']}_Stock_Summary.xlsx")


def _maint_summary(mod, mid):
    st.subheader("Maintenance Summary")
    rows = [dict(r) for r in _fa("""
        SELECT m.maint_type, COUNT(*) AS count, SUM(m.cost) AS total_cost,
               MIN(m.maint_date) AS first_date, MAX(m.maint_date) AS last_date
        FROM tbl_maintenance m WHERE m.module_id=?
        GROUP BY m.maint_type
    """,(mid,))]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    # By dept
    by_dept = [dict(r) for r in _fa("""
        SELECT d.dept_name, COUNT(*) AS total, SUM(m.cost) AS cost
        FROM tbl_maintenance m
        JOIN tbl_items i ON i.item_id=m.item_id
        LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
        WHERE m.module_id=? GROUP BY i.dept_id ORDER BY total DESC
    """,(mid,))]
    if by_dept:
        st.markdown("**By Department:**")
        st.dataframe(pd.DataFrame(by_dept), use_container_width=True, hide_index=True)


def _complaint_register(mod, mid):
    st.subheader("Complaint Register")
    from datetime import date, timedelta
    c1,c2 = st.columns(2)
    df_from = c1.date_input("From", value=date.today()-timedelta(days=90), key=f"{mid}_cr_from")
    df_to   = c2.date_input("To",   value=date.today(), key=f"{mid}_cr_to")
    rows = [dict(r) for r in _fa("""
        SELECT c.call_number, c.call_status, c.created_at,
               i.unique_item_id, i.description,
               d.dept_name, u.full_name AS raised_by,
               u2.full_name AS assignee
        FROM tbl_calls c
        LEFT JOIN tbl_items i ON i.item_id=c.item_id
        LEFT JOIN tbl_departments d ON d.dept_id=c.dept_id
        JOIN tbl_users u ON u.user_id=c.raised_by
        LEFT JOIN tbl_users u2 ON u2.user_id=c.current_assignee
        WHERE c.module_id=? AND date(c.created_at) BETWEEN ? AND ?
        ORDER BY c.created_at DESC
    """,(mid, str(df_from), str(df_to)))]
    if not rows: st.info("No complaints in range."); return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    # Status breakdown
    by_status = {}
    for r in rows: by_status[r["call_status"]] = by_status.get(r["call_status"],0)+1
    m_cols = st.columns(min(len(by_status),4))
    for i,(s,c) in enumerate(by_status.items()):
        m_cols[i%4].metric(s, c)
    export_df(df, f"{mod['module_code']}_Complaints.xlsx")


def _asset_report(mod, mid):
    st.subheader("Asset-wise Detailed Report")
    depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
    dm    = {"All Departments": None}
    dm.update({d["dept_name"]: d["dept_id"] for d in depts})
    sel_d = st.selectbox("Filter by Department",list(dm.keys()),key=f"{mid}_ar_dept")
    dept_id = dm[sel_d]

    q = """
        SELECT i.unique_item_id, it.type_name, i.description, i.make, i.model,
               i.serial_number, i.cost_per_unit, i.purchase_date, i.warranty_from, i.warranty_to,
               i.item_status, d.dept_name, l.location_name, s.supplier_name, inv.invoice_number
        FROM tbl_items i
        JOIN tbl_item_types it ON it.type_id=i.type_id
        LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
        LEFT JOIN tbl_locations l ON l.location_id=i.location_id
        LEFT JOIN tbl_suppliers s ON s.supplier_id=i.supplier_id
        LEFT JOIN tbl_invoices inv ON inv.invoice_id=i.invoice_id
        WHERE i.module_id=? AND i.is_deleted=0
    """
    params = [mid]
    if dept_id: q += " AND i.dept_id=?"; params.append(dept_id)
    q += " ORDER BY it.type_name, i.item_id"
    rows = [dict(r) for r in _fa(q, params)]
    if not rows: st.info("No assets."); return
    df = pd.DataFrame([{
        "UID":r["unique_item_id"],"Type":r["type_name"],"Description":r["description"],
        "Make":r.get("make","—"),"Model":r.get("model","—"),"Serial":r.get("serial_number","—"),
        "Cost Rs.":r["cost_per_unit"],"Purchase Date":format_date(r.get("purchase_date")),
        "Warranty To":format_date(r.get("warranty_to")),"Status":r["item_status"],
        "Dept":r.get("dept_name","Central Stock"),"Location":r.get("location_name","—"),
        "Supplier":r.get("supplier_name","—"),"Invoice":r.get("invoice_number","—"),
    } for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True)
    export_df(df, f"{mod['module_code']}_Asset_Report.xlsx")
