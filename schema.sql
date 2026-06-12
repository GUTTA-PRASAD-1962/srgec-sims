-- ═══════════════════════════════════════════════════════════════════
-- SRGEC — Integrated Inventory & Maintenance System (SIMS)
-- Master Database Schema
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── 1. MODULES ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_modules (
    module_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    module_code     TEXT NOT NULL UNIQUE,   -- 'IT','UPS','ELEC','CIVIL','FURN','STAT','LCD','CCTV'
    module_name     TEXT NOT NULL,
    module_icon     TEXT DEFAULT '📦',
    module_color    TEXT DEFAULT '#1B4F9A',
    description     TEXT,
    is_active       INTEGER DEFAULT 1,
    sort_order      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 2. ROLES (global) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_roles (
    role_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name       TEXT NOT NULL UNIQUE,
    role_label      TEXT NOT NULL,
    is_super_admin  INTEGER DEFAULT 0,
    can_configure   INTEGER DEFAULT 0
);

-- ── 3. MODULE ROLES (role scoped to a module) ─────────────────────
CREATE TABLE IF NOT EXISTS tbl_module_roles (
    module_role_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    role_name       TEXT NOT NULL,
    role_label      TEXT NOT NULL,
    UNIQUE(module_id, role_name)
);

-- ── 4. DEPARTMENTS & LOCATIONS ────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_departments (
    dept_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name       TEXT NOT NULL,
    dept_code       TEXT NOT NULL UNIQUE,
    is_active       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tbl_locations (
    location_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_id         INTEGER REFERENCES tbl_departments(dept_id),
    location_name   TEXT NOT NULL,
    location_code   TEXT NOT NULL,
    location_type   TEXT DEFAULT 'ROOM',  -- ROOM, LAB, FLOOR, BLOCK
    is_active       INTEGER DEFAULT 1
);

-- ── 5. USERS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    employee_id     TEXT NOT NULL UNIQUE,
    email           TEXT,
    phone           TEXT,
    dept_id         INTEGER REFERENCES tbl_departments(dept_id),
    is_active       INTEGER DEFAULT 1,
    is_super_admin  INTEGER DEFAULT 0,
    last_login      TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 6. USER MODULE ACCESS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_user_module_access (
    access_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES tbl_users(user_id),
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    role_name       TEXT NOT NULL,
    is_active       INTEGER DEFAULT 1,
    granted_at      TEXT DEFAULT (datetime('now','localtime')),
    granted_by      INTEGER REFERENCES tbl_users(user_id),
    UNIQUE(user_id, module_id)
);

-- ── 7. ITEM TYPE DEFINITIONS (SuperAdmin configures) ──────────────
CREATE TABLE IF NOT EXISTS tbl_item_types (
    type_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    type_name       TEXT NOT NULL,
    type_code       TEXT NOT NULL,
    id_prefix       TEXT NOT NULL,
    description     TEXT,
    has_config      INTEGER DEFAULT 0,  -- has technical configuration fields
    is_active       INTEGER DEFAULT 1,
    UNIQUE(module_id, type_code)
);

-- ── 8. FIELD DEFINITIONS (SuperAdmin defines custom fields) ───────
CREATE TABLE IF NOT EXISTS tbl_field_definitions (
    field_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id         INTEGER NOT NULL REFERENCES tbl_item_types(type_id),
    field_name      TEXT NOT NULL,      -- internal key
    field_label     TEXT NOT NULL,      -- display label
    field_type      TEXT NOT NULL       -- text|number|date|dropdown|boolean|textarea
        CHECK(field_type IN ('text','number','date','dropdown','boolean','textarea')),
    field_options   TEXT,               -- JSON array for dropdown options
    is_required     INTEGER DEFAULT 0,
    is_config_field INTEGER DEFAULT 0,  -- belongs to technical config section
    sort_order      INTEGER DEFAULT 0,
    placeholder     TEXT,
    UNIQUE(type_id, field_name)
);

-- ── 9. SUPPLIERS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_suppliers (
    supplier_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name   TEXT NOT NULL,
    contact_person  TEXT,
    phone           TEXT,
    email           TEXT,
    address         TEXT,
    is_active       INTEGER DEFAULT 1
);

-- ── 10. INVOICES ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    invoice_number  TEXT NOT NULL,
    invoice_date    TEXT,
    supplier_id     INTEGER REFERENCES tbl_suppliers(supplier_id),
    total_amount    REAL DEFAULT 0,
    received_date   TEXT,
    received_by     INTEGER REFERENCES tbl_users(user_id),
    remarks         TEXT,
    invoice_scan_path TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 11. ITEMS (all modules) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_items (
    item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    type_id         INTEGER NOT NULL REFERENCES tbl_item_types(type_id),
    unique_item_id  TEXT NOT NULL UNIQUE,
    invoice_id      INTEGER REFERENCES tbl_invoices(invoice_id),
    supplier_id     INTEGER REFERENCES tbl_suppliers(supplier_id),
    description     TEXT NOT NULL,
    make            TEXT,
    model           TEXT,
    serial_number   TEXT,
    cost_per_unit   REAL DEFAULT 0,
    purchase_date   TEXT,
    warranty_from   TEXT,
    warranty_to     TEXT,
    dept_id         INTEGER REFERENCES tbl_departments(dept_id),
    location_id     INTEGER REFERENCES tbl_locations(location_id),
    item_status     TEXT DEFAULT 'WORKING'
        CHECK(item_status IN ('WORKING','NOT WORKING','UNDER REPAIR',
                              'UNDER MAINTENANCE','CONDEMNED','DISPOSED')),
    is_deleted      INTEGER DEFAULT 0,
    created_by      INTEGER REFERENCES tbl_users(user_id),
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 12. ITEM FIELD VALUES (dynamic fields) ────────────────────────
CREATE TABLE IF NOT EXISTS tbl_item_field_values (
    value_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES tbl_items(item_id),
    field_id        INTEGER NOT NULL REFERENCES tbl_field_definitions(field_id),
    field_value     TEXT,
    UNIQUE(item_id, field_id)
);

-- ── 13. STOCK REGISTER (central) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_stock_register (
    stock_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    invoice_id      INTEGER NOT NULL REFERENCES tbl_invoices(invoice_id),
    type_id         INTEGER NOT NULL REFERENCES tbl_item_types(type_id),
    description     TEXT NOT NULL,
    qty_received    INTEGER DEFAULT 0,
    qty_issued      INTEGER DEFAULT 0,
    cost_per_unit   REAL DEFAULT 0,
    entry_date      TEXT DEFAULT (datetime('now','localtime')),
    remarks         TEXT
);

-- ── 14. WORKFLOW RULES (SuperAdmin configures) ────────────────────
CREATE TABLE IF NOT EXISTS tbl_workflow_rules (
    rule_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    from_status     TEXT NOT NULL,
    to_status       TEXT NOT NULL,
    action_label    TEXT NOT NULL,
    allowed_roles   TEXT NOT NULL,   -- comma-separated role names
    requires_comment INTEGER DEFAULT 1,
    requires_assignee INTEGER DEFAULT 0,
    sort_order      INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1
);

-- ── 15. COMPLAINTS / CALLS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_calls (
    call_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    call_number     TEXT NOT NULL UNIQUE,
    item_id         INTEGER REFERENCES tbl_items(item_id),
    raised_by       INTEGER NOT NULL REFERENCES tbl_users(user_id),
    dept_id         INTEGER REFERENCES tbl_departments(dept_id),
    location_id     INTEGER REFERENCES tbl_locations(location_id),
    complaint_text  TEXT NOT NULL,
    call_status     TEXT NOT NULL DEFAULT 'OPEN',
    current_assignee INTEGER REFERENCES tbl_users(user_id),
    photo_path      TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 16. CALL WORKFLOW LOG ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_call_workflow (
    workflow_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id         INTEGER NOT NULL REFERENCES tbl_calls(call_id),
    action_by       INTEGER NOT NULL REFERENCES tbl_users(user_id),
    action_type     TEXT NOT NULL,
    action_comment  TEXT,
    from_status     TEXT NOT NULL,
    to_status       TEXT NOT NULL,
    attachment_path TEXT,
    action_at       TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 17. MAINTENANCE RECORDS ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_maintenance (
    maint_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    item_id         INTEGER NOT NULL REFERENCES tbl_items(item_id),
    call_id         INTEGER REFERENCES tbl_calls(call_id),
    maint_date      TEXT NOT NULL,
    maint_type      TEXT DEFAULT 'CORRECTIVE'
        CHECK(maint_type IN ('CORRECTIVE','PREVENTIVE','AMC')),
    problem_desc    TEXT,
    work_done       TEXT,
    parts_used      TEXT,
    cost            REAL DEFAULT 0,
    attended_by     INTEGER REFERENCES tbl_users(user_id),
    verified_by     INTEGER REFERENCES tbl_users(user_id),
    remarks         TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 18. SPARE PARTS INDENT ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_spare_indent (
    indent_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER NOT NULL REFERENCES tbl_modules(module_id),
    call_id         INTEGER REFERENCES tbl_calls(call_id),
    prepared_by     INTEGER NOT NULL REFERENCES tbl_users(user_id),
    description     TEXT NOT NULL,
    quantity        INTEGER DEFAULT 1,
    cost_per_unit   REAL DEFAULT 0,
    total_cost      REAL DEFAULT 0,
    source          TEXT,
    authorized_by   INTEGER REFERENCES tbl_users(user_id),
    authorized_at   TEXT,
    indent_status   TEXT DEFAULT 'PENDING'
        CHECK(indent_status IN ('PENDING','AUTHORIZED','PROCURED','CANCELLED')),
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 19. NOTIFICATIONS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_notifications (
    notif_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER REFERENCES tbl_modules(module_id),
    to_user_id      INTEGER NOT NULL REFERENCES tbl_users(user_id),
    from_user_id    INTEGER REFERENCES tbl_users(user_id),
    title           TEXT NOT NULL,
    message         TEXT,
    call_id         INTEGER REFERENCES tbl_calls(call_id),
    priority        TEXT DEFAULT 'NORMAL',
    is_read         INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ── 20. AUDIT LOG ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tbl_audit (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id       INTEGER REFERENCES tbl_modules(module_id),
    user_id         INTEGER REFERENCES tbl_users(user_id),
    action          TEXT NOT NULL,
    table_name      TEXT,
    record_id       INTEGER,
    old_value       TEXT,
    new_value       TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);
