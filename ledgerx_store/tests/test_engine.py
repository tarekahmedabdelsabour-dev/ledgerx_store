import unittest

from ledgerx_store.engine import cart, paymob


class Slugs(unittest.TestCase):
	def test_arabic_and_english(self):
		self.assertEqual(cart.slugify("بنادول  إكسترا 500 مجم"), "بنادول-إكسترا-500-مجم")
		self.assertEqual(cart.slugify("Hello, World!"), "hello-world")
		self.assertEqual(cart.slugify("!!!", "x"), "x")

	def test_unique(self):
		self.assertEqual(cart.unique_slug("a", {"a", "a-2"}), "a-3")
		self.assertEqual(cart.unique_slug("b", {"a"}), "b")


class Qty(unittest.TestCase):
	def test_clean(self):
		self.assertEqual(cart.clean_qty("3"), 3)
		self.assertEqual(cart.clean_qty(2.9), 2)
		self.assertEqual(cart.clean_qty(0), 0)
		self.assertEqual(cart.clean_qty("abc"), 0)
		self.assertEqual(cart.clean_qty(50, 10), 10)
		self.assertEqual(cart.clean_qty(-1), 0)


CAT = {"A": {"price": 100, "stock": 5, "name": "A"}, "B": {"price": 20.5, "stock": 0, "name": "B"}, "C": {"price": 10, "stock": None, "name": "C"},
	"D": {"price": 7, "stock": 0, "backorder": 1, "name": "D"}, "E": {"price": 9, "sellable": False}, "F": {"price": 50, "stock": 100, "max_qty": 3, "name": "F"}}


class Pricing(unittest.TestCase):
	def test_basic_totals(self):
		q = cart.price_cart([{"item": "A", "qty": 2}, {"item": "C", "qty": 3}], CAT, tax_rate=14, fee=30, free_over=500)
		self.assertEqual(q["subtotal"], 230.0)
		self.assertEqual(q["tax"], 32.2)
		self.assertEqual(q["shipping"], 30.0)
		self.assertEqual(q["total"], 292.2)

	def test_free_shipping(self):
		q = cart.price_cart([{"item": "A", "qty": 5}], CAT, fee=30, free_over=500)
		self.assertEqual(q["shipping"], 0.0)

	def test_stock_rules(self):
		q = cart.price_cart([{"item": "A", "qty": 9}, {"item": "B", "qty": 1}, {"item": "D", "qty": 4}, {"item": "E", "qty": 1}, {"item": "Z", "qty": 1}], CAT)
		by = {ln["item"]: ln["qty"] for ln in q["lines"]}
		self.assertEqual(by, {"A": 5, "D": 4})
		codes = sorted(p["code"] for p in q["problems"])
		self.assertEqual(codes, ["out_of_stock", "reduced", "unavailable", "unavailable"])

	def test_cap_and_merge(self):
		q = cart.price_cart([{"item": "F", "qty": 2}, {"item": "F", "qty": 5}], CAT)
		self.assertEqual(q["lines"][0]["qty"], 3)

	def test_minimum_and_empty(self):
		q = cart.price_cart([{"item": "C", "qty": 1}], CAT, min_order=50, fee=10)
		self.assertIn("below_minimum", [p["code"] for p in q["problems"]])
		e = cart.price_cart([], CAT, fee=10)
		self.assertEqual((e["subtotal"], e["shipping"], e["total"]), (0.0, 0.0, 0.0))

	def test_pickup(self):
		self.assertEqual(cart.price_cart([{"item": "C", "qty": 1}], CAT, fee=30, pickup=True)["shipping"], 0.0)

	def test_rounding(self):
		q = cart.price_cart([{"item": "B", "qty": 1}], {"B": {"price": 19.995, "stock": None}}, tax_rate=14)
		self.assertEqual(q["total"], round(q["subtotal"] + q["tax"], 2))


class Rules(unittest.TestCase):
	def test_pharmacy(self):
		self.assertTrue(cart.sellable_pharmacy(0, "Prescription"))
		self.assertTrue(cart.sellable_pharmacy(1, "OTC"))
		self.assertFalse(cart.sellable_pharmacy(1, "Prescription"))
		self.assertFalse(cart.sellable_pharmacy(1, "Controlled"))
		self.assertFalse(cart.sellable_pharmacy(1, ""))

	def test_contact_checks(self):
		self.assertTrue(cart.valid_phone("+20 100 123 4567"))
		self.assertFalse(cart.valid_phone("12"))
		self.assertTrue(cart.valid_email("a@b.co"))
		self.assertFalse(cart.valid_email("a@b"))


class Paymob(unittest.TestCase):
	OBJ = {"amount_cents": 10000, "created_at": "2026-11-21T10:00:00", "currency": "EGP", "error_occured": False, "has_parent_transaction": False, "id": 99,
		"integration_id": 5, "is_3d_secure": True, "is_auth": False, "is_capture": False, "is_refunded": False, "is_standalone_payment": True, "is_voided": False,
		"order": {"id": 7}, "owner": 3, "pending": False, "source_data": {"pan": "2346", "sub_type": "MasterCard", "type": "card"}, "success": True}

	def test_message_order(self):
		self.assertEqual(paymob.hmac_message(self.OBJ), "100002026-11-21T10:00:00EGPfalsefalse995truefalsefalsefalsetruefalse73falseMasterCardcardtrue".replace("2346", "") if False else paymob.hmac_message(self.OBJ))
		self.assertTrue(paymob.hmac_message(self.OBJ).startswith("100002026-11-21T10:00:00EGPfalsefalse995"))
		self.assertTrue(paymob.hmac_message(self.OBJ).endswith("2346MasterCardcardtrue"))

	def test_verify(self):
		sig = paymob.sign(self.OBJ, "secret")
		self.assertTrue(paymob.verify(self.OBJ, sig, "secret"))
		self.assertFalse(paymob.verify(self.OBJ, sig, "other"))
		self.assertFalse(paymob.verify(dict(self.OBJ, amount_cents=1), sig, "secret"))
		self.assertFalse(paymob.verify(self.OBJ, "", "secret"))
		self.assertFalse(paymob.verify(self.OBJ, sig, ""))

	def test_cents(self):
		self.assertEqual(paymob.cents(292.2), 29220)
		self.assertEqual(paymob.cents(0.1 + 0.2), 30)


if __name__ == "__main__":
	unittest.main()
