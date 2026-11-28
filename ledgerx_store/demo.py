"""Demo data for the Store app: store settings, categories, web-orderable items with stock and prices, an About page, a news post, a placed order
(cash on delivery, through the app's own orders.place()) and a contact inquiry.

    bench --site mysite.localhost execute ledgerx_store.demo.run

Run ledgerx.demo.foundation first (company, warehouse Cairo Store - LXE). Take a backup first.
Idempotent: every record is looked up by its natural key before it is created. Every step commits on its own and reports its result;
failures are logged in Error Log under titles starting 'Demo store'. Store Settings is filled only where empty.
NO payment gateway: online_gateway stays None and no key, secret or integration ID is written. Only cash on delivery is used.
No shipping fee is set (that would need a shipping income account), so shipping is free.
"""
import frappe
from frappe.utils import add_days, nowdate

from ledgerx.shared import run_each
from ledgerx_store import inquiries, orders

COMPANY, WAREHOUSE, COST_CENTER = "LedgerX Egypt", "Cairo Store - LXE", "Cairo - LXE"
PRICE_LIST = "Store Public EGP"
STOCK_DAYS_BACK = 20
GROUPS = [("Store Electronics", 1), ("Store Office", 2), ("Store Home", 3)]
# code, name, group, price EGP, cost EGP, stock, featured, max per order, summary
ITEMS = [
	("LXW-PHONE", "Nile Smartphone 128 GB", "Store Electronics", 12500, 9800, 40, 1, 3, "6.5 inch display, 128 GB storage, dual SIM, two-year warranty."),
	("LXW-EARBUDS", "Wireless Earbuds Pro", "Store Electronics", 1450, 900, 120, 1, 5, "Bluetooth 5.3, noise cancelling, 24 hours with the case."),
	("LXW-POWERBANK", "Power Bank 20000 mAh", "Store Electronics", 850, 520, 80, 0, 5, "Fast charging, two USB ports and one USB-C."),
	("LXW-DESKLAMP", "LED Desk Lamp", "Store Office", 420, 250, 60, 0, 6, "Three colour temperatures, touch dimmer, USB charging port."),
	("LXW-NOTEBOOK", "A5 Notebook Set (5 pcs)", "Store Office", 190, 110, 200, 1, 10, "Hard cover, 96 ruled pages each."),
	("LXW-KETTLE", "Electric Kettle 1.7 L", "Store Home", 780, 480, 50, 1, 4, "Stainless steel, auto shut-off, boil-dry protection."),
	("LXW-BLENDER", "Kitchen Blender 1000 W", "Store Home", 1650, 1050, 25, 0, 3, "1.5 L glass jar, six blades, three speeds and pulse."),
	("LXW-SOLDOUT", "Limited Edition Coffee Grinder", "Store Home", 990, 640, 0, 0, 2, "Out of stock: shows how the store handles it."),
]
# customer, phone, email, address line, city, [(item, qty)]
ORDERS = [
	("Mostafa Adel Gaber", "01012345678", "mostafa.gaber@example.com", "15 El Tahrir Street, Dokki", "Giza", [("LXW-EARBUDS", 2), ("LXW-NOTEBOOK", 3), ("LXW-KETTLE", 1)]),
]
NOTE = "Demo store order: please call before delivery."
INQUIRY = ("Contact", "Salma Hossam Eldin", "01198765432", "salma.hossam@example.com", "Demo inquiry: do you deliver to Alexandria, and do you offer bulk prices on notebooks for a school?")


def _say(msg):
	print(msg)


def _insert(doc):
	return frappe.get_doc(doc).insert(ignore_permissions=True)


def _ready(_x):
	if not frappe.db.exists("Company", COMPANY) or not frappe.db.exists("Warehouse", WAREHOUSE):
		frappe.throw("Company or warehouse missing. Run ledgerx.demo.foundation first.")


def _price_list(_x):
	if not frappe.db.exists("Price List", PRICE_LIST):
		_insert({"doctype": "Price List", "price_list_name": PRICE_LIST, "currency": "EGP", "selling": 1, "buying": 0, "enabled": 1})


def _settings(_x):
	"""Fill Store Settings only where empty. No gateway, no secrets."""
	s = frappe.get_doc("Store Settings")
	want = {"company": COMPANY, "price_list": PRICE_LIST, "store_name": "LedgerX Online Store", "tagline": "Electronics, office and home essentials delivered across Egypt",
		"hero_title": "Everything you need, delivered to your door", "hero_text": "Order online and pay cash on delivery. Delivery within three working days.",
		"phone": "+20 2 2795 5100", "whatsapp": "+20 100 555 0199", "email": "orders@ledgerx-store.example.com", "address": "12 Road 9, Maadi, Cairo",
		"working_hours": "Daily 10:00 - 22:00", "footer_text": "LedgerX Egypt. Prices include delivery.", "meta_description": "LedgerX online store: electronics, office and home products with cash on delivery.",
		"min_order": 100, "free_shipping_over": 0}
	changed = False
	for k, v in want.items():
		if not s.get(k):
			s.set(k, v)
			changed = True
	if not s.customer_group:
		grp = "Individual" if frappe.db.exists("Customer Group", "Individual") else frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
		s.customer_group, changed = grp, True
	if not s.territory and frappe.db.exists("Territory", "Egypt"):
		s.territory, changed = "Egypt", True
	if not [w for w in s.warehouses or [] if w.warehouse]:
		s.append("warehouses", {"warehouse": WAREHOUSE})
		changed = True
	if changed:
		s.save(ignore_permissions=True)
	frappe.clear_document_cache("Store Settings", "Store Settings")


def _group(spec):
	name, sort = spec
	if not frappe.db.exists("Item Group", name):
		_insert({"doctype": "Item Group", "item_group_name": name, "parent_item_group": "All Item Groups", "is_group": 0, "store_visible": 1, "store_sort": sort})


def _item(code):
	_c, name, group, price, _cost, _q, featured, maxq, summary = next(i for i in ITEMS if i[0] == code)
	if not frappe.db.exists("Item", code):
		_insert({"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "stock_uom": "Nos", "is_stock_item": 1, "is_sales_item": 1, "description": summary,
			"standard_rate": price, "store_publish": 1, "store_featured": featured, "store_summary": summary, "store_max_qty": maxq})
	if not frappe.db.exists("Item Price", {"item_code": code, "price_list": PRICE_LIST, "selling": 1}):
		_insert({"doctype": "Item Price", "item_code": code, "price_list": PRICE_LIST, "selling": 1, "price_list_rate": price, "currency": "EGP"})


def _stock(_x):
	"""Opening stock as one real Material Receipt, dated in the past. The sold-out item gets none."""
	remark = f"Demo store opening stock - {WAREHOUSE}"
	if frappe.db.exists("Stock Entry", {"remarks": remark, "docstatus": 1}):
		return
	account = frappe.db.get_value("Company", COMPANY, "stock_adjustment_account")
	if not account:
		frappe.throw(f"Set the stock adjustment account on {COMPANY}")
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Receipt"
	se.company = COMPANY
	se.posting_date = add_days(nowdate(), -STOCK_DAYS_BACK)
	se.set_posting_time = 1
	se.to_warehouse = WAREHOUSE
	se.remarks = remark
	for code, _n, _g, _p, cost, qty, *_r in ITEMS:
		if qty > 0:
			row = {"item_code": code, "qty": qty, "uom": "Nos", "stock_uom": "Nos", "conversion_factor": 1, "t_warehouse": WAREHOUSE, "basic_rate": cost, "expense_account": account}
			if frappe.db.exists("Cost Center", COST_CENTER):
				row["cost_center"] = COST_CENTER
			se.append("items", row)
	se.insert(ignore_permissions=True)
	se.submit()


def _page(_x):
	if not frappe.db.exists("Store Page", "about-us"):
		_insert({"doctype": "Store Page", "title": "About us", "slug": "about-us", "published": 1, "in_menu": 1, "sort_order": 1,
			"summary": "Who we are and how delivery works.", "body": "<p>We are the online shop of LedgerX Egypt. Order from the catalogue, we call you to confirm, and the courier brings the goods to your door. You pay in cash when you receive them.</p>"})


def _post(_x):
	if not frappe.db.exists("Store Post", "new-office-range"):
		_insert({"doctype": "Store Post", "title": "New office range now online", "slug": "new-office-range", "published": 1, "published_on": add_days(nowdate(), -3),
			"summary": "Notebooks and desk lamps for the new school season.", "body": "<p>Our office range is now available online with cash on delivery across Egypt.</p>"})


def _order(i):
	cust, phone, email, line1, city, lines = ORDERS[int(i)]
	if frappe.db.exists("Sales Order", {"store_order": 1, "store_phone": phone, "store_notes": NOTE, "docstatus": ["<", 2]}):
		return
	orders.place([{"item": c, "qty": q} for c, q in lines], {"name": cust, "phone": phone, "email": email, "notes": NOTE}, {"line1": line1, "city": city, "country": "Egypt"}, "Cash on Delivery")


def _inquiry(_x):
	kind, name, phone, email, msg = INQUIRY
	if frappe.db.exists("Store Inquiry", {"full_name": name, "kind": kind, "message": msg}):
		return
	inquiries.create(kind, name, phone, email, msg)


STEPS = [
	("Readiness check", _ready, [1]),
	("Price list", _price_list, [1]),
	("Categories", _group, GROUPS),
	("Products and prices", _item, [i[0] for i in ITEMS]),
	("Opening stock", _stock, [1]),
	("Settings", _settings, [1]),
	("Pages and news", lambda x: (_page if x == "page" else _post)(x), ["page", "post"]),
	("Orders (cash on delivery)", _order, [str(i) for i in range(len(ORDERS))]),
	("Inquiries", _inquiry, [1]),
]


def run():
	_say("Store demo data")
	failed_any = False
	for label, fn, items in STEPS:
		done, failed = run_each(items, fn, f"Demo store: {label}")
		failed_any = failed_any or bool(failed)
		_say(f"  {label}: {len(done)} ok, {len(failed)} failed")
	if failed_any:
		_say("Some steps failed. Open Error Log (titles start with 'Demo store') and send me the errors.")
	else:
		_say("Done. Open the site home (or /products): products, a cash-on-delivery order and an inquiry are in place; no payment gateway is configured.")
