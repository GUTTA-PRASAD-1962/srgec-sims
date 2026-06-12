"""
setup_sims.py — Initialize SRGEC-SIMS database
Run once: python setup_sims.py
"""
import sqlite3, hashlib
from pathlib import Path
from datetime import datetime

DB_PATH = Path("db/sims_data.db")
DB_PATH.parent.mkdir(exist_ok=True)

from db.schema import init_db
init_db(str(DB_PATH))
print("Schema created")

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def h(p): return hashlib.sha256(p.encode()).hexdigest()
def ins(sql, params):
    try: conn.execute(sql, params); return True
    except: return False

# Roles
for r in [("SuperAdmin","Super Administrator",1),("SysAdmin","System Administrator",0),
          ("HoD","Head of Department",0),("Coordinator","Module Coordinator",0),
          ("Technician","Technician / Engineer",0),("Lab-IC","Lab In-Charge",0),("User","Regular User",0)]:
    ins("INSERT INTO tbl_roles (role_name,role_label,is_super_admin) VALUES (?,?,?)",r)

# Modules
for m in [
    ("IT",   "IT Infrastructure (IIMS)",     "💻","#1B4F9A",1,1),
    ("UPS",  "UPS Management",               "⚡","#E65100",1,2),
    ("ELEC", "Electrical Maintenance",       "🔌","#F57F17",1,3),
    ("CIVIL","Civil Infrastructure",         "🏗","#2E7D32",1,4),
    ("FURN", "Furniture Management",         "🪑","#6A1B9A",1,5),
    ("STAT", "Stationery Management",        "📝","#00838F",0,6),
    ("LCD",  "LCD Projector Management",     "📽","#AD1457",1,7),
    ("CCTV", "CC Camera Management",         "📷","#37474F",1,8),
]:
    ins("INSERT INTO tbl_modules (module_code,module_name,module_icon,module_color,has_maintenance,sort_order) VALUES (?,?,?,?,?,?)",m)

conn.commit()
mids = {r["module_code"]:r["module_id"] for r in conn.execute("SELECT module_id,module_code FROM tbl_modules").fetchall()}

# Departments
for d in [("Computer Science & Engineering","CSE"),("Electrical & Electronics Engineering","EEE"),
          ("Electronics & Communication Engineering","ECE"),("Civil Engineering","CIVIL"),
          ("Mechanical Engineering","MECH"),("Information Technology","IT"),
          ("Artificial Intelligence & Data Science","AIDS"),("Administration","ADMIN"),("Library","LIB")]:
    ins("INSERT INTO tbl_departments (dept_name,dept_code) VALUES (?,?)",d)

conn.commit()
dept_ids = {r["dept_code"]:r["dept_id"] for r in conn.execute("SELECT dept_id,dept_code FROM tbl_departments").fetchall()}

# SuperAdmin
try:
    conn.execute("""
        INSERT INTO tbl_users (username,password_hash,full_name,employee_id,is_active,is_super_admin,created_at)
        VALUES (?,?,?,?,1,1,?)
    """,("superadmin",h("admin@sims123"),"Super Administrator","EMP-SUPER-001",now))
    print("SuperAdmin: superadmin / admin@sims123")
except: print("SuperAdmin already exists")

conn.commit()
sa_id = conn.execute("SELECT user_id FROM tbl_users WHERE username='superadmin'").fetchone()["user_id"]

# Grant SuperAdmin access to all modules
for mc, mid in mids.items():
    try: conn.execute("INSERT INTO tbl_user_module_access (user_id,module_id,role_name,is_active,granted_at) VALUES (?,?,?,1,?)",
                      (sa_id,mid,"SuperAdmin",now))
    except: pass

# Item types for all modules
item_types = [
    ("IT","CPU","CPU","CPU",1),("IT","Printer","PRN","PRN",0),("IT","Scanner","SCN","SCN",0),
    ("IT","Switch","SWT","SWT",1),("IT","Server","SRV","SRV",1),
    ("UPS","UPS Unit","UPS","UPS",1),("UPS","Battery Bank","BAT","BAT",1),("UPS","Inverter","INV","INV",1),
    ("ELEC","Generator","GEN","GEN",1),("ELEC","Transformer","TRF","TRF",1),
    ("ELEC","Distribution Board","DB","DB",1),("ELEC","Stabilizer","STB","STB",1),
    ("CIVIL","Building/Block","BLD","BLD",0),("CIVIL","Plumbing","PLB","PLB",0),("CIVIL","Flooring","FLR","FLR",0),
    ("FURN","Chair","CHR","CHR",0),("FURN","Table/Desk","TBL","TBL",0),
    ("FURN","Almirah","ALM","ALM",0),("FURN","Bench","BNC","BNC",0),
    ("LCD","LCD Projector","LCD","LCD",1),("LCD","Projection Screen","SCR","SCR",0),
    ("CCTV","IP Camera","CAM","CAM",1),("CCTV","DVR/NVR","DVR","DVR",1),("CCTV","Monitor","MON","MON",0),
]
for mc,tn,tc,pf,cfg in item_types:
    mid = mids.get(mc)
    if mid: ins("INSERT INTO tbl_item_types (module_id,type_name,type_code,id_prefix,has_config) VALUES (?,?,?,?,?)",(mid,tn,tc,pf,cfg))

conn.commit()

# UPS field definitions
ups_type = conn.execute("SELECT type_id FROM tbl_item_types WHERE type_code='UPS'").fetchone()
if ups_type:
    tid = ups_type["type_id"]
    for f in [
        ("kva_rating","KVA Rating","number",1,1,"e.g. 5",0),
        ("va_capacity","VA Capacity","number",0,1,"e.g. 5000",1),
        ("input_voltage","Input Voltage Range","text",0,1,"e.g. 160-260V",2),
        ("output_voltage","Output Voltage","text",0,1,"e.g. 230V",3),
        ("battery_count","Number of Batteries","number",1,0,"e.g. 4",4),
        ("battery_make","Battery Make","text",0,0,"e.g. Exide",5),
        ("battery_ah","Battery AH Rating","number",0,0,"e.g. 42",6),
        ("backup_time","Backup Time (minutes)","number",0,0,"e.g. 30",7),
        ("inverter_make","Inverter Make","text",0,0,"",8),
        ("last_service","Last Service Date","date",0,0,"",9),
        ("amc_vendor","AMC Vendor","text",0,0,"",10),
        ("amc_from","AMC From","date",0,0,"",11),
        ("amc_to","AMC To","date",0,0,"",12),
    ]:
        fn,fl,ft,req,cfg,ph,order = f
        ins("INSERT INTO tbl_field_defs (type_id,field_name,field_label,field_type,is_required,is_config_field,placeholder,sort_order) VALUES (?,?,?,?,?,?,?,?)",
            (tid,fn,fl,ft,req,cfg,ph,order))

# UPS Workflow rules
ups_mid = mids.get("UPS")
if ups_mid:
    for r in [
        ("OPEN","UNDER REVIEW","Forward to Coordinator","HoD,Coordinator,SysAdmin",1,0,0),
        ("UNDER REVIEW","ASSIGNED","Assign to Technician","SysAdmin,Coordinator",1,1,1),
        ("ASSIGNED","UNDER REPAIR","Start Repair / Service","Technician",1,0,2),
        ("ASSIGNED","PARTS NEEDED","Parts Required — Raise Indent","Technician",1,0,3),
        ("PARTS NEEDED","PARTS ORDERED","Authorise & Order Parts","SysAdmin,Coordinator",1,0,4),
        ("PARTS ORDERED","UNDER REPAIR","Parts Received — Hand Over","SysAdmin",1,0,5),
        ("UNDER REPAIR","REPAIRED","Service / Repair Complete","Technician",1,0,6),
        ("REPAIRED","VERIFIED","Verify — Working Correctly","Lab-IC,User",1,0,7),
        ("VERIFIED","CLOSED","Acknowledge & Forward","HoD",1,0,8),
        ("CLOSED","FILE CLOSED","Close File","SysAdmin",1,0,9),
        ("OPEN","REJECTED","Reject Complaint","SysAdmin,Coordinator",1,0,10),
    ]:
        fs,ts,al,roles,rc,ra,order = r
        ins("INSERT INTO tbl_workflow_rules (module_id,from_status,to_status,action_label,allowed_roles,requires_comment,requires_assignee,sort_order) VALUES (?,?,?,?,?,?,?,?)",
            (ups_mid,fs,ts,al,roles,rc,ra,order))
    print("UPS workflow rules seeded")

# Copy same workflow rules to ELEC, CIVIL, FURN, LCD, CCTV
for code in ["ELEC","CIVIL","FURN","LCD","CCTV"]:
    other_mid = mids.get(code)
    if not other_mid: continue
    for r in [
        ("OPEN","UNDER REVIEW","Forward to Coordinator","HoD,Coordinator,SysAdmin",1,0,0),
        ("UNDER REVIEW","ASSIGNED","Assign to Technician","SysAdmin,Coordinator",1,1,1),
        ("ASSIGNED","UNDER REPAIR","Start Repair / Service","Technician",1,0,2),
        ("ASSIGNED","PARTS NEEDED","Parts Required — Raise Indent","Technician",1,0,3),
        ("PARTS NEEDED","PARTS ORDERED","Authorise & Order Parts","SysAdmin,Coordinator",1,0,4),
        ("PARTS ORDERED","UNDER REPAIR","Parts Received — Hand Over","SysAdmin",1,0,5),
        ("UNDER REPAIR","REPAIRED","Service / Repair Complete","Technician",1,0,6),
        ("REPAIRED","VERIFIED","Verify — Working Correctly","Lab-IC,User",1,0,7),
        ("VERIFIED","CLOSED","Acknowledge & Forward","HoD",1,0,8),
        ("CLOSED","FILE CLOSED","Close File","SysAdmin",1,0,9),
        ("OPEN","REJECTED","Reject Complaint","SysAdmin,Coordinator",1,0,10),
    ]:
        fs,ts,al,roles,rc,ra,order = r
        ins("INSERT INTO tbl_workflow_rules (module_id,from_status,to_status,action_label,allowed_roles,requires_comment,requires_assignee,sort_order) VALUES (?,?,?,?,?,?,?,?)",
            (other_mid,fs,ts,al,roles,rc,ra,order))

conn.commit()
conn.close()

print("\nSRGEC-SIMS v2 initialized!")
print("Run: python -m streamlit run app.py")
print("Login: superadmin / admin@sims123")
