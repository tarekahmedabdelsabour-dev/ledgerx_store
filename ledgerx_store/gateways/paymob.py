"""Paymob Accept: start a card payment and read its callback. Written from Paymob's public documentation; not run against a real account."""
import frappe
from frappe import _
from frappe.utils import flt

from ledgerx_store.engine import paymob as eng

BASE = "https://accept.paymob.com/api"


def _post(path, body):
	import requests

	r = requests.post(BASE + path, json=body, timeout=30)
	try:
		data = r.json()
	except ValueError:
		data = {}
	if r.status_code >= 400:
		frappe.throw(_("The payment gateway did not accept the request ({0}).").format(r.status_code))
	return data


def start(so, info, address):
	"""-> iframe url for the customer. Stores the gateway order id on the Sales Order."""
	from ledgerx_store import data

	s = data.settings()
	key = s.get_password("paymob_api_key", raise_exception=False)
	if not (key and s.paymob_integration_id and s.paymob_iframe_id):
		frappe.throw(_("Online payment is not set up yet."))
	token = _post("/auth/tokens", {"api_key": key})["token"]
	cents = eng.cents(so.grand_total)
	order = _post("/ecommerce/orders", {"auth_token": token, "delivery_needed": False, "amount_cents": cents, "currency": so.currency,
		"merchant_order_id": f"{so.name}-{frappe.generate_hash(length=4)}", "items": []})
	pay = _post("/acceptance/payment_keys", {"auth_token": token, "amount_cents": cents, "expiration": 3600, "order_id": order["id"], "currency": so.currency,
		"integration_id": int(s.paymob_integration_id), "billing_data": eng.billing(info.get("name"), info.get("email"), info.get("phone"), address)})
	frappe.db.set_value("Sales Order", so.name, "store_payment_ref", f"paymob-order:{order['id']}", update_modified=False)
	return eng.iframe_url(s.paymob_iframe_id, pay["token"])


def handle_callback(payload, received_hmac):
	"""Returns the Sales Order name that was marked paid, or None. Raises PermissionError on a bad signature."""
	from ledgerx_store import data, orders

	s = data.settings()
	secret = s.get_password("paymob_hmac_secret", raise_exception=False)
	obj = (payload or {}).get("obj") or {}
	if not eng.verify(obj, received_hmac, secret):
		raise frappe.PermissionError
	order_id = str((obj.get("order") or {}).get("id") or "")
	so_name = frappe.db.get_value("Sales Order", {"store_payment_ref": f"paymob-order:{order_id}"}, "name")
	if not so_name:
		return None
	paid_cents = obj.get("amount_cents") or 0
	so = frappe.get_doc("Sales Order", so_name)
	if so.store_payment_status == "Paid":
		return None
	if obj.get("success") and not obj.get("pending") and not obj.get("is_voided") and not obj.get("is_refunded"):
		if abs(paid_cents - eng.cents(so.grand_total)) > 1:
			frappe.db.set_value("Sales Order", so_name, "store_payment_status", "Failed", update_modified=False)
			frappe.log_error(title=f"Store: Paymob amount mismatch on {so_name}", message=str(obj))
			return None
		orders.record_payment(so_name, s.online_mode_of_payment, f"paymob:{obj.get('id')}", flt(so.grand_total))
		return so_name
	frappe.db.set_value("Sales Order", so_name, "store_payment_status", "Failed", update_modified=False)
	return None
