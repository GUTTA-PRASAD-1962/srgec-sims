"""pages/common_warranty.py — Warranty Alerts & Expiring Soon for all modules"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db.connection import fetchall as _fa, fetchone as _fo
from utils.auth import require_module_access
from utils.helpers import format_date, export_df


def show(module_code):
    role = require_module_access(module_code)
    mod  = _fo("SELECT * FROM tbl_modules WHERE module_code=?", (module_code,))
    if not mod: return
    mod  = dict(mod); mid = mod["module_id"]
    st.title(f"{mod['module_icon']} {mod['module_name']} — Warranty")

    tab1, tab2 = st.tabs(["Warranty Alerts","Expiring Soon"])
    with tab1: _alerts(mod, mid)
    with tab2: _expiring(mod, mid)


def _alerts(mod, mid):
    st.subheader("Warranty Alerts")
    today = str(date.today())
    # Already expired
    expired = [dict(r) for r in _fa("""
        SELECT i.unique_item_id, it.type_name, i.description,
               i.warranty_to, i.warranty_from, i.item_status,
               d.dept_name, l.location_name
        FROM tbl_items i
        JOIN tbl_item_types it ON it.type_id=i.type_id
        LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
        LEFT JOIN tbl_locations l ON l.location_id=i.location_id
        WHERE i.module_id=? AND i.is_deleted=0
          AND i.warranty_to IS NOT NULL AND i.warranty_to != ''
          AND i.warranty_to < ?
        ORDER BY i.warranty_to DESC
    """,(mid, today))]

    if expired:
        st.error(f"**{len(expired)} assets with EXPIRED warranty:**")
        df = pd.DataFrame([{
            "UID":r["unique_item_id"],"Type":r["type_name"],"Description":r["description"],
            "Warranty Expired":format_date(r["warranty_to"]),"Status":r["item_status"],
            "Dept":r.get("dept_name","—"),"Location":r.get("location_name","—"),
        } for r in expired])
        st.dataframe(df, use_container_width=True, hide_index=True)
        export_df(df, f"{mod['module_code']}_Expired_Warranty.xlsx")
    else:
        st.success("No expired warranty assets.")


def _expiring(mod, mid):
    st.subheader("Expiring Soon")
    days = st.selectbox("Show expiring within",["30 days","60 days","90 days","180 days"],key=f"{mid}_wexp_days")
    d = int(days.split()[0])
    today     = str(date.today())
    threshold = str(date.today() + timedelta(days=d))

    items = [dict(r) for r in _fa("""
        SELECT i.unique_item_id, it.type_name, i.description,
               i.warranty_from, i.warranty_to, i.item_status,
               d.dept_name, l.location_name, s.supplier_name
        FROM tbl_items i
        JOIN tbl_item_types it ON it.type_id=i.type_id
        LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
        LEFT JOIN tbl_locations l ON l.location_id=i.location_id
        LEFT JOIN tbl_suppliers s ON s.supplier_id=i.supplier_id
        WHERE i.module_id=? AND i.is_deleted=0
          AND i.warranty_to IS NOT NULL AND i.warranty_to != ''
          AND i.warranty_to >= ? AND i.warranty_to <= ?
        ORDER BY i.warranty_to ASC
    """,(mid, today, threshold))]

    if not items:
        st.success(f"No assets expiring in next {d} days."); return

    st.warning(f"**{len(items)} assets expiring in next {d} days:**")
    df = pd.DataFrame([{
        "UID":r["unique_item_id"],"Type":r["type_name"],"Description":r["description"],
        "Warranty To":format_date(r["warranty_to"]),"Days Left": (
            date.fromisoformat(r["warranty_to"][:10]) - date.today()).days,
        "Supplier":r.get("supplier_name","—"),
        "Dept":r.get("dept_name","—"),"Status":r["item_status"],
    } for r in items])
    st.dataframe(df.sort_values("Days Left"), use_container_width=True, hide_index=True)
    export_df(df, f"{mod['module_code']}_Expiring_Warranty.xlsx")
