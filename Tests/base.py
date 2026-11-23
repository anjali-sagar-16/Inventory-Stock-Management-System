import os
import re
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from database import db as database


class AppTestCase(unittest.TestCase):
    """Each test gets an isolated temporary database; the real DB is never touched."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app({"TESTING": True, "DATABASE": self.path, "SECRET_KEY": "test"})
        with self.app.app_context():
            database.init_db()
        self.conn = database._connect(self.path)
        self.add_user("alice", "password123")
        self.add_user("bob", "password123", active=0)
        self.client = self.app.test_client()

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    # helpers
    def add_user(self, username, password, active=1, role="staff"):
        self.conn.execute("INSERT INTO users (username, password_hash, role, is_active) VALUES (?,?,?,?)",
                          (username, generate_password_hash(password), role, active))

    def token(self, client=None):
        c = client or self.client
        # Logged-out clients see the login form; logged-in ones are redirected, so
        # fall back to the dashboard (whose logout form carries the token).
        for url in ("/login", "/dashboard"):
            html = c.get(url).get_data(as_text=True)
            m = re.search(r'name="csrf_token" value="([^"]+)"', html)
            if m:
                return m.group(1)
        raise AssertionError("no CSRF token found")

    def login(self, username="alice", password="password123"):
        return self.client.post("/login", data={"username": username, "password": password,
                                                "csrf_token": self.token()})

    def post(self, url, data=None, follow=True):
        data = dict(data or {})
        data["csrf_token"] = self.token()
        return self.client.post(url, data=data, follow_redirects=follow)

    def q(self, sql, args=()):
        return self.conn.execute(sql, args).fetchall()

    def make_product(self, name="Widget", price="10.00", reorder="5", stock=0, code=None):
        self.post("/products/new", {"product_name": name, "unit_price": price, "reorder_level": reorder,
                                    "product_code": code or ""})
        pid = self.q("SELECT product_id FROM products WHERE product_name=?", (name,))[0][0]
        if stock:
            self.post("/stock/new", {"product_id": pid, "movement_type": "IN", "quantity": stock})
        return pid

    def qty(self, pid):
        return self.q("SELECT quantity FROM products WHERE product_id=?", (pid,))[0][0]
