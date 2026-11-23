"""Inventory & Stock Management System: Flask app factory, CSRF, CLI."""
import hmac
import logging
import secrets

import click
from flask import Flask, abort, render_template, request, session
from werkzeug.security import generate_password_hash

from config import Config
from database import db as database


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)
    database.init_app(app)

    # ---- CSRF (NFR-02): session token checked on every state-changing request
    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def csrf_protect():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
            expected = session.get("_csrf", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400, "Invalid or missing CSRF token. Reload the page and try again.")

    # ---- Blueprints
    from routes import auth, catalog, inventory, sales, main
    for bp in (auth.bp, main.bp, catalog.bp, inventory.bp, sales.bp):
        app.register_blueprint(bp)

    # ---- Safe error pages (no stack traces / DB internals shown)
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400, message=getattr(e, "description", "Bad request.")), 400

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="The page or record you asked for was not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500, message="Something went wrong. The error has been logged."), 500

    @app.errorhandler(Exception)
    def unexpected(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Unhandled error")
        return server_error(e)

    # ---- CLI
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables (safe to re-run; keeps existing data)."""
        database.init_db()
        click.echo(f"Database ready at {app.config['DATABASE']}")

    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--full-name", prompt="Full name", default="")
    @click.option("--role", type=click.Choice(["admin", "staff"]), default="admin", show_default=True)
    @click.password_option()
    def create_user_command(username, full_name, role, password):
        """Create an application user (no public self-registration)."""
        import sqlite3
        database.init_db()
        username = username.strip()
        if not username or len(password) < 8:
            raise click.ClickException("Username required and password must be at least 8 characters.")
        conn = database._connect(app.config["DATABASE"])
        try:
            conn.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
                         (username, generate_password_hash(password), full_name.strip() or None, role))
        except sqlite3.IntegrityError:
            raise click.ClickException(f"Username '{username}' already exists.")
        finally:
            conn.close()
        click.echo(f"User '{username}' ({role}) created.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Load demo suppliers, products, stock movements and sales (skips if data exists)."""
        import seed_demo
        database.init_db()
        conn = database._connect(app.config["DATABASE"])
        try:
            result = seed_demo.seed(conn)
        finally:
            conn.close()
        if result is None:
            click.echo("Products already exist; demo data not loaded.")
        else:
            click.echo(f"Demo data loaded: {result}. If no user existed, log in as demo / demo12345.")

    if not app.config.get("TESTING") and not app.config.get("SECRET_KEY_FROM_ENV"):
        app.logger.warning("SECRET_KEY not set; using a random per-process key (sessions reset on restart).")
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
