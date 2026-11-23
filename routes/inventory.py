"""FR-04 Stock-In, FR-05 Stock-Out, movement history."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, g

from database.db import get_db
from routes.auth import login_required
from services import ValidationError, parse_int, record_movement

bp = Blueprint("inventory", __name__)


@bp.route("/stock")
@login_required
def movements():
    product_id = request.args.get("product_id", type=int)
    sql = ("SELECT m.*, p.product_name, p.product_code, u.username FROM stock_movements m "
           "JOIN products p ON p.product_id = m.product_id JOIN users u ON u.user_id = m.user_id")
    args = ()
    if product_id:
        sql += " WHERE m.product_id = ?"
        args = (product_id,)
    rows = get_db().execute(sql + " ORDER BY m.movement_id DESC LIMIT 500", args).fetchall()
    return render_template("stock_movements.html", movements=rows, product_id=product_id)


@bp.route("/stock/new", methods=("GET", "POST"))
@login_required
def movement_new():
    db = get_db()
    form = request.form if request.method == "POST" else request.args
    if request.method == "POST":
        try:
            pid = parse_int(form.get("product_id"), "Product", 1)
            new_qty = record_movement(db, pid, g.user["user_id"], (form.get("movement_type") or "").upper(),
                                      form.get("quantity"), form.get("notes"))
            flash(f"Stock {form.get('movement_type').upper()} recorded. New quantity: {new_qty}.", "success")
            return redirect(url_for("inventory.movements"))
        except ValidationError as e:
            flash(str(e), "error")
    products = db.execute("SELECT product_id, product_name, product_code, quantity FROM products "
                          "ORDER BY product_name").fetchall()
    return render_template("stock_movement_form.html", products=products, form=form)
