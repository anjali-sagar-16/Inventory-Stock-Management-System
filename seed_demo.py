"""Demo data (about 10 rows per section). Loaded through the real business rules in services.py.

Run:  flask --app app seed-demo
Safe to re-run: it does nothing if products already exist.
"""
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

import services

DEMO_USER = ("demo", "demo12345", "Demo Admin", "admin")  # demo-only credentials

SUPPLIERS = [
    ("Sri Ganesh Stationery", "9876543210", "sales@sriganesh.example", "12 MG Road, Bengaluru"),
    ("Karnataka Paper Mills", "9845012345", "orders@kpm.example", "45 Peenya Industrial Area, Bengaluru"),
    ("Techno World Distributors", "9900112233", "hello@technoworld.example", "8 SP Road, Bengaluru"),
    ("Bright Office Supplies", "9886677889", "info@brightoffice.example", "27 Commercial Street, Bengaluru"),
    ("Mysore Writing Instruments", "9741122334", "sales@mysorepens.example", "3 Devaraja Mohalla, Mysuru"),
    ("Delta Electronics Pvt Ltd", "9731234567", "support@deltaelec.example", "101 Electronic City, Bengaluru"),
    ("Greenleaf Art Traders", "9620098765", "art@greenleaf.example", "16 Jayanagar, Bengaluru"),
    ("Southern Plastics", "9590011223", "contact@southplastics.example", "9 Hosur Road, Bengaluru"),
    ("Quick Print Solutions", "9448899001", "print@quickprint.example", "64 Indiranagar, Bengaluru"),
    ("Metro Wholesale Mart", "9380022446", "wholesale@metromart.example", "5 KR Market, Bengaluru"),
]

# code, name, description, price, reorder level, supplier index (0-based)
PRODUCTS = [
    ("NB-001", "A4 Notebook", "200 pages, ruled", 40, 20, 1),
    ("PN-002", "Ball Pen (Blue)", "0.7 mm, smooth ink", 10, 50, 4),
    ("PN-003", "Gel Pen Pack", "Pack of 5 assorted colours", 120, 15, 4),
    ("ST-004", "Stapler Medium", "Metal body, 24/6 pins", 85, 10, 3),
    ("EL-005", "USB Flash Drive 32GB", "USB 3.0", 450, 8, 2),
    ("EL-006", "Wireless Mouse", "2.4 GHz, silent click", 650, 6, 5),
    ("EL-007", "LED Desk Lamp", "Rechargeable, 3 brightness levels", 799, 5, 5),
    ("WB-008", "Whiteboard Marker Set", "4 colours, refillable", 150, 12, 0),
    ("DS-009", "A3 Drawing Sheets (Pack)", "Pack of 25 sheets", 95, 10, 6),
    ("SN-010", "Sticky Notes Pad", "3x3 inch, 100 sheets", 35, 25, 9),
]

# (product code, type, qty, note, days ago)
MOVEMENTS = [
    ("NB-001", "IN", 100, "Opening stock", 10),
    ("PN-002", "IN", 300, "Opening stock", 10),
    ("PN-003", "IN", 60, "Opening stock", 10),
    ("ST-004", "IN", 30, "Opening stock", 10),
    ("EL-005", "IN", 40, "Opening stock", 10),
    ("EL-006", "IN", 25, "Opening stock", 10),
    ("EL-007", "IN", 20, "Opening stock", 10),
    ("WB-008", "IN", 50, "Opening stock", 10),
    ("DS-009", "IN", 40, "Opening stock", 10),
    ("SN-010", "IN", 120, "Opening stock", 10),
    ("EL-005", "IN", 10, "Restock from supplier", 6),
    ("EL-006", "OUT", 2, "Damaged in storage", 7),
]

# list of (days ago, [(product code, qty), ...])
SALES = [
    (9, [("NB-001", 5), ("PN-002", 20)]),
    (8, [("EL-007", 3), ("EL-006", 4)]),
    (7, [("ST-004", 6), ("SN-010", 20), ("WB-008", 2)]),
    (6, [("EL-005", 5), ("EL-006", 3)]),
    (5, [("EL-007", 4), ("NB-001", 10), ("PN-003", 3)]),
    (4, [("SN-010", 30), ("ST-004", 5), ("DS-009", 6)]),
    (3, [("EL-006", 6), ("EL-007", 5), ("EL-005", 8)]),
    (2, [("ST-004", 10), ("SN-010", 48), ("PN-002", 40)]),
    (1, [("EL-007", 4), ("EL-006", 5), ("EL-005", 7)]),
    (0, [("NB-001", 15), ("PN-003", 5), ("WB-008", 4), ("DS-009", 4)]),
]


def _stamp(days_ago, hour=11):
    d = datetime.utcnow().replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    return d.strftime("%Y-%m-%d %H:%M:%S")


def seed(db):
    """db: an open sqlite3 connection (foreign keys on). Returns a dict of counts, or None if skipped."""
    if db.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
        return None
    user = db.execute("SELECT user_id FROM users WHERE is_active = 1 ORDER BY user_id LIMIT 1").fetchone()
    if user is None:
        u, p, n, r = DEMO_USER
        db.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
                   (u, generate_password_hash(p), n, r))
        user = db.execute("SELECT user_id FROM users WHERE username = ?", (u,)).fetchone()
    uid = user[0]

    sup_ids = [db.execute("INSERT INTO suppliers (supplier_name, phone, email, address) VALUES (?,?,?,?)", s).lastrowid
               for s in SUPPLIERS]
    ids = {}
    for code, name, desc, price, reorder, si in PRODUCTS:
        ids[code] = db.execute(
            "INSERT INTO products (product_code, product_name, description, unit_price, quantity, reorder_level, "
            "supplier_id) VALUES (?,?,?,?,0,?,?)", (code, name, desc, price, reorder, sup_ids[si])).lastrowid

    for code, mtype, qty, note, days in MOVEMENTS:
        services.record_movement(db, ids[code], uid, mtype, qty, note)
        db.execute("UPDATE stock_movements SET movement_date = ? "
                   "WHERE movement_id = (SELECT MAX(movement_id) FROM stock_movements)", (_stamp(days, 9),))
    for days, lines in SALES:
        sale_id = services.create_sale(db, uid, [(ids[c], q) for c, q in lines])
        db.execute("UPDATE sales SET sale_date = ? WHERE sale_id = ?", (_stamp(days), sale_id))
        db.execute("UPDATE stock_movements SET movement_date = ? WHERE notes = ?", (_stamp(days), f"Sale #{sale_id}"))
    return {"suppliers": len(SUPPLIERS), "products": len(PRODUCTS),
            "movements": db.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0], "sales": len(SALES)}
