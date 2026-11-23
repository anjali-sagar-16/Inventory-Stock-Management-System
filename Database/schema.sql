-- Inventory & Stock Management System: SQLite schema (agreed logical baseline).
-- Foreign keys are enforced per connection with PRAGMA foreign_keys = ON (see db.py).

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    role          TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('admin', 'staff')),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    phone         TEXT,
    email         TEXT,
    address       TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code  TEXT UNIQUE,
    product_name  TEXT NOT NULL,
    description   TEXT,
    unit_price    REAL CHECK (unit_price IS NULL OR unit_price >= 0),
    quantity      INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    supplier_id   INTEGER REFERENCES suppliers (supplier_id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products (product_id),
    user_id       INTEGER NOT NULL REFERENCES users (user_id),
    movement_type TEXT NOT NULL CHECK (movement_type IN ('IN', 'OUT')),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    notes         TEXT,
    movement_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (user_id),
    sale_date    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0)
);

CREATE TABLE IF NOT EXISTS sale_items (
    sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id      INTEGER NOT NULL REFERENCES sales (sale_id),
    product_id   INTEGER NOT NULL REFERENCES products (product_id),
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   REAL NOT NULL CHECK (unit_price >= 0),
    line_total   REAL NOT NULL CHECK (line_total >= 0)
);

CREATE INDEX IF NOT EXISTS idx_products_supplier   ON products (supplier_id);
CREATE INDEX IF NOT EXISTS idx_products_name       ON products (product_name);
CREATE INDEX IF NOT EXISTS idx_movements_product   ON stock_movements (product_id);
CREATE INDEX IF NOT EXISTS idx_movements_user      ON stock_movements (user_id);
CREATE INDEX IF NOT EXISTS idx_movements_date      ON stock_movements (movement_date);
CREATE INDEX IF NOT EXISTS idx_sales_user          ON sales (user_id);
CREATE INDEX IF NOT EXISTS idx_sales_date          ON sales (sale_date);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale     ON sale_items (sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product  ON sale_items (product_id);
