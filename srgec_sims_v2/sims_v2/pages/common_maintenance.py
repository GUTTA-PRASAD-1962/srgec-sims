"""
pages/common_maintenance.py — Generic Maintenance Sheet + Asset Movement + Lab Maint Register

Usage:
    from pages.common_maintenance import show
    show(MODULE_CODE)
"""
import streamlit as st
import pandas as pd
from datetime import date
from db.connection import fetchall as _fa, fetchone as _fo, get_conn
from utils.auth import current_user, require_module_access
from utils.helpers import format_date, export_df


def show(module_code):
    role = require_module_access(module_code)
    user = current_user()
    mod  = _fo("SELECT * FROM tbl_modules WHERE module_code=?", (module_code,))
    if not mod: st.error("Module not found."); return
    mod  = dict(mod); mid = mod["module_id"]

    st.title(f"{mod['module_icon']} {mod['module_name']} — Maintenance")
    st.caption(f"Your role: **{role}**")

    tab1,tab2,tab3 = st.tabs([
        "Maintenance Sheet",
        "Asset Movement",
        "Lab Maintenance Register",
    ])
    with tab1: _maint_sheet(user, role, mod, mid)
    with tab2: _asset_movement(user, role, mod, mid)
    with tab3: _lab_maint(user, role, mod, mid)


# ══ MAINTENANCE SHEET ════════════════════════════════════════════
def _maint_sheet(user, role, mod, mid):
    sub1,sub2 = st.tabs(["New Entry","History"])

    with sub1:
        st.subheader("New Maintenance Entry")
        uid = st.text_input("Asset UID *",key=f"{mid}_ms_uid")
        if not uid.strip(): st.info("Enter Asset UID."); return

        item = _fo("""
            SELECT i.*, it.type_name, d.dept_name
            FROM tbl_items i JOIN tbl_item_types it ON it.type_id=i.type_id
            LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
            WHERE i.unique_item_id=? AND i.module_id=?
        """,(uid.strip(),mid))
        if not item: st.error("Asset not found."); return
        item = dict(item)
        st.success(f"{item['type_name']} — {item['description']} | {item.get('dept_name','—')} | {item['item_status']}")

        c1,c2,c3 = st.columns(3)
        mdate = c1.date_input("Maintenance Date *",value=date.today(),key=f"{mid}_ms_date")
        mtype = c2.selectbox("Type",["CORRECTIVE","PREVENTIVE","AMC"],key=f"{mid}_ms_type")
        cost  = c3.number_input("Cost (Rs.)",min_value=0.0,step=100.0,key=f"{mid}_ms_cost")
        prob  = st.text_area("Problem Identified *",key=f"{mid}_ms_prob",height=80)
        work  = st.text_area("Work Done *",key=f"{mid}_ms_work",height=80)
        parts = st.text_input("Parts Used",key=f"{mid}_ms_parts")
        nsd   = st.date_input("Next Service Due",key=f"{mid}_ms_nsd")
        rem   = st.text_input("Remarks",key=f"{mid}_ms_rem")

        if st.button("Save Maintenance Record",type="primary",key=f"{mid}_ms_save"):
            if not prob.strip() or not work.strip(): st.error("Problem and Work Done required."); return
            try:
                conn = get_conn()
                conn.execute("""
                    INSERT INTO tbl_maintenance
                        (module_id,item_id,maint_date,maint_type,problem_desc,work_done,
                         parts_used,cost,attended_by,next_service_date,remarks)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,(mid,item["item_id"],str(mdate),mtype,prob.strip(),work.strip(),
                     parts.strip() or None,cost,user["user_id"],str(nsd),rem.strip() or None))
                conn.commit(); conn.close()
                st.success("Maintenance record saved.")
            except Exception as ex: st.error(f"Failed: {ex}")

    with sub2:
        st.subheader("Maintenance History")
        srch = st.text_input("Search UID / Type",key=f"{mid}_ms_hist")
        rows = [dict(r) for r in _fa("""
            SELECT m.*, i.unique_item_id, it.type_name, i.description,
                   d.dept_name, u.full_name AS attended_by_name
            FROM tbl_maintenance m
            JOIN tbl_items i ON i.item_id=m.item_id
            JOIN tbl_item_types it ON it.type_id=i.type_id
            LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
            LEFT JOIN tbl_users u ON u.user_id=m.attended_by
            WHERE m.module_id=? ORDER BY m.maint_date DESC
        """,(mid,))]
        if srch.strip():
            s = srch.lower()
            rows = [r for r in rows if s in r.get("unique_item_id","").lower()
                    or s in r.get("type_name","").lower()
                    or s in r.get("description","").lower()]
        if not rows: st.info("No maintenance records."); return
        df = pd.DataFrame([{
            "Date":format_date(r["maint_date"]),"UID":r["unique_item_id"],
            "Type":r["type_name"],"Maint Type":r["maint_type"],
            "Problem":(r.get("problem_desc","") or "")[:60],
            "Work Done":(r.get("work_done","") or "")[:60],
            "Parts":r.get("parts_used","") or "—","Cost Rs.":r.get("cost",0),
            "Attended By":r.get("attended_by_name",""),
            "Next Service":format_date(r.get("next_service_date")),
            "Dept":r.get("dept_name","—"),
        } for r in rows])
        st.dataframe(df,use_container_width=True,hide_index=True)
        export_df(df,f"{mod['module_code']}_Maintenance_History.xlsx")


# ══ ASSET MOVEMENT ═══════════════════════════════════════════════
def _asset_movement(user, role, mod, mid):
    sub1,sub2 = st.tabs(["New Movement","Movement History"])

    with sub1:
        st.subheader("Record Asset Movement")
        uid_input = st.text_area("Asset UIDs (one per line or comma separated)",
                                  key=f"{mid}_mv_uid",height=80)
        if not uid_input.strip(): st.info("Enter Asset UID(s)."); return

        uids = [u.strip() for u in uid_input.replace(",","\n").split("\n") if u.strip()]
        depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
        dm    = {d["dept_name"]: d["dept_id"] for d in depts}
        c1,c2 = st.columns(2)
        to_d  = c1.selectbox("Move To Department *",list(dm.keys()),key=f"{mid}_mv_dept")
        locs  = [dict(r) for r in _fa("SELECT * FROM tbl_locations WHERE dept_id=? AND is_active=1",(dm[to_d],))]
        lm    = {"— No specific location —":None}
        lm.update({l["location_name"]:l["location_id"] for l in locs})
        to_l  = c2.selectbox("To Location",list(lm.keys()),key=f"{mid}_mv_loc")
        purp  = st.text_input("Purpose *",key=f"{mid}_mv_purp")

        if st.button("Record Movement",type="primary",key=f"{mid}_mv_save"):
            if not purp.strip(): st.error("Purpose required."); return
            moved = []; not_found = []
            try:
                conn = get_conn()
                for uid in uids:
                    item = conn.execute(
                        "SELECT item_id,dept_id,location_id FROM tbl_items WHERE unique_item_id=? AND module_id=?",
                        (uid,mid)).fetchone()
                    if not item: not_found.append(uid); continue
                    conn.execute("""
                        INSERT INTO tbl_asset_movement
                            (module_id,item_id,moved_by,from_dept_id,to_dept_id,
                             from_location_id,to_location_id,purpose)
                        VALUES (?,?,?,?,?,?,?,?)
                    """,(mid,item["item_id"],user["user_id"],item["dept_id"],dm[to_d],
                         item["location_id"],lm[to_l],purp.strip()))
                    conn.execute("UPDATE tbl_items SET dept_id=?,location_id=? WHERE item_id=?",
                                 (dm[to_d],lm[to_l],item["item_id"]))
                    moved.append(uid)
                conn.commit(); conn.close()
                if moved: st.success(f"{len(moved)} asset(s) moved to {to_d}.")
                if not_found: st.warning(f"Not found: {', '.join(not_found)}")
            except Exception as ex: st.error(f"Failed: {ex}")

    with sub2:
        st.subheader("Movement History")
        rows = [dict(r) for r in _fa("""
            SELECT mv.*, i.unique_item_id, i.description,
                   d1.dept_name AS from_dept, d2.dept_name AS to_dept,
                   l1.location_name AS from_loc, l2.location_name AS to_loc,
                   u.full_name AS moved_by_name
            FROM tbl_asset_movement mv
            JOIN tbl_items i ON i.item_id=mv.item_id
            LEFT JOIN tbl_departments d1 ON d1.dept_id=mv.from_dept_id
            LEFT JOIN tbl_departments d2 ON d2.dept_id=mv.to_dept_id
            LEFT JOIN tbl_locations l1 ON l1.location_id=mv.from_location_id
            LEFT JOIN tbl_locations l2 ON l2.location_id=mv.to_location_id
            JOIN tbl_users u ON u.user_id=mv.moved_by
            WHERE mv.module_id=? ORDER BY mv.moved_at DESC
        """,(mid,))]
        if not rows: st.info("No movements recorded."); return
        df = pd.DataFrame([{
            "Date":str(r.get("moved_at",""))[:16],"UID":r["unique_item_id"],
            "Description":r["description"],
            "From Dept":r.get("from_dept","—"),"From Loc":r.get("from_loc","—"),
            "To Dept":r.get("to_dept","—"),"To Loc":r.get("to_loc","—"),
            "Purpose":r.get("purpose",""),"Moved By":r.get("moved_by_name",""),
        } for r in rows])
        st.dataframe(df,use_container_width=True,hide_index=True)
        export_df(df,f"{mod['module_code']}_Movement_History.xlsx")


# ══ LAB MAINTENANCE REGISTER ═════════════════════════════════════
def _lab_maint(user, role, mod, mid):
    sub1,sub2 = st.tabs(["New Entry","Register"])

    with sub1:
        st.subheader("Lab Maintenance Entry")
        depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
        dm    = {d["dept_name"]: d["dept_id"] for d in depts}
        c1,c2,c3 = st.columns(3)
        dept  = c1.selectbox("Department *",list(dm.keys()),key=f"{mid}_lm_dept")
        mdate = c2.date_input("Date *",value=date.today(),key=f"{mid}_lm_date")
        mtype = c3.selectbox("Type",["PREVENTIVE","AMC","CORRECTIVE"],key=f"{mid}_lm_type")
        desc  = st.text_input("Description / Scope of Work *",key=f"{mid}_lm_desc")
        c4,c5,c6 = st.columns(3)
        vendor = c4.text_input("Vendor / Agency",key=f"{mid}_lm_vendor")
        cost   = c5.number_input("Cost (Rs.)",min_value=0.0,step=100.0,key=f"{mid}_lm_cost")
        nsd    = c6.date_input("Next Service Due",key=f"{mid}_lm_nsd")
        rem    = st.text_input("Remarks",key=f"{mid}_lm_rem")

        if st.button("Save Lab Maintenance Record",type="primary",key=f"{mid}_lm_save"):
            if not desc.strip(): st.error("Description required."); return
            try:
                conn = get_conn()
                # Use a placeholder item from this dept if available, else skip item_id
                item = conn.execute(
                    "SELECT item_id FROM tbl_items WHERE module_id=? AND dept_id=? AND is_deleted=0 LIMIT 1",
                    (mid,dm[dept])).fetchone()
                if not item:
                    st.warning("No assets in this dept for this module. Add assets first."); return
                conn.execute("""
                    INSERT INTO tbl_maintenance
                        (module_id,item_id,maint_date,maint_type,problem_desc,work_done,
                         cost,attended_by,next_service_date,remarks)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """,(mid,item["item_id"],str(mdate),mtype,
                     f"Lab maintenance — {desc.strip()}",
                     f"Vendor: {vendor}" if vendor else desc.strip(),
                     cost,user["user_id"],str(nsd),rem.strip() or None))
                conn.commit(); conn.close()
                st.success("Lab maintenance record saved.")
            except Exception as ex: st.error(f"Failed: {ex}")

    with sub2:
        st.subheader("Lab Maintenance Register")
        # Show maintenance records grouped by dept
        rows = [dict(r) for r in _fa("""
            SELECT m.maint_date, m.maint_type, m.problem_desc, m.work_done,
                   m.cost, m.next_service_date, m.remarks,
                   d.dept_name, u.full_name AS attended_by_name
            FROM tbl_maintenance m
            JOIN tbl_items i ON i.item_id=m.item_id
            LEFT JOIN tbl_departments d ON d.dept_id=i.dept_id
            LEFT JOIN tbl_users u ON u.user_id=m.attended_by
            WHERE m.module_id=? ORDER BY m.maint_date DESC
        """,(mid,))]
        if not rows: st.info("No records."); return
        df = pd.DataFrame([{
            "Date":format_date(r["maint_date"]),"Dept":r.get("dept_name","—"),
            "Type":r["maint_type"],"Work":(r.get("work_done","") or "")[:80],
            "Cost Rs.":r.get("cost",0),"Next Service":format_date(r.get("next_service_date")),
            "Attended By":r.get("attended_by_name",""),
        } for r in rows])
        st.dataframe(df,use_container_width=True,hide_index=True)
        export_df(df,f"{mod['module_code']}_Lab_Maint_Register.xlsx")
