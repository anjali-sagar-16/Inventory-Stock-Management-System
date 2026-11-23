import unittest
from tests.base import AppTestCase


class AuthTests(AppTestCase):
    def test_login_success_and_access(self):
        r = self.login()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_invalid_password_rejected(self):
        r = self.client.post("/login", data={"username": "alice", "password": "wrong", "csrf_token": self.token()})
        self.assertIn(b"Invalid username or password", r.data)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_unknown_user_rejected(self):
        r = self.client.post("/login", data={"username": "nobody", "password": "x", "csrf_token": self.token()})
        self.assertIn(b"Invalid username or password", r.data)

    def test_inactive_account_rejected(self):
        r = self.client.post("/login", data={"username": "bob", "password": "password123", "csrf_token": self.token()})
        self.assertIn(b"inactive", r.data)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_anonymous_blocked_on_all_protected_routes(self):
        for url in ["/dashboard", "/products", "/products/new", "/suppliers", "/suppliers/new",
                    "/stock", "/stock/new", "/sales", "/sales/new", "/sales/1", "/products/1"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"], url)

    def test_logout_removes_access(self):
        self.login()
        r = self.post("/logout", follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_password_is_hashed(self):
        h = self.q("SELECT password_hash FROM users WHERE username='alice'")[0][0]
        self.assertNotIn("password123", h)

    def test_deactivated_mid_session_loses_access(self):
        self.login()
        self.conn.execute("UPDATE users SET is_active=0 WHERE username='alice'")
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_csrf_missing_or_invalid_rejected(self):
        self.login()
        self.assertEqual(self.client.post("/products/new", data={"product_name": "X"}).status_code, 400)
        self.assertEqual(self.client.post("/products/new", data={"product_name": "X", "csrf_token": "bad"}).status_code, 400)
        self.assertEqual(self.q("SELECT COUNT(*) FROM products")[0][0], 0)
        self.assertEqual(self.client.post("/logout", data={}).status_code, 400)

    def test_open_redirect_blocked(self):
        r = self.client.post("/login?next=//evil.com", data={"username": "alice", "password": "password123",
                                                              "csrf_token": self.token()})
        self.assertNotIn("evil.com", r.headers["Location"])

    def test_not_found_is_safe(self):
        self.login()
        r = self.client.get("/products/999")
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(b"Traceback", r.data)


if __name__ == "__main__":
    unittest.main()
