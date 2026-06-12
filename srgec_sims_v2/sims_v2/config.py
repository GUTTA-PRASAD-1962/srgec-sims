import os
from pathlib import Path

DB_PATH      = os.getenv("DB_PATH", "db/sims_data.db")
APP_TITLE    = "SRGEC — Integrated Inventory & Maintenance System"
APP_SHORT    = "SRGEC-SIMS"
APP_VERSION  = "v2.0"
COLLEGE_NAME = "Seshadri Rao Gudlavalleru Engineering College"
UPLOAD_DIR   = Path("uploads")

# Module registry — code → display info
MODULES = {
    "IT":    {"name":"IT Infrastructure (IIMS)",     "icon":"💻","color":"#1B4F9A","has_maintenance":True},
    "UPS":   {"name":"UPS Management",               "icon":"⚡","color":"#E65100","has_maintenance":True},
    "ELEC":  {"name":"Electrical Maintenance",       "icon":"🔌","color":"#F57F17","has_maintenance":True},
    "CIVIL": {"name":"Civil Infrastructure",         "icon":"🏗","color":"#2E7D32","has_maintenance":True},
    "FURN":  {"name":"Furniture Management",         "icon":"🪑","color":"#6A1B9A","has_maintenance":True},
    "STAT":  {"name":"Stationery Management",        "icon":"📝","color":"#00838F","has_maintenance":False},
    "LCD":   {"name":"LCD Projector Management",     "icon":"📽","color":"#AD1457","has_maintenance":True},
    "CCTV":  {"name":"CC Camera Management",         "icon":"📷","color":"#37474F","has_maintenance":True},
}
