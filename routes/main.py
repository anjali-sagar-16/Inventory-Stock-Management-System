"""FR-09 / FR-10 Dashboard and low-stock."""
from flask import Blueprint, redirect, render_template, url_for

from database.db import get_db
from routes.auth import login_required

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    stats = db.execute(
        "SELECT (SELECT COUNT(*) FROM products) AS products, "
        "(SELECT COUNT(*) FROM suppliers) AS suppliers, "
        "(SELECT COALESCE(SUM(quantity), 0) FROM products) AS units").fetchone()
    low = db.execute("SELECT product_id, product_code, product_name, quantity, reorder_level "
                     "FROM products WHERE quantity <= reorder_level ORDER BY quantity, product_name").fetchall()
    recent = db.execute("SELECT s.sale_id, s.sale_date, s.total_amount, u.username "
                        "FROM sales s JOIN users u ON u.user_id = s.user_id "
                        "ORDER BY s.sale_id DESC LIMIT 5").fetchall()
    levels = db.execute("SELECT product_id, product_name, quantity, reorder_level FROM products "
                        "ORDER BY (quantity * 1.0 / MAX(reorder_level, 1)), product_name LIMIT 10").fetchall()
    return render_template("dashboard.html", stats=stats, low=low, recent=recent, levels=levels)
