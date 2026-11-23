"""FR-01 Authentication."""
from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db

bp = Blueprint("auth", __name__)

# Used to keep response time similar when the username does not exist.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = None
    if uid is not None:
        user = get_db().execute(
            "SELECT user_id, username, full_name, role FROM users WHERE user_id = ? AND is_active = 1",
            (uid,)).fetchone()
        if user is None:
            session.pop("user_id", None)  # deleted/deactivated mid-session
        g.user = user


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        ok = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, password)
        if user is None or not ok:
            flash("Invalid username or password.", "error")
        elif not user["is_active"]:
            flash("This account is inactive. Contact an administrator.", "error")
        else:
            csrf = session.get("_csrf")
            session.clear()  # prevent session fixation
            if csrf:
                session["_csrf"] = csrf
            session["user_id"] = user["user_id"]
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("main.dashboard"))
    elif g.user is not None:
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
