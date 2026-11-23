import unittest
from tests.base import AppTestCase


class ProductTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_create_list_update_and_zero_quantity(self):
        pid = self.make_product("Pen", "2.50", "3", code="P1")
        self.assertEqual(self.qty(pid), 0)
        self.assertIn(b"Pen", self.client.get("/products").data)
        self.post(f"/products/{pid}/edit", {"product_name": "Pen2", "unit_price": "3", "reorder_level": "4",
                                            "product_code": "P1"})
        row = self.q("SELECT product_name, unit_price, reorder_level FROM products WHERE product_id=?", (pid,))[0]
        self.assertEqual(tuple(row), ("Pen2", 3.0, 4))

    def test_quantity_cannot_be_set_via_form(self):
        self.post("/products/new", {"product_name": "A", "quantity": "99", "reorder_level": "0"})
        self.assertEqual(self.q("SELECT quantity FROM products")[0][0], 0)

    def test_duplicate_code_rejected(self):
        self.make_product("A", code="X1")
        r = self.post("/products/new", {"product_name": "B", "product_code": "X1", "reorder_level": "0"})
        self.assertIn(b"already in use", r.data)
        self.assertEqual(self.q("SELECT COUNT(*) FROM products")[0][0], 1)

    def test_negative_values_and_missing_name_rejected(self):
        for data, msg in [({"product_name": "A", "unit_price": "-1"}, b"cannot be negative"),
                          ({"product_name": "A", "reorder_level": "-1"}, b"Reorder level"),
                          ({"product_name": " "}, b"name is required"),
                          ({"product_name": "A", "unit_price": "abc"}, b"must be a number"),
                          ({"product_name": "A", "unit_price": "nan"}, b"must be a number"),
                          ({"product_name": "A", "supplier_id": "999"}, b"does not exist")]:
            r = self.post("/products/new", data)
            self.assertIn(msg, r.data, data)
        self.assertEqual(self.q("SELECT COUNT(*) FROM products")[0][0], 0)

    def test_delete_blocked_when_history_exists(self):
        pid = self.make_product("A", stock=5)
        r = self.post(f"/products/{pid}/delete")
        self.assertIn(b"Cannot delete", r.data)
        self.assertEqual(self.q("SELECT COUNT(*) FROM products")[0][0], 1)

    def test_delete_unused_product(self):
        pid = self.make_product("A")
        self.post(f"/products/{pid}/delete")
        self.assertEqual(self.q("SELECT COUNT(*) FROM products")[0][0], 0)

    def test_search(self):
        self.make_product("Apple"); self.make_product("Banana")
        r = self.client.get("/products?q=Appl").data
        self.assertIn(b"Apple", r); self.assertNotIn(b"Banana", r)

    def test_html_escaped(self):
        self.make_product("<script>alert(1)</script>")
        self.assertNotIn(b"<script>alert(1)</script>", self.client.get("/products").data)

    def test_sql_injection_string_is_just_data(self):
        self.make_product("A")
        r = self.client.get("/products?q=' OR 1=1; DROP TABLE products;--")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.q("SELECT COUNT(*) FROM products")[0][0], 1)


class SupplierTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def make_supplier(self, name="Acme"):
        self.post("/suppliers/new", {"supplier_name": name, "phone": "123", "email": "a@b.co"})
        return self.q("SELECT supplier_id FROM suppliers WHERE supplier_name=?", (name,))[0][0]

    def test_create_list_update(self):
        sid = self.make_supplier()
        self.assertIn(b"Acme", self.client.get("/suppliers").data)
        self.post(f"/suppliers/{sid}/edit", {"supplier_name": "Acme Ltd"})
        self.assertEqual(self.q("SELECT supplier_name FROM suppliers")[0][0], "Acme Ltd")

    def test_validation(self):
        self.assertIn(b"name is required", self.post("/suppliers/new", {"supplier_name": ""}).data)
        self.assertIn(b"Email", self.post("/suppliers/new", {"supplier_name": "X", "email": "bad"}).data)

    def test_delete_unassigns_products_and_keeps_them_valid(self):
        sid = self.make_supplier()
        self.post("/products/new", {"product_name": "P", "supplier_id": sid, "reorder_level": "0"})
        self.post(f"/suppliers/{sid}/delete")
        self.assertEqual(self.q("SELECT COUNT(*) FROM suppliers")[0][0], 0)
        self.assertIsNone(self.q("SELECT supplier_id FROM products")[0][0])

    def test_foreign_keys_enforced(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO products (product_name, supplier_id) VALUES ('x', 999)")


if __name__ == "__main__":
    unittest.main()
