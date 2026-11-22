"""Turns a priced cart into a customer, an address and a Sales Order; records payments."""
import secrets

import frappe
from frappe import _
from frappe.model import child_table_fields, default_fields
from frappe.utils import add_days, flt, nowdate

from ledgerx_store import data
from ledgerx_store.engine import cart


def quote(lines, pickup=False):
	s = data.settings()
	codes = [ln.get("item") for ln in lines or [] if ln.get("item")]
	cat = data.catalog(codes) if codes else {}
	return cart.price_cart(lines, cat, data.tax_rate(), flt(s.shipping_fee), flt(s.free_shipping_over), flt(s.min_order), pickup), cat


def _customer_for(info, user):
	"""The logged-in user's customer, else one found by email or phone, else a new one."""
	s = data.settings()
	if user and user != "Guest":
		c = _customer_of_user(user)
		if c:
			return c
	email, phone = (info.get("email") or "").strip().lower(), (info.get("phone") or "").strip()
	if email:
		c = frappe.db.sql("select dl.link_name from `tabContact Email` ce join `tabDynamic Link` dl on dl.parent = ce.parent and dl.parenttype = 'Contact' and dl.link_doctype = 'Customer' where lower(ce.email_id) = %s limit 1", email)
		if c:
			return c[0][0]
	if phone:
		c = frappe.db.sql("select dl.link_name from `tabContact Phone` cp join `tabDynamic Link` dl on dl.parent = cp.parent and dl.parenttype = 'Contact' and dl.link_doctype = 'Customer' where cp.phone = %s limit 1", phone)
		if c:
			return c[0][0]
	cust = frappe.get_doc({"doctype": "Customer", "customer_name": info["name"][:140], "customer_type": "Individual", "customer_group": s.customer_group or frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual",
		"territory": s.territory or frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"})
	cust.insert(ignore_permissions=True)
	contact = frappe.get_doc({"doctype": "Contact", "first_name": info["name"][:140], "email_ids": [{"email_id": email, "is_primary": 1}] if email else [], "phone_nos": [{"phone": phone, "is_primary_mobile_no": 1}] if phone else [],
		"links": [{"link_doctype": "Customer", "link_name": cust.name}]})
	if user and user != "Guest":
		contact.user = user
	contact.insert(ignore_permissions=True)
	return cust.name


def _customer_of_user(user):
	found = customers_of_user(user)
	return found[0] if found else None


def customers_of_user(user):
	return [r[0] for r in frappe.db.sql("select dl.link_name from `tabContact` c join `tabDynamic Link` dl on dl.parent = c.name and dl.parenttype = 'Contact' and dl.link_doctype = 'Customer' where c.user = %s", user)]


def _address_for(customer, a, phone):
	if not (a.get("line1") and a.get("city")):
		return None
	same = frappe.db.sql("""select a.name from `tabAddress` a join `tabDynamic Link` dl on dl.parent = a.name and dl.parenttype = 'Address' and dl.link_doctype = 'Customer' and dl.link_name = %s
		where a.address_line1 = %s and a.city = %s and ifnull(a.disabled, 0) = 0 limit 1""", (customer, a["line1"][:140], a["city"][:140]))
	if same:
		return same[0][0]
	addr = frappe.get_doc({"doctype": "Address", "address_title": customer, "address_type": "Shipping", "address_line1": a["line1"][:140], "address_line2": (a.get("line2") or "")[:140],
		"city": a["city"][:140], "state": (a.get("state") or "")[:140], "country": a.get("country") or frappe.db.get_single_value("System Settings", "country") or "Egypt",
		"phone": phone, "links": [{"link_doctype": "Customer", "link_name": customer}]})
	addr.insert(ignore_permissions=True)
	return addr.name


def place(lines, info, address, payment, pickup=False, user=None):
	"""Creates the Sales Order. Raises frappe.ValidationError with a message the customer can read."""
	s = data.settings()
	if not s.enabled:
		frappe.throw(_("The store is closed right now."))
	info = info or {}
	name, phone, email = (info.get("name") or "").strip(), (info.get("phone") or "").strip(), (info.get("email") or "").strip()
	if len(name) < 2:
		frappe.throw(_("Enter your name."))
	if not cart.valid_phone(phone):
		frappe.throw(_("Enter a phone number we can call."))
	if email and not cart.valid_email(email):
		frappe.throw(_("The email address is not valid."))
	if not pickup and not ((address or {}).get("line1") and (address or {}).get("city")):
		frappe.throw(_("Enter the delivery address and the city."))
	allowed = {"Cash on Delivery": s.cod_enabled, "Bank Transfer": s.transfer_enabled, "Online Payment": s.online_gateway not in (None, "", "None")}
	if not allowed.get(payment):
		frappe.throw(_("This payment method is not available."))
	q, cat = quote(lines, pickup)
	if not q["lines"]:
		frappe.throw(_("Your cart is empty or its items are no longer available."))
	blocking = [p for p in q["problems"] if p.get("code") in ("out_of_stock", "unavailable", "reduced", "below_minimum")]
	if blocking:
		frappe.throw(_("Some items changed since you added them. Review your cart and try again."))
	if flt(s.shipping_fee) and not s.shipping_account:
		frappe.throw(_("The store is not ready to take orders: set the shipping account."))
	customer = _customer_for({"name": name, "phone": phone, "email": email}, user)
	addr = None if pickup else _address_for(customer, address, phone)
	so = frappe.new_doc("Sales Order")
	so.update({"company": s.company, "customer": customer, "transaction_date": nowdate(), "delivery_date": add_days(nowdate(), s.delivery_days or 3), "selling_price_list": s.price_list,
		"shipping_address_name": addr, "customer_address": addr, "order_type": "Sales", "store_order": 1, "store_payment_method": payment, "store_payment_status": "Pending" if payment == "Online Payment" else "Unpaid",
		"store_phone": phone, "store_notes": (info.get("notes") or "")[:500], "store_key": secrets.token_hex(12), "po_no": ""})
	for ln in q["lines"]:
		item = frappe.db.get_value("Item", ln["item"], ["item_name", "stock_uom"], as_dict=True)
		so.append("items", {"item_code": ln["item"], "qty": ln["qty"], "uom": item.stock_uom, "rate": ln["price"], "price_list_rate": ln["price"], "delivery_date": so.delivery_date, "warehouse": (data.warehouses() or [None])[0]})
	if s.sales_taxes_template:
		# Added here, not left to the order's own validation: that step skips the template once any tax row (the shipping row below) exists.
		so.taxes_and_charges = s.sales_taxes_template
		for row in _template_taxes(s.sales_taxes_template):
			so.append("taxes", row)
	so.run_method("set_missing_values")
	if q["shipping"]:
		so.append("taxes", {"charge_type": "Actual", "account_head": s.shipping_account, "description": "Shipping", "tax_amount": q["shipping"]})
	so.run_method("calculate_taxes_and_totals")
	so.flags.ignore_permissions = True
	so.insert()
	if s.auto_submit_orders:
		so.submit()
	_tell_staff(so)
	return so


def _template_taxes(template):
	rows = []
	for t in frappe.get_cached_doc("Sales Taxes and Charges Template", template).get("taxes"):
		d = t.as_dict()
		for k in default_fields + child_table_fields:
			d.pop(k, None)
		rows.append(d)
	return rows


def _tell_staff(so):
	s = data.settings()
	role = s.notify_role or "Store Manager"
	users = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent")
	for u in {x for x in users if x not in ("Administrator", "Guest") and frappe.db.get_value("User", x, "enabled")}:
		try:
			frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "reference_type": "Sales Order", "reference_name": so.name, "date": nowdate(),
				"description": _("New online order {0} from {1}: {2}").format(so.name, so.customer_name, frappe.format(so.grand_total, {"fieldtype": "Currency"})), "priority": "Medium"}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Store: order notice")


def can_view(so_name, key=None, user=None):
	row = frappe.db.get_value("Sales Order", so_name, ["store_key", "customer", "store_order"], as_dict=True)
	if not row or not row.store_order:
		return False
	if key and row.store_key and secrets.compare_digest(str(key), str(row.store_key)):
		return True
	return bool(user and user != "Guest" and row.customer in customers_of_user(user))


def record_payment(so_name, mode_of_payment, reference=None, amount=None):
	"""Payment Entry against the order, then marks it paid. Safe to call twice.
	Runs as Administrator: the gateway callback has no login, and the accounting helpers check the caller's rights."""
	with data.as_admin():
		return _record_payment(so_name, mode_of_payment, reference, amount)


def _record_payment(so_name, mode_of_payment, reference, amount):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	so = frappe.get_doc("Sales Order", so_name)
	if so.docstatus != 1:
		frappe.throw(_("Submit the order first."))
	if so.store_payment_status == "Paid":
		return None
	try:
		pe = get_payment_entry("Sales Order", so.name, party_amount=flt(amount) or None)
	except AttributeError:
		frappe.throw(_("Set a default bank or cash account on the company before recording payments."))
	pe.mode_of_payment = mode_of_payment
	account = frappe.db.get_value("Mode of Payment Account", {"parent": mode_of_payment, "company": so.company}, "default_account")
	if account and account != pe.paid_to and frappe.db.get_value("Account", account, "account_currency") == pe.paid_to_account_currency:
		pe.paid_to = account
		pe.paid_to_account_type = frappe.db.get_value("Account", account, "account_type")
	pe.reference_no = reference or so.name
	pe.reference_date = nowdate()
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.submit()
	frappe.db.set_value("Sales Order", so.name, {"store_payment_status": "Paid", "store_payment_ref": reference or ""}, update_modified=False)
	return pe.name
