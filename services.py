"""Business rules and transaction orchestration (FR-04..FR-08, BR-01..BR-07).

All stock-changing writes happen inside explicit transactions so that stock,
movements and sales succeed or fail together.
"""
from decimal import Decimal, ROUND_HALF_UP
import sqlite3


class ValidationError(Exception):
    """User-facing validation / business-rule failure."""


def parse_int(value, label, minimum=0):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{label} must be a whole number.")
    if n < minimum:
        raise ValidationError(f"{label} must be {'greater than 0' if minimum == 1 else 'at least ' + str(minimum)}.")
    return n


def parse_money(value, label):
    """Return float rounded to 2dp, or None if blank. Rejects negatives."""
    value = (value or "").strip()
    if value == "":
        return None
    try:
        d = Decimal(value)
    except Exception:
        raise ValidationError(f"{label} must be a number.")
    if not d.is_finite():
        raise ValidationError(f"{label} must be a number.")
    if d < 0:
        raise ValidationError(f"{label} cannot be negative.")
    return float(d.quantize(Decimal("0.01"), ROUND_HALF_UP))


def _money(d):
    return float(Decimal(d).quantize(Decimal("0.01"), ROUND_HALF_UP))


def record_movement(db, product_id, user_id, movement_type, quantity, notes=None):
    """Stock-In / Stock-Out. Returns the resulting quantity."""
    if movement_type not in ("IN", "OUT"):
        raise ValidationError("Movement type must be IN or OUT.")
    quantity = parse_int(quantity, "Quantity", 1)
    notes = (notes or "").strip() or None
    if notes and len(notes) > 500:
        raise ValidationError("Notes must be 500 characters or fewer.")
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT quantity FROM products WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise ValidationError("Product not found.")
        if movement_type == "OUT":
            if quantity > row["quantity"]:
                raise ValidationError(
                    f"Insufficient stock: requested {quantity}, available {row['quantity']}.")
            cur = db.execute(
                "UPDATE products SET quantity = quantity - ? WHERE product_id = ? AND quantity >= ?",
                (quantity, product_id, quantity))
            if cur.rowcount != 1:
                raise ValidationError("Insufficient stock.")
        else:
            db.execute("UPDATE products SET quantity = quantity + ? WHERE product_id = ?",
                       (quantity, product_id))
        db.execute(
            "INSERT INTO stock_movements (product_id, user_id, movement_type, quantity, notes) "
            "VALUES (?, ?, ?, ?, ?)", (product_id, user_id, movement_type, quantity, notes))
        new_qty = db.execute("SELECT quantity FROM products WHERE product_id = ?",
                             (product_id,)).fetchone()["quantity"]
        db.execute("COMMIT")
        return new_qty
    except Exception:
        db.execute("ROLLBACK")
        raise


def create_sale(db, user_id, lines):
    """lines: iterable of (product_id_raw, quantity_raw). Returns new sale_id.

    Duplicate product lines are aggregated before the availability check (FR-08).
    Totals are computed on the server from stored unit prices (FR-06).
    """
    wanted = {}
    for pid_raw, qty_raw in lines:
        if str(pid_raw).strip() == "" and str(qty_raw).strip() == "":
            continue  # ignore fully blank rows
        pid = parse_int(pid_raw, "Product", 1)
        qty = parse_int(qty_raw, "Quantity", 1)
        wanted[pid] = wanted.get(pid, 0) + qty
    if not wanted:
        raise ValidationError("Add at least one product line to the sale.")

    db.execute("BEGIN IMMEDIATE")
    try:
        priced = []
        for pid, qty in wanted.items():
            p = db.execute("SELECT product_id, product_name, unit_price, quantity "
                           "FROM products WHERE product_id = ?", (pid,)).fetchone()
            if p is None:
                raise ValidationError(f"Product #{pid} does not exist.")
            if p["unit_price"] is None:
                raise ValidationError(f"'{p['product_name']}' has no unit price set; set one before selling.")
            if qty > p["quantity"]:
                raise ValidationError(
                    f"Insufficient stock for '{p['product_name']}': requested {qty}, available {p['quantity']}.")
            line_total = _money(Decimal(str(p["unit_price"])) * qty)
            priced.append((pid, qty, p["unit_price"], line_total))
        total = _money(sum(Decimal(str(x[3])) for x in priced))
        sale_id = db.execute("INSERT INTO sales (user_id, total_amount) VALUES (?, ?)",
                             (user_id, total)).lastrowid
        for pid, qty, unit_price, line_total in priced:
            db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, line_total) "
                       "VALUES (?, ?, ?, ?, ?)", (sale_id, pid, qty, unit_price, line_total))
            cur = db.execute("UPDATE products SET quantity = quantity - ? "
                             "WHERE product_id = ? AND quantity >= ?", (qty, pid, qty))
            if cur.rowcount != 1:
                raise ValidationError("Insufficient stock.")
            db.execute("INSERT INTO stock_movements (product_id, user_id, movement_type, quantity, notes) "
                       "VALUES (?, ?, 'OUT', ?, ?)", (pid, user_id, qty, f"Sale #{sale_id}"))
        db.execute("COMMIT")
        return sale_id
    except Exception:
        db.execute("ROLLBACK")
        raise
