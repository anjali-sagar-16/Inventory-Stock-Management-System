"""FR-06 / FR-07 / FR-08 Sales."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database.db import get_db
from routes.auth import login_required
from services import ValidationError, create_sale

bp = Blueprint("sales", __name__)


@bp.route("/sales")
@login_required
def sales_list():
    rows = get_db().execute(
        "SELECT s.sale_id, s.sale_date, s.total_amount, u.username, "
        "(SELECT COUNT(*) FROM sale_items i WHERE i.sale_id = s.sale_id) AS item_count "
        "FROM sales s JOIN users u ON u.user_id = s.user_id ORDER BY s.sale_id DESC LIMIT 200").fetchall()
    return render_template("sales.html", sales=rows)


@bp.route("/sales/new", methods=("GET", "POST"))
@login_required
def sale_new():
    db = get_db()
    submitted = []
    if request.method == "POST":
        pids = request.form.getlist("product_id")
        qtys = request.form.getlist("quantity")
        submitted = list(zip(pids, qtys))
        try:
            sale_id = create_sale(db, g.user["user_id"], submitted)
            flash("Sale recorded and stock deducted.", "success")
            return redirect(url_for("sales.sale_detail", sale_id=sale_id))
        except ValidationError as e:
            flash(str(e), "error")
    products = db.execute("SELECT product_id, product_name, product_code, unit_price, quantity FROM products "
                          "ORDER BY product_name").fetchall()
    return render_template("sale_form.html", products=products, submitted=submitted)


@bp.route("/sales/<int:sale_id>")
@login_required
def sale_detail(sale_id):
    db = get_db()
    sale = db.execute("SELECT s.*, u.username FROM sales s JOIN users u ON u.user_id = s.user_id "
                      "WHERE s.sale_id = ?", (sale_id,)).fetchone()
    if sale is None:
        abort(404)
    items = db.execute("SELECT i.*, p.product_name, p.product_code FROM sale_items i "
                       "JOIN products p ON p.product_id = i.product_id WHERE i.sale_id = ? "
                       "ORDER BY i.sale_item_id", (sale_id,)).fetchall()
    return render_template("sale_detail.html", sale=sale, items=items)
