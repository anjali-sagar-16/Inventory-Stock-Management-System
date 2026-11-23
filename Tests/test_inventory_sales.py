import unittest
from tests.base import AppTestCase


class StockTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login()
        self.pid = self.make_product("Widget", "10.00", "5")

    def move(self, t, q, notes=""):
        return self.post("/stock/new", {"product_id": self.pid, "movement_type": t, "quantity": q, "notes": notes})

    def test_stock_in_increases_and_records(self):
        self.move("IN", "10", "opening")
        self.assertEqual(self.qty(self.pid), 10)
        m = self.q("SELECT movement_type, quantity, notes, user_id FROM stock_movements")[0]
        self.assertEqual((m[0], m[1], m[2]), ("IN", 10, "opening"))
        self.assertIsNotNone(m[3])

    def test_invalid_quantities_leave_stock_unchanged(self):
        self.move("IN", "10")
        for bad in ["0", "-3", "abc", "", "1.5"]:
            self.move("IN", bad); self.move("OUT", bad)
        self.assertEqual(self.qty(self.pid), 10)
        self.assertEqual(self.q("SELECT COUNT(*) FROM stock_movements")[0][0], 1)

    def test_stock_out_decreases(self):
        self.move("IN", "10"); self.move("OUT", "4")
        self.assertEqual(self.qty(self.pid), 6)
        self.assertEqual(self.q("SELECT COUNT(*) FROM stock_movements WHERE movement_type='OUT'")[0][0], 1)

    def test_excessive_out_rejected(self):
        self.move("IN", "10")
        r = self.move("OUT", "11")
        self.assertIn(b"Insufficient stock", r.data)
        self.assertEqual(self.qty(self.pid), 10)
        self.assertEqual(self.q("SELECT COUNT(*) FROM stock_movements")[0][0], 1)

    def test_out_exactly_available_allowed(self):
        self.move("IN", "3"); self.move("OUT", "3")
        self.assertEqual(self.qty(self.pid), 0)

    def test_unknown_product_and_type(self):
        r = self.post("/stock/new", {"product_id": 999, "movement_type": "IN", "quantity": 1})
        self.assertIn(b"not found", r.data)
        r = self.post("/stock/new", {"product_id": self.pid, "movement_type": "XX", "quantity": 1})
        self.assertIn(b"IN or OUT", r.data)

    def test_history_page(self):
        self.move("IN", "2", "hello")
        r = self.client.get("/stock")
        self.assertIn(b"hello", r.data); self.assertIn(b"alice", r.data)


class SaleTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login()
        self.a = self.make_product("A", "10.00", "5", stock=10)
        self.b = self.make_product("B", "2.50", "1", stock=4)

    def sale(self, lines):
        data = {"product_id": [p for p, _ in lines], "quantity": [str(q) for _, q in lines]}
        return self.post("/sales/new", data)

    def test_multi_item_sale_success(self):
        r = self.sale([(self.a, 3), (self.b, 2)])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.qty(self.a), 7); self.assertEqual(self.qty(self.b), 2)
        s = self.q("SELECT sale_id, total_amount FROM sales")
        self.assertEqual(len(s), 1); self.assertAlmostEqual(s[0][1], 35.0)
        items = self.q("SELECT quantity, unit_price, line_total FROM sale_items ORDER BY product_id")
        self.assertEqual([tuple(i) for i in items], [(3, 10.0, 30.0), (2, 2.5, 5.0)])
        mv = self.q("SELECT movement_type, notes FROM stock_movements WHERE notes LIKE 'Sale #%'")
        self.assertEqual(len(mv), 2); self.assertEqual(mv[0][0], "OUT")
        self.assertIn(b"35.00", r.data)

    def test_totals_ignore_browser_submitted_values(self):
        self.post("/sales/new", {"product_id": [self.a], "quantity": ["2"], "total_amount": "0.01", "unit_price": "0.01"})
        self.assertAlmostEqual(self.q("SELECT total_amount FROM sales")[0][0], 20.0)

    def test_insufficient_stock_rolls_back_everything(self):
        r = self.sale([(self.b, 1), (self.a, 11)])  # first line fine, second fails
        self.assertIn(b"Insufficient stock", r.data)
        self.assertEqual(self.qty(self.a), 10); self.assertEqual(self.qty(self.b), 4)
        self.assertEqual(self.q("SELECT COUNT(*) FROM sales")[0][0], 0)
        self.assertEqual(self.q("SELECT COUNT(*) FROM sale_items")[0][0], 0)
        self.assertEqual(self.q("SELECT COUNT(*) FROM stock_movements WHERE notes LIKE 'Sale%'")[0][0], 0)

    def test_duplicate_lines_aggregated(self):
        r = self.sale([(self.a, 6), (self.a, 5)])  # 11 > 10
        self.assertIn(b"Insufficient stock", r.data)
        self.assertEqual(self.qty(self.a), 10)
        self.sale([(self.a, 6), (self.a, 4)])  # exactly 10
        self.assertEqual(self.qty(self.a), 0)
        self.assertEqual(self.q("SELECT quantity FROM sale_items")[0][0], 10)
        self.assertEqual(self.q("SELECT COUNT(*) FROM sale_items")[0][0], 1)

    def test_invalid_lines_rejected(self):
        for lines in [[], [(self.a, 0)], [(self.a, -1)], [(self.a, "x")], [(999, 1)], [("", 1)]]:
            data = {"product_id": [p for p, _ in lines], "quantity": [str(q) for _, q in lines]}
            self.post("/sales/new", data)
        self.assertEqual(self.q("SELECT COUNT(*) FROM sales")[0][0], 0)
        self.assertEqual(self.qty(self.a), 10)

    def test_product_without_price_cannot_be_sold(self):
        pid = self.make_product("NoPrice", price="", stock=5)
        r = self.sale([(pid, 1)])
        self.assertIn(b"no unit price", r.data)
        self.assertEqual(self.qty(pid), 5)

    def test_sale_price_snapshot_survives_price_change(self):
        self.sale([(self.a, 1)])
        self.post(f"/products/{self.a}/edit", {"product_name": "A", "unit_price": "99", "reorder_level": "5"})
        self.assertEqual(self.q("SELECT unit_price FROM sale_items")[0][0], 10.0)

    def test_sale_pages(self):
        self.sale([(self.a, 1)])
        self.assertIn(b"#1", self.client.get("/sales").data)
        self.assertEqual(self.client.get("/sales/1").status_code, 200)
        self.assertEqual(self.client.get("/sales/99").status_code, 404)
        self.assertEqual(self.client.get("/sales/new").status_code, 200)

    def test_db_check_blocks_negative_stock_directly(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE products SET quantity = -1 WHERE product_id = ?", (self.a,))


class DashboardTests(AppTestCase):
    def test_counts_and_low_stock_threshold(self):
        self.login()
        self.post("/suppliers/new", {"supplier_name": "S"})
        low_eq = self.make_product("Equal", reorder="5", stock=5)   # qty == reorder -> low
        low_lt = self.make_product("Below", reorder="5", stock=2)
        ok = self.make_product("Fine", reorder="5", stock=6)         # qty > reorder -> not low
        html = self.client.get("/dashboard").get_data(as_text=True)
        self.assertIn("Equal", html); self.assertIn("Below", html)
        low_section = html.split("Low-stock products</h2>")[1].split("Recent sales")[0]
        self.assertNotIn("Fine", low_section)
        stats = self.q("SELECT (SELECT COUNT(*) FROM products), (SELECT COUNT(*) FROM suppliers), "
                       "(SELECT SUM(quantity) FROM products)")[0]
        self.assertEqual(tuple(stats), (3, 1, 13))
        self.assertIn('<span>13</span>Total units', html)
        self.assertIn('<span>2</span>Low-stock products', html)

    def test_recent_sales_shown(self):
        self.login()
        pid = self.make_product("W", "5", "0", stock=3)
        self.post("/sales/new", {"product_id": [pid], "quantity": ["1"]})
        self.assertIn(b"#1", self.client.get("/dashboard").data)


class DemoScenarioTest(AppTestCase):
    """Section 16 main demonstration scenario, end to end through HTTP."""

    def test_demo(self):
        self.login()
        self.post("/suppliers/new", {"supplier_name": "Acme"})
        sid = self.q("SELECT supplier_id FROM suppliers")[0][0]
        self.post("/products/new", {"product_name": "Notebook", "unit_price": "4.00", "reorder_level": "5",
                                    "supplier_id": sid})
        pid = self.q("SELECT product_id FROM products")[0][0]
        self.assertEqual(self.qty(pid), 0)
        self.post("/stock/new", {"product_id": pid, "movement_type": "IN", "quantity": "10"})
        self.post("/sales/new", {"product_id": [pid], "quantity": ["3"]})
        self.assertEqual(self.qty(pid), 7)
        self.assertAlmostEqual(self.q("SELECT total_amount FROM sales")[0][0], 12.0)
        r = self.post("/sales/new", {"product_id": [pid], "quantity": ["8"]})
        self.assertIn(b"Insufficient stock", r.data)
        self.assertEqual(self.qty(pid), 7)
        self.post("/stock/new", {"product_id": pid, "movement_type": "OUT", "quantity": "2"})
        self.assertEqual(self.qty(pid), 5)
        self.assertIn(b"Notebook", self.client.get("/dashboard").data.split(b"Recent sales")[0])
        self.assertEqual(len(self.q("SELECT * FROM stock_movements")), 3)  # IN 10, sale OUT 3, OUT 2


if __name__ == "__main__":
    unittest.main()
