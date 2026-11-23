"""FR-02 Products and FR-03 Suppliers."""
import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from database.db import get_db
from routes.auth import login_required
from services import ValidationError, parse_int, parse_money

bp = Blueprint("catalog", __name__)


# ------------------------------------------------------------------ products
def _suppliers(db):
    return db.execute("SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name").fetchall()


def _product_or_404(db, product_id):
    p = db.execute("SELECT p.*, s.supplier_name FROM products p "
                   "LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id WHERE p.product_id = ?",
                   (product_id,)).fetchone()
    if p is None:
        abort(404)
    return p


def _validate_product(db, form, product_id=None):
    name = (form.get("product_name") or "").strip()
    if not name:
        raise ValidationError("Product name is required.")
    if len(name) > 200:
        raise ValidationError("Product name must be 200 characters or fewer.")
    code = (form.get("product_code") or "").strip() or None
    price = parse_money(form.get("unit_price"), "Unit price")
    reorder = parse_int(form.get("reorder_level") or "0", "Reorder level", 0)
    supplier_id = (form.get("supplier_id") or "").strip()
    if supplier_id:
        supplier_id = parse_int(supplier_id, "Supplier", 1)
        if db.execute("SELECT 1 FROM suppliers WHERE supplier_id = ?", (supplier_id,)).fetchone() is None:
            raise ValidationError("Selected supplier does not exist.")
    else:
        supplier_id = None
    if code:
        dup = db.execute("SELECT product_id FROM products WHERE product_code = ? AND product_id IS NOT ?",
                         (code, product_id)).fetchone()
        if dup:
            raise ValidationError(f"Product code '{code}' is already in use.")
    return dict(product_name=name, product_code=code, description=(form.get("description") or "").strip() or None,
                unit_price=price, reorder_level=reorder, supplier_id=supplier_id)


@bp.route("/products")
@login_required
def products():
    q = (request.args.get("q") or "").strip()
    sql = ("SELECT p.*, s.supplier_name FROM products p LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id")
    args = ()
    if q:
        sql += " WHERE p.product_name LIKE ? OR p.product_code LIKE ?"
        args = (f"%{q}%", f"%{q}%")
    rows = get_db().execute(sql + " ORDER BY p.product_name", args).fetchall()
    return render_template("products.html", products=rows, q=q)


@bp.route("/products/new", methods=("GET", "POST"))
@login_required
def product_new():
    db = get_db()
    if request.method == "POST":
        try:
            v = _validate_product(db, request.form)
            # BR-07: quantity always starts at 0; opening stock goes through Stock-In.
            db.execute("INSERT INTO products (product_code, product_name, description, unit_price, "
                       "quantity, reorder_level, supplier_id) VALUES (?,?,?,?,0,?,?)",
                       (v["product_code"], v["product_name"], v["description"], v["unit_price"],
                        v["reorder_level"], v["supplier_id"]))
            flash("Product created with quantity 0. Record opening stock using Stock-In.", "success")
            return redirect(url_for("catalog.products"))
        except ValidationError as e:
            flash(str(e), "error")
        except sqlite3.IntegrityError:
            flash("Could not save product: product code must be unique.", "error")
    return render_template("product_form.html", product=request.form if request.method == "POST" else None,
                           suppliers=_suppliers(db), editing=False)


@bp.route("/products/<int:product_id>")
@login_required
def product_view(product_id):
    db = get_db()
    p = _product_or_404(db, product_id)
    moves = db.execute("SELECT m.*, u.username FROM stock_movements m JOIN users u ON u.user_id = m.user_id "
                       "WHERE m.product_id = ? ORDER BY m.movement_id DESC LIMIT 20", (product_id,)).fetchall()
    return render_template("product_detail.html", p=p, moves=moves)


@bp.route("/products/<int:product_id>/edit", methods=("GET", "POST"))
@login_required
def product_edit(product_id):
    db = get_db()
    p = _product_or_404(db, product_id)
    if request.method == "POST":
        try:
            v = _validate_product(db, request.form, product_id)
            # Quantity is intentionally NOT editable here (only via stock movements).
            db.execute("UPDATE products SET product_code=?, product_name=?, description=?, unit_price=?, "
                       "reorder_level=?, supplier_id=? WHERE product_id=?",
                       (v["product_code"], v["product_name"], v["description"], v["unit_price"],
                        v["reorder_level"], v["supplier_id"], product_id))
            flash("Product updated.", "success")
            return redirect(url_for("catalog.products"))
        except ValidationError as e:
            flash(str(e), "error")
        except sqlite3.IntegrityError:
            flash("Could not save product: product code must be unique.", "error")
    return render_template("product_form.html", product=request.form if request.method == "POST" else p,
                           suppliers=_suppliers(db), editing=True, product_id=product_id)


@bp.route("/products/<int:product_id>/delete", methods=("POST",))
@login_required
def product_delete(product_id):
    db = get_db()
    p = _product_or_404(db, product_id)
    used = db.execute("SELECT (SELECT COUNT(*) FROM stock_movements WHERE product_id = ?) + "
                      "(SELECT COUNT(*) FROM sale_items WHERE product_id = ?) AS n",
                      (product_id, product_id)).fetchone()["n"]
    if used:
        flash(f"Cannot delete '{p['product_name']}': it has stock-movement or sales history.", "error")
        return redirect(url_for("catalog.products"))
    try:
        db.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        flash("Product deleted.", "success")
    except sqlite3.IntegrityError:
        flash("Cannot delete this product because other records reference it.", "error")
    return redirect(url_for("catalog.products"))


# ----------------------------------------------------------------- suppliers
def _validate_supplier(form):
    name = (form.get("supplier_name") or "").strip()
    if not name:
        raise ValidationError("Supplier name is required.")
    if len(name) > 200:
        raise ValidationError("Supplier name must be 200 characters or fewer.")
    email = (form.get("email") or "").strip() or None
    if email and ("@" not in email or " " in email or len(email) > 200):
        raise ValidationError("Email address looks invalid.")
    phone = (form.get("phone") or "").strip() or None
    if phone and len(phone) > 50:
        raise ValidationError("Phone must be 50 characters or fewer.")
    return dict(supplier_name=name, phone=phone, email=email, address=(form.get("address") or "").strip() or None)


def _supplier_or_404(db, supplier_id):
    s = db.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,)).fetchone()
    if s is None:
        abort(404)
    return s


@bp.route("/suppliers")
@login_required
def suppliers():
    rows = get_db().execute(
        "SELECT s.*, (SELECT COUNT(*) FROM products p WHERE p.supplier_id = s.supplier_id) AS product_count "
        "FROM suppliers s ORDER BY s.supplier_name").fetchall()
    return render_template("suppliers.html", suppliers=rows)


@bp.route("/suppliers/new", methods=("GET", "POST"))
@login_required
def supplier_new():
    if request.method == "POST":
        try:
            v = _validate_supplier(request.form)
            get_db().execute("INSERT INTO suppliers (supplier_name, phone, email, address) VALUES (?,?,?,?)",
                             (v["supplier_name"], v["phone"], v["email"], v["address"]))
            flash("Supplier created.", "success")
            return redirect(url_for("catalog.suppliers"))
        except ValidationError as e:
            flash(str(e), "error")
    return render_template("supplier_form.html", supplier=request.form if request.method == "POST" else None,
                           editing=False)


@bp.route("/suppliers/<int:supplier_id>")
@login_required
def supplier_view(supplier_id):
    db = get_db()
    s = _supplier_or_404(db, supplier_id)
    prods = db.execute("SELECT product_id, product_name, quantity FROM products WHERE supplier_id = ? "
                       "ORDER BY product_name", (supplier_id,)).fetchall()
    return render_template("supplier_detail.html", s=s, products=prods)


@bp.route("/suppliers/<int:supplier_id>/edit", methods=("GET", "POST"))
@login_required
def supplier_edit(supplier_id):
    db = get_db()
    s = _supplier_or_404(db, supplier_id)
    if request.method == "POST":
        try:
            v = _validate_supplier(request.form)
            db.execute("UPDATE suppliers SET supplier_name=?, phone=?, email=?, address=? WHERE supplier_id=?",
                       (v["supplier_name"], v["phone"], v["email"], v["address"], supplier_id))
            flash("Supplier updated.", "success")
            return redirect(url_for("catalog.suppliers"))
        except ValidationError as e:
            flash(str(e), "error")
    return render_template("supplier_form.html", supplier=request.form if request.method == "POST" else s,
                           editing=True, supplier_id=supplier_id)


@bp.route("/suppliers/<int:supplier_id>/delete", methods=("POST",))
@login_required
def supplier_delete(supplier_id):
    """Assumption (FR-03): linked products are unassigned (supplier_id -> NULL), atomically."""
    db = get_db()
    s = _supplier_or_404(db, supplier_id)
    db.execute("BEGIN IMMEDIATE")
    try:
        n = db.execute("UPDATE products SET supplier_id = NULL WHERE supplier_id = ?", (supplier_id,)).rowcount
        db.execute("DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    msg = f"Supplier '{s['supplier_name']}' deleted."
    if n:
        msg += f" {n} linked product(s) were left without a supplier."
    flash(msg, "success")
    return redirect(url_for("catalog.suppliers"))
