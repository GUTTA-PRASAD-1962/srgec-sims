"""
pages/common_procurement.py — Generic Procurement Module for ALL modules.
Mirrors IT-IIMS procurement: Forward → Joint Entry → HoD Approval

Usage:
    from pages.common_procurement import show
    show(MODULE_CODE)
"""
import streamlit as st
import pandas as pd
from datetime import date
from db.connection import fetchall as _fa, fetchone as _fo, get_conn
from utils.auth import current_user, require_module_access
from utils.helpers import (save_scan, show_scan, format_date,
                            get_dynamic_fields, render_dynamic_fields,
                            save_field_values, generate_item_id, export_df)


def show(module_code):
    role = require_module_access(module_code)
    user = current_user()
    mod  = _fo("SELECT * FROM tbl_modules WHERE module_code=?", (module_code,))
    if not mod: st.error("Module not found."); return
    mod  = dict(mod); mid = mod["module_id"]

    st.title(f"{mod['module_icon']} {mod['module_name']} — Procurement")
    st.caption(f"Your role: **{role}**")

    if st.session_state.get(f"_proc_msg_{mid}"):
        t,m = st.session_state.pop(f"_proc_msg_{mid}")
        (st.success if t=="s" else st.error)(m)

    tab1,tab2,tab3,tab4 = st.tabs([
        "Forward Procurement",
        "Joint Data Entry",
        "Pending Approvals",
        "Procurement Log",
    ])
    with tab1: _forward(user, role, mod, mid)
    with tab2: _joint_entry(user, role, mod, mid)
    with tab3: _approvals(user, role, mod, mid)
    with tab4: _log(user, role, mod, mid)


# ══ TAB 1 — FORWARD PROCUREMENT ══════════════════════════════════
def _forward(user, role, mod, mid):
    if role not in ("SuperAdmin","SysAdmin","Coordinator","HoD"):
        st.info("Forward Procurement is for SysAdmin / Coordinator / HoD."); return

    st.subheader("Forward Procurement to Data Entry Staff")

    # View existing scans
    with st.expander("View Previously Uploaded Invoice Scans"):
        scans = [dict(r) for r in _fa(
            "SELECT invoice_number, invoice_scan_path FROM tbl_invoices WHERE module_id=? AND invoice_scan_path IS NOT NULL ORDER BY invoice_id DESC",(mid,))]
        if scans:
            sc1,sc2 = st.columns([2,3])
            srch = sc1.text_input("Search Invoice No",key=f"{mid}_fwd_scan_srch")
            fl   = [s for s in scans if srch.lower() in s["invoice_number"].lower()] if srch.strip() else scans
            if fl:
                sel = sc2.selectbox("Select Invoice",[s["invoice_number"] for s in fl],key=f"{mid}_fwd_scan_sel")
                show_scan(next(s["invoice_scan_path"] for s in fl if s["invoice_number"]==sel))
        else:
            st.info("No invoice scans yet.")
    st.divider()

    # Supplier
    st.markdown("#### Step 1 — Supplier")
    supps  = [dict(r) for r in _fa("SELECT * FROM tbl_suppliers WHERE is_active=1 ORDER BY supplier_name")]
    s_opts = {"— select —":None}; s_opts.update({s["supplier_name"]:s["supplier_id"] for s in supps})
    new_s  = st.checkbox("Add New Supplier",key=f"{mid}_fwd_new_s")
    if new_s:
        a1,a2,a3 = st.columns(3)
        sn=a1.text_input("Name *",key=f"{mid}_fwd_sn"); sp=a2.text_input("Phone",key=f"{mid}_fwd_sp"); se=a3.text_input("Email",key=f"{mid}_fwd_se")
        if st.button("Save Supplier",key=f"{mid}_fwd_ss"):
            if sn.strip():
                c=get_conn(); c.execute("INSERT INTO tbl_suppliers (supplier_name,phone,email) VALUES (?,?,?)",(sn.strip(),sp,se)); c.commit(); c.close()
                st.success(f"Supplier '{sn}' saved."); st.rerun()
        return
    sel_s = st.selectbox("Supplier *",list(s_opts.keys()),key=f"{mid}_fwd_supp")
    sup_id = s_opts[sel_s]

    st.markdown("#### Step 2 — Invoice Details")
    c1,c2,c3 = st.columns(3)
    inv_no  = c1.text_input("Invoice No *",key=f"{mid}_fwd_ino")
    inv_dt  = c2.date_input("Invoice Date",value=date.today(),key=f"{mid}_fwd_idt")
    rec_dt  = c3.date_input("Receipt Date",value=date.today(),key=f"{mid}_fwd_rdt")
    c4,c5   = st.columns(2)
    inv_amt = c4.number_input("Total Amount (Rs.)",min_value=0.0,step=100.0,key=f"{mid}_fwd_amt")
    inv_rem = c5.text_input("Remarks",key=f"{mid}_fwd_rem")
    inv_scan= st.file_uploader("Invoice Scan",type=["pdf","jpg","jpeg","png"],key=f"{mid}_fwd_scan")

    st.markdown("#### Step 3 — Department & Lab")
    depts = [dict(r) for r in _fa("SELECT * FROM tbl_departments WHERE is_active=1 ORDER BY dept_name")]
    dm    = {d["dept_name"]: d for d in depts}
    dept_name = st.selectbox("Department *",list(dm.keys()),key=f"{mid}_fwd_dept")
    dept  = dm[dept_name]
    locs  = [dict(r) for r in _fa("SELECT * FROM tbl_locations WHERE dept_id=? AND is_active=1",(dept["dept_id"],))]
    lm    = {"— No specific location —":None}; lm.update({l["location_name"]:l["location_id"] for l in locs})
    to_loc = st.selectbox("Location",list(lm.keys()),key=f"{mid}_fwd_loc")

    st.markdown("#### Step 4 — Assign to Data Entry Staff")
    # Get Lab-IC users for this module
    staff = [dict(r) for r in _fa("""
        SELECT u.user_id, u.full_name, a.role_name FROM tbl_users u
        JOIN tbl_user_module_access a ON a.user_id=u.user_id
        JOIN tbl_modules m ON m.module_id=a.module_id
        WHERE m.module_code=? AND a.role_name IN ('Lab-IC','Technician','Coordinator') AND u.is_active=1
    """,(mod["module_code"],))]
    if not staff: st.warning("No Lab-IC/Technician assigned to this module."); return
    staff_opts = {f"{s['full_name']} ({s['role_name']})": s["user_id"] for s in staff}
    sel_staff  = st.selectbox("Assign to *",list(staff_opts.keys()),key=f"{mid}_fwd_staff")
    staff_id   = staff_opts[sel_staff]

    if st.button("Forward to Data Entry Staff",type="primary",use_container_width=True,key=f"{mid}_fwd_submit"):
        errs = []
        if not sel_s or sel_s=="— select —": errs.append("Select supplier.")
        if not inv_no.strip(): errs.append("Invoice number required.")
        if errs:
            for e in errs: st.error(e); return
        try:
            conn = get_conn()
            inv_id = conn.execute("""
                INSERT INTO tbl_invoices (module_id,invoice_number,invoice_date,supplier_id,
                    total_amount,received_date,received_by,remarks)
                VALUES (?,?,?,?,?,?,?,?)
            """,(mid,inv_no.strip(),str(inv_dt),sup_id,inv_amt,str(rec_dt),user["user_id"],inv_rem)).lastrowid
            conn.commit()
            scan_path = save_scan(inv_scan,inv_no.strip()) if inv_scan else None
            if scan_path:
                conn.execute("UPDATE tbl_invoices SET invoice_scan_path=? WHERE invoice_id=?",(scan_path,inv_id))
            proc_id = conn.execute("""
                INSERT INTO tbl_proc_forward (module_id,invoice_id,dept_id,location_id,
                    forwarded_by,assigned_to,entry_status)
                VALUES (?,?,?,?,?,?,'FORWARDED')
            """,(mid,inv_id,dept["dept_id"],lm[to_loc],user["user_id"],staff_id)).lastrowid
            conn.commit(); conn.close()
            st.session_state[f"_proc_msg_{mid}"] = ("s",
                f"Forwarded Ref #{proc_id} — Invoice {inv_no.strip()} assigned to {sel_staff.split('(')[0].strip()}.")
            st.rerun()
        except Exception as ex: st.error(f"Failed: {ex}")


# ══ TAB 2 — JOINT DATA ENTRY ══════════════════════════════════════
def _joint_entry(user, role, mod, mid):
    if role not in ("SuperAdmin","SysAdmin","Lab-IC","Technician","Coordinator"):
        st.info("Joint Data Entry is for Lab-IC / Technician staff."); return

    st.subheader("Joint Data Entry")
    st.info("Enter asset details for forwarded invoices. Both assignee and co-signer must acknowledge.")

    # Get forwarded entries for this user
    if role in ("SuperAdmin","SysAdmin","Coordinator"):
        entries = [dict(r) for r in _fa("""
            SELECT pf.*, inv.invoice_number, inv.invoice_date, inv.total_amount, inv.invoice_scan_path,
                   s.supplier_name, d.dept_name, l.location_name, u.full_name AS assigned_to_name
            FROM tbl_proc_forward pf
            JOIN tbl_invoices inv ON inv.invoice_id=pf.invoice_id
            LEFT JOIN tbl_suppliers s ON s.supplier_id=inv.supplier_id
            JOIN tbl_departments d ON d.dept_id=pf.dept_id
            LEFT JOIN tbl_locations l ON l.location_id=pf.location_id
            LEFT JOIN tbl_users u ON u.user_id=pf.assigned_to
            WHERE pf.module_id=? AND pf.entry_status IN ('FORWARDED','CORRECTION REQUIRED')
            ORDER BY pf.created_at DESC
        """,(mid,))]
    else:
        entries = [dict(r) for r in _fa("""
            SELECT pf.*, inv.invoice_number, inv.invoice_date, inv.total_amount, inv.invoice_scan_path,
                   s.supplier_name, d.dept_name, l.location_name, u.full_name AS assigned_to_name
            FROM tbl_proc_forward pf
            JOIN tbl_invoices inv ON inv.invoice_id=pf.invoice_id
            LEFT JOIN tbl_suppliers s ON s.supplier_id=inv.supplier_id
            JOIN tbl_departments d ON d.dept_id=pf.dept_id
            LEFT JOIN tbl_locations l ON l.location_id=pf.location_id
            LEFT JOIN tbl_users u ON u.user_id=pf.assigned_to
            WHERE pf.module_id=? AND pf.assigned_to=?
              AND pf.entry_status IN ('FORWARDED','CORRECTION REQUIRED')
        """,(mid, user["user_id"]))]

    if not entries: st.success("No forwarded invoices pending entry."); return

    opts   = {f"#{e['proc_id']} — {e['invoice_number']} | {e['supplier_name']} | {e['dept_name']} | {e['entry_status']}": e for e in entries}
    sel    = st.selectbox("Select Forwarded Invoice",list(opts.keys()),key=f"{mid}_je_sel")
    e      = opts[sel]

    st.markdown(f"**Invoice:** `{e['invoice_number']}` | **Supplier:** {e['supplier_name']} | "
                f"**Dept:** {e['dept_name']} | **Amount:** Rs.{float(e['total_amount']):,.2f}")

    if e.get("invoice_scan_path"):
        with st.expander("View Invoice Scan"):
            show_scan(e["invoice_scan_path"])

    if e.get("correction_remarks"):
        st.warning(f"**HoD Correction Remarks:** {e['correction_remarks']}")

    # Co-signer
    st.markdown("#### Co-signer (Technical Support Staff)")
    cosigners = [dict(r) for r in _fa("""
        SELECT u.user_id, u.full_name, a.role_name FROM tbl_users u
        JOIN tbl_user_module_access a ON a.user_id=u.user_id
        JOIN tbl_modules m ON m.module_id=a.module_id
        WHERE m.module_code=? AND u.is_active=1 AND u.user_id != ?
    """,(mod["module_code"],user["user_id"]))]
    if not cosigners: st.warning("No other users for co-signing."); return
    cos_opts  = {f"{c['full_name']} ({c['role_name']})": c["user_id"] for c in cosigners}
    cos_name  = st.selectbox("Co-signer *",list(cos_opts.keys()),key=f"{mid}_je_cos")
    lan_id    = cos_opts[cos_name]

    # Asset entry
    types = [dict(r) for r in _fa("SELECT * FROM tbl_item_types WHERE module_id=? AND is_active=1 ORDER BY type_name",(mid,))]
    if not types: st.warning("No item types configured."); return
    type_map = {t["type_name"]: t for t in types}

    st.markdown("#### Asset Details")
    n_types  = st.number_input("Number of asset types",min_value=1,max_value=20,value=1,key=f"{mid}_je_nt")
    rows = []
    for i in range(int(n_types)):
        st.markdown(f"---\n**Asset Type {i+1}**")
        r1,r2,r3,r4 = st.columns([2,1,2,2])
        atype  = r1.selectbox("Type *",list(type_map.keys()),key=f"{mid}_je_at_{i}")
        qty    = r2.number_input("Qty *",min_value=1,value=1,key=f"{mid}_je_q_{i}")
        desc   = r3.text_input("Description *",key=f"{mid}_je_d_{i}")
        make   = r4.text_input("Make/Brand",key=f"{mid}_je_mk_{i}")
        r5,r6,r7,r8 = st.columns(4)
        model  = r5.text_input("Model",key=f"{mid}_je_mo_{i}")
        serial = r6.text_input("Serial No (1st unit)",key=f"{mid}_je_sn_{i}")
        cost   = r7.number_input("Cost/Unit (Rs.) *",min_value=0.0,step=100.0,key=f"{mid}_je_c_{i}")
        pdate  = r8.text_input("Purchase Date",value=str(e["invoice_date"] or date.today())[:10],key=f"{mid}_je_pd_{i}")
        w1,w2  = st.columns(2)
        wf = w1.text_input("Warranty From",key=f"{mid}_je_wf_{i}")
        wt = w2.text_input("Warranty To",key=f"{mid}_je_wt_{i}")
        tinfo  = type_map[atype]
        fields = get_dynamic_fields(tinfo["type_id"])
        cfg    = render_dynamic_fields(fields,key_prefix=f"{mid}_je_f{i}") if fields else {}
        rows.append({"tinfo":tinfo,"qty":int(qty),"desc":desc,"make":make,"model":model,
                     "serial":serial,"cost":float(cost),"pdate":pdate,"wf":wf,"wt":wt,"cfg":cfg})

    grand = sum(r["qty"]*r["cost"] for r in rows)
    st.markdown(f"**Grand Total: Rs.{grand:,.2f}**")
    notes = st.text_area("Entry Notes",key=f"{mid}_je_notes",height=60)

    if st.button("Submit for HoD Approval",type="primary",use_container_width=True,key=f"{mid}_je_submit"):
        errs = []
        for i,r in enumerate(rows):
            if not r["desc"].strip(): errs.append(f"Type {i+1}: Description required.")
            if r["cost"]<=0: errs.append(f"Type {i+1}: Cost must be > 0.")
        if errs:
            for er in errs: st.error(er); return
        try:
            conn = get_conn()
            created = []
            for r in rows:
                ti = r["tinfo"]
                for u in range(r["qty"]):
                    serial = f"{r['serial']}-{u+1:03d}" if r["qty"]>1 and r["serial"] else r["serial"]
                    uid    = generate_item_id(mod["module_code"],e.get("dept_code","DEPT"),ti["id_prefix"],r["pdate"])
                    item_id = conn.execute("""
                        INSERT INTO tbl_items (module_id,type_id,unique_item_id,invoice_id,
                            description,make,model,serial_number,cost_per_unit,purchase_date,
                            warranty_from,warranty_to,dept_id,location_id,item_status,created_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,(mid,ti["type_id"],uid,e["invoice_id"],r["desc"],r["make"],r["model"],serial,
                         r["cost"],r["pdate"],r["wf"] or None,r["wt"] or None,
                         e["dept_id"],e.get("location_id"),"WORKING",user["user_id"])).lastrowid
                    conn.commit()
                    if r["cfg"]: save_field_values(conn,item_id,ti["type_id"],r["cfg"])
                    created.append(uid)
                # DSR + CSR entries
                conn.execute("""
                    INSERT INTO tbl_dept_stock (module_id,dept_id,invoice_id,type_id,description,qty_received,cost_per_unit)
                    VALUES (?,?,?,?,?,?,?)
                """,(mid,e["dept_id"],e["invoice_id"],ti["type_id"],r["desc"],r["qty"],r["cost"]))
                conn.execute("""
                    INSERT OR IGNORE INTO tbl_stock_register (module_id,invoice_id,type_id,description,qty_received,qty_issued,cost_per_unit)
                    VALUES (?,?,?,?,?,?,?)
                """,(mid,e["invoice_id"],ti["type_id"],r["desc"],r["qty"],r["qty"],r["cost"]))
            # Update proc_forward status
            conn.execute("""
                UPDATE tbl_proc_forward SET entry_status='PENDING HOD APPROVAL',
                    assigned_to=?,lan_staff_id=?,revision_count=revision_count+1
                WHERE proc_id=?
            """,(user["user_id"],lan_id,e["proc_id"]))
            conn.commit(); conn.close()
            st.session_state[f"_proc_msg_{mid}"] = ("s",
                f"{sum(r['qty'] for r in rows)} asset(s) submitted for HoD approval. IDs: {', '.join(created[:5])}")
            st.rerun()
        except Exception as ex: st.error(f"Failed: {ex}")


# ══ TAB 3 — PENDING APPROVALS ════════════════════════════════════
def _approvals(user, role, mod, mid):
    if role not in ("SuperAdmin","SysAdmin","HoD","Coordinator"):
        st.info("Approvals are for HoD / SysAdmin."); return

    st.subheader("Pending HoD Approvals")
    entries = [dict(r) for r in _fa("""
        SELECT pf.*, inv.invoice_number, inv.total_amount, inv.invoice_scan_path,
               s.supplier_name, d.dept_name, u.full_name AS assigned_to_name
        FROM tbl_proc_forward pf
        JOIN tbl_invoices inv ON inv.invoice_id=pf.invoice_id
        LEFT JOIN tbl_suppliers s ON s.supplier_id=inv.supplier_id
        JOIN tbl_departments d ON d.dept_id=pf.dept_id
        LEFT JOIN tbl_users u ON u.user_id=pf.assigned_to
        WHERE pf.module_id=? AND pf.entry_status='PENDING HOD APPROVAL'
        ORDER BY pf.created_at DESC
    """,(mid,))]

    if not entries: st.success("No entries pending approval."); return

    opts = {f"#{e['proc_id']} — {e['invoice_number']} | {e['supplier_name']} | {e['dept_name']}": e for e in entries}
    sel  = st.selectbox("Select Entry",list(opts.keys()),key=f"{mid}_appr_sel")
    e    = opts[sel]

    # Show items registered under this invoice
    items = [dict(r) for r in _fa("""
        SELECT i.unique_item_id, it.type_name, i.description, i.make, i.model,
               i.serial_number, i.cost_per_unit, i.warranty_to
        FROM tbl_items i JOIN tbl_item_types it ON it.type_id=i.type_id
        WHERE i.invoice_id=? AND i.module_id=?
    """,(e["invoice_id"],mid))]

    if items:
        st.markdown(f"**{len(items)} asset(s) entered by {e['assigned_to_name']}:**")
        df = pd.DataFrame([{
            "UID":i["unique_item_id"],"Type":i["type_name"],"Description":i["description"],
            "Make":i.get("make","—"),"Serial":i.get("serial_number","—"),
            "Cost Rs.":i["cost_per_unit"],"Warranty To":i.get("warranty_to","—"),
        } for i in items])
        st.dataframe(df,use_container_width=True,hide_index=True)

    if e.get("invoice_scan_path"):
        with st.expander("View Invoice Scan"):
            show_scan(e["invoice_scan_path"])

    st.divider()
    dec = st.radio("Decision",["Approve","Return for Correction"],key=f"{mid}_appr_dec")
    rem = st.text_area("Remarks *",key=f"{mid}_appr_rem",height=80)

    if st.button("Submit Decision",type="primary",key=f"{mid}_appr_submit"):
        if not rem.strip(): st.error("Remarks required."); return
        try:
            conn = get_conn()
            if dec == "Approve":
                conn.execute("UPDATE tbl_proc_forward SET entry_status='APPROVED',hod_user_id=? WHERE proc_id=?",
                             (user["user_id"],e["proc_id"]))
                st.session_state[f"_proc_msg_{mid}"] = ("s","Entry approved. Assets are now live.")
            else:
                conn.execute("""
                    UPDATE tbl_proc_forward SET entry_status='CORRECTION REQUIRED',
                        correction_remarks=? WHERE proc_id=?
                """,(rem.strip(),e["proc_id"]))
                # Remove items entered (need re-entry)
                conn.execute("UPDATE tbl_items SET is_deleted=1 WHERE invoice_id=? AND module_id=?",
                             (e["invoice_id"],mid))
                st.session_state[f"_proc_msg_{mid}"] = ("s","Returned for correction.")
            conn.commit(); conn.close()
            st.rerun()
        except Exception as ex: st.error(f"Failed: {ex}")


# ══ TAB 4 — PROCUREMENT LOG ══════════════════════════════════════
def _log(user, role, mod, mid):
    st.subheader("Procurement Log")
    rows = [dict(r) for r in _fa("""
        SELECT pf.proc_id, pf.entry_status, pf.created_at,
               inv.invoice_number, inv.total_amount,
               s.supplier_name, d.dept_name,
               u1.full_name AS forwarded_by_name,
               u2.full_name AS assigned_to_name
        FROM tbl_proc_forward pf
        JOIN tbl_invoices inv ON inv.invoice_id=pf.invoice_id
        LEFT JOIN tbl_suppliers s ON s.supplier_id=inv.supplier_id
        JOIN tbl_departments d ON d.dept_id=pf.dept_id
        JOIN tbl_users u1 ON u1.user_id=pf.forwarded_by
        LEFT JOIN tbl_users u2 ON u2.user_id=pf.assigned_to
        WHERE pf.module_id=? ORDER BY pf.created_at DESC
    """,(mid,))]
    if not rows: st.info("No procurement records."); return
    df = pd.DataFrame([{
        "Ref #":r["proc_id"],"Invoice":r["invoice_number"],"Supplier":r.get("supplier_name","—"),
        "Dept":r.get("dept_name","—"),"Amount Rs.":r["total_amount"],
        "Status":r["entry_status"],"Forwarded By":r.get("forwarded_by_name",""),
        "Assigned To":r.get("assigned_to_name","—"),"Date":str(r.get("created_at",""))[:10],
    } for r in rows])
    st.dataframe(df,use_container_width=True,hide_index=True)
    export_df(df,f"{mod['module_code']}_Procurement_Log.xlsx")
